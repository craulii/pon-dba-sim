"""
Motor de simulación de eventos discretos (DES).
Cola de eventos implementada con heap mínimo (heapq).
"""
import heapq
from dataclasses import dataclass, field
from typing import Any, Callable, Dict


# Tipos de eventos del simulador GPON
EVT_OLT_BWMAP        = "OLT_GENERATE_BWMAP"    # OLT genera BWmap cada 125 μs
EVT_ONU_RECV_BWMAP   = "ONU_RECEIVE_BWMAP"     # ONU recibe BWmap (tras delay propagación)
EVT_ONU_GEN_TRAFFIC  = "ONU_GENERATE_TRAFFIC"  # generador de paquetes (self-scheduling)
EVT_OLT_RECV_DATA    = "OLT_RECEIVE_DATA"       # OLT recibe burst upstream de ONU
EVT_OLT_RECV_REPORT  = "OLT_RECEIVE_REPORT"    # OLT recibe DBRu de ONU


@dataclass(order=True)
class Event:
    time: float
    seq: int                              # desempate determinístico
    event_type: str  = field(compare=False)
    data: Any        = field(compare=False, default=None)


class SimEngine:
    """
    Motor DES minimalista: heap de eventos + tabla de handlers.
    No depende de ningún framework externo.
    """

    def __init__(self):
        self._heap: list         = []
        self._seq:  int          = 0
        self._now:  float        = 0.0
        self._handlers: Dict[str, Callable] = {}

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    @property
    def now(self) -> float:
        return self._now

    def schedule(self, delay: float, event_type: str, data: Any = None) -> None:
        """Programa un evento en now+delay segundos."""
        t = self._now + delay
        evt = Event(time=t, seq=self._seq, event_type=event_type, data=data)
        heapq.heappush(self._heap, evt)
        self._seq += 1

    def schedule_at(self, time: float, event_type: str, data: Any = None) -> None:
        """Programa un evento en un tiempo absoluto."""
        evt = Event(time=time, seq=self._seq, event_type=event_type, data=data)
        heapq.heappush(self._heap, evt)
        self._seq += 1

    def register(self, event_type: str, handler: Callable) -> None:
        self._handlers[event_type] = handler

    def run(self, until: float) -> int:
        """Ejecuta el loop principal hasta 'until'. Retorna eventos procesados."""
        processed = 0
        while self._heap:
            evt = self._heap[0]
            if evt.time > until:
                break
            heapq.heappop(self._heap)
            self._now = evt.time
            handler = self._handlers.get(evt.event_type)
            if handler:
                handler(evt)
            processed += 1
        return processed
