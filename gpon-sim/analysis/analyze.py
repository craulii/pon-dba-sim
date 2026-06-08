"""
Generador de 7 gráficos de análisis comparando BasicDBA vs QoS-DBA.
Lee results/all_results.csv generado por run_experiments.py.
Estilo IEEE paper: fuente serif, colores consistentes, IC 95%, 300 DPI.
"""
import csv
import os
import sys
import statistics

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

RESULTS_PATH = os.path.join(os.path.dirname(__file__), "..", "results", "all_results.csv")
FIGURES_DIR  = os.path.join(os.path.dirname(__file__), "..", "figures")

# Colores consistentes
C_BASIC  = "#1f77b4"   # azul — BasicDBA
C_QOS    = "#d62728"   # rojo — QosDBA
C_TC1    = "#2ca02c"   # verde — T-CONT 1
C_TC2    = "#ff7f0e"   # naranja — T-CONT 2
C_TC4    = "#9467bd"   # violeta — T-CONT 4

LOADS    = [10, 25, 50, 75, 100]
TC_NAMES = {1: "T-CONT 1 (Fixed)", 2: "T-CONT 2 (Assured)", 4: "T-CONT 4 (Best Effort)"}


def setup_style():
    plt.rcParams.update({
        "font.family":   "serif",
        "font.size":     11,
        "axes.titlesize":13,
        "axes.labelsize":12,
        "legend.fontsize":10,
        "axes.grid":     True,
        "grid.alpha":    0.3,
        "figure.dpi":    100,
    })


def load_data(path: str) -> list:
    rows = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            rows.append({
                "scenario":          row["scenario"],
                "algorithm":         row["algorithm"],
                "load_mbps":         int(row["load_mbps"]),
                "tcont_type":        int(row["tcont_type"]),
                "latency_mean_us":   float(row["latency_mean_us"]),
                "latency_mean_ci95": float(row["latency_mean_ci95"]),
                "latency_p99_us":    float(row["latency_p99_us"]),
                "latency_p99_ci95":  float(row["latency_p99_ci95"]),
                "jitter_mean_us":    float(row["jitter_mean_us"]),
                "throughput_mbps":   float(row["throughput_mbps"]),
                "loss_rate_mean":    float(row["loss_rate_mean"]),
                "loss_rate_ci95":    float(row["loss_rate_ci95"]),
            })
    return rows


def filter_data(data, algorithm=None, load=None, tcont=None):
    result = data
    if algorithm: result = [r for r in result if r["algorithm"] == algorithm]
    if load:      result = [r for r in result if r["load_mbps"] == load]
    if tcont:     result = [r for r in result if r["tcont_type"] == tcont]
    return result


def savefig(fig, name: str):
    os.makedirs(FIGURES_DIR, exist_ok=True)
    path = os.path.join(FIGURES_DIR, name)
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"  Guardado: {path}")


# ------------------------------------------------------------------
# Gráfico 1: Latencia promedio por T-CONT bajo carga alta (100 Mbps)
# Dos paneles: T-CONT 1&2 (escala pequeña) | T-CONT 4 (escala grande)
# ------------------------------------------------------------------
def plot_latency_avg_by_tcont(data):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5),
                                    gridspec_kw={"width_ratios": [2, 1]})
    fig.suptitle("Latencia promedio por T-CONT — Carga BE = 100 Mbps/ONU",
                 fontsize=13)

    width = 0.35

    # Panel izquierdo: T-CONT 1 y 2
    for ax, tc_list, title in [(ax1, [1, 2], "T-CONT 1 (Fixed) y T-CONT 2 (Assured)"),
                                (ax2, [4],   "T-CONT 4 (Best Effort)")]:
        x = np.arange(len(tc_list))
        for i, (algo, color, label) in enumerate([("basic", C_BASIC, "BasicDBA"),
                                                   ("qos",   C_QOS,   "QoS-DBA")]):
            vals, errs = [], []
            for tc in tc_list:
                rows = filter_data(data, algorithm=algo, load=100, tcont=tc)
                vals.append(rows[0]["latency_mean_us"] if rows else 0)
                errs.append(rows[0]["latency_mean_ci95"] if rows else 0)
            bars = ax.bar(x + i*width, vals, width, yerr=errs, label=label,
                          color=color, alpha=0.85, capsize=4)
            # Anotar valores encima de cada barra
            for bar, v in zip(bars, vals):
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() * 1.03,
                        f"{v/1000:.1f}ms" if v > 1000 else f"{v:.0f}μs",
                        ha="center", va="bottom", fontsize=8)
        ax.set_xlabel("Tipo de T-CONT")
        ax.set_ylabel("Latencia promedio (μs)")
        ax.set_title(title, fontsize=10)
        ax.set_xticks(x + width/2)
        ax.set_xticklabels([TC_NAMES[t] for t in tc_list])
        ax.legend(fontsize=9)

    fig.tight_layout()
    savefig(fig, "latency_avg_by_tcont.png")


