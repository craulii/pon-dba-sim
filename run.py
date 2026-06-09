#!/usr/bin/env python3
"""
Menú interactivo del simulador GPON DBA — OmneTeam TEL-341
Ejecutar: python3 run.py
"""
import os, sys, time, json, csv, statistics, random
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
from main import load_config, build_config, run_simulation

# ─────────────────────────────────────────────
# ANSI colors / styles
# ─────────────────────────────────────────────
class C:
    RESET  = "\033[0m"
    BOLD   = "\033[1m"
    DIM    = "\033[2m"
    CYAN   = "\033[96m"
    GREEN  = "\033[92m"
    RED    = "\033[91m"
    YELLOW = "\033[93m"
    BLUE   = "\033[94m"
    MAGENTA= "\033[95m"
    WHITE  = "\033[97m"
    GRAY   = "\033[90m"
    BG_DARK= "\033[48;5;235m"

def c(color, text):  return f"{color}{text}{C.RESET}"
def bold(text):      return c(C.BOLD, text)
def dim(text):       return c(C.DIM + C.GRAY, text)

W = 68  # ancho de la UI

# ─────────────────────────────────────────────
# Primitivas de UI
# ─────────────────────────────────────────────
def clr():
    os.system("clear" if os.name == "posix" else "cls")

def rule(char="─"):
    print(c(C.GRAY, char * W))

def header():
    clr()
    print()
    print(c(C.CYAN + C.BOLD, "┌" + "─" * (W - 2) + "┐"))
    title  = "GPON DBA Simulator  ·  OmneTeam  ·  TEL-341 UTFSM"
    sub    = "ITU-T G.984  ·  1.24416 Gbps upstream  ·  125 μs/trama"
    print(c(C.CYAN + C.BOLD, "│") + f"  {c(C.BOLD+C.WHITE, title):^{W+8}}  " + c(C.CYAN+C.BOLD,"│"))
    print(c(C.CYAN + C.BOLD, "│") + f"  {c(C.GRAY, sub):^{W+8}}  "           + c(C.CYAN+C.BOLD,"│"))
    print(c(C.CYAN + C.BOLD, "└" + "─" * (W - 2) + "┘"))
    print()

def section(title):
    print()
    print(c(C.CYAN + C.BOLD, f"  ── {title} " + "─" * max(0, W - len(title) - 6)))

def progress_bar(current, total, width=30):
    pct  = current / total if total else 0
    done = int(pct * width)
    bar  = c(C.CYAN, "█" * done) + c(C.GRAY, "░" * (width - done))
    return f"[{bar}] {c(C.WHITE+C.BOLD, f'{pct*100:5.1f}%')}"

def spinner_frame(n):
    return ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"][n % 10]

def fmt_us(v):
    """Formatea microsegundos de forma legible."""
    if v >= 1_000_000: return f"{v/1_000_000:.2f}s"
    if v >= 1_000:     return f"{v/1_000:.1f}ms"
    return f"{v:.0f}μs"

def color_latency(v_us, tcont_type):
    """Colorea la latencia según si es aceptable para el T-CONT."""
    thresholds = {1: 5_000, 2: 50_000, 4: 999_999_999}
    limit = thresholds.get(tcont_type, 999_999_999)
    txt = fmt_us(v_us)
    if v_us < limit * 0.1:  return c(C.GREEN,  txt)
    if v_us < limit:        return c(C.YELLOW, txt)
    return c(C.RED + C.BOLD, txt)

def press_enter():
    print()
    print(dim("  Presiona Enter para continuar..."))
    input()

