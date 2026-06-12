"""
IPACT — Interleaved Polling with Adaptive Cycle Time (Kramer et al. 2002,
EPON IEEE 802.3ah). Adaptado aquí para XG-PON solo con fines comparativos
(Fase 3): la OLT recorre las ONUs en round-robin, sondeando una a la vez,
y el ciclo completo dura `sum(grant_time_i + guard_time)` -- variable,
a diferencia de la trama fija de 125us de SR-DBA/GIANT/QoSDBA.

Servicio "limited": grant_total = min(demanda_total_reportada, B_max).

Sub-asignación intra-ONU: misma prioridad T1 > T2 > T4 que QoSDBA, para
aislar el efecto de "cómo se determina el ancho de banda/timing por ONU"
(la variable que realmente difiere entre IPACT/GIANT/QoSDBA) del efecto de
"cómo se prioriza intra-ONU" (constante, ya evaluado con QoSDBA).

Nota de interfaz: a diferencia de BasicDBA/QoSDBA/GiantDBA (allocate() por
trama, para todas las ONUs a la vez), IpactDBA expone allocate_onu() -- se
llama una vez por poll, para UNA sola ONU. IpactDBA solo se usa con
OLTPolling (simulator/olt_ipact.py), nunca con OLT.
"""
from typing import Dict


class IpactDBA:

    def allocate_onu(self, onu_id: int, report: Dict,
                      b_max_bytes: int, config: Dict) -> Dict[int, int]:
        """
        Parámetros:
          onu_id: id de la ONU sondeada en este poll
          report: {"onu_id":.., "queue_bytes": {tcont_type: bytes}} (último
                   reporte conocido de esta ONU, puede tener hasta ~1 ciclo
                   de antigüedad)
          b_max_bytes: ventana máxima de transmisión por poll ("limited
                       service")
          config: no usado directamente aquí (incluido por consistencia de
                  interfaz)

        Retorna:
          {tcont_type: bytes_granted}, con sum(valores) <= b_max_bytes
        """
        queue = report.get("queue_bytes", {1: 0, 2: 0, 4: 0})
        total_demand = sum(queue.values())

        # Servicio "limited": grant total = min(demanda, B_max)
        grant_total = min(total_demand, b_max_bytes)

        result = {1: 0, 2: 0, 4: 0}
        remaining = grant_total

        # Prioridad T1 > T2 > T4 (igual que QoSDBA, para aislar la variable
        # "timing/bw por ONU" del "orden intra-ONU")
        for tc in (1, 2, 4):
            demand = queue.get(tc, 0)
            grant  = min(demand, remaining)
            result[tc] = grant
            remaining -= grant

        return result