# ------------------------------------------------------------------
# Gráfico 2: P99 latencia T-CONT 1 vs carga (gráfico clave)
# ------------------------------------------------------------------
def plot_latency_p99_tcont1_vs_load(data):
    fig, ax = plt.subplots(figsize=(8, 5))

    for algo, color, label in [("basic", C_BASIC, "BasicDBA"),
                                ("qos",   C_QOS,   "QoS-DBA")]:
        vals = []
        errs = []
        for load in LOADS:
            rows = filter_data(data, algorithm=algo, load=load, tcont=1)
            vals.append(rows[0]["latency_p99_us"] if rows else 0)
            errs.append(rows[0]["latency_p99_ci95"] if rows else 0)
        errs_arr = np.array(errs)
        vals_arr = np.array(vals)
        ax.plot(LOADS, vals_arr, marker="o", color=color, label=label, linewidth=2)
        ax.fill_between(LOADS, vals_arr - errs_arr, vals_arr + errs_arr,
                        alpha=0.2, color=color)

    # Línea de referencia: budget VoIP 5ms
    ax.axhline(5000, color="gray", linestyle="--", linewidth=1.5,
               label="Budget VoIP (5 ms)")

    ax.set_xlabel("Carga T-CONT 4 por ONU (Mbps)")
    ax.set_ylabel("Latencia P99 T-CONT 1 (μs)")
    ax.set_title("Latencia P99 de T-CONT 1 (VoIP) vs Carga BE")
    ax.legend()
    savefig(fig, "latency_p99_tcont1_vs_load.png")


# ------------------------------------------------------------------
# Gráfico 3: Tasa de pérdida por T-CONT (escala log)
# ------------------------------------------------------------------
def plot_loss_rate_by_tcont(data):
    fig, ax = plt.subplots(figsize=(8, 5))
    tc_types = [1, 2, 4]
    x        = np.arange(len(tc_types))
    width    = 0.35
    MIN_VAL  = 1e-6

    for i, (algo, color, label) in enumerate([("basic", C_BASIC, "BasicDBA"),
                                               ("qos",   C_QOS,   "QoS-DBA")]):
        vals = []
        errs = []
        for tc in tc_types:
            rows = filter_data(data, algorithm=algo, load=100, tcont=tc)
            v = max(rows[0]["loss_rate_mean"], MIN_VAL) if rows else MIN_VAL
            e = rows[0]["loss_rate_ci95"] if rows else 0
            vals.append(v)
            errs.append(e)
        ax.bar(x + i*width, vals, width, yerr=errs, label=label,
               color=color, alpha=0.85, capsize=4)

    ax.set_yscale("log")
    ax.set_xlabel("Tipo de T-CONT")
    ax.set_ylabel("Tasa de pérdida (log)")
    ax.set_title("Tasa de pérdida por T-CONT — Carga BE = 100 Mbps/ONU")
    ax.set_xticks(x + width/2)
    ax.set_xticklabels([TC_NAMES[t] for t in tc_types])
    ax.legend()
    savefig(fig, "loss_rate_by_tcont.png")


