# Simulador XG-PON DBA — ITU-T G.987

**Equipo OmneTeam** · David Retuerto · José Vega · Matías Perelli
Universidad Técnica Federico Santa María (UTFSM) · TEL-341 Simulación de Redes · 2026

---

## ¿Qué es este proyecto?

Simulador de eventos discretos propio (100% Python, sin frameworks externos)
de una red **XG-PON1** según el estándar **ITU-T G.987**, que compara 3
algoritmos de asignación dinámica de ancho de banda (DBA) bajo un **SLA de
latencia explícito** para tráfico de voz (T-CONT1 ≤ 2 ms):

- **IPACT** — polling round-robin de ciclo variable, adaptado de EPON (declarado como comparación, no como modelo de XG-PON)
- **GIANT** — GPA/SPA con contadores SImax/SImin, nativo de GPON/XG-PON
- **QoSDBA** — prioridad estricta T-CONT 1 > 2 > 4 (la referencia heredada de la Fase 2 del proyecto, reescalada a XG-PON)

Este es el resultado de un pivote pedido por la profesora el 9/6/2026 sobre
un simulador GPON anterior (ver [Legacy](#legacy--fases-1-y-2) abajo).

---

## Estándar implementado: XG-PON1 ITU-T G.987

| Parámetro | Valor | Fuente |
|-----------|-------|--------|
| Upstream | 2.48832 Gbps | G.987.2 |
| Downstream | 9.95328 Gbps | G.987.2 |
| Trama GTC | 125 μs (8,000 tramas/s) | G.987.3 |
| Bytes/trama upstream | 38,880 bytes | calculado |
| Split ratio | 1:8 | requerimiento del proyecto |
| Alcance / RTT | 20 km / 200 μs | G.987.2 Clase N1 |
| Guard band | 32 bytes/ONU | G.984.3 §8.2 (heredado) |

### T-CONTs simulados

| T-CONT | Nombre | Tráfico simulado | Distribución | SLA (delay máx) |
|--------|--------|-------------------|--------------|------------------|
| T-CONT 1 | Fixed (CBR) | VoIP G.711 (1 Mbps, 160 B) | Determinístico | ≤ 2 ms |
| T-CONT 2 | Assured | Video streaming (40 Mbps, 1000 B) | Poisson | ≤ 20 ms |
| T-CONT 4 | Best Effort | Datos masivos (variable, 1400 B) | Pareto α=1.5 | ≤ 500 ms (diagnóstica) |

### 3 algoritmos DBA comparados

| Algoritmo | Mecanismo | Archivo |
|---|---|---|
| **IPACT** | Polling round-robin de ciclo variable (adaptado de EPON, declarado) | `simulator/dba_ipact.py` + `simulator/olt_ipact.py` |
| **GIANT** | GPA/SPA con contadores SImax/SImin (nativo XG-PON, broadcast BWmap 125μs) | `simulator/dba_giant.py` |
| **QoSDBA** | Prioridad estricta T1 > T2 > T4 | `simulator/dba_qos.py` |

---

## Estructura del proyecto

```
/
├── main.py                 # CLI: una corrida individual
├── run_experiments.py      # Los 9 escenarios (3 algoritmos x 3 cargas x 10 repeticiones)
│
├── simulator/               # Motor DES y modelos de red
│   ├── engine.py            # Motor de eventos discretos (heapq)
│   ├── olt.py                # OLT broadcast (SR-DBA): BWmap cada 125 μs -- usado por GIANT/QoSDBA
│   ├── olt_ipact.py          # OLT polling: GATE individual, ciclo variable -- usado por IPACT
│   ├── onu.py                # ONU: T-CONTs, buffers, DBRu
│   ├── tcont.py               # T-CONT: buffer FIFO, métricas
│   ├── traffic.py             # CBR / Poisson / Pareto
│   ├── dba_giant.py           # GIANT: GPA/SPA
│   ├── dba_ipact.py           # IPACT: limited service por poll
│   └── dba_qos.py             # QoSDBA: prioridad T-CONT 1 -> 2 -> 4
├── metrics/
│   └── collector.py          # Latencia, throughput, jitter, pérdida, SLA, cycle_time
├── analysis/
│   └── analyze.py            # 6 gráficos PNG (estilo IEEE)
│
├── configs/
│   ├── default.json          # Parámetros XG-PON1 (G.987), T-CONTs, tabla SLA, IPACT/GIANT
│   └── scenarios.json        # 9 escenarios (3 algoritmos x 3 cargas)
├── results/
│   ├── results.csv            # Resultados consolidados
│   └── cycle_times.csv        # Muestras de duración de ciclo (IPACT)
├── figures/                   # 6 gráficos PNG generados
│
├── docs/                      # Documentación (ver tabla abajo)
├── entregas/
│   └── Parte_3/                # Índice de la entrega actual
│
└── legacy/                    # Fase 1 y Fase 2 archivadas -- ver sección Legacy
```

Los módulos `simulator/engine.py`, `simulator/onu.py`, `simulator/tcont.py`,
`simulator/traffic.py`, `simulator/olt.py`, `simulator/dba_qos.py` y
`metrics/collector.py` son compartidos con la Fase 2 archivada en
`legacy/fase2/` -- por eso viven en la raíz y no están duplicados ahí.

---

## Cómo ejecutar

### Requisitos

```bash
pip install matplotlib numpy scipy pandas
```

### Una corrida individual

```bash
python3 main.py --algorithm ipact --load 400 --verbose
python3 main.py --algorithm giant --load 800 --verbose
python3 main.py --algorithm qos   --load 200 --verbose
```

Opciones: `--algorithm [ipact|giant|qos]`, `--load` (Mbps T-CONT4 por ONU), `--num-onus`, `--duration`, `--warmup`, `--seed`.

### Los 9 escenarios completos (~8-15 min)

```bash
python3 run_experiments.py
```

Genera `results/results.csv` y `results/cycle_times.csv`.

### Generar los 6 gráficos

```bash
python3 analysis/analyze.py
```

Genera en `figures/`:

| Archivo | Contenido |
|---------|-----------|
| `sla_compliance_by_tcont.png` | Cumplimiento SLA por T-CONT @ 800 Mbps/ONU — **gráfico principal** |
| `max_delay_tcont1_vs_load.png` | Delay máximo T-CONT1 vs carga, línea SLA 2ms — **evidencia clave** |
| `cycle_time_distribution.png` | Distribución del ciclo de polling IPACT vs trama fija |
| `throughput_vs_load.png` | Throughput agregado vs carga |
| `sla_compliance_vs_load.png` | Cumplimiento SLA T-CONT1 vs carga |
| `summary_dashboard.png` | Dashboard 2×2 resumen |

---

## Resultado clave @ 800 Mbps/ONU (sobrecarga ~257%)

| Métrica | IPACT | GIANT | QoSDBA |
|---|---|---|---|
| T-CONT1 SLA% (≤2ms) | **88.4%** | 100.0% | 100.0% |
| T-CONT1 delay máximo (μs) | **2109.0** | 226.0 | 226.0 |
| Throughput agregado (Mbps) | 2424.5 | 2343.3 | 1812.6 |

**Conclusión:** GIANT y QoSDBA reservan T-CONT1 (VoIP) incondicionalmente
cada trama → SLA de 2 ms cumplido siempre. IPACT asigna T1 según el último
reporte (~1 ciclo de antigüedad); bajo saturación el ciclo se estanca en
1008 μs y el delay máximo de T1 supera los 2 ms → 88.4% de cumplimiento —
exactamente la comparación SR-DBA vs. polling demand-based que pidió la
profesora.

---

## Documentación

| Si quieres... | Lee... |
|---|---|
| Punto de entrada para alguien sin contexto del proyecto | [`docs/GUIA_INICIO.md`](docs/GUIA_INICIO.md) |
| Diseño completo y derivaciones | [`docs/PLAN_FASE3.md`](docs/PLAN_FASE3.md) |
| Explicación accesible, sin jerga, paso a paso | [`docs/COMO_FUNCIONA_FASE3.md`](docs/COMO_FUNCIONA_FASE3.md) |
| Referencia técnica formal (estándares, pseudocódigo, resultados) | [`docs/DOCUMENTACION_TECNICA_FASE3.md`](docs/DOCUMENTACION_TECNICA_FASE3.md) |
| Resumen ejecutivo + tabla de resultados clave | [`docs/PARA_LA_PROFE_FASE3.md`](docs/PARA_LA_PROFE_FASE3.md) |
| Checkpoint histórico de implementación | [`docs/ESTADO_FASE3.md`](docs/ESTADO_FASE3.md) |
| Índice de la entrega académica | [`entregas/Parte_3/`](entregas/Parte_3/) |

---

## Legacy — Fases 1 y 2

El proyecto pasó por dos generaciones anteriores antes de llegar a Fase 3,
archivadas en `legacy/` para no generar confusión con el código activo:

- **`legacy/fase1/`** — la propuesta original en OMNeT++ (rechazada por la
  profesora: mezclaba IPACT de EPON y categorías 5G que no son de GPON).
  Solo quedan el PDF y el PPTX de esa entrega, sin código.
- **`legacy/fase2/`** — el simulador GPON ITU-T G.984 completo (32 ONUs,
  BasicDBA vs QoSDBA). **Ya entregado, no se modifica**, pero sigue siendo
  ejecutable tal cual desde esa carpeta:

  ```bash
  python3 legacy/fase2/main.py --algorithm qos --load 100 --num-onus 32 --seed 6767 --verbose
  python3 legacy/fase2/run_experiments.py
  python3 legacy/fase2/analysis/analyze.py
  ```

  Documentación de Fase 2 en `legacy/fase2/docs/`.

---

## Contacto

Equipo OmneTeam — David Retuerto, José Vega, Matías Perelli
TEL-341 Simulación de Redes, UTFSM 2026
