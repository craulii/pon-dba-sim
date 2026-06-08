"""
Punto de entrada principal del simulador GPON DBA.

Uso:
  python main.py --algorithm basic --load 50 --seed 42
  python main.py --algorithm qos   --load 100 --num-onus 32 --duration 10
"""
import argparse
import copy
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(__file__))

from simulator.engine   import (SimEngine, EVT_OLT_BWMAP, EVT_ONU_RECV_BWMAP,
                                 EVT_ONU_GEN_TRAFFIC, EVT_OLT_RECV_DATA,
                                 EVT_OLT_RECV_REPORT)
from simulator.olt      import OLT
from simulator.onu      import ONU
from simulator.dba_basic import BasicDBA
from simulator.dba_qos   import QoSDBA
from metrics.collector   import MetricsCollector


CONFIG_PATH    = os.path.join(os.path.dirname(__file__), "configs", "default.json")
RESULTS_DIR    = os.path.join(os.path.dirname(__file__), "results")


def load_config(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def build_config(base: dict, num_onus: int, tcont4_rate_bps: int,
                 duration: float, warmup: float) -> dict:
    cfg = copy.deepcopy(base)
    cfg["gpon"]["num_onus"]              = num_onus
    cfg["tconts"]["4"]["rate_bps"]       = tcont4_rate_bps
    cfg["simulation"]["duration_s"]      = duration
    cfg["simulation"]["warmup_s"]        = warmup
    return cfg


def run_simulation(config: dict, algorithm: str, seed: int,
                   verbose: bool = False) -> dict:
    """
    Ejecuta una corrida completa del simulador.
    Retorna el dict de métricas calculadas.
    """
    random.seed(seed)

    num_onus  = config["gpon"]["num_onus"]
    duration  = config["simulation"]["duration_s"]
    warmup    = config["simulation"]["warmup_s"]

    engine  = SimEngine()
    metrics = MetricsCollector(warmup_s=warmup)

    # Instanciar DBA
    if algorithm == "qos":
        dba = QoSDBA()
    else:
        dba = BasicDBA()

    # Instanciar OLT
    olt = OLT(
        engine          = engine,
        num_onus        = num_onus,
        dba_algorithm   = dba,
        config          = config,
        metrics_collector = metrics,
    )

    # Instanciar ONUs
    onus = []
    for i in range(num_onus):
        onu = ONU(
            onu_id            = i,
            engine            = engine,
            config            = config,
            metrics_collector = metrics,
        )
        onus.append(onu)

    # Registrar handlers en el motor
    engine.register(EVT_OLT_BWMAP,       olt.on_generate_bwmap)
    engine.register(EVT_OLT_RECV_DATA,   olt.on_receive_data)
    engine.register(EVT_OLT_RECV_REPORT, olt.on_receive_report)

    # Handlers de ONUs: despachar por onu_id
    def dispatch_bwmap(evt):
        onu_id = evt.data["onu_id"]
        onus[onu_id].on_receive_bwmap(evt)

    def dispatch_traffic(evt):
        onu_id = evt.data["onu_id"]
        onus[onu_id].on_generate_traffic(evt)

    engine.register(EVT_ONU_RECV_BWMAP,  dispatch_bwmap)
    engine.register(EVT_ONU_GEN_TRAFFIC, dispatch_traffic)

    # Correr simulación
    processed = engine.run(until=duration)

    if verbose:
        print(f"  Eventos procesados: {processed:,}")
        print(f"  Tiempo final:       {engine.now:.6f} s")

    # Recopilar métricas
    summary = metrics.summary(duration)

    # Agregar drop stats de cada ONU
    drop_stats = {}
    for onu in onus:
        for tc_type, stats in onu.get_drop_stats().items():
            key = (onu.onu_id, tc_type)
            drop_stats[key] = stats
    summary["drop_stats"] = drop_stats

    return summary


def main():
    parser = argparse.ArgumentParser(description="Simulador GPON DBA — TEL-341 OmneTeam")
    parser.add_argument("--algorithm",  choices=["basic", "qos"], default="qos")
    parser.add_argument("--load",       type=int,   default=50,
                        help="Tasa T-CONT 4 en Mbps (default: 50)")
    parser.add_argument("--num-onus",   type=int,   default=32)
    parser.add_argument("--duration",   type=float, default=10.0)
    parser.add_argument("--warmup",     type=float, default=1.0)
    parser.add_argument("--seed",       type=int,   default=42)
    parser.add_argument("--output",     type=str,   default=None,
                        help="Archivo CSV de salida (opcional)")
    parser.add_argument("--verbose",    action="store_true")
    args = parser.parse_args()

    base_config = load_config(CONFIG_PATH)
    config = build_config(
        base          = base_config,
        num_onus      = args.num_onus,
        tcont4_rate_bps = args.load * 1_000_000,
        duration      = args.duration,
        warmup        = args.warmup,
    )

    print(f"Simulando: algoritmo={args.algorithm}, carga T-CONT4={args.load} Mbps, "
          f"ONUs={args.num_onus}, seed={args.seed}")

    summary = run_simulation(config, args.algorithm, args.seed, verbose=args.verbose)

    # Mostrar resumen por T-CONT
    print(f"\n{'T-CONT':<8} {'Lat.media(μs)':<16} {'P99(μs)':<12} "
          f"{'Jitter(μs)':<13} {'Thrput(Mbps)':<14} {'LossRate'}")
    print("-" * 75)

    for tc in [1, 2, 4]:
        # Agregar sobre todas las ONUs
        lats, p99s, jits, tputs, losses = [], [], [], [], []
        for onu_id in range(args.num_onus):
            key = (onu_id, tc)
            if key in summary:
                m = summary[key]
                if m["n_packets"] > 0:
                    lats.append(m["latency_mean_us"])
                    p99s.append(m["latency_p99_us"])
                    jits.append(m["jitter_mean_us"])
                    tputs.append(m["throughput_mbps"])
            ds = summary.get("drop_stats", {}).get(key)
            if ds:
                losses.append(ds["loss_rate"])

        if lats:
            import statistics as st
            print(f"T-CONT {tc}  "
                  f"{st.mean(lats):<16.1f}"
                  f"{st.mean(p99s):<12.1f}"
                  f"{st.mean(jits):<13.1f}"
                  f"{sum(tputs):<14.2f}"
                  f"{st.mean(losses) if losses else 0:.4f}")

    util = summary.get("channel_utilization", 0)
    print(f"\nUtilización canal upstream: {util*100:.1f}%")

    # Exportar CSV si se pide
    if args.output:
        os.makedirs(RESULTS_DIR, exist_ok=True)
        out_path = os.path.join(RESULTS_DIR, args.output)
        from metrics.collector import MetricsCollector as MC
        # Re-exportar directamente desde summary
        import csv
        rows = []
        for key, m in summary.items():
            if isinstance(key, tuple) and len(key) == 2:
                row = {
                    "algorithm":   args.algorithm,
                    "load_mbps":   args.load,
                    "seed":        args.seed,
                    **m,
                }
                rows.append(row)
        if rows:
            with open(out_path, "w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                w.writeheader()
                w.writerows(rows)
            print(f"\nResultados guardados en: {out_path}")


if __name__ == "__main__":
    main()
