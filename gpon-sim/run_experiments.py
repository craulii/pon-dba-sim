"""
Ejecuta todos los escenarios definidos en configs/scenarios.json.
Por cada escenario corre 10 repeticiones con seeds distintos.
Guarda resultados individuales en results/ como CSV.
"""
import copy
import csv
import json
import os
import random
import statistics
import sys

sys.path.insert(0, os.path.dirname(__file__))

from main import load_config, build_config, run_simulation

SCENARIOS_PATH = os.path.join(os.path.dirname(__file__), "configs", "scenarios.json")
CONFIG_PATH    = os.path.join(os.path.dirname(__file__), "configs", "default.json")
RESULTS_DIR    = os.path.join(os.path.dirname(__file__), "results")


def run_all():
    os.makedirs(RESULTS_DIR, exist_ok=True)

    with open(SCENARIOS_PATH) as f:
        scenarios_cfg = json.load(f)

    base_config = load_config(CONFIG_PATH)
    sim_cfg     = base_config["simulation"]
    repetitions = sim_cfg.get("repetitions", 10)
    seed_base   = sim_cfg.get("seed_base", 42)
    duration    = sim_cfg.get("duration_s", 10.0)
    warmup      = sim_cfg.get("warmup_s", 1.0)

    all_rows = []

    for scenario in scenarios_cfg["scenarios"]:
        name      = scenario["name"]
        algorithm = scenario["algorithm"]
        num_onus  = scenario.get("num_onus", 32)
        load_mbps = scenario["tcont4_rate_mbps"]

        config = build_config(
            base            = base_config,
            num_onus        = num_onus,
            tcont4_rate_bps = load_mbps * 1_000_000,
            duration        = duration,
            warmup          = warmup,
        )

        print(f"\n{'='*60}")
        print(f"Escenario: {name}  (alg={algorithm}, load={load_mbps} Mbps)")

        rep_summaries = []
        for rep in range(repetitions):
            seed = seed_base + rep
            print(f"  Rep {rep+1}/{repetitions} seed={seed} ...", end=" ", flush=True)
            summary = run_simulation(config, algorithm, seed, verbose=False)
            rep_summaries.append(summary)
            print("OK")

        # Agregar resultados de todas las repeticiones
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

            def _ci95(data):
                if len(data) < 2:
                    return 0.0
                n  = len(data)
                s  = statistics.stdev(data)
                return 1.96 * s / (n ** 0.5)

            row = {
                "scenario":         name,
                "algorithm":        algorithm,
                "load_mbps":        load_mbps,
                "num_onus":         num_onus,
                "tcont_type":       tc,
                "repetitions":      len(lats),
                "latency_mean_us":  statistics.mean(lats),
                "latency_mean_ci95":_ci95(lats),
                "latency_p99_us":   statistics.mean(p99s),
                "latency_p99_ci95": _ci95(p99s),
                "jitter_mean_us":   statistics.mean(jits),
                "throughput_mbps":  statistics.mean(tputs),
                "loss_rate_mean":   statistics.mean(losses) if losses else 0.0,
                "loss_rate_ci95":   _ci95(losses) if losses else 0.0,
            }
            all_rows.append(row)

            print(f"  T-CONT {tc}: lat={row['latency_mean_us']:.1f}±"
                  f"{row['latency_mean_ci95']:.1f} μs  "
                  f"P99={row['latency_p99_us']:.1f} μs  "
                  f"loss={row['loss_rate_mean']:.4f}")

    # Guardar CSV consolidado
    if all_rows:
        out_path = os.path.join(RESULTS_DIR, "all_results.csv")
        with open(out_path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(all_rows[0].keys()))
            w.writeheader()
            w.writerows(all_rows)
        print(f"\nResultados consolidados guardados en: {out_path}")
    else:
        print("\nNo se generaron resultados.")


if __name__ == "__main__":
    run_all()
