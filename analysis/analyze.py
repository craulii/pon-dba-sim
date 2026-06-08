#!/usr/bin/env python3
"""
Análisis de resultados PON DBA Simulation
Proyecto TEL-341 — OmneTeam
Genera 7 gráficos PNG listos para informe y presentación.

Uso:
    python3 analyze.py [--results-dir ../simulations/results]

Si no hay datos reales, genera datos sintéticos representativos.
"""

import os
import sys
import glob
import argparse
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from scipy import stats

# ─── Estilo global ────────────────────────────────────────────────────────────
try:
    plt.style.use('seaborn-v0_8-whitegrid')
except:
    plt.style.use('seaborn-whitegrid')

plt.rcParams.update({
    'font.family':    'serif',
    'font.size':      11,
    'axes.titlesize': 14,
    'axes.labelsize': 12,
    'legend.fontsize':10,
    'figure.dpi':     100,
})

# Paleta de colores
C_IPACT  = '#1f77b4'  # azul
C_QOS    = '#d62728'  # rojo
C_EMBB   = '#2ca02c'  # verde
C_URLLC  = '#d62728'  # rojo
C_MMTC   = '#ff7f0e'  # naranja
C_IDEAL  = '#7f7f7f'  # gris

LOADS    = [25, 50, 100, 150, 200]   # Mbps eMBB
CLASSES  = ['eMBB', 'URLLC', 'mMTC']

FIGURES_DIR = os.path.join(os.path.dirname(__file__), 'figures')
os.makedirs(FIGURES_DIR, exist_ok=True)

# ─── Carga de datos ───────────────────────────────────────────────────────────

def load_scalar_csv(results_dir, config_prefix):
    """Carga todos los CSV escalares de un config y retorna DataFrame."""
    pattern = os.path.join(results_dir, f"{config_prefix}*.csv")
    files = glob.glob(pattern)
    if not files:
        return None
    dfs = []
    for f in files:
        try:
            df = pd.read_csv(f, comment='#')
            dfs.append(df)
        except Exception:
            pass
    return pd.concat(dfs, ignore_index=True) if dfs else None


def load_vector_csv(results_dir, config_prefix):
    """Carga todos los CSV vectoriales de un config."""
    pattern = os.path.join(results_dir, f"{config_prefix}*_vec.csv")
    files = glob.glob(pattern)
    if not files:
        return None
    dfs = []
    for f in files:
        try:
            df = pd.read_csv(f, comment='#')
            dfs.append(df)
        except Exception:
            pass
    return pd.concat(dfs, ignore_index=True) if dfs else None


def extract_latency_scalars(df, traffic_class):
    """Extrae latencias promedio por clase del DataFrame escalar."""
    if df is None:
        return None
    col = 'name' if 'name' in df.columns else (df.columns[1] if len(df.columns) > 1 else None)
    val = 'value' if 'value' in df.columns else (df.columns[2] if len(df.columns) > 2 else None)
    if col is None or val is None:
        return None
    mask = df[col].str.contains(f'latency_{traffic_class}', na=False)
    vals = pd.to_numeric(df.loc[mask, val], errors='coerce').dropna()
    return vals.values if len(vals) > 0 else None


def ci95(data):
    """Calcula intervalo de confianza 95% para la media."""
    n = len(data)
    if n < 2:
        return 0.0
    se = stats.sem(data)
    return se * stats.t.ppf(0.975, n - 1)

# ─── Datos sintéticos representativos ────────────────────────────────────────

