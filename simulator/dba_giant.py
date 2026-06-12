"""
GIANT — Guaranteed + Surplus, alineado a ITU-T (Fase 3, comparación XG-PON).

GIANT divide la asignación de cada trama en dos fases:

  - GPA (Guaranteed Phase Allocation): T-CONT1 (Fixed, pre-reservado cada
    trama, igual que QoSDBA) + T-CONT2 (Assured, mediante un contador SImax
    de "service interval": cuando llega a 0 la ONU es elegible para un grant
    "catch-up" de hasta assured_bytes_per_frame * SImax bytes, luego el
    contador se reinicia a SImax).

  - SPA (Surplus Phase Allocation): T-CONT4 (Non-assured/best-effort), con
    un contador SImin análogo. Las ONUs elegibles (contador==0 y demanda>0)
    se sirven round-robin con lo que sobra de GPA.

Encaja en la arquitectura existente: misma firma allocate() que QoSDBA, una
instancia de GiantDBA se crea una vez por corrida (igual que QoSDBA()), por
lo que los contadores SI persisten como estado de instancia entre tramas.

Simplificaciones declaradas:
  - GIANT real opera por T-CONT (varios T-CONTs del mismo tipo por ONU);
    aquí cada ONU tiene exactamente un T-CONT de cada tipo 1/2/4, así que
    por-ONU == por-T-CONT.
  - El tamaño "catch-up" (assured_bytes_per_frame * SImax) es la
    interpretación propia del equipo de la semántica SImax de GIANT.
  - Los contadores T-CONT2 (_t2_counter) se inicializan escalonados
    (onu_id % SImax) para que, en régimen estable, solo una ONU sea
    elegible por trama (evita que las 8 ONUs compitan simultáneamente por
    `remaining` cada SImax tramas, lo que sesgaría a las ONUs de índice
    bajo por orden de iteración).
  - El puntero round-robin de SPA (_spa_rr_ptr) avanza solo hasta la última
    ONU efectivamente servida (no hasta el final del conjunto elegible),
    para que ONUs no servidas por falta de `remaining` queden primeras en
    la siguiente trama (evita postergación perpetua bajo sobrecarga
    sostenida).
"""
from typing import Dict


class GiantDBA:

    def __init__(self):
        self._initialized = False
        self._t2_counter: Dict[int, int] = {}   # onu_id -> tramas hasta próximo grant GPA T2
        self._t4_counter: Dict[int, int] = {}   # onu_id -> tramas hasta elegibilidad SPA T4
        self._spa_rr_ptr: int = 0               # puntero round-robin de SPA
        self._si_max: int = 8
        self._si_min: int = 32

    def _ensure_init(self, onu_reports: Dict[int, Dict], config: Dict) -> None:
        if self._initialized:
            return
        giant_cfg = config.get("giant", {})
        self._si_max = giant_cfg.get("si_max_frames", {}).get("2", 8)
        self._si_min = giant_cfg.get("si_min_frames", {}).get("4", 32)
        for onu_id in onu_reports:
            # Escalonado: en régimen estable, una sola ONU elegible por trama
            self._t2_counter[onu_id] = onu_id % max(self._si_max, 1)
            self._t4_counter[onu_id] = 0
        self._initialized = True

    def allocate(self,
                 onu_reports: Dict[int, Dict],
                 total_capacity_bytes: int,
                 num_onus: int,
                 config: Dict) -> Dict[int, Dict[int, int]]:
        self._ensure_init(onu_reports, config)

        bwmap: Dict[int, Dict[int, int]] = {
            onu_id: {1: 0, 2: 0, 4: 0} for onu_id in onu_reports
        }

        # Overhead de guard bands: 32 bytes por ONU activa (ITU-T G.984.3 Section 8.2)
        guard_overhead = 32 * num_onus
        remaining = max(0, total_capacity_bytes - guard_overhead)

        t1_cfg = config.get("tconts", {}).get("1", {})
        t2_cfg = config.get("tconts", {}).get("2", {})

        fixed_bytes_per_onu   = t1_cfg.get("fixed_bytes_per_frame", 160)
        assured_bytes_per_onu = t2_cfg.get("assured_bytes_per_frame", 1000)

        # ------------------------------------------------------------------
        # GPA paso 1 — T-CONT1 (Fixed): pre-reservado siempre, igual QoSDBA.
        # ------------------------------------------------------------------
        for onu_id in onu_reports:
            grant = min(fixed_bytes_per_onu, remaining)
            bwmap[onu_id][1] = grant
            remaining -= grant

        # ------------------------------------------------------------------
        # GPA paso 2 — T-CONT2 (Assured): contadores SImax escalonados.
        # Cuando el contador llega a 0, grant "catch-up" de hasta
        # assured_bytes_per_onu * SImax, luego se reinicia el contador.
        # ------------------------------------------------------------------
        for onu_id, report in onu_reports.items():
            demand = report["queue_bytes"].get(2, 0)
            if self._t2_counter[onu_id] == 0:
                cap   = assured_bytes_per_onu * self._si_max
                grant = max(0, min(demand, cap, remaining))
                bwmap[onu_id][2] = grant
                remaining -= grant
                self._t2_counter[onu_id] = self._si_max
            else:
                self._t2_counter[onu_id] -= 1

        # ------------------------------------------------------------------
        # SPA — T-CONT4 (Non-assured/Best effort): contadores SImin +
        # round-robin sobre las ONUs elegibles (contador==0 y demanda>0).
        # ------------------------------------------------------------------
        onu_ids = sorted(onu_reports.keys())
        n = len(onu_ids)
        eligible = []
        for onu_id in onu_ids:
            demand4 = onu_reports[onu_id]["queue_bytes"].get(4, 0)
            if self._t4_counter[onu_id] == 0:
                if demand4 > 0:
                    eligible.append(onu_id)
                else:
                    self._t4_counter[onu_id] = self._si_min  # inactivo -> reset
            else:
                self._t4_counter[onu_id] -= 1

        last_serviced = None
        if eligible and remaining > 0:
            ordered = sorted(eligible, key=lambda x: (x - self._spa_rr_ptr) % n)
            for onu_id in ordered:
                if remaining <= 0:
                    break
                demand4 = onu_reports[onu_id]["queue_bytes"].get(4, 0)
                grant = min(demand4, remaining)
                bwmap[onu_id][4] = grant
                remaining -= grant
                if grant >= demand4:
                    # cola drenada -> espera SImin tramas antes de volver a competir
                    self._t4_counter[onu_id] = self._si_min
                # si grant < demand4 (sigue congestionada), counter queda en 0
                # -> elegible de nuevo la próxima trama (round-robin continuo
                # bajo sobrecarga sostenida; evita "tramas muertas" SImin)
                last_serviced = onu_id

        if last_serviced is not None:
            self._spa_rr_ptr = (last_serviced + 1) % n

        return bwmap
