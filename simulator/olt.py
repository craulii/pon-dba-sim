"""
Modelo OLT (Optical Line Terminal) — ITU-T G.984.

La OLT genera un BWmap cada 125 μs (una trama GTC), recibe los DBRu
de las ONUs y ejecuta el algoritmo DBA para calcular la siguiente asignación.
No hace polling individual — el BWmap es broadcast y los reportes llegan
embebidos en el tráfico upstream.
"""
from typing import Dict, List
from .engine import (SimEngine, EVT_OLT_BWMAP, EVT_ONU_RECV_BWMAP,
                     EVT_OLT_RECV_DATA, EVT_OLT_RECV_REPORT)


BYTES_PER_FRAME = 19_440   # 1.24416 Gbps × 125 μs / 8 bits = 19,440 bytes


class OLT:

    def __init__(self, engine: SimEngine, num_onus: int,
                 dba_algorithm, config: dict, metrics_collector):
        self.engine   = engine
        self.num_onus = num_onus
        self.dba      = dba_algorithm
        self.config   = config
        self.metrics  = metrics_collector

        gpon_cfg          = config["gpon"]
        self.frame_dur    = gpon_cfg["frame_duration_s"]       # 125 μs
        self.prop_delay   = (gpon_cfg["fiber_length_km"] *
                             gpon_cfg["prop_delay_s_per_km"])  # 100 μs para 20 km
        self.capacity     = gpon_cfg["bytes_per_frame"]        # 19,440 bytes

        # Estado DBA: último DBRu recibido de cada ONU
        # Inicializado con colas vacías para el primer BWmap
        self._onu_reports: Dict[int, Dict] = {
            i: {"onu_id": i, "queue_bytes": {1: 0, 2: 0, 4: 0}}
            for i in range(num_onus)
        }
        self._frame_number = 0

        # Arrancar ciclo de BWmap
        engine.schedule(0.0, EVT_OLT_BWMAP)

    # ------------------------------------------------------------------
    # Handlers de eventos
    # ------------------------------------------------------------------

    def on_generate_bwmap(self, evt) -> None:
        """
        Cada 125 μs: ejecuta DBA con los últimos reportes disponibles
        y envía el BWmap a todas las ONUs.
        """
        self._frame_number += 1

        bwmap = self.dba.allocate(
            onu_reports          = self._onu_reports,
            total_capacity_bytes = self.capacity,
            num_onus             = self.num_onus,
            config               = self.config,
        )

        # Calcular utilización de esta trama
        used = sum(
            sum(grants.values())
            for grants in bwmap.values()
        )
        self.metrics.record_frame_utilization(
            self.engine.now, used, self.capacity
        )

        # Enviar BWmap a cada ONU (delay de propagación downstream)
        for onu_id, allocation in bwmap.items():
            self.engine.schedule(
                delay      = self.prop_delay,
                event_type = EVT_ONU_RECV_BWMAP,
                data       = {"onu_id": onu_id, "allocation": allocation},
            )

        # Programar siguiente trama GTC
        self.engine.schedule(self.frame_dur, EVT_OLT_BWMAP)

    def on_receive_data(self, evt) -> None:
        """Recibe burst upstream de una ONU. Mide latencia y throughput."""
        d       = evt.data
        latency = self.engine.now - d["creation_time"]

        self.metrics.record_delivery(
            onu_id     = d["onu_id"],
            tcont_type = d["tcont_type"],
            pkt_size   = d["size"],
            latency_s  = latency,
            sim_time   = self.engine.now,
        )

    def on_receive_report(self, evt) -> None:
        """Recibe DBRu de una ONU. Actualiza estado para el próximo DBA."""
        report = evt.data
        onu_id = report["onu_id"]
        self._onu_reports[onu_id] = report
