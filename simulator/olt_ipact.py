"""
OLT en modo polling IPACT (Fase 3 -- comparación XG-PON).

A diferencia de OLT (timer fijo de 125us, BWmap broadcast a todas las
ONUs), OLTPolling recorre las ONUs en round-robin secuencial: para cada
ONU calcula un grant ("limited service": min(demanda, B_max)) a partir del
último reporte conocido, le envía un GATE individual, y agenda el siguiente
poll `grant_time + guard_time` después -- sin esperar la respuesta de la
ONU (igual que SR-DBA usa reportes con ~RTT de antigüedad). El ciclo
completo (recorrer las 8 ONUs y volver a la ONU 0) tiene duración VARIABLE:

    cycle_time = sum_{i=0..N-1} (grant_time_i + guard_time)

Ciclo mínimo (colas vacías) = N * guard_time.
Ciclo máximo (saturación, grant_i = B_max) = N * (B_max*8/upstream_rate + guard_time).

Con B_max=38880 bytes (=1 trama XGPON de 125us) y N=8, guard_time=1us:
ciclo máximo = 8*(125+1)us = 1.008ms.
"""
from typing import Dict
from .engine import (SimEngine, EVT_OLT_SEND_GATE, EVT_ONU_RECV_GATE,
                      EVT_OLT_POLL_NEXT, EVT_OLT_RECV_DATA,
                      EVT_OLT_RECV_REPORT)


class OLTPolling:

    def __init__(self, engine: SimEngine, num_onus: int,
                 dba_algorithm, config: dict, metrics_collector):
        self.engine   = engine
        self.num_onus = num_onus
        self.dba      = dba_algorithm           # IpactDBA
        self.config   = config
        self.metrics  = metrics_collector

        gpon_cfg = config["gpon"]
        self.prop_delay = (gpon_cfg["fiber_length_km"] *
                           gpon_cfg["prop_delay_s_per_km"])  # 100us para 20km

        ipact_cfg = config.get("ipact", {})
        self.b_max      = ipact_cfg.get("b_max_bytes", 38880)
        self.guard_time = ipact_cfg.get("guard_time_s", 1e-6)
        self.upstream_rate_bps = gpon_cfg["upstream_rate_bps"]

        # Último reporte conocido de cada ONU (misma estructura que OLT)
        self._onu_reports: Dict[int, Dict] = {
            i: {"onu_id": i, "queue_bytes": {1: 0, 2: 0, 4: 0}}
            for i in range(num_onus)
        }

        # Estado de polling round-robin
        self._poll_ptr        = 0     # próximo ONU a sondear (0..num_onus-1)
        self._cycle_start     = 0.0   # tiempo de inicio del ciclo actual
        self._cycle_count     = 0
        self._cycle_used_bytes = 0    # bytes otorgados en el ciclo en curso

        # Arrancar: GATE a ONU 0 en t=0
        engine.schedule(0.0, EVT_OLT_SEND_GATE, {"onu_id": 0})

    # ------------------------------------------------------------------
    # Handlers de eventos
    # ------------------------------------------------------------------

    def on_send_gate(self, evt) -> None:
        """OLT decide el grant para onu_id (según último reporte) y
        envía el GATE (tras prop_delay)."""
        onu_id = evt.data["onu_id"]
        report = self._onu_reports[onu_id]

        allocation = self.dba.allocate_onu(
            onu_id      = onu_id,
            report      = report,
            b_max_bytes = self.b_max,
            config      = self.config,
        )  # {tcont_type: bytes_granted}, sum <= b_max

        granted_total = sum(allocation.values())
        grant_time    = (granted_total * 8) / self.upstream_rate_bps

        # Nuevo ciclo cada vez que volvemos a la ONU 0
        if onu_id == 0:
            now = self.engine.now
            if self._cycle_count > 0:
                cycle_time = now - self._cycle_start
                self.metrics.record_cycle_time(now, cycle_time)
                self.metrics.record_frame_utilization(
                    now, self._cycle_used_bytes, self.b_max * self.num_onus)
            self._cycle_start = now
            self._cycle_count += 1
            self._cycle_used_bytes = 0

        self._cycle_used_bytes += granted_total

        # Enviar GATE a la ONU (delay de propagación downstream)
        self.engine.schedule(
            delay      = self.prop_delay,
            event_type = EVT_ONU_RECV_GATE,
            data       = {"onu_id": onu_id, "allocation": allocation},
        )

        # Programar el siguiente poll: el reloj de ciclo del OLT avanza en
        # grant_time + guard_time (no espera la respuesta de esta ONU --
        # el siguiente grant usará el último reporte disponible, igual que
        # SR-DBA usa reportes con ~RTT de antigüedad).
        self.engine.schedule(
            delay      = grant_time + self.guard_time,
            event_type = EVT_OLT_POLL_NEXT,
            data       = {},
        )

    def on_poll_next(self, evt) -> None:
        """Avanza el puntero round-robin y dispara el GATE del siguiente ONU."""
        self._poll_ptr = (self._poll_ptr + 1) % self.num_onus
        self.engine.schedule(0.0, EVT_OLT_SEND_GATE, {"onu_id": self._poll_ptr})

    def on_receive_data(self, evt) -> None:
        """Idéntico a OLT.on_receive_data."""
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
        """Idéntico a OLT.on_receive_report."""
        report = evt.data
        self._onu_reports[report["onu_id"]] = report