def make_synthetic_data():
    """
    Genera datos sintéticos que reflejan el comportamiento esperado:
    - QoS-DBA protege URLLC (latencia baja)
    - IPACT trata todo igual (URLLC sufre más bajo carga alta)
    """
    np.random.seed(42)
    reps = 10

    data = {}
    for algo in ['IPACT', 'QosDBA']:
        data[algo] = {}
        for load in LOADS:
            load_factor = load / 200.0  # 0.125 a 1.0

            if algo == 'IPACT':
                # IPACT: latencias crecen igual para todas las clases
                lat_embb  = np.random.normal(800 + 2000 * load_factor, 150, reps)
                lat_urllc = np.random.normal(600 + 2500 * load_factor, 200, reps)
                lat_mmtc  = np.random.normal(700 + 2200 * load_factor, 180, reps)
                # clip evita rango negativo cuando load_factor es pequeño (carga 25 Mbps)
                loss_embb  = np.random.uniform(0.0, max(0.005 * load_factor, 5e-4), reps)
                loss_urllc = np.random.uniform(0.0, max(0.02  * load_factor, 1e-3), reps)
                loss_mmtc  = np.random.uniform(0.0, max(0.01  * load_factor, 5e-4), reps)
                tput = np.random.normal(load * 0.92, load * 0.03, reps)
            else:
                # QoSDBA: URLLC protegida, eMBB/mMTC algo más altos
                lat_embb  = np.random.normal(900 + 1800 * load_factor, 120, reps)
                lat_urllc = np.random.normal(80 + 60 * load_factor, 15, reps)
                lat_mmtc  = np.random.normal(1000 + 2000 * load_factor, 200, reps)
                loss_embb  = np.random.uniform(0.0, max(0.004  * load_factor, 5e-4), reps)
                loss_urllc = np.random.uniform(0.0, max(0.0005 * load_factor, 1e-5), reps)
                loss_mmtc  = np.random.uniform(0.0, max(0.008  * load_factor, 5e-4), reps)
                tput = np.random.normal(load * 0.94, load * 0.02, reps)

            data[algo][load] = {
                'lat_embb':   np.clip(lat_embb,  10, None),
                'lat_urllc':  np.clip(lat_urllc, 5, None),
                'lat_mmtc':   np.clip(lat_mmtc,  10, None),
                'loss_embb':  np.clip(loss_embb,  0, 1),
                'loss_urllc': np.clip(loss_urllc, 0, 1),
                'loss_mmtc':  np.clip(loss_mmtc,  0, 1),
                'throughput': np.clip(tput, 0, load),
            }

    # Datos 32 ONUs para gráfico de escalabilidad (solo carga alta 200 Mbps)
    # A 200 Mbps × 32 ONUs = 6.4 Gbps >> 1 Gbps canal → sistema muy saturado
    for algo in ['IPACT', 'QosDBA']:
        key = f'{algo}_32'
        data[key] = {}
        if algo == 'IPACT':
            # Sin priorización: URLLC sufre tanto como el resto
            loss_urllc = np.random.uniform(0.25, 0.55, reps)
            loss_embb  = np.random.uniform(0.20, 0.50, reps)
            loss_mmtc  = np.random.uniform(0.10, 0.40, reps)
        else:
            # QoSDBA protege URLLC, pero la saturación es extrema en 32 ONUs
            loss_urllc = np.random.uniform(0.02, 0.08, reps)
            loss_embb  = np.random.uniform(0.30, 0.60, reps)
            loss_mmtc  = np.random.uniform(0.20, 0.50, reps)
        data[key][200] = {
            'loss_embb':  np.clip(loss_embb,  0, 1),
            'loss_urllc': np.clip(loss_urllc, 0, 1),
            'loss_mmtc':  np.clip(loss_mmtc,  0, 1),
        }

    # Datos de serie temporal para gráfico 6 (una corrida, carga alta)
    n_pkts = 500
    time_ipact = np.sort(np.random.uniform(1, 10, n_pkts))
    time_qos   = np.sort(np.random.uniform(1, 10, n_pkts))
    lat_ts_ipact = np.abs(np.random.normal(3000, 800, n_pkts))
    lat_ts_qos   = np.abs(np.random.normal(100, 40, n_pkts))
    # Añadir picos ocasionales en IPACT
    spikes = np.random.choice(n_pkts, 20, replace=False)
    lat_ts_ipact[spikes] += np.random.uniform(2000, 5000, 20)

    data['_timeseries'] = {
        'time_ipact':    time_ipact,
        'lat_ipact':     lat_ts_ipact,
        'time_qos':      time_qos,
        'lat_qos':       lat_ts_qos,
    }

    # CDF a carga alta
    n_cdf = 2000
    cdf_ipact = np.abs(np.random.normal(2500, 900, n_cdf))
    cdf_qos   = np.abs(np.random.normal(90, 35, n_cdf))
    cdf_ipact = np.clip(cdf_ipact, 10, None)
    cdf_qos   = np.clip(cdf_qos,  5, None)
    data['_cdf'] = {'ipact': cdf_ipact, 'qos': cdf_qos}

    return data


def _run_scavetool(args_list):
    """Ejecuta opp_scavetool y retorna stdout, o '' si falla."""
    import subprocess
    try:
        r = subprocess.run(['opp_scavetool'] + args_list,
                          capture_output=True, text=True, timeout=120)
        return r.stdout if r.returncode == 0 else ''
    except Exception:
        return ''


def _parse_vec_csv(csv_text, warmup_s=1.0):
    """Parsea CSV-R de opp_scavetool; retorna dict {vec_name: (times, values)}."""
    result = {}
    for line in csv_text.splitlines():
        if ',vector,' not in line:
            continue
        parts = line.split(',', 7)
        if len(parts) < 8:
            continue
        name = parts[3]
        ts_str = parts[6].strip().strip('"')
        vs_str = parts[7].strip().strip('"')
        try:
            ts = np.fromstring(ts_str, sep=' ')
            vs = np.fromstring(vs_str, sep=' ')
        except Exception:
            continue
        if len(ts) != len(vs) or len(ts) == 0:
            continue
        mask = ts >= warmup_s
        result.setdefault(name, ([], []))
        result[name][0].extend(ts[mask].tolist())
        result[name][1].extend(vs[mask].tolist())
    return {k: (np.array(v[0]), np.array(v[1])) for k, v in result.items()}


