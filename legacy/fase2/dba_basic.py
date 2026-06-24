"""
DBA Básico — proporcional sin diferenciación de T-CONT.
Equivalente conceptual a IPACT pero para GPON centralizado:
todos los T-CONTs compiten igual por el ancho de banda disponible.
"""
from typing import Dict


class BasicDBA:
    """
    Reparte el ancho de banda de la trama proporcional a la demanda total
    de cada ONU, sin considerar el tipo de T-CONT.

    Bajo carga alta, T-CONT 1 (VoIP) compite en igualdad con T-CONT 4
    (best effort), lo que degrada su latencia.
    """

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
          config: configuración de T-CONTs (fijo, asegurado, etc.)

        Retorna:
          bwmap: {onu_id: {tcont_type: bytes_granted}}
        """
        bwmap: Dict[int, Dict[int, int]] = {}

        # Restar guard bands igual que QosDBA (ITU-T G.984.3 §8.2: 32 bytes/ONU)
        guard_overhead = 32 * num_onus
        effective_capacity = max(0, total_capacity_bytes - guard_overhead)

        # Demanda total de cada ONU (suma de todos sus T-CONTs)
        onu_demand = {}
        for onu_id, report in onu_reports.items():
            onu_demand[onu_id] = sum(report["queue_bytes"].values())

        total_demand = sum(onu_demand.values())

        for onu_id, report in onu_reports.items():
            bwmap[onu_id] = {}
            demand = onu_demand[onu_id]

            if total_demand > 0:
                # Proporción de la capacidad efectiva (sin guard bands)
                share = int(effective_capacity * demand / total_demand)
                share = min(share, demand)
            else:
                share = effective_capacity // max(num_onus, 1)

            # Repartir share entre T-CONTs proporcionalmente a sus colas
            onu_total = sum(report["queue_bytes"].values())
            for tcont_type, qbytes in report["queue_bytes"].items():
                if onu_total > 0 and share > 0:
                    bwmap[onu_id][tcont_type] = int(share * qbytes / onu_total)
                else:
                    bwmap[onu_id][tcont_type] = 0

        return bwmap
