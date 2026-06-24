"""
Visualiza como genera trafico cada T-CONT: CBR (T1), Poisson (T2), Pareto (T4).
No corre el simulador completo -- instancia los generadores de
simulator/traffic.py directamente y dibuja los arribos resultantes.

Las 3 tasas se normalizan a la misma media (1 paquete/ms) solo para esta
figura, asi la comparacion visual es sobre la FORMA de la distribucion
(determinista vs exponencial vs cola pesada), no sobre la tasa -- las tasas
reales usadas en la simulacion (configs/default.json) difieren en varios
ordenes de magnitud entre T-CONTs y no se verian comparables en un mismo eje.
"""
import os
import random
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from simulator.traffic import CBRTrafficGen, PoissonTrafficGen, ParetoTrafficGen

FIGURES_DIR = os.path.join(os.path.dirname(__file__), "..", "figures")

MEAN_INTERVAL_S = 0.001  # 1 ms, comun a los 3 generadores solo para esta figura

GENS = [
    ("T-CONT 1 (VoIP) -- CBR",     CBRTrafficGen(rate_bps=160 * 8 / MEAN_INTERVAL_S, pkt_size=160),     "#1f77b4"),
    ("T-CONT 2 (Video) -- Poisson", PoissonTrafficGen(rate_bps=1000 * 8 / MEAN_INTERVAL_S, pkt_size=1000), "#2ca02c"),
    ("T-CONT 4 (Best Effort) -- Pareto (alpha=1.5)", ParetoTrafficGen(rate_bps=1400 * 8 / MEAN_INTERVAL_S, pkt_size=1400, alpha=1.5), "#d62728"),
]

WINDOW_S = 0.05   # ventana de 50 ms para el raster de arribos
N_SAMPLES = 3000  # muestras para el histograma de inter-arribos


def arrival_times(gen, window_s):
    t = 0.0
    times = []
    while t < window_s:
        t += gen.next_interval()
        if t < window_s:
            times.append(t)
    return times


def inter_arrivals(gen, n):
    return [gen.next_interval() for _ in range(n)]


def main():
    random.seed(6767)
    plt.rcParams.update({"font.family": "serif", "font.size": 11, "axes.grid": True, "grid.alpha": 0.3})

    fig, axes = plt.subplots(3, 2, figsize=(12, 7.5))
    fig.suptitle("Como simula el trafico cada T-CONT (tasas normalizadas a la misma media = 1 ms, solo para esta figura)",
                 fontsize=12)

    for row, (label, gen, color) in enumerate(GENS):
        # --- Columna izquierda: raster de arribos en una ventana de tiempo ---
        ax = axes[row, 0]
        times = arrival_times(gen, WINDOW_S)
        ax.eventplot([t * 1000 for t in times], colors=color, lineoffsets=0, linelengths=0.8)
        ax.set_xlim(0, WINDOW_S * 1000)
        ax.set_yticks([])
        ax.set_ylabel(label, fontsize=9, rotation=0, ha="right", va="center")
        if row == 2:
            ax.set_xlabel("Tiempo (ms)")
        if row == 0:
            ax.set_title(f"Arribos de paquetes en una ventana de {WINDOW_S*1000:.0f} ms\n(cada marca = 1 paquete generado)")

        # --- Columna derecha: histograma de inter-arribos ---
        ax2 = axes[row, 1]
        intervals_ms = [x * 1000 for x in inter_arrivals(gen, N_SAMPLES)]
        if row == 0:
            # CBR: intervalo constante -- un histograma queda degenerado (1 sola barra
            # infinitamente angosta), se grafica como spike explicito en su lugar.
            ax2.axvline(intervals_ms[0], color=color, linewidth=4)
            ax2.set_xlim(0, 2)
            ax2.text(intervals_ms[0] + 0.05, 0.5, "determinístico:\nsiempre 1.00 ms",
                      fontsize=8, va="center")
            ax2.set_yticks([])
        else:
            ax2.hist(intervals_ms, bins=50, color=color, alpha=0.8)
            ax2.axvline(MEAN_INTERVAL_S * 1000, color="black", linestyle="--", linewidth=1, label="media = 1 ms")
            ax2.set_xlim(0, np.percentile(intervals_ms, 99))
            ax2.legend(fontsize=8)
        if row == 2:
            ax2.set_xlabel("Intervalo entre paquetes (ms)")
        if row == 0:
            ax2.set_title(f"Distribucion del intervalo entre paquetes\n({N_SAMPLES} muestras)")

    fig.tight_layout(rect=[0.05, 0, 1, 0.94])
    os.makedirs(FIGURES_DIR, exist_ok=True)
    out_path = os.path.join(FIGURES_DIR, "traffic_generation.png")
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Guardado: {out_path}")


if __name__ == "__main__":
    main()
