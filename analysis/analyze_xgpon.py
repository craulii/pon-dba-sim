"""
Generador de gráficos -- Fase 3: XG-PON, IPACT vs GIANT vs QoSDBA, 8 ONUs.
Lee results/xgpon_results.csv y results/xgpon_cycle_times.csv generados por
run_experiments_xgpon.py.
Estilo IEEE paper: fuente serif, colores consistentes, IC 95%, 300 DPI.
Headline: cumplimiento de SLA (T-CONT1 <= 2 ms).
"""
import csv
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

RESULTS_PATH      = os.path.join(os.path.dirname(__file__), "..", "results", "xgpon_results.csv")
CYCLE_RESULTS_PATH= os.path.join(os.path.dirname(__file__), "..", "results", "xgpon_cycle_times.csv")
FIGURES_DIR       = os.path.join(os.path.dirname(__file__), "..", "figures", "xgpon")

# Colores consistentes
C_IPACT  = "#1f77b4"   # azul   — IPACT (polling)
C_GIANT  = "#2ca02c"   # verde  — GIANT (GPA/SPA)
C_QOS    = "#d62728"   # rojo   — QoSDBA (Fase 2 re-parametrizado)

ALGOS    = [("ipact", C_IPACT, "IPACT (polling)"),
            ("giant", C_GIANT, "GIANT (GPA/SPA)"),
            ("qos",   C_QOS,   "QoSDBA")]

LOADS    = [200, 400, 800]
TC_NAMES = {1: "T-CONT 1\n(VoIP/control)", 2: "T-CONT 2\n(Video)", 4: "T-CONT 4\n(Best Effort)"}

CAPACITY_MBPS = 2488.32   # XG-PON1 upstream (G.987.2)
SLA_T1_US     = 2000.0    # 2 ms
FRAME_US      = 125.0     # trama fija GIANT/QoSDBA


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
            sla = row["sla_compliance_pct"]
            sla_ci = row["sla_compliance_ci95"]
            rows.append({
                "scenario":           row["scenario"],
                "algorithm":          row["algorithm"],
                "load_mbps":          int(row["load_mbps"]),
                "tcont_type":         int(row["tcont_type"]),
                "latency_mean_us":    float(row["latency_mean_us"]),
                "latency_mean_ci95":  float(row["latency_mean_ci95"]),
                "latency_p99_us":     float(row["latency_p99_us"]),
                "latency_p99_ci95":   float(row["latency_p99_ci95"]),
                "latency_max_us":     float(row["latency_max_us"]),
                "latency_max_ci95":   float(row["latency_max_ci95"]),
                "jitter_mean_us":     float(row["jitter_mean_us"]),
                "throughput_mbps":    float(row["throughput_mbps"]),
                "loss_rate_mean":     float(row["loss_rate_mean"]),
                "loss_rate_ci95":     float(row["loss_rate_ci95"]),
                "sla_compliance_pct": float(sla) if sla not in ("", None) else None,
                "sla_compliance_ci95":float(sla_ci) if sla_ci not in ("", None) else 0.0,
            })
    return rows


