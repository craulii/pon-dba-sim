"""
Recolector de métricas por ONU × T-CONT.
Almacena series temporales en memoria y exporta a CSV al final.
"""
import csv
import os
import statistics
from collections import defaultdict
from typing import Dict, List, Optional


class MetricsCollector:

    def __init__(self, warmup_s: float = 1.0,
                 sla_bounds_s: Optional[Dict[int, float]] = None):
        self.warmup_s = warmup_s
        # {tcont_type: max_delay_s} -- Fase 3, cotas SLA por tipo de T-CONT
        self.sla_bounds_s: Dict = sla_bounds_s or {}
        # {(onu_id, tcont_type): [latencia_s, ...]}
        self._latencies:    Dict = defaultdict(list)
        self._jitters:      Dict = defaultdict(list)
        self._last_latency: Dict = {}              # para calcular jitter
        # {(onu_id, tcont_type): bytes}
        self._bytes_delivered: Dict = defaultdict(int)
        # utilización por trama: [(time, utilized_bytes), ...]
        self._frame_util: List = []
        # ciclos de polling (Fase 3, IPACT): [(time, cycle_time_s), ...]
        self._cycle_times: List = []

    # ------------------------------------------------------------------
    # Registro en tiempo de ejecución
    # ------------------------------------------------------------------

    def record_delivery(self, onu_id: int, tcont_type: int,
                        pkt_size: int, latency_s: float, sim_time: float) -> None:
        if sim_time < self.warmup_s:
            return
        key = (onu_id, tcont_type)
        self._latencies[key].append(latency_s)
        self._bytes_delivered[key] += pkt_size

        # Jitter = |latencia_actual - latencia_anterior|
        if key in self._last_latency:
            jitter = abs(latency_s - self._last_latency[key])
            self._jitters[key].append(jitter)
        self._last_latency[key] = latency_s

    def record_frame_utilization(self, sim_time: float,
                                  used_bytes: int, capacity_bytes: int) -> None:
        if sim_time < self.warmup_s:
            return
        util = used_bytes / capacity_bytes if capacity_bytes > 0 else 0.0
        self._frame_util.append((sim_time, util))

    def record_cycle_time(self, sim_time: float, cycle_time_s: float) -> None:
        """Fase 3 (IPACT): registra la duración de un ciclo de polling completo."""
        if sim_time < self.warmup_s:
            return
        self._cycle_times.append((sim_time, cycle_time_s))

    # ------------------------------------------------------------------
    # Cálculo de estadísticas al final
    # ------------------------------------------------------------------

    def _percentile(self, data: List[float], p: float) -> float:
        if not data:
            return 0.0
        sorted_data = sorted(data)
        idx = int(len(sorted_data) * p / 100)
        idx = min(idx, len(sorted_data) - 1)
        return sorted_data[idx]

    def summary(self, sim_duration_s: float) -> Dict:
        """Retorna dict con todas las métricas calculadas."""
        result = {}
        effective_duration = sim_duration_s - self.warmup_s

        all_keys = set(self._latencies.keys()) | set(self._bytes_delivered.keys())

        for key in all_keys:
            onu_id, tcont_type = key
            lats  = self._latencies.get(key, [])
            jits  = self._jitters.get(key, [])
            bdel  = self._bytes_delivered.get(key, 0)

            sla_bound = self.sla_bounds_s.get(tcont_type)
            if lats and sla_bound is not None:
                n_compliant = sum(1 for l in lats if l <= sla_bound)
                sla_pct = 100.0 * n_compliant / len(lats)
            else:
                sla_pct = None

            result[key] = {
                "onu_id":         onu_id,
                "tcont_type":     tcont_type,
                "n_packets":      len(lats),
                "latency_mean_us":   statistics.mean(lats) * 1e6     if lats else 0.0,
                "latency_p95_us":    self._percentile(lats, 95) * 1e6 if lats else 0.0,
                "latency_p99_us":    self._percentile(lats, 99) * 1e6 if lats else 0.0,
                "latency_max_us":    max(lats) * 1e6                 if lats else 0.0,
                "jitter_mean_us":    statistics.mean(jits) * 1e6     if jits else 0.0,
                "throughput_mbps":   (bdel * 8 / effective_duration / 1e6)
                                      if effective_duration > 0 else 0.0,
                "sla_bound_us":      (sla_bound * 1e6) if sla_bound is not None else None,
                "sla_compliance_pct": sla_pct,
            }

        # Utilización media del canal
        if self._frame_util:
            utils = [u for _, u in self._frame_util]
            result["channel_utilization"] = statistics.mean(utils)
        else:
            result["channel_utilization"] = 0.0

        # Estadísticas de duración de ciclo (Fase 3, IPACT)
        if self._cycle_times:
            cts = [c for _, c in self._cycle_times]
            result["cycle_time_mean_us"] = statistics.mean(cts) * 1e6
            result["cycle_time_p99_us"]  = self._percentile(cts, 99) * 1e6
            result["cycle_time_min_us"]  = min(cts) * 1e6
            result["cycle_time_max_us"]  = max(cts) * 1e6
            result["cycle_time_samples"] = cts
        else:
            result["cycle_time_mean_us"] = 0.0
            result["cycle_time_p99_us"]  = 0.0
            result["cycle_time_min_us"]  = 0.0
            result["cycle_time_max_us"]  = 0.0
            result["cycle_time_samples"] = []

        return result

    def export_csv(self, filepath: str, extra_fields: Optional[Dict] = None) -> None:
        """Exporta métricas por (onu_id, tcont_type) a CSV."""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        rows = []
        for key, lats in self._latencies.items():
            onu_id, tcont_type = key
            jits  = self._jitters.get(key, [])
            bdel  = self._bytes_delivered.get(key, 0)

            sla_bound = self.sla_bounds_s.get(tcont_type)
            max_lat   = max(lats) * 1e6 if lats else 0.0
            sla_pct   = (100.0 * sum(1 for l in lats if l <= sla_bound) / len(lats)
                          if (lats and sla_bound is not None) else "")

            for i, lat in enumerate(lats):
                row = {
                    "onu_id":      onu_id,
                    "tcont_type":  tcont_type,
                    "latency_s":   lat,
                    "jitter_s":    jits[i - 1] if i > 0 and i - 1 < len(jits) else "",
                    "bytes_delivered": bdel,
                    "latency_max_us":     max_lat,
                    "sla_bound_us":       (sla_bound * 1e6) if sla_bound is not None else "",
                    "sla_compliance_pct": sla_pct,
                }
                if extra_fields:
                    row.update(extra_fields)
                rows.append(row)

        if not rows:
            return

        with open(filepath, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