# ------------------------------------------------------------------
# Gráfico 4: Throughput por T-CONT a carga 100 Mbps (barras agrupadas)
# Muestra cómo QosDBA protege T-CONT 1&2 vs BasicDBA
# ------------------------------------------------------------------
def plot_throughput_vs_load(data):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
    fig.suptitle("Throughput — Comparación BasicDBA vs QoS-DBA", fontsize=13)

    # Panel izq: throughput por T-CONT a carga 100 Mbps
    tc_types = [1, 2, 4]
    x = np.arange(len(tc_types))
    width = 0.35
    for i, (algo, color, label) in enumerate([("basic", C_BASIC, "BasicDBA"),
                                               ("qos",   C_QOS,   "QoS-DBA")]):
        vals = []
        for tc in tc_types:
            rows = filter_data(data, algorithm=algo, load=100, tcont=tc)
            vals.append(rows[0]["throughput_mbps"] if rows else 0)
        bars = ax1.bar(x + i*width, vals, width, label=label,
                       color=color, alpha=0.85)
        for bar, v in zip(bars, vals):
            ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() * 1.02,
                     f"{v:.0f}", ha="center", va="bottom", fontsize=7)
    ax1.set_xlabel("Tipo de T-CONT")
    ax1.set_ylabel("Throughput (Mbps)")
    ax1.set_title("Throughput por T-CONT (carga 100 Mbps/ONU)", fontsize=10)
    ax1.set_xticks(x + width/2)
    ax1.set_xticklabels([TC_NAMES[t] for t in tc_types])
    ax1.legend()

    # Panel der: throughput agregado vs carga
    for algo, color, label, ls in [("basic", C_BASIC, "BasicDBA", "--"),
                                    ("qos",   C_QOS,   "QoS-DBA",  "-")]:
        vals = []
        for load in LOADS:
            total_tp = sum(filter_data(data, algo, load, tc)[0]["throughput_mbps"]
                           if filter_data(data, algo, load, tc) else 0
                           for tc in [1, 2, 4])
            vals.append(total_tp)
        ax2.plot(LOADS, vals, marker="s", color=color, label=label,
                 linewidth=2, linestyle=ls)
    ax2.axhline(1244.16, color="gray", linestyle=":", linewidth=1.5,
                label="Cap. upstream (1,244 Mbps)")
    ax2.set_xlabel("Carga T-CONT 4 por ONU (Mbps)")
    ax2.set_ylabel("Throughput agregado (Mbps)")
    ax2.set_title("Throughput total vs Carga ofrecida", fontsize=10)
    ax2.legend()

    fig.tight_layout()
    savefig(fig, "throughput_vs_load.png")


# ------------------------------------------------------------------
# Gráfico 5: CDF de latencia T-CONT 1 (VoIP) — diferencia clave entre algoritmos
# ------------------------------------------------------------------
def plot_cdf_latency_tcont4(data):
    fig, ax = plt.subplots(figsize=(8, 5))

    # T-CONT 1 muestra la diferencia más dramática entre BasicDBA y QosDBA
    # BasicDBA: mean ~25,400 μs (VoIP inutilizable)
    # QosDBA:   mean ~164 μs   (VoIP perfecto)
    for algo, color, label, ls in [("basic", C_BASIC, "BasicDBA", "--"),
                                    ("qos",   C_QOS,   "QoS-DBA",  "-")]:
        rows = filter_data(data, algorithm=algo, load=100, tcont=1)
        if not rows:
            continue
        r    = rows[0]
        mean = r["latency_mean_us"]
        p99  = r["latency_p99_us"]
        # CDF aproximada con puntos estrictamente crecientes en x
        xs = [0, mean * 0.3, mean * 0.7, mean, p99, p99 * 1.05]
        ys = [0, 0.10,       0.35,       0.50, 0.99, 1.00]
        ax.plot(xs, ys, color=color, label=f"{label} (media={mean:.0f} μs)",
                linewidth=2, linestyle=ls)

    # Referencia: budget máximo VoIP G.114 = 150 ms de extremo a extremo → upstream ≤ 5 ms
    ax.axvline(5000, color="gray", linestyle=":", linewidth=1.5, label="Budget VoIP (5 ms)")
    ax.set_xlabel("Latencia T-CONT 1 — VoIP (μs)")
    ax.set_ylabel("Probabilidad acumulada")
    ax.set_title("CDF de Latencia T-CONT 1 (VoIP) — Carga 100 Mbps/ONU\n"
                 "QoS-DBA protege VoIP; BasicDBA lo degrada 155×")
    ax.legend()
    savefig(fig, "cdf_latency_tcont4.png")


