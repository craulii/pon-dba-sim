"""
Modelo ONU (Optical Network Unit) — ITU-T G.984.

Cada ONU tiene T-CONTs independientes con sus propios buffers y generadores.
Al recibir el BWmap, transmite según la asignación y envía el DBRu embebido.
"""
from typing import Dict, List
from .engine import (SimEngine, EVT_ONU_GEN_TRAFFIC, EVT_ONU_RECV_BWMAP,
                     EVT_OLT_RECV_DATA, EVT_OLT_RECV_REPORT)
from .tcont import TCont, Packet
from .traffic import CBRTrafficGen, PoissonTrafficGen, ParetoTrafficGen


UPSTREAM_RATE_BPS = 1_244_160_000   # 1.244 Gbps upstream ITU-T G.984.2


def _make_traffic_gen(tcont_type: int, tcfg: dict):
    kind = tcfg.get("traffic", "poisson")
    rate = tcfg.get("rate_bps", 1_000_000)
    pkt  = tcfg.get("pkt_size", 160)
    if kind == "cbr":
        return CBRTrafficGen(rate, pkt)
    elif kind == "pareto":
        return ParetoTrafficGen(rate, pkt, alpha=tcfg.get("pareto_alpha", 1.5))
    else:
        return PoissonTrafficGen(rate, pkt)


class ONU:

    def __init__(self, onu_id: int, engine: SimEngine,
                 config: dict, metrics_collector):
        self.onu_id  = onu_id
        self.engine  = engine
        self.metrics = metrics_collector

        gpon_cfg = config["gpon"]
        self.prop_delay = (gpon_cfg["fiber_length_km"] *
                           gpon_cfg["prop_delay_s_per_km"])   # 20 km × 5 μs/km = 100 μs

        # Construir T-CONTs según configuración
        self.tconts: Dict[int, TCont] = {}
        for tc_str, tcfg in config.get("tconts", {}).items():
            tc_type = int(tc_str)
            gen     = _make_traffic_gen(tc_type, tcfg)
            tcont   = TCont(
                onu_id           = onu_id,
                tcont_type       = tc_type,
                buffer_size_bytes= tcfg.get("buffer_bytes", 1_000_000),
                traffic_gen      = gen,
            )
            self.tconts[tc_type] = tcont

        # Arrancar generadores de tráfico con offset por onu_id (evita sincronización)
        offset = onu_id * 1e-4
        for tc_type, tcont in self.tconts.items():
            first_interval = tcont.traffic_gen.next_interval()
            self.engine.schedule(
                delay      = offset + first_interval,
                event_type = EVT_ONU_GEN_TRAFFIC,
                data       = {"onu_id": onu_id, "tcont_type": tc_type},
            )

    # ------------------------------------------------------------------
    # Handlers de eventos
    # ------------------------------------------------------------------

    def on_generate_traffic(self, evt) -> None:
        """Genera un paquete y lo encola en el T-CONT correspondiente."""
        d = evt.data
        if d["onu_id"] != self.onu_id:
            return

        tc_type = d["tcont_type"]
        tcont   = self.tconts.get(tc_type)
        if tcont is None:
            return

        pkt = Packet(
            onu_id       = self.onu_id,
            tcont_type   = tc_type,
            size         = tcont.traffic_gen.next_pkt_size(),
            creation_time= self.engine.now,
        )
        tcont.enqueue(pkt)  # drop interno si buffer lleno

        # Self-scheduling: programar próximo paquete
        self.engine.schedule(
            delay      = tcont.traffic_gen.next_interval(),
            event_type = EVT_ONU_GEN_TRAFFIC,
            data       = {"onu_id": self.onu_id, "tcont_type": tc_type},
        )

    def on_receive_bwmap(self, evt) -> None:
        """
        Recibe el BWmap de la OLT.
        Transmite paquetes según la asignación y envía DBRu embebido.
        """
        d = evt.data
        if d["onu_id"] != self.onu_id:
            return

        allocation: Dict[int, int] = d["allocation"]  # {tcont_type: bytes_granted}

        total_tx_bytes = 0
        tx_time_acc    = 0.0

        for tc_type, granted_bytes in allocation.items():
            tcont = self.tconts.get(tc_type)
            if tcont is None or granted_bytes <= 0:
                continue

            pkts = tcont.dequeue(granted_bytes)
            for pkt in pkts:
                tx_time   = (pkt.size * 8) / UPSTREAM_RATE_BPS
                arrive_at = (self.engine.now
                             + tx_time_acc
                             + tx_time
                             + self.prop_delay)
                self.engine.schedule_at(
                    time       = arrive_at,
                    event_type = EVT_OLT_RECV_DATA,
                    data       = {
                        "onu_id":       self.onu_id,
                        "tcont_type":   tc_type,
                        "size":         pkt.size,
                        "creation_time":pkt.creation_time,
                    },
                )
                tx_time_acc    += tx_time
                total_tx_bytes += pkt.size

        # DBRu embebido: enviar reporte con estado actual de buffers
        # En GPON real va en el header del upstream burst (ITU-T G.984.3 Section 9.3.2)
        queue_report = {tc: t.queue_bytes() for tc, t in self.tconts.items()}
        self.engine.schedule(
            delay      = self.prop_delay,
            event_type = EVT_OLT_RECV_REPORT,
            data       = {
                "onu_id":      self.onu_id,
                "queue_bytes": queue_report,
            },
        )

    # ------------------------------------------------------------------
    # Acceso a contadores de drops (para métricas finales)
    # ------------------------------------------------------------------

    def get_drop_stats(self) -> Dict:
        result = {}
        for tc_type, tcont in self.tconts.items():
            result[tc_type] = {
                "pkts_generated":  tcont.pkts_generated,
                "pkts_dropped":    tcont.pkts_dropped,
                "bytes_generated": tcont.bytes_generated,
                "bytes_dropped":   tcont.bytes_dropped,
                "loss_rate":       (tcont.pkts_dropped / tcont.pkts_generated
                                    if tcont.pkts_generated > 0 else 0.0),
            }
        return result