# ─────────────────────────────────────────────
# Tabla de resultados
# ─────────────────────────────────────────────
def print_results_table(summary, num_onus, label=""):
    TC_NAMES = {1: "T-CONT 1  Fixed CBR",
                2: "T-CONT 2  Assured  ",
                4: "T-CONT 4  Best Efft"}
    if label:
        print(c(C.BOLD + C.WHITE, f"\n  Resultados — {label}"))
    print()
    hdr = (f"  {'T-CONT':<20} {'Lat.media':>10} {'P99':>10} "
           f"{'Jitter':>9} {'Thrput':>10} {'Loss':>8}")
    print(c(C.GRAY, hdr))
    print(c(C.GRAY, "  " + "─" * (W - 2)))

    for tc in [1, 2, 4]:
        lats, p99s, jits, tputs, losses = [], [], [], [], []
        for onu_id in range(num_onus):
            key = (onu_id, tc)
            if key in summary and summary[key]["n_packets"] > 0:
                m = summary[key]
                lats.append(m["latency_mean_us"])
                p99s.append(m["latency_p99_us"])
                jits.append(m["jitter_mean_us"])
                tputs.append(m["throughput_mbps"])
            ds = summary.get("drop_stats", {}).get(key)
            if ds and ds["pkts_generated"] > 0:
                losses.append(ds["loss_rate"] * 100)

        if not lats:
            continue
        lat  = statistics.mean(lats)
        p99  = statistics.mean(p99s)
        jit  = statistics.mean(jits)
        tput = sum(tputs)
        loss = statistics.mean(losses) if losses else 0.0

        lat_str  = color_latency(lat, tc)
        p99_str  = color_latency(p99, tc)
        loss_col = C.GREEN if loss < 0.01 else (C.YELLOW if loss < 1 else C.RED)
        tput_col = C.WHITE

        print(f"  {c(C.BOLD, TC_NAMES[tc])}  "
              f"{lat_str:>18}  {p99_str:>18}  "
              f"{c(C.GRAY, fmt_us(jit)):>17}  "
              f"{c(tput_col, f'{tput:.1f} Mbps'):>18}  "
              f"{c(loss_col, f'{loss:.3f}%'):>16}")

    util = summary.get("channel_utilization", 0)
    util_col = C.GREEN if util > 0.85 else C.YELLOW
    print()
    print(f"  Utilización canal:  {c(util_col + C.BOLD, f'{util*100:.1f}%')}")

# ─────────────────────────────────────────────
# Opción 1: Prueba rápida
# ─────────────────────────────────────────────
def run_quick_test():
    header()
    section("Prueba rápida")
    print(f"\n  {c(C.GRAY, 'Parámetros:')} QosDBA · 100 Mbps · 8 ONUs · 2s sim · seed 42\n")
    base    = load_config("configs/default.json")
    config  = build_config(base, num_onus=8, tcont4_rate_bps=100_000_000,
                           duration=2.0, warmup=0.2)
    t0 = time.time()
    spin = 0
    print(f"  {spinner_frame(spin)}  Simulando...", end="", flush=True)

    # Correr en hilo para mostrar spinner (simplificado: mostrar tiempo)
    result = None
    import threading
    done = threading.Event()

    def worker():
        nonlocal result
        result = run_simulation(config, "qos", seed=42)
        done.set()

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    while not done.is_set():
        spin += 1
        elapsed = time.time() - t0
        print(f"\r  {c(C.CYAN, spinner_frame(spin))}  "
              f"Simulando... {c(C.GRAY, f'{elapsed:.1f}s')}", end="", flush=True)
        time.sleep(0.1)
    elapsed = time.time() - t0
    print(f"\r  {c(C.GREEN, '✓')}  "
          f"Completado en {c(C.WHITE+C.BOLD, f'{elapsed:.2f}s')}           ")

    print_results_table(result, 8, "QosDBA · 100 Mbps/ONU · 8 ONUs")
    press_enter()

