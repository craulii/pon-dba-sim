"""
Punto de entrada XG-PON (Fase 3) -- TEL-341 OmneTeam.

Compara 3 algoritmos DBA bajo XG-PON1 (ITU-T G.987), 8 ONUs idénticas:
  - ipact: polling round-robin de ciclo variable (adaptado de EPON)
  - giant: GPA/SPA con contadores SImax/SImin (nativo GPON/XG-PON)
  - qos:   QoSDBA de Fase 2, re-parametrizado a XG-PON/8 ONUs

Uso:
  python main_xgpon.py --algorithm ipact --load 400 --seed 6767
  python main_xgpon.py --algorithm giant --load 800
  python main_xgpon.py --algorithm qos   --load 200
"""
import argparse
import copy
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(__file__))

from simulator.engine    import (SimEngine, EVT_OLT_BWMAP, EVT_ONU_RECV_BWMAP,
                                  EVT_ONU_GEN_TRAFFIC, EVT_OLT_RECV_DATA,
                                  EVT_OLT_RECV_REPORT, EVT_OLT_SEND_GATE,
                                  EVT_OLT_POLL_NEXT, EVT_ONU_RECV_GATE)
from simulator.olt        import OLT
from simulator.olt_ipact  import OLTPolling
from simulator.onu        import ONU
from simulator.dba_qos    import QoSDBA
from simulator.dba_giant  import GiantDBA
from simulator.dba_ipact  import IpactDBA
from metrics.collector    import MetricsCollector


CONFIG_PATH = os.path.join(os.path.dirname(__file__), "configs", "xgpon.json")
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")


