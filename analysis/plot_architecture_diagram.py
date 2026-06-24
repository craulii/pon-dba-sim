"""
Diagrama de flujo de decision del simulador (para la presentacion).
No usa datos de resultados -- es un diagrama conceptual, hecho a mano con
matplotlib (sin depender de LaTeX) que muestra el loop del motor de
eventos y las decisiones que toma cada rama: generacion de trafico, OLT
en modo broadcast (GIANT/QoSDBA), OLT en modo polling (IPACT), la ONU al
transmitir, y la OLT al medir.
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Polygon

FIGURES_DIR = os.path.join(os.path.dirname(__file__), "..", "figures")

GRIS = "#444444"
NEGRO = "#1a1a1a"

COL_TRAFICO = ("#eaf7e6", "#2ca02c")
COL_BROADCAST = ("#dde9f7", "#1f4e8c")
COL_POLLING = ("#fde9d0", "#d4760a")
COL_ONU = ("#ece4f7", "#6a3fa0")
COL_OLT_MIDE = ("#fff6cf", "#a8860a")
COL_NEUTRO = ("#f2f2f2", "#444444")


def rect(ax, center, w, h, text, fontsize=8, colors=COL_NEUTRO, bold=False):
    x, y = center
    face, edge = colors
    ax.add_patch(FancyBboxPatch(
        (x - w / 2, y - h / 2), w, h,
        boxstyle="round,pad=0.02,rounding_size=0.06",
        linewidth=1.3, edgecolor=edge, facecolor=face,
    ))
    ax.text(x, y, text, ha="center", va="center", fontsize=fontsize,
             color=NEGRO, fontweight="bold" if bold else "normal",
             linespacing=1.4)


def diamond(ax, center, w, h, text, fontsize=8.5, colors=COL_NEUTRO):
    x, y = center
    face, edge = colors
    pts = [(x, y + h / 2), (x + w / 2, y), (x, y - h / 2), (x - w / 2, y)]
    ax.add_patch(Polygon(pts, closed=True, linewidth=1.3,
                           edgecolor=edge, facecolor=face))
    ax.text(x, y, text, ha="center", va="center", fontsize=fontsize,
             color=NEGRO, linespacing=1.3)


def arrow(ax, p1, p2, text=None, dx=0.0, dy=0.0, color=GRIS, lw=1.4,
          fontsize=7.5, connectionstyle=None, ls="-"):
    kw = dict(arrowstyle="-|>", mutation_scale=14, linewidth=lw, color=color,
              linestyle=ls)
    if connectionstyle:
        kw["connectionstyle"] = connectionstyle
    ax.add_patch(FancyArrowPatch(p1, p2, **kw))
    if text:
        mx = (p1[0] + p2[0]) / 2 + dx
        my = (p1[1] + p2[1]) / 2 + dy
        ax.text(mx, my, text, ha="center", va="center", fontsize=fontsize,
                 color=color)


def col_header(ax, x, y, text, color):
    ax.text(x, y, text, ha="center", va="center", fontsize=9.5,
             color=color, fontweight="bold")


def main():
    plt.rcParams.update({"font.family": "serif"})
    fig, ax = plt.subplots(figsize=(16, 11.5))
    ax.set_xlim(-0.5, 16)
    ax.set_ylim(0, 11.5)
    ax.axis("off")

    cols = {"A": 1.6, "B": 4.9, "C": 8.2, "D": 11.4, "E": 14.4}

    # ------------------------------------------------------------------
    # Columna troncal: inicio, chequeo de fin, sacar evento, tipo de evento
    # ------------------------------------------------------------------
    cx = 8.2

    rect(ax, (cx, 10.9), 7.6, 0.9,
         "INICIO\nCargar configuración, crear OLT y 8 ONUs,\n"
         "agendar los primeros eventos de tráfico",
         fontsize=9, colors=COL_NEUTRO, bold=True)

    diamond(ax, (cx, 9.55), 4.6, 1.5,
            "¿Cola de eventos vacía\no tiempo > límite?", fontsize=9)
    arrow(ax, (cx, 10.45), (cx, 10.3))

    rect(ax, (13.6, 9.55), 3.6, 1.0,
         "FIN\nCalcular métricas: latencia,\ncumplimiento de SLA, throughput",
         fontsize=8.5, colors=COL_NEUTRO, bold=True)
    arrow(ax, (cx + 2.3, 9.55), (11.8, 9.55), text="sí", dy=0.25)

    rect(ax, (cx, 8.15), 6.4, 0.85,
         "Sacar el evento con menor (tiempo, secuencia);\n"
         "reloj_actual = evento.tiempo  (el reloj salta, no avanza fijo)",
         fontsize=8.5)
    arrow(ax, (cx, 8.8), (cx, 8.6), text="no", dx=0.45)

    diamond(ax, (cx, 6.75), 4.2, 1.5, "¿Qué tipo de\nevento es?", fontsize=9)
    arrow(ax, (cx, 7.7), (cx, 7.5))

    # ------------------------------------------------------------------
    # Bus horizontal: del diamante a cada columna en linea recta (sin
    # diagonales que crucen por encima de los titulos de otras columnas)
    # ------------------------------------------------------------------
    bus_top_y = 6.0
    ax.plot([cx, cx], [6.0, bus_top_y], color=GRIS, linewidth=1.3)
    ax.plot([cols["A"], cols["E"]], [bus_top_y, bus_top_y], color=GRIS, linewidth=1.3)
    for key in cols:
        arrow(ax, (cols[key], bus_top_y), (cols[key], 4.95), color=GRIS, lw=1.1)

    # ------------------------------------------------------------------
    # Encabezados de columna (debajo del bus, no los cruza ninguna linea
    # de otra columna)
    # ------------------------------------------------------------------
    col_header(ax, cols["A"], 5.55, "Generar tráfico\n(self-scheduling)", COL_TRAFICO[1])
    col_header(ax, cols["B"], 5.55, "OLT: turno broadcast\n(GIANT / QoSDBA, cada 125 µs)", COL_BROADCAST[1])
    col_header(ax, cols["C"], 5.55, "OLT: turno de polling\n(IPACT, 1 ONU a la vez)", COL_POLLING[1])
    col_header(ax, cols["D"], 5.55, "ONU recibe\nla asignación", COL_ONU[1])
    col_header(ax, cols["E"], 5.55, "OLT recibe\ndatos / reporte", COL_OLT_MIDE[1])

    # ------------------------------------------------------------------
    # Columna A: generación de tráfico
    # ------------------------------------------------------------------
    ax_ = cols["A"]
    rect(ax, (ax_, 4.55), 2.7, 0.95,
         "Encolar paquete nuevo\nen el T-CONT correspondiente",
         colors=COL_TRAFICO)
    arrow(ax, (ax_, 4.075), (ax_, 3.82))
    rect(ax, (ax_, 3.35), 2.7, 1.05,
         "Calcular el próximo intervalo:\nCBR fijo / Poisson exponencial /\nPareto cola pesada",
         colors=COL_TRAFICO)
    arrow(ax, (ax_, 2.825), (ax_, 2.57))
    rect(ax, (ax_, 2.1), 2.7, 0.9,
         "Agendar el siguiente paquete\nen (ahora + intervalo)",
         colors=COL_TRAFICO)

    # ------------------------------------------------------------------
    # Columna B: OLT broadcast (GIANT / QoSDBA)
    # ------------------------------------------------------------------
    bx_ = cols["B"]
    rect(ax, (bx_, 4.55), 2.9, 0.95,
         "T-CONT1: reservar 160 B\nsiempre, sin mirar demanda",
         colors=COL_BROADCAST)
    arrow(ax, (bx_, 4.075), (bx_, 3.82))
    diamond(ax, (bx_, 3.25), 2.9, 1.3,
            "T-CONT2: ¿contador\nSImax llegó a 0?", fontsize=7.8,
            colors=COL_BROADCAST)
    arrow(ax, (bx_, 2.6), (bx_, 2.35), text="sí: grant\nde catch-up",
          dx=1.15, fontsize=6.8, color=COL_BROADCAST[1])
    rect(ax, (bx_, 1.95), 2.9, 0.85,
         "T-CONT4: round-robin entre\nONUs elegibles (contador SImin)",
         colors=COL_BROADCAST)
    arrow(ax, (bx_, 1.525), (bx_, 1.27))
    rect(ax, (bx_, 0.85), 2.9, 0.85,
         "Armar el BWmap y enviarlo\na las 8 ONUs (broadcast)",
         colors=COL_BROADCAST)

    # ------------------------------------------------------------------
    # Columna C: OLT polling (IPACT)
    # ------------------------------------------------------------------
    cx_ = cols["C"]
    rect(ax, (cx_, 4.55), 2.9, 0.95,
         "Leer el último reporte\nconocido de esta ONU",
         colors=COL_POLLING)
    arrow(ax, (cx_, 4.075), (cx_, 3.82))
    rect(ax, (cx_, 3.35), 2.9, 1.05,
         "grant = mínimo(demanda\nreportada, B_max = 38880 B)",
         colors=COL_POLLING)
    arrow(ax, (cx_, 2.825), (cx_, 2.57))
    rect(ax, (cx_, 2.1), 2.9, 0.95,
         "Enviar GATE individual;\nagendar el siguiente turno\n(grant_time + guard_time)",
         colors=COL_POLLING)

    # ------------------------------------------------------------------
    # Columna D: ONU transmite
    # ------------------------------------------------------------------
    dx_ = cols["D"]
    rect(ax, (dx_, 4.55), 2.7, 0.95,
         "Transmitir paquetes hasta\nagotar el grant otorgado",
         colors=COL_ONU)
    arrow(ax, (dx_, 4.075), (dx_, 3.82))
    rect(ax, (dx_, 3.35), 2.7, 0.95,
         "Enviar reporte (DBRu) con\nel estado actual de las colas",
         colors=COL_ONU)

    # ------------------------------------------------------------------
    # Columna E: OLT mide
    # ------------------------------------------------------------------
    ex_ = cols["E"]
    rect(ax, (ex_, 4.55), 2.6, 0.95,
         "Medir latencia y registrar\nmétricas de esta entrega",
         colors=COL_OLT_MIDE)
    arrow(ax, (ex_, 4.075), (ex_, 3.82))
    rect(ax, (ex_, 3.35), 2.6, 0.95,
         "Actualizar el último reporte\nconocido de esa ONU",
         colors=COL_OLT_MIDE)

    # ------------------------------------------------------------------
    # Linea colectora: todas las ramas vuelven al inicio del loop
    # ------------------------------------------------------------------
    bottoms = {
        "A": 1.65, "B": 0.4, "C": 1.625, "D": 2.875, "E": 2.875,
    }
    bus_y = 0.05
    for key, x in cols.items():
        arrow(ax, (x, bottoms[key]), (x, bus_y + 0.05), color="#999999", lw=1.0)
    ax.plot([cols["A"], cols["E"]], [bus_y, bus_y], color="#999999", linewidth=1.2)
    riser_x = 0.0
    ax.plot([riser_x, riser_x], [bus_y, 8.15], color="#999999", linewidth=1.2)
    ax.plot([riser_x, cols["A"]], [bus_y, bus_y], color="#999999", linewidth=1.2)
    arrow(ax, (riser_x, 8.15), (4.95, 8.15), text="vuelve al inicio del loop",
          dy=0.22, fontsize=8, color="#666666")

    fig.tight_layout()
    os.makedirs(FIGURES_DIR, exist_ok=True)
    out_path = os.path.join(FIGURES_DIR, "architecture_diagram.png")
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Guardado: {out_path}")


if __name__ == "__main__":
    main()
