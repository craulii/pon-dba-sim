# Simulador GPON DBA — ITU-T G.984

**Equipo OmneTeam** · David Retuerto · José Vega · Matías Perelli  
Universidad Técnica Federico Santa María (UTFSM) · TEL-341 Simulación de Redes · 2026

---

## ¿Qué es este proyecto?

Simulador de eventos discretos propio (100% Python, sin frameworks externos) de una red **GPON** según el estándar **ITU-T G.984**, que compara dos algoritmos de asignación dinámica de ancho de banda (DBA):

- **BasicDBA** — reparto proporcional sin diferenciación de T-CONT
- **QosDBA** — prioridad estricta por tipo de T-CONT según ITU-T G.984.3

**Por qué Python puro y no OMNeT++:** el simulador anterior usaba OMNeT++ con conceptos de EPON (IPACT) y clases de tráfico 5G (eMBB/URLLC/mMTC) que no corresponden al estándar GPON. Este simulador implementa correctamente GPON desde cero.

---

## Estándar implementado: GPON ITU-T G.984

| Parámetro | Valor | Fuente |
|-----------|-------|--------|
| Upstream | 1.244 Gbps (1,244,160,000 bps) | G.984.2 |
| Downstream | 2.488 Gbps | G.984.2 |
| Trama GTC | 125 μs (8,000 tramas/s) | G.984.3 |
| Bytes/trama upstream | 19,440 bytes | calculado |
| Split ratio | 1:32 | G.984.1 |
| Alcance | 20 km | G.984.1 |
| Delay propagación | 5 μs/km → 100 μs (20 km) | G.984.1 |
| Guard band | 32 bytes/ONU | G.984.3 §8.2 |

### Tipos de T-CONT usados (ITU-T G.984.3)

| T-CONT | Nombre | Asignación | Tráfico simulado | Distribución |
|--------|--------|------------|-----------------|--------------|
| T-CONT 1 | Fixed (CBR) | Pre-reservada, siempre | VoIP G.711 (1 Mbps, 160 B) | Determinístico |
| T-CONT 2 | Assured | Garantizada, demand-based | Video streaming (5 Mbps, 1000 B) | Poisson |
| T-CONT 4 | Best Effort | Lo que sobra | Datos masivos (variable, 1400 B) | Pareto α=1.5 |

### Mecanismo DBA: SR-DBA centralizado (NO polling IPACT)

- La OLT genera un **BWmap** cada 125 μs (broadcast a todas las ONUs)
- Las ONUs envían **DBRu** embebido en su burst upstream
- La OLT aplica el algoritmo DBA y calcula el siguiente BWmap
- **No hay polling individual** — diferencia clave con EPON/IPACT

---

## Estructura del proyecto

```
/
├── simulator/              # Motor DES y modelos de red
│   ├── engine.py           # Motor eventos discretos (heapq)
│   ├── olt.py              # OLT: BWmap cada 125 μs
│   ├── onu.py              # ONU: T-CONTs, buffers, DBRu
│   ├── tcont.py            # T-CONT: buffer FIFO, métricas
│   ├── traffic.py          # CBR / Poisson / Pareto
│   ├── dba_basic.py        # BasicDBA: proporcional sin QoS
│   └── dba_qos.py          # QosDBA: prioridad T-CONT 1 → 2 → 4
├── metrics/
│   └── collector.py        # Latencia, throughput, jitter, pérdida
├── analysis/
│   └── analyze.py          # 7 gráficos PNG (estilo IEEE)
├── configs/
│   ├── default.json        # Parámetros GPON ITU-T G.984
│   └── scenarios.json      # 10 escenarios (5 cargas × 2 algoritmos)
├── results/
│   └── all_results.csv     # Resultados consolidados (10 repeticiones)
├── figures/                # 7 gráficos PNG generados
├── main.py                 # CLI: una corrida individual
├── run_experiments.py      # Todos los escenarios (100 corridas)
├── DOCUMENTACION_TECNICA.md
├── INFORME_ESTADO.md
├── Parte 1/                # Presentación inicial del proyecto
└── Parte 2/                # Informe de avances + presentación
```

---

## Cómo ejecutar

### Requisitos

```bash
pip install matplotlib numpy scipy pandas
```

### Una corrida individual

```bash
python3 main.py --algorithm qos --load 100 --num-onus 32 --seed 42 --verbose
python3 main.py --algorithm basic --load 100 --num-onus 32 --seed 42 --verbose
```

Opciones: `--algorithm [basic|qos]`, `--load` (Mbps T-CONT 4), `--num-onus`, `--duration`, `--warmup`, `--seed`.

### Todos los escenarios (100 corridas, ~15 min)

```bash
python3 run_experiments.py
```

Genera `results/all_results.csv` con 10 escenarios × 3 T-CONTs, 10 repeticiones cada uno.

### Generar los 7 gráficos

```bash
python3 analysis/analyze.py
```

Genera en `figures/`:

| Archivo | Contenido |
|---------|-----------|
| `latency_avg_by_tcont.png` | Latencia media por T-CONT (barras) |
| `latency_p99_tcont1_vs_load.png` | P99 VoIP vs carga — gráfico clave |
| `loss_rate_by_tcont.png` | Tasa de pérdida (escala log) |
| `throughput_vs_load.png` | Throughput por T-CONT y agregado |
| `cdf_latency_tcont4.png` | CDF latencia T-CONT 1 VoIP |
| `channel_utilization.png` | Utilización canal upstream vs carga |
| `summary_dashboard.png` | Dashboard 2×2 para presentación |

---

## Resultados clave

A carga máxima (100 Mbps/ONU × 32 ONUs = 3,200 Mbps demanda vs 1,244 Mbps capacidad):

| Métrica | BasicDBA | QosDBA |
|---------|----------|--------|
| T-CONT 1 latencia media | **25,437 μs** (VoIP destruido) | **164 μs** ✓ |
| T-CONT 1 P99 | 26,076 μs | 226 μs |
| T-CONT 2 latencia media | 4,411 μs | 401 μs |
| T-CONT 4 latencia | 177,875 μs | 177,875 μs (igual, esperado) |
| T-CONT 4 pérdida | 17.8% | 17.8% (igual, esperado) |
| Utilización canal | ~100% | ~100% |

**Conclusión:** QosDBA garantiza latencia constante de T-CONT 1 (VoIP) ≤ 226 μs P99 independiente de la carga. BasicDBA deja que el tráfico best-effort destruya el VoIP (25 ms a plena carga — inaceptable para telefonía, budget G.114 ≤ 150 ms extremo a extremo).

---

## Contacto

Equipo OmneTeam — David Retuerto, José Vega, Matías Perelli  
TEL-341 Simulación de Redes, UTFSM 2026
