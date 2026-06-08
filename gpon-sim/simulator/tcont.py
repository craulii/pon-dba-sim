"""
T-CONT (Transmission Container) — ITU-T G.984.3.
Cada ONU tiene uno o más T-CONTs. Cada T-CONT tiene su propio buffer
y generador de tráfico independiente.
"""
from collections import deque
from typing import List, Dict, Any


class Packet:
    __slots__ = ("onu_id", "tcont_type", "size", "creation_time")

    def __init__(self, onu_id: int, tcont_type: int, size: int, creation_time: float):
        self.onu_id        = onu_id
        self.tcont_type    = tcont_type
        self.size          = size          # bytes
        self.creation_time = creation_time # segundos de simulación


class TCont:
    """
    Buffer FIFO para un tipo de T-CONT en una ONU.

    T-CONT 1 (Fixed):        CBR, pre-reservado en BWmap sin importar el reporte.
    T-CONT 2 (Assured):      Garantía mínima, demand-based.
    T-CONT 4 (Best effort):  Solo lo que sobra, demand-based.
    """

    def __init__(self, onu_id: int, tcont_type: int,
                 buffer_size_bytes: int, traffic_gen):
        self.onu_id           = onu_id
        self.tcont_type       = tcont_type
        self.buffer_size      = buffer_size_bytes
        self.traffic_gen      = traffic_gen

        self._buffer: deque   = deque()
        self.current_bytes    = 0

        # Contadores de métricas
        self.pkts_generated   = 0
        self.pkts_dropped     = 0
        self.bytes_generated  = 0
        self.bytes_dropped    = 0

    # ------------------------------------------------------------------

    def enqueue(self, pkt: Packet) -> bool:
        """
        Intenta encolar un paquete.
        Retorna True si fue descartado (buffer overflow).
        """
        self.pkts_generated  += 1
        self.bytes_generated += pkt.size

        if self.current_bytes + pkt.size > self.buffer_size:
            self.pkts_dropped  += 1
            self.bytes_dropped += pkt.size
            return True   # dropped

        self._buffer.append(pkt)
        self.current_bytes += pkt.size
        return False

    def dequeue(self, granted_bytes: int) -> List[Packet]:
        """
        Extrae paquetes hasta agotar granted_bytes.
        Si granted_bytes > 0, se envía al menos el primer paquete aunque supere
        levemente el grant (comportamiento estándar en schedulers reales de GPON:
        el último paquete de un burst puede exceder el límite en hasta un paquete).
        """
        if granted_bytes <= 0 or not self._buffer:
            return []

        sent = []
        remaining = granted_bytes

        # Primer paquete: siempre se envía si hay grant (min 1 pkt)
        first_pkt = self._buffer.popleft()
        self.current_bytes -= first_pkt.size
        remaining          -= first_pkt.size
        sent.append(first_pkt)

        # Paquetes adicionales: solo si caben completamente
        while self._buffer and remaining > 0:
            pkt = self._buffer[0]
            if pkt.size > remaining:
                break
            self._buffer.popleft()
            self.current_bytes -= pkt.size
            remaining          -= pkt.size
            sent.append(pkt)

        return sent

    def queue_bytes(self) -> int:
        return self.current_bytes

    def report(self) -> Dict[str, Any]:
        return {
            "tcont_type":    self.tcont_type,
            "queue_bytes":   self.current_bytes,
        }