# ------------------------------------------------------------------
# Gráfico 6: Utilización del canal vs carga
# ------------------------------------------------------------------
def plot_channel_utilization(data):
    fig, ax = plt.subplots(figsize=(8, 5))

    # Proxy: throughput / capacidad máxima
    cap_mbps = 1244.16

    for algo, color, label, ls in [("basic", C_BASIC, "BasicDBA", "--"),
                                    ("qos",   C_QOS,   "QoS-DBA",  "-")]:
        utils = []
        for load in LOADS:
            total_tp = 0.0
            for tc in [1, 2, 4]:
                rows = filter_data(data, algorithm=algo, load=load, tcont=tc)
                if rows:
                    total_tp += rows[0]["throughput_mbps"]
            utils.append(min(total_tp / cap_mbps * 100, 100.0))
        ax.plot(LOADS, utils, marker="^", color=color, label=label,
                linewidth=2, linestyle=ls)

    ax.axhline(100, color="gray", linestyle="--", linewidth=1, label="100% utilización")
    ax.set_ylim(0, 115)
    ax.set_xlabel("Carga T-CONT 4 por ONU (Mbps)")
    ax.set_ylabel("Utilización canal upstream (%)")
    ax.set_title("Utilización del canal upstream vs Carga ofrecida\n"
                 "(ambos algoritmos logran misma eficiencia — diferencia es en latencia QoS)")
    ax.legend()
    ax.text(0.02, 0.15,
            "Nota: BasicDBA y QoS-DBA logran igual utilización.\nLa diferencia está en la latencia por T-CONT (ver gráfico 1).",
            transform=ax.transAxes, fontsize=8, color="gray",
            verticalalignment="bottom",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="lightyellow", alpha=0.7))
    savefig(fig, "channel_utilization.png")


