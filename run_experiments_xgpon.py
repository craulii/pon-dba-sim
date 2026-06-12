"""
Ejecuta todos los escenarios definidos en configs/scenarios_xgpon.json
(Fase 3 -- XG-PON, IPACT vs GIANT vs QoSDBA, 8 ONUs).

Por cada escenario corre `repetitions` repeticiones con seeds distintos.
Guarda resultados consolidados en results/xgpon_results.csv y, para los
escenarios IPACT, las muestras de duración de ciclo en
results/xgpon_cycle_times.csv.

Los 9 escenarios son independientes entre sí, así que se ejecutan en
paralelo (multiprocessing) -- IPACT en particular es computacionalmente
costoso (ciclos de polling de hasta ~1us de granularidad bajo sobrecarga).
"""
import csv
import json
import multiprocessing as mp
import os
import statistics
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))

from main_xgpon import load_config, build_config, run_simulation

SCENARIOS_PATH = os.path.join(os.path.dirname(__file__), "configs", "scenarios_xgpon.json")
CONFIG_PATH    = os.path.join(os.path.dirname(__file__), "configs", "xgpon.json")
RESULTS_DIR    = os.path.join(os.path.dirname(__file__), "results")


def _ci95(data):
    if len(data) < 2:
        return 0.0
    n = len(data)
    s = statistics.stdev(data)
    return 1.96 * s / (n ** 0.5)


def run_scenario(args):
    scenario, base_config, repetitions, seed_base, duration, warmup = args
    name      = scenario["name"]
    algorithm = scenario["algorithm"]
    num_onus  = scenario.get("num_onus", 8)
    load_mbps = scenario["tcont4_rate_mbps"]

    config = build_config(
        base            = base_config,
        num_onus        = num_onus,
        tcont4_rate_bps = load_mbps * 1_000_000,
        duration        = duration,
        warmup          = warmup,
    )

    rows = []
    cycle_rows = []
    rep_summaries = []

    print(f"  -> {name} (alg={algorithm}, load={load_mbps} Mbps/ONU): iniciando "
          f"{repetitions} repeticiones...", flush=True)
    t_start = time.time()

    for rep in range(repetitions):
        seed = seed_base + rep
        rep_t0 = time.time()
        summary = run_simulation(config, algorithm, seed, verbose=False)
        rep_summaries.append(summary)
        print(f"     {name}: rep {rep+1}/{repetitions} OK "
              f"({time.time()-rep_t0:.1f}s, acumulado {time.time()-t_start:.1f}s)",
              flush=True)

        if algorithm == "ipact":
            for ct_s in summary.get("cycle_time_samples", []):
                cycle_rows.append({
                    "scenario":  name,
                    "algorithm": algorithm,
                    "load_mbps": load_mbps,
                    "seed":      seed,
                    "cycle_time_us": ct_s * 1e6,
                })

    # Agregar resultados de todas las repeticiones, por T-CONT
    for tc in [1, 2, 4]:
        lats, p99s, maxs, jits, tputs, losses, slas = [], [], [], [], [], [], []

        for s in rep_summaries:
            tc_lats, tc_p99s, tc_maxs, tc_jits, tc_tputs, tc_slas = [], [], [], [], [], []
            for onu_id in range(num_onus):
                key = (onu_id, tc)
                if key in s and s[key]["n_packets"] > 0:
                    m = s[key]
                    tc_lats.append(m["latency_mean_us"])
                    tc_p99s.append(m["latency_p99_us"])
                    tc_maxs.append(m["latency_max_us"])
                    tc_jits.append(m["jitter_mean_us"])
                    tc_tputs.append(m["throughput_mbps"])
                    if m["sla_compliance_pct"] is not None:
                        tc_slas.append(m["sla_compliance_pct"])
                ds = s.get("drop_stats", {}).get(key)
                if ds and ds["pkts_generated"] > 0:
                    losses.append(ds["loss_rate"])

            if tc_lats:
                lats.append(statistics.mean(tc_lats))
                p99s.append(statistics.mean(tc_p99s))
                maxs.append(statistics.mean(tc_maxs))
                jits.append(statistics.mean(tc_jits))
                tputs.append(sum(tc_tputs))
            if tc_slas:
                slas.append(statistics.mean(tc_slas))

        if not lats:
            continue

        row = {
            "scenario":           name,
            "algorithm":          algorithm,
            "load_mbps":          load_mbps,
            "num_onus":           num_onus,
            "tcont_type":         tc,
            "repetitions":        len(lats),
            "latency_mean_us":    statistics.mean(lats),
            "latency_mean_ci95":  _ci95(lats),
            "latency_p99_us":     statistics.mean(p99s),
            "latency_p99_ci95":   _ci95(p99s),
            "latency_max_us":     statistics.mean(maxs),
            "latency_max_ci95":   _ci95(maxs),
            "jitter_mean_us":     statistics.mean(jits),
            "throughput_mbps":    statistics.mean(tputs),
            "loss_rate_mean":     statistics.mean(losses) if losses else 0.0,
            "loss_rate_ci95":     _ci95(losses) if losses else 0.0,
            "sla_compliance_pct": statistics.mean(slas) if slas else "",
            "sla_compliance_ci95":_ci95(slas) if slas else 0.0,
        }
        rows.append(row)

    print(f"  [OK] {name} (alg={algorithm}, load={load_mbps} Mbps/ONU) -- "
          f"{len(rows)} filas, {len(cycle_rows)} muestras de ciclo, "
          f"total {time.time()-t_start:.1f}s", flush=True)

    return rows, cycle_rows