def load_config(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def build_config(base: dict, num_onus: int, tcont4_rate_bps: int,
                 duration: float, warmup: float) -> dict:
    cfg = copy.deepcopy(base)
    cfg["gpon"]["num_onus"]         = num_onus
    cfg["tconts"]["4"]["rate_bps"]  = tcont4_rate_bps
    cfg["simulation"]["duration_s"] = duration
    cfg["simulation"]["warmup_s"]   = warmup
    return cfg


def run_simulation(config: dict, algorithm: str, seed: int,
                   verbose: bool = False) -> dict:
    """
    Ejecuta una corrida completa del simulador XG-PON.
    Retorna el dict de métricas calculadas.
    """
    random.seed(seed)

    num_onus = config["gpon"]["num_onus"]
    duration = config["simulation"]["duration_s"]
    warmup   = config["simulation"]["warmup_s"]

    sla_bounds = {int(k): v["max_delay_s"] for k, v in config.get("sla", {}).items()}

    engine  = SimEngine()
    metrics = MetricsCollector(warmup_s=warmup, sla_bounds_s=sla_bounds)

    # Instanciar ONUs (idénticas, T-CONT1/2/4)
    onus = []
    for i in range(num_onus):
        onu = ONU(
            onu_id            = i,
            engine            = engine,
            config            = config,
            metrics_collector = metrics,
        )
        onus.append(onu)

    def dispatch_traffic(evt):
        onu_id = evt.data["onu_id"]
        onus[onu_id].on_generate_traffic(evt)

    engine.register(EVT_ONU_GEN_TRAFFIC, dispatch_traffic)

    if algorithm == "ipact":
        dba = IpactDBA()
        olt = OLTPolling(
            engine            = engine,
            num_onus          = num_onus,
            dba_algorithm     = dba,
            config            = config,
            metrics_collector = metrics,
        )

        engine.register(EVT_OLT_SEND_GATE,   olt.on_send_gate)
        engine.register(EVT_OLT_POLL_NEXT,   olt.on_poll_next)
        engine.register(EVT_OLT_RECV_DATA,   olt.on_receive_data)
        engine.register(EVT_OLT_RECV_REPORT, olt.on_receive_report)

        def dispatch_gate(evt):
            onu_id = evt.data["onu_id"]
            onus[onu_id].on_receive_gate(evt)

        engine.register(EVT_ONU_RECV_GATE, dispatch_gate)

    else:
        dba_cls = {"giant": GiantDBA, "qos": QoSDBA}[algorithm]
        dba = dba_cls()
        olt = OLT(
            engine            = engine,
            num_onus          = num_onus,
            dba_algorithm     = dba,
            config            = config,
            metrics_collector = metrics,
        )

        engine.register(EVT_OLT_BWMAP,       olt.on_generate_bwmap)
        engine.register(EVT_OLT_RECV_DATA,   olt.on_receive_data)
        engine.register(EVT_OLT_RECV_REPORT, olt.on_receive_report)

        def dispatch_bwmap(evt):
            onu_id = evt.data["onu_id"]
            onus[onu_id].on_receive_bwmap(evt)

        engine.register(EVT_ONU_RECV_BWMAP, dispatch_bwmap)

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
    parser = argparse.ArgumentParser(
        description="Simulador XG-PON DBA (Fase 3) -- TEL-341 OmneTeam")
    parser.add_argument("--algorithm", choices=["ipact", "giant", "qos"], default="qos")
    parser.add_argument("--load",      type=int,   default=400,
                        help="Tasa T-CONT4 en Mbps/ONU (default: 400)")
    parser.add_argument("--num-onus",  type=int,   default=8)
    parser.add_argument("--duration",  type=float, default=10.0)
    parser.add_argument("--warmup",    type=float, default=1.0)
    parser.add_argument("--seed",      type=int,   default=6767)
    parser.add_argument("--output",    type=str,   default=None,
                        help="Archivo CSV de salida (opcional)")
    parser.add_argument("--verbose",   action="store_true")
    args = parser.parse_args()

    base_config = load_config(CONFIG_PATH)
    config = build_config(
        base            = base_config,
        num_onus        = args.num_onus,
        tcont4_rate_bps = args.load * 1_000_000,
        duration        = args.duration,
        warmup          = args.warmup,
    )

    print(f"Simulando XG-PON: algoritmo={args.algorithm}, carga T-CONT4={args.load} Mbps/ONU, "
          f"ONUs={args.num_onus}, seed={args.seed}")

    summary = run_simulation(config, args.algorithm, args.seed, verbose=args.verbose)

    # Mostrar resumen por T-CONT, incluyendo delay máximo y % cumplimiento SLA
    print(f"\n{'T-CONT':<8} {'Lat.media(us)':<14} {'P99(us)':<10} {'Max(us)':<10} "
          f"{'SLA%':<8} {'Thrput(Mbps)':<13} {'LossRate'}")
    print("-" * 80)

    for tc in [1, 2, 4]:
        lats, p99s, maxs, slas, tputs, losses = [], [], [], [], [], []
        for onu_id in range(args.num_onus):
            key = (onu_id, tc)
            if key in summary and summary[key]["n_packets"] > 0:
                m = summary[key]
                lats.append(m["latency_mean_us"])
                p99s.append(m["latency_p99_us"])
                maxs.append(m["latency_max_us"])
                if m["sla_compliance_pct"] is not None:
                    slas.append(m["sla_compliance_pct"])
                tputs.append(m["throughput_mbps"])
            ds = summary.get("drop_stats", {}).get(key)
            if ds:
                losses.append(ds["loss_rate"])

        if lats:
            import statistics as st
            sla_str = f"{st.mean(slas):.1f}%" if slas else "n/a"
            print(f"T-CONT {tc}  "
                  f"{st.mean(lats):<14.1f}"
                  f"{st.mean(p99s):<10.1f}"
                  f"{st.mean(maxs):<10.1f}"
                  f"{sla_str:<8}"
                  f"{sum(tputs):<13.2f}"
                  f"{st.mean(losses) if losses else 0:.4f}")

    util = summary.get("channel_utilization", 0)
    print(f"\nUtilizacion canal upstream: {util*100:.1f}%")

    if summary.get("cycle_time_samples"):
        print(f"Cycle time (IPACT): mean={summary['cycle_time_mean_us']:.1f}us "
              f"min={summary['cycle_time_min_us']:.1f}us "
              f"max={summary['cycle_time_max_us']:.1f}us "
              f"p99={summary['cycle_time_p99_us']:.1f}us")

    # Exportar CSV si se pide
    if args.output:
        os.makedirs(RESULTS_DIR, exist_ok=True)
        out_path = os.path.join(RESULTS_DIR, args.output)
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
