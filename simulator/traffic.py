"""
Generadores de tráfico por tipo de T-CONT.
Cada generador produce inter-arrivals según la distribución correcta para su clase.
"""
import random
import math


class CBRTrafficGen:
    """
    T-CONT 1 — Fixed bandwidth (CBR).
    VoIP G.711: paquetes de 160 bytes cada 20 ms → 64 kbps.
    Inter-arrival determinístico: pkt_size*8 / rate_bps.
    """
    def __init__(self, rate_bps: float, pkt_size: int = 160):
        self.rate_bps  = rate_bps
        self.pkt_size  = pkt_size
        self.interval  = (pkt_size * 8) / rate_bps   # segundos entre paquetes

    def next_interval(self) -> float:
        return self.interval

    def next_pkt_size(self) -> int:
        return self.pkt_size


class PoissonTrafficGen:
    """
    T-CONT 2 — Assured bandwidth.
    Proceso de Poisson (inter-arrival exponencial).
    Video streaming: paquetes ~1000 bytes, tasa media garantizada.
    """
    def __init__(self, rate_bps: float, pkt_size: int = 1000):
        self.rate_bps     = rate_bps
        self.pkt_size     = pkt_size
        self.mean_interval = (pkt_size * 8) / rate_bps

    def next_interval(self) -> float:
        return random.expovariate(1.0 / self.mean_interval)

    def next_pkt_size(self) -> int:
        return self.pkt_size


class ParetoTrafficGen:
    """
    T-CONT 4 — Best effort.
    Distribución Pareto de cola pesada (α=1.5) para capturar self-similarity
    del tráfico de datos masivos (descargas, web, P2P).
    Fórmula idéntica a la validada en el simulador OMNeT++ previo.
    """
    def __init__(self, rate_bps: float, pkt_size: int = 1400, alpha: float = 1.5):
        self.rate_bps  = rate_bps
        self.pkt_size  = pkt_size
        self.alpha     = alpha
        # xm: mínimo de Pareto tal que E[X] = mean_interval
        self._mean = (pkt_size * 8) / rate_bps
        self._xm   = self._mean / (alpha / (alpha - 1))

    def next_interval(self) -> float:
        u = random.uniform(0.001, 0.999)
        return self._xm * math.pow(u, -1.0 / self.alpha)

    def next_pkt_size(self) -> int:
        return self.pkt_size