def run_all():
    os.makedirs(RESULTS_DIR, exist_ok=True)

    with open(SCENARIOS_PATH) as f:
        scenarios_cfg = json.load(f)

    base_config = load_config(CONFIG_PATH)
    sim_cfg     = base_config["simulation"]
    repetitions = sim_cfg.get("repetitions", 10)
    seed_base   = sim_cfg.get("seed_base", 6767)
    duration    = sim_cfg.get("duration_s", 10.0)
    warmup      = sim_cfg.get("warmup_s", 1.0)

    scenarios = scenarios_cfg["scenarios"]
    tasks = [(s, base_config, repetitions, seed_base, duration, warmup) for s in scenarios]

    n_proc = min(len(scenarios), os.cpu_count() or 1)
    print(f"Ejecutando {len(scenarios)} escenarios x {repetitions} repeticiones "
          f"({n_proc} procesos en paralelo)...", flush=True)

    all_rows = []
    cycle_rows = []
    with mp.Pool(processes=n_proc) as pool:
        for rows, c_rows in pool.imap(run_scenario, tasks):
            all_rows.extend(rows)
            cycle_rows.extend(c_rows)

    # Mantener el orden original de configs/scenarios_xgpon.json
    order = {s["name"]: i for i, s in enumerate(scenarios)}
    all_rows.sort(key=lambda r: (order[r["scenario"]], r["tcont_type"]))

    # Guardar CSV consolidado
    if all_rows:
        out_path = os.path.join(RESULTS_DIR, "xgpon_results.csv")
        with open(out_path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(all_rows[0].keys()))
            w.writeheader()
            w.writerows(all_rows)
        print(f"\nResultados consolidados guardados en: {out_path}")
    else:
        print("\nNo se generaron resultados.")

    # Guardar muestras de cycle time (solo IPACT)
    if cycle_rows:
        out_path = os.path.join(RESULTS_DIR, "xgpon_cycle_times.csv")
        with open(out_path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(cycle_rows[0].keys()))
            w.writeheader()
            w.writerows(cycle_rows)
        print(f"Cycle times (IPACT) guardados en: {out_path}")


if __name__ == "__main__":
    run_all()
