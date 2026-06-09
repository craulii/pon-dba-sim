"""
DBA con QoS — algoritmo propio de prioridades inspirado en la jerarquía
de T-CONTs de GPON. ITU-T G.984.3 define los tipos de T-CONT y el mecanismo
SR-DBA, pero no especifica un algoritmo de asignación obligatorio.

Orden de asignación implementado:
  1. T-CONT 1 (Fixed):   pre-reservado, NO demand-based. Siempre asignado.
  2. T-CONT 2 (Assured): garantía mínima, demand-based.
  3. T-CONT 4 (Best effort): lo que sobra, proporcional a demanda.

Esto garantiza latencia constante para T-CONT 1 (VoIP/TDM)
independientemente de la carga de best-effort.
"""
from typing import Dict


class QoSDBA:

    def allocate(self,
                 onu_reports: Dict[int, Dict],
                 total_capacity_bytes: int,
                 num_onus: int,
                 config: Dict) -> Dict[int, Dict[int, int]]:
        """
        Parámetros:
          onu_reports: {onu_id: {"queue_bytes": {tcont_type: bytes}}}
          total_capacity_bytes: bytes disponibles en esta trama upstream
          num_onus: número de ONUs activas
          config: debe contener config["tconts"]["1"]["fixed_bytes_per_frame"]
                  y config["tconts"]["2"]["assured_bytes_per_frame"]

        Retorna:
          bwmap: {onu_id: {tcont_type: bytes_granted}}
        """
        bwmap: Dict[int, Dict[int, int]] = {
            onu_id: {1: 0, 2: 0, 4: 0} for onu_id in onu_reports
        }

        # Overhead de guard bands: 32 bytes por ONU activa (ITU-T G.984.3 Section 8.2)
        guard_overhead = 32 * num_onus
        remaining = max(0, total_capacity_bytes - guard_overhead)

        t1_cfg = config.get("tconts", {}).get("1", {})
        t2_cfg = config.get("tconts", {}).get("2", {})

        fixed_bytes_per_onu    = t1_cfg.get("fixed_bytes_per_frame", 16)
        assured_bytes_per_onu  = t2_cfg.get("assured_bytes_per_frame", 78)

        # ------------------------------------------------------------------
        # Paso 1 — T-CONT 1 (Fixed, CBR): pre-reservado siempre.
        # La OLT asigna fixed_bytes_per_onu a cada ONU sin consultar el reporte.
        # Referencia: ITU-T G.984.3 Section 9.2.1
        # ------------------------------------------------------------------
        for onu_id in onu_reports:
            grant = min(fixed_bytes_per_onu, remaining)
            bwmap[onu_id][1] = grant
            remaining        -= grant

        # ------------------------------------------------------------------
        # Paso 2 — T-CONT 2 (Assured): garantía mínima demand-based.
        # Se concede hasta assured_bytes_per_onu, limitado por lo disponible.
        # ------------------------------------------------------------------
        for onu_id, report in onu_reports.items():
            demand = report["queue_bytes"].get(2, 0)
            fair_share = remaining // max(num_onus, 1)
            grant  = min(demand, assured_bytes_per_onu, fair_share, remaining)
            grant  = max(0, grant)
            bwmap[onu_id][2]  = grant
            remaining        -= grant

        # ------------------------------------------------------------------
        # Paso 3 — T-CONT 4 (Best effort): lo que sobra, proporcional.
        # ------------------------------------------------------------------
        be_demands = {
            onu_id: report["queue_bytes"].get(4, 0)
            for onu_id, report in onu_reports.items()
        }
        total_be_demand = sum(be_demands.values())

        if remaining > 0 and total_be_demand > 0:
            for onu_id, demand in be_demands.items():
                grant = int(remaining * demand / total_be_demand)
                grant = min(grant, demand)
                bwmap[onu_id][4] = grant
        # Si remaining=0 o no hay demanda BE, todos quedan en 0

        return bwmap