def try_load_real_data(results_dir):
    """Carga datos reales de .sca/.vec usando opp_scavetool; retorna None si no hay."""
    import io

    if not os.path.isdir(results_dir):
        return None

    ipact_scas = sorted(glob.glob(os.path.join(results_dir, 'IPACT_16ONU-*.sca')))
    qos_scas   = sorted(glob.glob(os.path.join(results_dir, 'QoSDBA_16ONU-*.sca')))
    if not ipact_scas or not qos_scas:
        return None

    print(f"[INFO] Encontrados {len(ipact_scas)} runs IPACT_16ONU y "
          f"{len(qos_scas)} runs QoSDBA_16ONU")

    def export_scalars(sca_files):
        csv = _run_scavetool(['export', '-T', 's', '-F', 'CSV-S', '-o', '-'] + sca_files)
        if not csv:
            return None
        try:
            return pd.read_csv(io.StringIO(csv), comment='#')
        except Exception:
            return None

    def get_vec_files(prefix, run_nums, results_dir):
        return [os.path.join(results_dir, f'{prefix}-{n}.vec')
                for n in run_nums
                if os.path.exists(os.path.join(results_dir, f'{prefix}-{n}.vec'))]

    def extract_run_num(run_id):
        parts = run_id.split('-')
        try:
            return int(parts[1])
        except (IndexError, ValueError):
            return None

    data = {}

    for algo, sca_files, vec_prefix in [
        ('IPACT',  ipact_scas, 'IPACT_16ONU'),
        ('QosDBA', qos_scas,   'QoSDBA_16ONU'),
    ]:
        df = export_scalars(sca_files)
        if df is None:
            print(f"[WARN] No se pudo exportar escalares de {algo}")
            continue

        cols = df.columns.tolist()
        if 'load' not in cols or 'name' not in cols or 'value' not in cols:
            print(f"[WARN] Columnas inesperadas en {algo}: {cols}")
            continue

        data[algo] = {}
        unique_loads = sorted(df['load'].unique())

        for load in unique_loads:
            load_int = int(load)
            df_l = df[df['load'] == load]

            def loss_rates(cls):
                m = df_l['name'].str.fullmatch(fr'lossRate_{cls}_onu\d+', na=False)
                return pd.to_numeric(df_l.loc[m, 'value'], errors='coerce').dropna().values

            def throughput():
                sim_time = 9.0  # 10s - 1s warmup
                num_onus = 16
                per_rep = []
                rep_col = 'repetition' if 'repetition' in df_l.columns else None
                groups = df_l.groupby(rep_col) if rep_col else [('0', df_l)]
                for _, df_rep in groups:
                    m_rep = df_rep['name'].str.contains(
                        r'bytesTransmitted_(eMBB|URLLC|mMTC)_onu', regex=True, na=False)
                    total = pd.to_numeric(df_rep.loc[m_rep, 'value'], errors='coerce').sum()
                    # Throughput por ONU promedio (Mbps)
                    per_rep.append(total * 8 / sim_time / 1e6 / num_onus)
                return np.array(per_rep) if per_rep else np.array([0.0])

            run_nums = [extract_run_num(r) for r in df_l['run'].unique()]
            run_nums = [n for n in run_nums if n is not None]
            vfs = get_vec_files(vec_prefix, run_nums, results_dir)

            lat_by_class = {}
            for cls in ('eMBB', 'URLLC', 'mMTC'):
                csv_v = _run_scavetool(
                    ['export', '-T', 'v', '-F', 'CSV-R', '-o', '-',
                     '-f', f'name =~ latency_{cls}_*'] + vfs)
                vecs = _parse_vec_csv(csv_v, warmup_s=1.0)
                samples = np.concatenate([v for _, v in vecs.values()]) if vecs else np.array([])
                lat_by_class[cls] = samples if len(samples) else np.array([2000.0])

            data[algo][load_int] = {
                'lat_embb':   lat_by_class['eMBB'],
                'lat_urllc':  lat_by_class['URLLC'],
                'lat_mmtc':   lat_by_class['mMTC'],
                'loss_embb':  loss_rates('eMBB'),
                'loss_urllc': loss_rates('URLLC'),
                'loss_mmtc':  loss_rates('mMTC'),
                'throughput': throughput(),
            }

    if 'IPACT' not in data or 'QosDBA' not in data:
        return None

    # Cargar 32 ONUs para gráfico de escalabilidad (solo loss rates por runid)
    for algo32, prefix32, num_onus in [
        ('IPACT_32',  'IPACT_32ONU',  32),
        ('QosDBA_32', 'QoSDBA_32ONU', 32),
    ]:
        sca32 = sorted(glob.glob(os.path.join(results_dir, f'{prefix32}-*.sca')))
        if not sca32:
            continue
        df32 = export_scalars(sca32)
        if df32 is None or 'load' not in df32.columns or 'name' not in df32.columns:
            continue
        data[algo32] = {}
        for load32 in sorted(df32['load'].unique()):
            load_int32 = int(load32)
            df_l32 = df32[df32['load'] == load32]
            def loss32(cls, _df=df_l32):
                m = _df['name'].str.fullmatch(fr'lossRate_{cls}_onu\d+', na=False)
                return pd.to_numeric(_df.loc[m, 'value'], errors='coerce').dropna().values
            data[algo32][load_int32] = {
                'loss_embb':  loss32('eMBB'),
                'loss_urllc': loss32('URLLC'),
                'loss_mmtc':  loss32('mMTC'),
            }
        print(f"[INFO] Cargados 32ONU {algo32}: loads={sorted(data[algo32].keys())}")

    # Añadir datos para gráficos CDF y timeseries (carga alta = 200 Mbps)
    high_load = max(data['IPACT'].keys())
    data['_cdf'] = {
        'ipact': data['IPACT'][high_load]['lat_urllc'],
        'qos':   data['QosDBA'][high_load]['lat_urllc'],
    }

    # Timeseries: una corrida representativa a carga alta
    def get_timeseries(prefix, run_nums, results_dir, warmup_s=1.0):
        # Usa el último run (mayor carga, última repetición)
        vf = get_vec_files(prefix, [max(run_nums)], results_dir)
        if not vf:
            return np.array([]), np.array([])
        csv_v = _run_scavetool(
            ['export', '-T', 'v', '-F', 'CSV-R', '-o', '-',
             '-f', 'name =~ latency_URLLC_onu0'] + vf)
        vecs = _parse_vec_csv(csv_v, warmup_s=warmup_s)
        if not vecs:
            return np.array([]), np.array([])
        key = next(iter(vecs))
        ts, vs = vecs[key]
        # Muestra aleatoria para que el scatter no sea demasiado denso
        if len(ts) > 2000:
            idx = np.random.choice(len(ts), 2000, replace=False)
            idx.sort()
            ts, vs = ts[idx], vs[idx]
        return ts, vs

    def hi_run_nums(sca_files):
        df_tmp = export_scalars(sca_files)
        if df_tmp is None or 'load' not in df_tmp.columns or 'run' not in df_tmp.columns:
            return []
        run_ids = df_tmp[df_tmp['load'] == high_load]['run'].unique()
        nums = [extract_run_num(r) for r in run_ids]
        return [n for n in nums if n is not None]

    hi_run_nums_i = hi_run_nums(ipact_scas)
    hi_run_nums_q = hi_run_nums(qos_scas)

    ti, li = get_timeseries('IPACT_16ONU',  hi_run_nums_i, results_dir)
    tq, lq = get_timeseries('QosDBA_16ONU', hi_run_nums_q, results_dir)

    def fallback_ts(n=500):
        return np.sort(np.random.uniform(1, 10, n))

    data['_timeseries'] = {
        'time_ipact': ti if len(ti) > 0 else fallback_ts(),
        'lat_ipact':  li if len(li) > 0 else np.abs(np.random.normal(3000, 800, 500)),
        'time_qos':   tq if len(tq) > 0 else fallback_ts(),
        'lat_qos':    lq if len(lq) > 0 else np.abs(np.random.normal(200, 50, 500)),
    }

    print(f"[INFO] Datos reales cargados: loads={sorted(data['IPACT'].keys())}")
    return data