# ─────────────────────────────────────────────
# Opción 2: Corrida custom
# ─────────────────────────────────────────────
def run_custom():
    header()
    section("Corrida personalizada")
    print()

    def ask(prompt, options, default):
        opts_str = "  ".join(
            f"{c(C.CYAN, f'[{i+1}]')} {o}" for i, o in enumerate(options)
        )
        print(f"  {c(C.BOLD, prompt)}")
        print(f"  {opts_str}")
        try:
            raw = input(f"  {c(C.GRAY, f'Opción [1-{len(options)}] (default={default+1}): ')}").strip()
            idx = int(raw) - 1
            if 0 <= idx < len(options):
                return idx
        except (ValueError, EOFError):
            pass
        return default

    alg_idx  = ask("Algoritmo:", ["BasicDBA", "QosDBA"], default=1)
    load_idx = ask("Carga T-CONT 4:", ["10 Mbps", "25 Mbps", "50 Mbps", "75 Mbps", "100 Mbps"], default=4)
    onus_idx = ask("ONUs:", ["8", "16", "32"], default=2)
    dur_idx  = ask("Duración:", ["2s (rápido)", "5s", "10s (completo)"], default=0)
    print()

    alg     = ["basic", "qos"][alg_idx]
    load    = [10, 25, 50, 75, 100][load_idx] * 1_000_000
    num_onus= [8, 16, 32][onus_idx]
    dur     = [2.0, 5.0, 10.0][dur_idx]
    warmup  = min(1.0, dur * 0.1)
    seed    = 42

    base   = load_config("configs/default.json")
    config = build_config(base, num_onus=num_onus, tcont4_rate_bps=load,
                          duration=dur, warmup=warmup)

    label_alg  = ["BasicDBA", "QosDBA"][alg_idx]
    label_load = [10, 25, 50, 75, 100][load_idx]
    print(f"  {c(C.GRAY, '─'*50)}")
    print(f"  {c(C.BOLD,'Ejecutando:')} {label_alg} · {label_load} Mbps/ONU · "
          f"{num_onus} ONUs · {dur}s")
    print()

    import threading
    result, done = None, threading.Event()
    def worker():
        nonlocal result
        result = run_simulation(config, alg, seed=seed)
        done.set()

    t0 = time.time()
    threading.Thread(target=worker, daemon=True).start()
    spin = 0
    while not done.is_set():
        spin += 1
        elapsed = time.time() - t0
        pct = min(elapsed / dur, 0.99)
        bar = progress_bar(int(pct * 20), 20, width=20)
        print(f"\r  {c(C.CYAN, spinner_frame(spin))}  {bar}  "
              f"{c(C.GRAY, f'{elapsed:.1f}s / ~{dur:.0f}s')}", end="", flush=True)
        time.sleep(0.1)

    elapsed = time.time() - t0
    print(f"\r  {c(C.GREEN,'✓')}  Completado en {c(C.WHITE+C.BOLD, f'{elapsed:.2f}s')}          ")

    print_results_table(result, num_onus,
                        f"{label_alg} · {label_load} Mbps/ONU · {num_onus} ONUs")
    press_enter()