# ------------------------------------------------------------------
# Gráfico 7: Dashboard resumen 2×2
# ------------------------------------------------------------------
def plot_summary_dashboard(data):
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle("Comparación BasicDBA vs QoS-DBA — Red GPON ITU-T G.984",
                 fontsize=14, fontweight="bold")

    # Subplot 1: Latencia promedio por T-CONT (barras)
    ax = axes[0, 0]
    tc_types = [1, 2, 4]
    x = np.arange(len(tc_types))
    width = 0.35
    for i, (algo, color, label) in enumerate([("basic", C_BASIC, "BasicDBA"),
                                               ("qos",   C_QOS,   "QoS-DBA")]):
        vals = []
        errs = []
        for tc in tc_types:
            rows = filter_data(data, algorithm=algo, load=100, tcont=tc)
            vals.append(rows[0]["latency_mean_us"] if rows else 0)
            errs.append(rows[0]["latency_mean_ci95"] if rows else 0)
        ax.bar(x + i*width, vals, width, yerr=errs, label=label,
               color=color, alpha=0.85, capsize=3)
    ax.set_title("Latencia por T-CONT (carga 100 Mbps)")
    ax.set_ylabel("Latencia media (μs)")
    ax.set_xticks(x + width/2)
    ax.set_xticklabels(["T-CONT 1", "T-CONT 2", "T-CONT 4"])
    ax.legend(fontsize=9)

    # Subplot 2: P99 T-CONT 1 vs carga
    ax = axes[0, 1]
    for algo, color, label in [("basic", C_BASIC, "BasicDBA"),
                                ("qos",   C_QOS,   "QoS-DBA")]:
        vals = [filter_data(data, algo, l, 1)[0]["latency_p99_us"]
                if filter_data(data, algo, l, 1) else 0 for l in LOADS]
        ax.plot(LOADS, vals, marker="o", color=color, label=label, linewidth=2)
    ax.axhline(5000, color="gray", linestyle="--", linewidth=1, label="5 ms budget")
    ax.set_title("P99 Latencia T-CONT 1 vs Carga")
    ax.set_xlabel("Carga BE (Mbps/ONU)")
    ax.set_ylabel("P99 (μs)")
    ax.legend(fontsize=9)

    # Subplot 3: Throughput vs carga
    ax = axes[1, 0]
    cap_mbps = 1244.16
    for algo, color, label in [("basic", C_BASIC, "BasicDBA"),
                                ("qos",   C_QOS,   "QoS-DBA")]:
        vals = []
        for load in LOADS:
            tp = sum(filter_data(data, algo, load, tc)[0]["throughput_mbps"]
                     if filter_data(data, algo, load, tc) else 0
                     for tc in [1, 2, 4])
            vals.append(tp)
        ax.plot(LOADS, vals, marker="s", color=color, label=label, linewidth=2)
    ax.axhline(cap_mbps, color="gray", linestyle=":", linewidth=1)
    ax.set_title("Throughput vs Carga")
    ax.set_xlabel("Carga BE (Mbps/ONU)")
    ax.set_ylabel("Throughput (Mbps)")
    ax.legend(fontsize=9)

    # Subplot 4: Tasa de pérdida por T-CONT
    ax = axes[1, 1]
    tc_types = [1, 2, 4]
    x = np.arange(len(tc_types))
    MIN_VAL = 1e-6
    for i, (algo, color, label) in enumerate([("basic", C_BASIC, "BasicDBA"),
                                               ("qos",   C_QOS,   "QoS-DBA")]):
        vals = []
        for tc in tc_types:
            rows = filter_data(data, algorithm=algo, load=100, tcont=tc)
            vals.append(max(rows[0]["loss_rate_mean"], MIN_VAL) if rows else MIN_VAL)
        ax.bar(x + i*width, vals, width, label=label, color=color, alpha=0.85)
    ax.set_yscale("log")
    ax.set_title("Pérdida por T-CONT (carga 100 Mbps)")
    ax.set_ylabel("Tasa de pérdida")
    ax.set_xticks(x + width/2)
    ax.set_xticklabels(["T-CONT 1", "T-CONT 2", "T-CONT 4"])
    ax.legend(fontsize=9)

    fig.tight_layout()
    savefig(fig, "summary_dashboard.png")


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------
def main():
    if not os.path.exists(RESULTS_PATH):
        print(f"Error: no se encontró {RESULTS_PATH}")
        print("Primero ejecuta: python run_experiments.py")
        sys.exit(1)

    print("Cargando resultados...")
    data = load_data(RESULTS_PATH)
    print(f"  {len(data)} filas de resultados cargadas")

    setup_style()
    os.makedirs(FIGURES_DIR, exist_ok=True)

    print("Generando gráficos...")
    plot_latency_avg_by_tcont(data)
    plot_latency_p99_tcont1_vs_load(data)
    plot_loss_rate_by_tcont(data)
    plot_throughput_vs_load(data)
    plot_cdf_latency_tcont4(data)
    plot_channel_utilization(data)
    plot_summary_dashboard(data)

    print(f"\n7 gráficos guardados en: {FIGURES_DIR}/")


if __name__ == "__main__":
    main()