def load_cycle_data(path: str) -> list:
    rows = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            rows.append({
                "scenario":     row["scenario"],
                "algorithm":    row["algorithm"],
                "load_mbps":    int(row["load_mbps"]),
                "seed":         int(row["seed"]),
                "cycle_time_us":float(row["cycle_time_us"]),
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
# Gráfico 1 (HEADLINE): Cumplimiento de SLA por T-CONT, carga 800 Mbps/ONU
# ------------------------------------------------------------------
def plot_sla_compliance_by_tcont(data, load=800):
    fig, ax = plt.subplots(figsize=(9, 5))
    tc_types = [1, 2, 4]
    x = np.arange(len(tc_types))
    width = 0.25

    for i, (algo, color, label) in enumerate(ALGOS):
        vals, errs = [], []
        for tc in tc_types:
            rows = filter_data(data, algorithm=algo, load=load, tcont=tc)
            v = rows[0]["sla_compliance_pct"] if (rows and rows[0]["sla_compliance_pct"] is not None) else 0
            e = rows[0]["sla_compliance_ci95"] if rows else 0
            vals.append(v)
            errs.append(e)
        bars = ax.bar(x + i*width, vals, width, yerr=errs, label=label,
                       color=color, alpha=0.85, capsize=4)
        for bar, v in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                    f"{v:.1f}%", ha="center", va="bottom", fontsize=8)

    ax.axhline(100, color="gray", linestyle=":", linewidth=1.5)
    ax.set_ylim(0, 110)
    ax.set_xlabel("Tipo de T-CONT")
    ax.set_ylabel("Cumplimiento SLA (%)")
    ax.set_title(f"Cumplimiento de SLA por T-CONT — Carga BE = {load} Mbps/ONU "
                  f"(sobrecarga ~{load*8/CAPACITY_MBPS*100:.0f}%)\n"
                  f"T-CONT1 SLA: delay máximo $\\leq$ 2 ms")
    ax.set_xticks(x + width)
    ax.set_xticklabels([TC_NAMES[t] for t in tc_types])
    ax.legend()
    savefig(fig, "sla_compliance_by_tcont.png")


# ------------------------------------------------------------------
# Gráfico 2: Delay máximo de T-CONT1 vs carga, con línea SLA 2ms
# ------------------------------------------------------------------
def plot_max_delay_tcont1_vs_load(data):
    fig, ax = plt.subplots(figsize=(8, 5))

    for algo, color, label in ALGOS:
        vals, errs = [], []
        for load in LOADS:
            rows = filter_data(data, algorithm=algo, load=load, tcont=1)
            vals.append(rows[0]["latency_max_us"] if rows else 0)
            errs.append(rows[0]["latency_max_ci95"] if rows else 0)
        vals_arr = np.array(vals)
        errs_arr = np.array(errs)
        ax.plot(LOADS, vals_arr, marker="o", color=color, label=label, linewidth=2)
        ax.fill_between(LOADS, vals_arr - errs_arr, vals_arr + errs_arr,
                        alpha=0.2, color=color)

    ax.axhline(SLA_T1_US, color="black", linestyle="--", linewidth=1.5,
               label="SLA T-CONT1 (2 ms)")

    ax.set_xlabel("Carga T-CONT 4 por ONU (Mbps)")
    ax.set_ylabel("Delay máximo T-CONT 1 (μs)")
    ax.set_title("¿Supera T-CONT1 el SLA de 2 ms? — Delay máximo observado vs carga")
    ax.set_xticks(LOADS)
    ax.legend()
    savefig(fig, "max_delay_tcont1_vs_load.png")


# ------------------------------------------------------------------
# Gráfico 3: Throughput vs carga (agregado), con referencia de capacidad
# ------------------------------------------------------------------
def plot_throughput_vs_load_xgpon(data):
    fig, ax = plt.subplots(figsize=(8, 5))

    for algo, color, label in ALGOS:
        vals = []
        for load in LOADS:
            total_tp = sum(filter_data(data, algo, load, tc)[0]["throughput_mbps"]
                           if filter_data(data, algo, load, tc) else 0
                           for tc in [1, 2, 4])
            vals.append(total_tp)
        ax.plot(LOADS, vals, marker="s", color=color, label=label, linewidth=2)

    ax.axhline(CAPACITY_MBPS, color="gray", linestyle=":", linewidth=1.5,
               label=f"Capacidad upstream ({CAPACITY_MBPS:.2f} Mbps)")

    ax.set_xlabel("Carga T-CONT 4 por ONU (Mbps)")
    ax.set_ylabel("Throughput agregado (Mbps)")
    ax.set_title("Throughput total vs carga ofrecida — XG-PON1, 8 ONUs")
    ax.set_xticks(LOADS)
    ax.legend()
    savefig(fig, "throughput_vs_load_xgpon.png")


# ------------------------------------------------------------------
# Gráfico 4 (clave): Distribución del tiempo de ciclo IPACT vs trama fija
# ------------------------------------------------------------------
def plot_cycle_time_distribution(cycle_data):
    if not cycle_data:
        print("  (sin datos de cycle time -- omitiendo cycle_time_distribution.png)")
        return

    fig, axes = plt.subplots(1, len(LOADS), figsize=(13, 4.5), sharey=True)
    fig.suptitle("Polling de ciclo variable (IPACT) vs trama fija 125 μs (GIANT/QoSDBA)",
                  fontsize=13)

    for ax, load in zip(axes, LOADS):
        samples = [r["cycle_time_us"] for r in cycle_data
                   if r["load_mbps"] == load and r["algorithm"] == "ipact"]
        if samples:
            ax.hist(samples, bins=40, color=C_IPACT, alpha=0.75, label="IPACT (ciclo variable)")
        ax.axvline(FRAME_US, color="black", linestyle="--", linewidth=1.5,
                   label="Trama fija (125 μs)")
        ax.set_title(f"Carga = {load} Mbps/ONU")
        ax.set_xlabel("Duración de ciclo (μs)")
        if ax is axes[0]:
            ax.set_ylabel("Frecuencia")
        ax.legend(fontsize=8)

    fig.tight_layout()
    savefig(fig, "cycle_time_distribution.png")


# ------------------------------------------------------------------
# Gráfico 5: Cumplimiento de SLA de T-CONT1 vs carga
# ------------------------------------------------------------------
def plot_sla_compliance_vs_load(data):
    fig, ax = plt.subplots(figsize=(8, 5))

    for algo, color, label in ALGOS:
        vals, errs = [], []
        for load in LOADS:
            rows = filter_data(data, algorithm=algo, load=load, tcont=1)
            v = rows[0]["sla_compliance_pct"] if (rows and rows[0]["sla_compliance_pct"] is not None) else 0
            e = rows[0]["sla_compliance_ci95"] if rows else 0
            vals.append(v)
            errs.append(e)
        vals_arr = np.array(vals)
        errs_arr = np.array(errs)
        ax.plot(LOADS, vals_arr, marker="o", color=color, label=label, linewidth=2)
        ax.fill_between(LOADS, vals_arr - errs_arr, vals_arr + errs_arr,
                        alpha=0.2, color=color)

    ax.axhline(100, color="gray", linestyle=":", linewidth=1.5, label="100%")
    ax.set_ylim(0, 110)
    ax.set_xlabel("Carga T-CONT 4 por ONU (Mbps)")
    ax.set_ylabel("Cumplimiento SLA T-CONT 1 (%)")
    ax.set_title("Cumplimiento del SLA de T-CONT1 (delay $\\leq$ 2 ms) vs carga")
    ax.set_xticks(LOADS)
    ax.legend()
    savefig(fig, "sla_compliance_vs_load.png")


# ------------------------------------------------------------------
# Gráfico 6: Dashboard resumen 2x2
# ------------------------------------------------------------------
def plot_summary_dashboard_xgpon(data, cycle_data, load=800):
    fig, axs = plt.subplots(2, 2, figsize=(13, 10))
    fig.suptitle("Fase 3 — XG-PON1, IPACT vs GIANT vs QoSDBA (8 ONUs)", fontsize=15)

    # (a) SLA compliance por T-CONT @ load
    ax = axs[0, 0]
    tc_types = [1, 2, 4]
    x = np.arange(len(tc_types))
    width = 0.25
    for i, (algo, color, label) in enumerate(ALGOS):
        vals = []
        for tc in tc_types:
            rows = filter_data(data, algorithm=algo, load=load, tcont=tc)
            vals.append(rows[0]["sla_compliance_pct"] if (rows and rows[0]["sla_compliance_pct"] is not None) else 0)
        ax.bar(x + i*width, vals, width, label=label, color=color, alpha=0.85)
    ax.axhline(100, color="gray", linestyle=":", linewidth=1)
    ax.set_ylim(0, 110)
    ax.set_xticks(x + width)
    ax.set_xticklabels([TC_NAMES[t] for t in tc_types], fontsize=9)
    ax.set_ylabel("SLA compliance (%)")
    ax.set_title(f"(a) Cumplimiento SLA @ {load} Mbps/ONU")
    ax.legend(fontsize=8)

    # (b) Max delay T1 vs carga
    ax = axs[0, 1]
    for algo, color, label in ALGOS:
        vals = [filter_data(data, algo, l, 1)[0]["latency_max_us"]
                if filter_data(data, algo, l, 1) else 0 for l in LOADS]
        ax.plot(LOADS, vals, marker="o", color=color, label=label, linewidth=2)
    ax.axhline(SLA_T1_US, color="black", linestyle="--", linewidth=1.5, label="SLA (2 ms)")
    ax.set_xlabel("Carga T-CONT4 (Mbps/ONU)")
    ax.set_ylabel("Delay máximo T-CONT1 (μs)")
    ax.set_title("(b) Delay máximo T-CONT1 vs carga")
    ax.set_xticks(LOADS)
    ax.legend(fontsize=8)

    # (c) Throughput vs carga
    ax = axs[1, 0]
    for algo, color, label in ALGOS:
        vals = []
        for l in LOADS:
            total_tp = sum(filter_data(data, algo, l, tc)[0]["throughput_mbps"]
                           if filter_data(data, algo, l, tc) else 0
                           for tc in [1, 2, 4])
            vals.append(total_tp)
        ax.plot(LOADS, vals, marker="s", color=color, label=label, linewidth=2)
    ax.axhline(CAPACITY_MBPS, color="gray", linestyle=":", linewidth=1.5, label="Capacidad")
    ax.set_xlabel("Carga T-CONT4 (Mbps/ONU)")
    ax.set_ylabel("Throughput agregado (Mbps)")
    ax.set_title("(c) Throughput vs carga")
    ax.set_xticks(LOADS)
    ax.legend(fontsize=8)

    # (d) Distribución de cycle time (boxplot por algoritmo, carga=load)
    ax = axs[1, 1]
    box_data, box_labels, box_colors = [], [], []
    for algo, color, label in ALGOS:
        if algo == "ipact":
            samples = [r["cycle_time_us"] for r in cycle_data
                       if r["load_mbps"] == load and r["algorithm"] == "ipact"]
            if samples:
                box_data.append(samples)
                box_labels.append(label)
                box_colors.append(color)
        else:
            # GIANT/QoSDBA: trama fija de 125us (sin variabilidad)
            box_data.append([FRAME_US])
            box_labels.append(label)
            box_colors.append(color)
    bp = ax.boxplot(box_data, tick_labels=box_labels, patch_artist=True)
    for patch, color in zip(bp["boxes"], box_colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.6)
    ax.set_ylabel("Duración de ciclo / trama (μs)")
    ax.set_title(f"(d) Ciclo de polling vs trama fija @ {load} Mbps/ONU")
    ax.tick_params(axis="x", labelsize=8)

    fig.tight_layout(rect=[0, 0, 1, 0.96])
    savefig(fig, "summary_dashboard_xgpon.png")


# ------------------------------------------------------------------
def main():
    if not os.path.exists(RESULTS_PATH):
        print(f"Error: no se encontró {RESULTS_PATH}")
        print("Primero ejecuta: python run_experiments_xgpon.py")
        sys.exit(1)

    print("Cargando resultados...")
    data = load_data(RESULTS_PATH)
    print(f"  {len(data)} filas de resultados cargadas")

    cycle_data = []
    if os.path.exists(CYCLE_RESULTS_PATH):
        cycle_data = load_cycle_data(CYCLE_RESULTS_PATH)
        print(f"  {len(cycle_data)} muestras de cycle time cargadas")

    setup_style()
    os.makedirs(FIGURES_DIR, exist_ok=True)

    print("Generando gráficos...")
    plot_sla_compliance_by_tcont(data)
    plot_max_delay_tcont1_vs_load(data)
    plot_throughput_vs_load_xgpon(data)
    plot_cycle_time_distribution(cycle_data)
    plot_sla_compliance_vs_load(data)
    plot_summary_dashboard_xgpon(data, cycle_data)

    print(f"\n6 gráficos guardados en: {FIGURES_DIR}/")


if __name__ == "__main__":
    main()