# ─────────────────────────────────────────────
# Opción 3: Experimentos completos
# ─────────────────────────────────────────────
def run_full_experiments():
    header()
    section("Experimentos completos")

    with open("configs/scenarios.json") as f:
        scenarios = json.load(f)["scenarios"]
    base_cfg    = load_config("configs/default.json")
    sim_cfg     = base_cfg["simulation"]
    REPS        = sim_cfg.get("repetitions", 10)
    SEED_BASE   = sim_cfg.get("seed_base", 42)
    DURATION    = sim_cfg.get("duration_s", 10.0)
    WARMUP      = sim_cfg.get("warmup_s", 1.0)
    N_SCENARIOS = len(scenarios)
    TOTAL_RUNS  = N_SCENARIOS * REPS

    print(f"\n  {c(C.BOLD,'Plan:')} {N_SCENARIOS} escenarios × {REPS} repeticiones = "
          f"{c(C.CYAN+C.BOLD, f'{TOTAL_RUNS} corridas')}")
    print(f"  {c(C.GRAY, f'Duración por corrida: {DURATION}s sim · {WARMUP}s warmup')}")
    print()
    print(f"  {c(C.YELLOW, '⚠')}  Tiempo estimado: ~{N_SCENARIOS * REPS * 8 // 60 + 1} min")
    print()
    raw = input(f"  {c(C.BOLD,'¿Continuar? [S/n]: ')}").strip().lower()
    if raw == "n":
        return

    print()
    all_rows   = []
    run_count  = 0
    t_start    = time.time()

    for s_idx, scenario in enumerate(scenarios):
        name      = scenario["name"]
        algorithm = scenario["algorithm"]
        num_onus  = scenario.get("num_onus", 32)
        load_mbps = scenario["tcont4_rate_mbps"]
        alg_color = C.BLUE if algorithm == "basic" else C.RED
        alg_label = c(alg_color + C.BOLD,
                      "BasicDBA" if algorithm == "basic" else "QosDBA ")

        config = build_config(base_cfg, num_onus=num_onus,
                              tcont4_rate_bps=load_mbps * 1_000_000,
                              duration=DURATION, warmup=WARMUP)

        print(f"  {c(C.GRAY, f'[{s_idx+1:2}/{N_SCENARIOS}]')}  "
              f"{alg_label}  {c(C.WHITE+C.BOLD, f'{load_mbps:>3} Mbps/ONU')}  "
              f"{c(C.GRAY, f'{num_onus} ONUs')}")

        rep_summaries = []
        rep_times     = []

        for rep in range(REPS):
            seed    = SEED_BASE + rep
            t_rep   = time.time()

            # Progress inline
            bar = progress_bar(rep, REPS, width=20)
            eta_str = ""
            if run_count > 0:
                elapsed  = time.time() - t_start
                per_run  = elapsed / run_count
                remaining = (TOTAL_RUNS - run_count) * per_run
                m, s = divmod(int(remaining), 60)
                eta_str = c(C.GRAY, f"  ETA {m:02d}:{s:02d}")
            print(f"\r     {bar}  rep {rep+1}/{REPS}  seed={seed}{eta_str}    ",
                  end="", flush=True)

            summary = run_simulation(config, algorithm, seed=seed, verbose=False)
            rep_summaries.append(summary)
            rep_times.append(time.time() - t_rep)
            run_count += 1

        # Línea completada
        avg_rep = statistics.mean(rep_times)
        print(f"\r     {progress_bar(REPS, REPS, width=20)}  "
              f"{c(C.GREEN,'✓')} {REPS}/{REPS}  "
              f"{c(C.GRAY, f'{avg_rep:.2f}s/rep')}          ")

        # Agregar métricas
        for tc in [1, 2, 4]:
            lats, p99s, jits, tputs, losses = [], [], [], [], []
            for s in rep_summaries:
                tc_lats, tc_p99s, tc_jits, tc_tputs = [], [], [], []
                for onu_id in range(num_onus):
                    key = (onu_id, tc)
                    if key in s and s[key]["n_packets"] > 0:
                        tc_lats.append(s[key]["latency_mean_us"])
                        tc_p99s.append(s[key]["latency_p99_us"])
                        tc_jits.append(s[key]["jitter_mean_us"])
                        tc_tputs.append(s[key]["throughput_mbps"])
                    ds = s.get("drop_stats", {}).get(key)
                    if ds and ds["pkts_generated"] > 0:
                        losses.append(ds["loss_rate"])
                if tc_lats:
                    lats.append(statistics.mean(tc_lats))
                    p99s.append(statistics.mean(tc_p99s))
                    jits.append(statistics.mean(tc_jits))
                    tputs.append(sum(tc_tputs))
            if not lats:
                continue

            def ci95(data):
                if len(data) < 2: return 0.0
                return 1.96 * statistics.stdev(data) / len(data)**0.5

            all_rows.append({
                "scenario":          name,
                "algorithm":         algorithm,
                "load_mbps":         load_mbps,
                "num_onus":          num_onus,
                "tcont_type":        tc,
                "repetitions":       len(lats),
                "latency_mean_us":   statistics.mean(lats),
                "latency_mean_ci95": ci95(lats),
                "latency_p99_us":    statistics.mean(p99s),
                "latency_p99_ci95":  ci95(p99s),
                "jitter_mean_us":    statistics.mean(jits),
                "throughput_mbps":   statistics.mean(tputs),
                "loss_rate_mean":    statistics.mean(losses) if losses else 0.0,
                "loss_rate_ci95":    ci95(losses) if losses else 0.0,
            })

    # Guardar CSV
    os.makedirs("results", exist_ok=True)
    out_path = "results/all_results.csv"
    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(all_rows[0].keys()))
        w.writeheader()
        w.writerows(all_rows)

    total_time = time.time() - t_start
    m, s = divmod(int(total_time), 60)
    print()
    rule()
    print(f"\n  {c(C.GREEN+C.BOLD,'✓')}  {TOTAL_RUNS} corridas completadas en "
          f"{c(C.WHITE+C.BOLD, f'{m:02d}:{s:02d}')}")
    print(f"  {c(C.GRAY,'Guardado:')} {out_path}  "
          f"({c(C.CYAN, f'{len(all_rows)} filas')})")

    # Mini resumen del resultado clave
    section("Resultado clave — T-CONT 1 a 100 Mbps/ONU")
    print()
    for alg, alg_col, label in [("basic", C.BLUE, "BasicDBA"),
                                  ("qos",   C.RED,  "QosDBA ")]:
        row = next((r for r in all_rows
                    if r["algorithm"] == alg
                    and r["load_mbps"] == 100
                    and r["tcont_type"] == 1), None)
        if row:
            lat = row["latency_mean_us"]
            lat_str = color_latency(lat, 1)
            print(f"  {c(alg_col+C.BOLD, label)}  T-CONT 1 latencia: {lat_str}")
    print()

    ask_generate_graphs()
    press_enter()