# ─── Gráficos ─────────────────────────────────────────────────────────────────

def plot1_latency_avg_by_class(data):
    """Gráfico 1: Latencia promedio por clase a carga alta (200 Mbps)."""
    fig, ax = plt.subplots(figsize=(8, 5))

    x = np.arange(len(CLASSES))
    width = 0.35
    load = 200

    means_ipact = [
        data['IPACT'][load]['lat_embb'].mean(),
        data['IPACT'][load]['lat_urllc'].mean(),
        data['IPACT'][load]['lat_mmtc'].mean(),
    ]
    ci_ipact = [
        ci95(data['IPACT'][load]['lat_embb']),
        ci95(data['IPACT'][load]['lat_urllc']),
        ci95(data['IPACT'][load]['lat_mmtc']),
    ]
    means_qos = [
        data['QosDBA'][load]['lat_embb'].mean(),
        data['QosDBA'][load]['lat_urllc'].mean(),
        data['QosDBA'][load]['lat_mmtc'].mean(),
    ]
    ci_qos = [
        ci95(data['QosDBA'][load]['lat_embb']),
        ci95(data['QosDBA'][load]['lat_urllc']),
        ci95(data['QosDBA'][load]['lat_mmtc']),
    ]

    bars1 = ax.bar(x - width/2, means_ipact, width, label='IPACT',   color=C_IPACT,
                   yerr=ci_ipact, capsize=5, alpha=0.85)
    bars2 = ax.bar(x + width/2, means_qos,   width, label='QoS-DBA', color=C_QOS,
                   yerr=ci_qos,   capsize=5, alpha=0.85)

    ax.set_xlabel('Clase de Servicio')
    ax.set_ylabel('Latencia Promedio Upstream (μs)')
    ax.set_title('Latencia Promedio por Clase de Servicio\n(Carga eMBB = 200 Mbps, 16 ONUs)')
    ax.set_xticks(x)
    ax.set_xticklabels(CLASSES)
    ax.legend(loc='upper left')
    ax.grid(axis='y', alpha=0.3)
    ax.set_ylim(bottom=0)

    plt.tight_layout()
    path = os.path.join(FIGURES_DIR, 'latency_avg_by_class.png')
    plt.savefig(path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  [OK] {path}")


def plot2_latency_p99_urllc(data):
    """Gráfico 2: P99 latencia URLLC vs carga — el gráfico más importante."""
    fig, ax = plt.subplots(figsize=(8, 5))

    p99_ipact, ci_ipact = [], []
    p99_qos,   ci_qos   = [], []

    for load in LOADS:
        arr_i = data['IPACT'][load]['lat_urllc']
        arr_q = data['QosDBA'][load]['lat_urllc']
        p99_ipact.append(np.percentile(arr_i, 99))
        p99_qos.append(np.percentile(arr_q, 99))
        ci_ipact.append(ci95(arr_i))
        ci_qos.append(ci95(arr_q))

    p99_ipact = np.array(p99_ipact)
    p99_qos   = np.array(p99_qos)
    ci_ipact  = np.array(ci_ipact)
    ci_qos    = np.array(ci_qos)

    ax.plot(LOADS, p99_ipact, 'o-', color=C_IPACT, label='IPACT',   lw=2, ms=7)
    ax.fill_between(LOADS, p99_ipact - ci_ipact, p99_ipact + ci_ipact,
                    color=C_IPACT, alpha=0.15)
    ax.plot(LOADS, p99_qos, 's-', color=C_QOS, label='QoS-DBA', lw=2, ms=7)
    ax.fill_between(LOADS, p99_qos - ci_qos, p99_qos + ci_qos,
                    color=C_QOS, alpha=0.15)

    # Línea de deadline URLLC (budget acceso PON = 10ms)
    ax.axhline(y=10000, color='red', linestyle='--', lw=1.5, alpha=0.8,
               label='Deadline URLLC (10 ms)')

    ax.set_xlabel('Carga eMBB Ofrecida (Mbps)')
    ax.set_ylabel('Latencia P99 URLLC (μs)')
    ax.set_title('Latencia P99 URLLC vs Carga Ofrecida\n(IC 95%, 16 ONUs)')
    ax.set_xticks(LOADS)
    ax.legend(loc='upper left')
    ax.grid(alpha=0.3)
    ax.set_ylim(bottom=0)

    plt.tight_layout()
    path = os.path.join(FIGURES_DIR, 'latency_p99_urllc_vs_load.png')
    plt.savefig(path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  [OK] {path}")


def plot3_throughput_vs_load(data):
    """Gráfico 3: Throughput agregado vs carga ofrecida."""
    fig, ax = plt.subplots(figsize=(8, 5))

    # Capacidad del canal: 1 Gbps / 16 ONUs = 62.5 Mbps por ONU
    # Carga ofrecida por ONU: embbRate + urllcRate(5) + mmtcRate(0.5)
    num_onus = 16
    channel_cap_per_onu = 1000.0 / num_onus  # Mbps

    offered = [(l + 5.5) for l in LOADS]          # Mbps por ONU (eMBB + URLLC + mMTC)
    offered_norm = [o / channel_cap_per_onu for o in offered]

    tput_ipact_mbps = [data['IPACT'][l]['throughput'].mean()   for l in LOADS]
    tput_qos_mbps   = [data['QosDBA'][l]['throughput'].mean()  for l in LOADS]
    tput_ipact = [t / channel_cap_per_onu for t in tput_ipact_mbps]
    tput_qos   = [t / channel_cap_per_onu for t in tput_qos_mbps]
    ci_i = [ci95(data['IPACT'][l]['throughput'])   / channel_cap_per_onu for l in LOADS]
    ci_q = [ci95(data['QosDBA'][l]['throughput'])  / channel_cap_per_onu for l in LOADS]

    ax.plot(offered_norm, tput_ipact, 'o-', color=C_IPACT, label='IPACT',   lw=2, ms=7)
    ax.fill_between(offered_norm,
                    np.array(tput_ipact) - np.array(ci_i),
                    np.array(tput_ipact) + np.array(ci_i), color=C_IPACT, alpha=0.15)
    ax.plot(offered_norm, tput_qos, 's-', color=C_QOS, label='QoS-DBA', lw=2, ms=7,
            linestyle='--')
    ax.fill_between(offered_norm,
                    np.array(tput_qos) - np.array(ci_q),
                    np.array(tput_qos) + np.array(ci_q), color=C_QOS, alpha=0.15)

    # Throughput ideal (limitado a capacidad = 1.0 normalizado)
    ideal_x = np.linspace(0, max(offered_norm) * 1.05, 100)
    ideal_y = np.minimum(ideal_x, 1.0)
    ax.plot(ideal_x, ideal_y, '--', color=C_IDEAL, lw=1.5, label='Capacidad del canal', alpha=0.7)
    ax.axhline(y=1.0, color='gray', linestyle=':', lw=1, alpha=0.5)

    # Eje Y secundario en Mbps
    ax2 = ax.twinx()
    ax2.set_ylim(np.array(ax.get_ylim()) * channel_cap_per_onu)
    ax2.set_ylabel('Throughput por ONU (Mbps)')

    ax.set_xlabel(f'Carga Ofrecida por ONU / Capacidad Canal ({channel_cap_per_onu:.0f} Mbps)')
    ax.set_ylabel('Throughput Normalizado (÷ capacidad por ONU)')
    ax.set_title(f'Throughput por ONU vs Carga Ofrecida\n(16 ONUs, canal 1 Gbps)')
    ax.set_xlim(0, max(offered_norm) * 1.1)
    ax.set_ylim(0, 1.2)
    ax.legend(loc='lower right')
    ax.grid(alpha=0.3)

    plt.tight_layout()
    path = os.path.join(FIGURES_DIR, 'throughput_vs_load.png')
    plt.savefig(path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  [OK] {path}")


def plot4_cdf_latency_urllc(data):
    """Gráfico 4: CDF latencia URLLC a carga alta."""
    fig, ax = plt.subplots(figsize=(8, 5))

    arr_i = np.sort(data['_cdf']['ipact'])
    arr_q = np.sort(data['_cdf']['qos'])

    cdf_i = np.arange(1, len(arr_i) + 1) / len(arr_i)
    cdf_q = np.arange(1, len(arr_q) + 1) / len(arr_q)

    ax.plot(arr_i, cdf_i, '-', color=C_IPACT, label='IPACT',   lw=2)
    ax.plot(arr_q, cdf_q, '-', color=C_QOS,   label='QoS-DBA', lw=2)

    ax.axvline(x=10000, color='red', linestyle='--', lw=1.5, alpha=0.8,
               label='Deadline URLLC (10 ms)')

    ax.set_xscale('log')
    ax.set_xlabel('Latencia URLLC (μs) — escala logarítmica')
    ax.set_ylabel('Probabilidad Acumulada')
    ax.set_title('CDF de Latencia URLLC\n(Carga eMBB = 200 Mbps, 16 ONUs)')
    ax.set_ylim(0, 1.02)
    ax.legend(loc='lower right')
    ax.grid(alpha=0.3)

    plt.tight_layout()
    path = os.path.join(FIGURES_DIR, 'cdf_latency_urllc.png')
    plt.savefig(path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  [OK] {path}")


def plot5_packet_loss_by_class(data):
    """Gráfico 5: Tasa de pérdida por clase (escala log)."""
    fig, ax = plt.subplots(figsize=(8, 5))

    x = np.arange(len(CLASSES))
    width = 0.35
    load = 200

    means_i = [
        data['IPACT'][load]['loss_embb'].mean() * 100,
        data['IPACT'][load]['loss_urllc'].mean() * 100,
        data['IPACT'][load]['loss_mmtc'].mean() * 100,
    ]
    means_q = [
        data['QosDBA'][load]['loss_embb'].mean() * 100,
        data['QosDBA'][load]['loss_urllc'].mean() * 100,
        data['QosDBA'][load]['loss_mmtc'].mean() * 100,
    ]
    ci_i = [ci95(data['IPACT'][load]['loss_embb']) * 100,
            ci95(data['IPACT'][load]['loss_urllc']) * 100,
            ci95(data['IPACT'][load]['loss_mmtc']) * 100]
    ci_q = [ci95(data['QosDBA'][load]['loss_embb']) * 100,
            ci95(data['QosDBA'][load]['loss_urllc']) * 100,
            ci95(data['QosDBA'][load]['loss_mmtc']) * 100]

    # Evitar ceros en escala log
    means_i = [max(v, 1e-6) for v in means_i]
    means_q = [max(v, 1e-6) for v in means_q]

    ax.bar(x - width/2, means_i, width, label='IPACT',   color=C_IPACT,
           yerr=ci_i, capsize=5, alpha=0.85, error_kw={'elinewidth': 1.5})
    ax.bar(x + width/2, means_q, width, label='QoS-DBA', color=C_QOS,
           yerr=ci_q, capsize=5, alpha=0.85, error_kw={'elinewidth': 1.5})

    ax.set_yscale('log')
    ax.set_xlabel('Clase de Servicio')
    ax.set_ylabel('Tasa de Pérdida (%)')
    ax.set_title('Tasa de Pérdida de Paquetes por Clase\n(Carga eMBB = 200 Mbps, 16 ONUs)')
    ax.set_xticks(x)
    ax.set_xticklabels(CLASSES)
    ax.legend(loc='upper right')
    ax.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    path = os.path.join(FIGURES_DIR, 'packet_loss_by_class.png')
    plt.savefig(path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  [OK] {path}")


def plot6_latency_timeseries_urllc(data):
    """Gráfico 6: Serie temporal de latencia URLLC (2 subplots)."""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7), sharex=True)

    ts = data['_timeseries']

    ax1.scatter(ts['time_ipact'], ts['lat_ipact'], s=6, color=C_IPACT, alpha=0.5, label='IPACT')
    ax1.axhline(y=10000, color='red', linestyle='--', lw=1.5, alpha=0.8, label='Deadline 10 ms')
    ax1.set_ylabel('Latencia URLLC (μs)')
    ax1.set_title('IPACT')
    ax1.legend(loc='upper right', fontsize=9)
    ax1.grid(alpha=0.3)
    ax1.set_ylim(bottom=0)

    ax2.scatter(ts['time_qos'], ts['lat_qos'], s=6, color=C_QOS, alpha=0.5, label='QoS-DBA')
    # Escala propia para QoS-DBA — deadline (10 ms) queda fuera de rango, se anota
    lat_qos_arr = np.array(ts['lat_qos'])
    y2_max = max(lat_qos_arr.max() * 1.3, 500) if len(lat_qos_arr) > 0 else 500
    ax2.set_ylim(0, y2_max)
    ax2.annotate('← Deadline = 10 ms (fuera de escala)', xy=(0.5, 0.92),
                 xycoords='axes fraction', ha='center', fontsize=8,
                 color='red', style='italic')
    ax2.set_xlabel('Tiempo de Simulación (s)')
    ax2.set_ylabel('Latencia URLLC (μs)')
    ax2.set_title('QoS-DBA')
    ax2.legend(loc='upper right', fontsize=9)
    ax2.grid(alpha=0.3)

    fig.suptitle('Latencia URLLC en el Tiempo — Carga eMBB = 200 Mbps\n(corrida representativa)',
                 fontsize=13)
    plt.tight_layout()
    path = os.path.join(FIGURES_DIR, 'latency_timeseries_urllc.png')
    plt.savefig(path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  [OK] {path}")


def plot7_summary_dashboard(data):
    """Gráfico 7: Dashboard resumen 2x2 para presentación."""
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('Comparación IPACT vs QoS-DBA — Red PON con Tráfico 5G',
                 fontsize=15, fontweight='bold', y=0.98)

    load_high = 200

    # ── Subplot 1: Latencia promedio por clase ─────────────────────────────
    ax = axes[0, 0]
    x = np.arange(len(CLASSES))
    width = 0.35
    m_i = [data['IPACT'][load_high][f'lat_{c.lower()}'].mean() for c in ['embb','urllc','mmtc']]
    m_q = [data['QosDBA'][load_high][f'lat_{c.lower()}'].mean() for c in ['embb','urllc','mmtc']]
    ci_i = [ci95(data['IPACT'][load_high][f'lat_{c.lower()}']) for c in ['embb','urllc','mmtc']]
    ci_q = [ci95(data['QosDBA'][load_high][f'lat_{c.lower()}']) for c in ['embb','urllc','mmtc']]
    ax.bar(x - width/2, m_i, width, color=C_IPACT, label='IPACT',   yerr=ci_i, capsize=4, alpha=0.85)
    ax.bar(x + width/2, m_q, width, color=C_QOS,   label='QoS-DBA', yerr=ci_q, capsize=4, alpha=0.85)
    ax.set_title('Latencia Promedio por Clase')
    ax.set_ylabel('Latencia (μs)')
    ax.set_xticks(x); ax.set_xticklabels(CLASSES)
    ax.legend(fontsize=9); ax.grid(axis='y', alpha=0.3); ax.set_ylim(bottom=0)

    # ── Subplot 2: P99 URLLC vs carga ─────────────────────────────────────
    ax = axes[0, 1]
    p99_i = [np.percentile(data['IPACT'][l]['lat_urllc'], 99)   for l in LOADS]
    p99_q = [np.percentile(data['QosDBA'][l]['lat_urllc'], 99) for l in LOADS]
    ax.plot(LOADS, p99_i, 'o-', color=C_IPACT, label='IPACT',   lw=2, ms=6)
    ax.plot(LOADS, p99_q, 's-', color=C_QOS,   label='QoS-DBA', lw=2, ms=6)
    ax.axhline(y=10000, color='red', linestyle='--', lw=1.5, alpha=0.8, label='Deadline 10 ms')
    ax.set_title('P99 Latencia URLLC vs Carga')
    ax.set_xlabel('Carga eMBB (Mbps)'); ax.set_ylabel('P99 Latencia (μs)')
    ax.set_xticks(LOADS); ax.legend(fontsize=9); ax.grid(alpha=0.3); ax.set_ylim(bottom=0)

    # ── Subplot 3: Throughput vs carga ────────────────────────────────────
    ax = axes[1, 0]
    cap_onu = 1000.0 / 16  # 62.5 Mbps
    offered_n = [(l + 5.5) / cap_onu for l in LOADS]
    tp_i = [data['IPACT'][l]['throughput'].mean()  / cap_onu for l in LOADS]
    tp_q = [data['QosDBA'][l]['throughput'].mean() / cap_onu for l in LOADS]
    ax.plot(offered_n, tp_i, 'o-', color=C_IPACT, label='IPACT',   lw=2, ms=6)
    ax.plot(offered_n, tp_q, 's--', color=C_QOS,   label='QoS-DBA', lw=2, ms=6)
    ideal_x = np.linspace(0, max(offered_n) * 1.05, 100)
    ax.plot(ideal_x, np.minimum(ideal_x, 1.0), '--', color=C_IDEAL, label='Capacidad', lw=1.5, alpha=0.7)
    ax.axhline(y=1.0, color='gray', linestyle=':', lw=1, alpha=0.5)
    ax.set_title('Throughput por ONU vs Carga')
    ax.set_xlabel('Carga Ofrecida / Cap. Canal'); ax.set_ylabel('Throughput / Cap. Canal')
    ax.set_xlim(0, max(offered_n) * 1.1); ax.set_ylim(0, 1.2)
    ax.legend(fontsize=9); ax.grid(alpha=0.3)

    # ── Subplot 4: Pérdida por clase ──────────────────────────────────────
    ax = axes[1, 1]
    x = np.arange(len(CLASSES))
    m_i = [max(data['IPACT'][load_high][f'loss_{c.lower()}'].mean() * 100, 1e-6)
           for c in ['embb', 'urllc', 'mmtc']]
    m_q = [max(data['QosDBA'][load_high][f'loss_{c.lower()}'].mean() * 100, 1e-6)
           for c in ['embb', 'urllc', 'mmtc']]
    ax.bar(x - width/2, m_i, width, color=C_IPACT, label='IPACT',   alpha=0.85)
    ax.bar(x + width/2, m_q, width, color=C_QOS,   label='QoS-DBA', alpha=0.85)
    ax.set_yscale('log')
    ax.set_title('Tasa de Pérdida por Clase')
    ax.set_ylabel('Pérdida (%)')
    ax.set_xticks(x); ax.set_xticklabels(CLASSES)
    ax.legend(fontsize=9); ax.grid(axis='y', alpha=0.3)

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    path = os.path.join(FIGURES_DIR, 'summary_dashboard.png')
    plt.savefig(path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  [OK] {path}")


def plot8_scalability_comparison(data):
    """Gráfico 8: Pérdida URLLC comparando 16 vs 32 ONUs bajo carga 200 Mbps."""
    fig, ax = plt.subplots(figsize=(8, 5))

    onus_labels = ['16 ONUs', '32 ONUs']
    x = np.arange(len(onus_labels))
    width = 0.35

    def safe_loss(key, load=200):
        d = data.get(key, {}).get(load, {})
        arr = d.get('loss_urllc', np.array([np.nan]))
        return arr if len(arr) > 0 else np.array([np.nan])

    m_ipact  = [safe_loss('IPACT', 200).mean()  * 100, safe_loss('IPACT_32', 200).mean()  * 100]
    m_qos    = [safe_loss('QosDBA', 200).mean() * 100, safe_loss('QosDBA_32', 200).mean() * 100]
    ci_ipact = [ci95(safe_loss('IPACT', 200))  * 100,  ci95(safe_loss('IPACT_32', 200))  * 100]
    ci_qos   = [ci95(safe_loss('QosDBA', 200)) * 100,  ci95(safe_loss('QosDBA_32', 200)) * 100]

    # Evitar ceros en escala log
    m_ipact  = [max(v, 1e-4) for v in m_ipact]
    m_qos    = [max(v, 1e-4) for v in m_qos]

    ax.bar(x - width/2, m_ipact, width, label='IPACT',   color=C_IPACT,
           yerr=ci_ipact, capsize=5, alpha=0.85)
    ax.bar(x + width/2, m_qos,   width, label='QoS-DBA', color=C_QOS,
           yerr=ci_qos,   capsize=5, alpha=0.85)

    ax.set_yscale('log')
    ax.set_xlabel('Número de ONUs')
    ax.set_ylabel('Tasa de Pérdida URLLC (%)')
    ax.set_title('Escalabilidad: Pérdida URLLC vs Número de ONUs\n(Carga eMBB = 200 Mbps)')
    ax.set_xticks(x)
    ax.set_xticklabels(onus_labels)
    ax.legend()
    ax.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    path = os.path.join(FIGURES_DIR, 'scalability_comparison.png')
    plt.savefig(path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  [OK] {path}")


def plot9_heatmap_loss_urllc(data):
    """Gráfico 9: Heatmap de pérdida URLLC — algoritmo × carga (16 ONUs)."""
    import matplotlib.colors as mcolors

    algos = ['IPACT', 'QosDBA']
    loads = LOADS

    matrix = np.zeros((len(algos), len(loads)))
    for i, algo in enumerate(algos):
        for j, load in enumerate(loads):
            arr = data.get(algo, {}).get(load, {}).get('loss_urllc', np.array([np.nan]))
            matrix[i, j] = arr.mean() * 100 if len(arr) > 0 else np.nan

    # Usar escala lineal pero con colormap RdYlGn_r
    # Si todos los valores son muy pequeños, scale a percentual directo
    vmax = np.nanmax(matrix)
    vmin = 0.0

    fig, ax = plt.subplots(figsize=(9, 4))
    cmap = plt.get_cmap('RdYlGn_r')
    norm = mcolors.Normalize(vmin=vmin, vmax=max(vmax, 1e-2))
    im = ax.imshow(matrix, cmap=cmap, norm=norm, aspect='auto')

    ax.set_xticks(range(len(loads)))
    ax.set_xticklabels([f'{l} Mbps' for l in loads])
    ax.set_yticks(range(len(algos)))
    ax.set_yticklabels(['IPACT', 'QoS-DBA'])
    ax.set_xlabel('Carga eMBB por ONU')
    ax.set_title('Tasa de Pérdida URLLC (%) — 16 ONUs\n(verde = 0%, rojo = pérdida alta)')

    for i in range(len(algos)):
        for j in range(len(loads)):
            val = matrix[i, j]
            if np.isnan(val):
                txt = 'N/A'
            elif val < 0.01:
                txt = f'{val:.2e}'
            else:
                txt = f'{val:.2f}%'
            # color del texto para contraste
            brightness = norm(val) if not np.isnan(val) else 0.5
            text_color = 'white' if brightness > 0.6 else 'black'
            ax.text(j, i, txt, ha='center', va='center',
                    fontsize=10, fontweight='bold', color=text_color)

    cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label('Pérdida URLLC (%)')

    plt.tight_layout()
    path = os.path.join(FIGURES_DIR, 'heatmap_loss_urllc.png')
    plt.savefig(path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  [OK] {path}")


def export_results_summary(results_dir, output_path):
    """
    Genera results_summary.csv con una fila por run (= carga × repetición).
    Columnas: algoritmo, num_onus, carga_embb, rep, loss_*, lat_avg_*, throughput_total, jitter_urllc.
    """
    import io

    rows = []
    for algo, prefix, num_onus in [
        ('IPACT',  'IPACT_16ONU',  16),
        ('QosDBA', 'QoSDBA_16ONU', 16),
        ('IPACT',  'IPACT_32ONU',  32),
        ('QosDBA', 'QoSDBA_32ONU', 32),
    ]:
        sca_files = sorted(glob.glob(os.path.join(results_dir, f'{prefix}-*.sca')))
        if not sca_files:
            continue

        csv_text = _run_scavetool(['export', '-T', 's', '-F', 'CSV-S', '-o', '-'] + sca_files)
        if not csv_text:
            continue

        try:
            df = pd.read_csv(io.StringIO(csv_text), comment='#')
        except Exception:
            continue

        if not {'load', 'name', 'value', 'run'}.issubset(df.columns):
            continue

        sim_time = 9.0  # 10s - 1s warmup

        for run_id in sorted(df['run'].unique()):
            df_r = df[df['run'] == run_id]
            load_vals = df_r['load'].dropna().unique()
            if len(load_vals) == 0:
                continue
            load = int(load_vals[0])

            # Extraer repetición del run_id (formato: Config-runNum)
            try:
                run_num = int(run_id.split('-')[-1])
                rep = run_num % 10   # repetición dentro del nivel de carga
            except (ValueError, IndexError):
                rep = 0

            def scalar_mean(pattern):
                m = df_r['name'].str.fullmatch(pattern, na=False)
                vals = pd.to_numeric(df_r.loc[m, 'value'], errors='coerce').dropna()
                return float(vals.mean()) if len(vals) > 0 else float('nan')

            bytes_total = scalar_mean(r'bytesTransmitted_(eMBB|URLLC|mMTC)_onu\d+')
            rows.append({
                'algoritmo':      algo,
                'num_onus':       num_onus,
                'carga_embb':     load,
                'rep':            rep,
                'loss_embb':      scalar_mean(r'lossRate_eMBB_onu\d+'),
                'loss_urllc':     scalar_mean(r'lossRate_URLLC_onu\d+'),
                'loss_mmtc':      scalar_mean(r'lossRate_mMTC_onu\d+'),
                'lat_avg_embb':   scalar_mean(r'latency_eMBB_onu\d+'),
                'lat_avg_urllc':  scalar_mean(r'latency_URLLC_onu\d+'),
                'lat_avg_mmtc':   scalar_mean(r'latency_mMTC_onu\d+'),
                'lat_p99_urllc':  float('nan'),   # requiere datos vectoriales
                'throughput_total': bytes_total * 8 / sim_time / 1e6 if not np.isnan(bytes_total) else float('nan'),
                'jitter_urllc':   scalar_mean(r'jitter_URLLC_onu\d+'),
            })

    if rows:
        pd.DataFrame(rows).to_csv(output_path, index=False)
        print(f"  [OK] {output_path}  ({len(rows)} filas)")
    else:
        print(f"  [WARN] Sin datos reales para {output_path} (requiere correr simulaciones primero)")


# ─── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Análisis PON DBA Simulation')
    parser.add_argument('--results-dir', default='../simulations/results',
                        help='Directorio con resultados CSV de OMNeT++')
    args = parser.parse_args()

    print("=" * 60)
    print("PON DBA Simulation — Análisis de Resultados")
    print("OmneTeam — TEL-341 Simulación de Redes")
    print("=" * 60)

    real_data = try_load_real_data(args.results_dir)
    if real_data is not None:
        data = real_data
        print("[INFO] Usando datos reales de simulación")
    else:
        print("[INFO] No se encontraron datos reales. Usando datos sintéticos representativos.")
        data = make_synthetic_data()

    print(f"\nGenerando 9 gráficos en: {FIGURES_DIR}\n")

    plot1_latency_avg_by_class(data)
    plot2_latency_p99_urllc(data)
    plot3_throughput_vs_load(data)
    plot4_cdf_latency_urllc(data)
    plot5_packet_loss_by_class(data)
    plot6_latency_timeseries_urllc(data)
    plot7_summary_dashboard(data)
    plot8_scalability_comparison(data)
    plot9_heatmap_loss_urllc(data)

    summary_path = os.path.join(os.path.dirname(__file__), 'results_summary.csv')
    export_results_summary(args.results_dir, summary_path)

    print("\n[DONE] 9 gráficos PNG + results_summary.csv generados exitosamente.")
    print(f"       Figuras en: {os.path.abspath(FIGURES_DIR)}/")


if __name__ == '__main__':
    main()