def ask_generate_graphs():
    raw = input(f"  {c(C.BOLD,'¿Generar gráficos ahora? [S/n]: ')}").strip().lower()
    if raw != "n":
        do_generate_graphs(quiet=True)

# ─────────────────────────────────────────────
# Opción 4: Generar gráficos
# ─────────────────────────────────────────────
def do_generate_graphs(quiet=False):
    if not quiet:
        header()
        section("Generar gráficos")
        print()

    if not os.path.exists("results/all_results.csv"):
        print(f"  {c(C.RED,'✗')}  No se encontró results/all_results.csv")
        print(f"  {c(C.GRAY,'→ Ejecuta primero los experimentos completos (opción 3)')}")
        press_enter()
        return

    print(f"  {c(C.CYAN, spinner_frame(0))}  Generando 7 gráficos...", end="", flush=True)
    import threading
    done  = threading.Event()
    error = [None]

    def worker():
        try:
            import subprocess
            subprocess.run([sys.executable, "analysis/analyze.py"],
                           check=True, capture_output=True)
        except Exception as e:
            error[0] = str(e)
        finally:
            done.set()

    t0   = time.time()
    spin = 0
    threading.Thread(target=worker, daemon=True).start()
    while not done.is_set():
        spin += 1
        print(f"\r  {c(C.CYAN, spinner_frame(spin))}  Generando 7 gráficos... "
              f"{c(C.GRAY, f'{time.time()-t0:.1f}s')}", end="", flush=True)
        time.sleep(0.1)

    if error[0]:
        print(f"\r  {c(C.RED,'✗')}  Error: {error[0]}")
    else:
        elapsed = time.time() - t0
        print(f"\r  {c(C.GREEN,'✓')}  7 gráficos generados en "
              f"{c(C.WHITE+C.BOLD, f'{elapsed:.1f}s')}      ")
        figs = [f for f in os.listdir("figures") if f.endswith(".png")]
        for fig in sorted(figs):
            print(f"     {c(C.GRAY,'→')} figures/{c(C.CYAN, fig)}")

    if not quiet:
        press_enter()

def run_generate_graphs():
    do_generate_graphs(quiet=False)

# ─────────────────────────────────────────────
# Opción 5: Ver resultados
# ─────────────────────────────────────────────
def view_results():
    header()
    section("Resultados guardados")

    if not os.path.exists("results/all_results.csv"):
        print(f"\n  {c(C.RED,'✗')}  No hay resultados. Ejecuta los experimentos primero.")
        press_enter()
        return

    rows = []
    with open("results/all_results.csv", newline="") as f:
        for r in csv.DictReader(f):
            rows.append({k: (float(v) if k not in ("scenario","algorithm")
                             else v) for k, v in r.items()})

    # Mostrar tabla comparativa para carga alta
    for load in [100, 75, 50]:
        subset = [r for r in rows if int(r["load_mbps"]) == load]
        if subset:
            break

    section(f"Comparativa — {load} Mbps/ONU (32 ONUs)")
    print()
    print(f"  {c(C.GRAY, f'  {'T-CONT':<8} {'BasicDBA lat':>14} {'QosDBA lat':>14} {'Factor':>8} {'BasicDBA loss':>14} {'QosDBA loss':>12}')}")
    print(c(C.GRAY, "  " + "─" * (W - 2)))

    for tc in [1, 2, 4]:
        b = next((r for r in subset if r["algorithm"]=="basic" and int(r["tcont_type"])==tc), None)
        q = next((r for r in subset if r["algorithm"]=="qos"   and int(r["tcont_type"])==tc), None)
        if not (b and q): continue

        bl  = b["latency_mean_us"]
        ql  = q["latency_mean_us"]
        fac = bl / ql if ql > 0 else 0
        bls = b["loss_rate_mean"] * 100
        qls = q["loss_rate_mean"] * 100

        fac_col = C.RED if fac > 10 else (C.YELLOW if fac > 2 else C.GREEN)
        tc_name = {1:"T-CONT 1", 2:"T-CONT 2", 4:"T-CONT 4"}[tc]

        print(f"  {c(C.BOLD, tc_name):<8}  "
              f"{color_latency(bl, tc):>22}  "
              f"{color_latency(ql, tc):>22}  "
              f"{c(fac_col+C.BOLD, f'{fac:.0f}×'):>16}  "
              f"{c(C.GREEN if bls<0.01 else C.RED, f'{bls:.2f}%'):>22}  "
              f"{c(C.GREEN if qls<0.01 else C.RED, f'{qls:.2f}%'):>20}")

    # Tabla completa de T-CONT 1
    section("Evolución T-CONT 1 (VoIP) con la carga")
    print()
    print(f"  {c(C.GRAY, f'  {'Carga':<10} {'BasicDBA':>14} {'QosDBA':>14} {'Ratio':>8}')}")
    print(c(C.GRAY, "  " + "─" * 50))

    for load_val in [10, 25, 50, 75, 100]:
        b = next((r for r in rows if int(r["load_mbps"])==load_val
                  and r["algorithm"]=="basic" and int(r["tcont_type"])==1), None)
        q = next((r for r in rows if int(r["load_mbps"])==load_val
                  and r["algorithm"]=="qos"   and int(r["tcont_type"])==1), None)
        if not (b and q): continue
        bl = b["latency_mean_us"]
        ql = q["latency_mean_us"]
        ratio = bl / ql if ql else 0
        print(f"  {c(C.GRAY, f'{load_val:>3} Mbps/ONU')}  "
              f"{color_latency(bl, 1):>22}  "
              f"{color_latency(ql, 1):>22}  "
              f"{c(C.RED+C.BOLD if ratio > 10 else C.GRAY, f'{ratio:.0f}×'):>16}")

    print()
    mtime = os.path.getmtime("results/all_results.csv")
    dt    = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
    print(f"  {dim(f'Última actualización: {dt}  ·  {len(rows)} filas')}")
    press_enter()

# ─────────────────────────────────────────────
# Menú principal
# ─────────────────────────────────────────────
MENU_OPTIONS = [
    ("1", "Prueba rápida",          "QosDBA · 100 Mbps · 8 ONUs · ~2s",         run_quick_test),
    ("2", "Corrida personalizada",  "Elegir algoritmo, carga, ONUs, duración",   run_custom),
    ("3", "Experimentos completos", "100 corridas · 10 escenarios · ~15 min",    run_full_experiments),
    ("4", "Generar gráficos",       "Desde results/all_results.csv → figures/",  run_generate_graphs),
    ("5", "Ver resultados",         "Tabla comparativa BasicDBA vs QosDBA",      view_results),
]

def main_menu():
    while True:
        header()

        # Estado del proyecto
        has_results = os.path.exists("results/all_results.csv")
        has_figures = any(f.endswith(".png") for f in os.listdir("figures")) \
                      if os.path.isdir("figures") else False
        status = []
        status.append(c(C.GREEN,"✓ results/all_results.csv") if has_results
                      else c(C.GRAY,"○ sin resultados"))
        status.append(c(C.GREEN,"✓ figures/ (7 PNGs)") if has_figures
                      else c(C.GRAY,"○ sin gráficos"))
        print(f"  {c(C.GRAY,'Estado:')}  {'  ·  '.join(status)}")
        print()

        # Opciones
        for key, name, desc, _ in MENU_OPTIONS:
            print(f"  {c(C.CYAN+C.BOLD, f'[{key}]')}  {c(C.BOLD+C.WHITE, f'{name:<26}')}  "
                  f"{c(C.GRAY, desc)}")
        print()
        print(f"  {c(C.GRAY, '[0]')}  {c(C.GRAY, 'Salir')}")
        print()
        rule()

        try:
            choice = input(f"\n  {c(C.BOLD,'Opción → ')}").strip()
        except (KeyboardInterrupt, EOFError):
            choice = "0"

        if choice == "0":
            clr()
            print(f"\n  {c(C.CYAN,'Hasta luego. ¡Buena suerte en la entrevista!')}\n")
            break

        for key, _, _, fn in MENU_OPTIONS:
            if choice == key:
                fn()
                break
        else:
            # Opción inválida: breve flash y volver al menú
            pass

if __name__ == "__main__":
    main_menu()
