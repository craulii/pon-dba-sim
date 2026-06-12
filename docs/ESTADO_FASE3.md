# Estado Fase 3 — checkpoint histórico (COMPLETADO)

> **Fase 3 completada.** Este documento es un checkpoint histórico del
> proceso de implementación (incluye el bug-fix de GIANT y los smoke tests,
> §2-3 más abajo, que siguen siendo relevantes para entender decisiones de
> diseño). Para el estado FINAL — resultados de la corrida completa,
> gráficos, documentación — ver:
> - [`PARA_LA_PROFE_FASE3.md`](PARA_LA_PROFE_FASE3.md) §6 (tabla de
>   resultados clave, ya completada)
> - [`DOCUMENTACION_TECNICA_FASE3.md`](DOCUMENTACION_TECNICA_FASE3.md)
>   (referencia técnica completa, incluye §13 con resultados)
> - [`COMO_FUNCIONA_FASE3.md`](COMO_FUNCIONA_FASE3.md) (explicación accesible)
> - `results/xgpon_results.csv`, `results/xgpon_cycle_times.csv`,
>   `figures/xgpon/*.png` (6 gráficos)
>
> El plan completo (diseño, derivaciones, código de referencia) está en
> `docs/PLAN_FASE3.md`.

---

## 1. Resumen ejecutivo

Implementación de Fase 3 (XG-PON, IPACT vs GIANT vs QoSDBA, 8 ONUs,
SLA-driven) **100% completada**:

- **Código: 100% implementado y verificado** (tasks 1-9 del plan).
- **Experimento completo corrido** (9 escenarios × 10 repeticiones × 10s),
  6 gráficos generados en `figures/xgpon/`, tabla de "resultados clave" en
  `PARA_LA_PROFE_FASE3.md` §6 completada, y documentación técnica detallada
  escrita (`docs/DOCUMENTACION_TECNICA_FASE3.md`,
  `entregas/Parte_3/README.md`).
- **Bug adicional encontrado y corregido durante el análisis final**:
  `cycle_time_samples` (segundos) se escribía sin convertir a la columna
  `cycle_time_us` de `results/xgpon_cycle_times.csv` — dejaba
  `cycle_time_distribution.png` vacío. Corregido en
  `run_experiments_xgpon.py` (ver `DOCUMENTACION_TECNICA_FASE3.md` §8.2).
- **Hallazgo central confirmado** con la corrida completa: T-CONT1 bajo
  IPACT alcanza `sla_compliance_pct = 88.4%` (vs 100% en GIANT/QoSDBA) a
  carga ≥400 Mbps/ONU, con `latency_max_us = 2109.0 > 2000` (SLA) —
  exactamente el resultado esperado/declarado.

---

## 2. Qué está HECHO (verificado funcionando)

### 2.1 Código nuevo/modificado (todos verificados)

| Archivo | Estado | Notas |
|---|---|---|
| `simulator/engine.py` | ✅ modificado (aditivo) | +3 constantes: `EVT_OLT_SEND_GATE`, `EVT_ONU_RECV_GATE`, `EVT_OLT_POLL_NEXT` |
| `metrics/collector.py` | ✅ modificado (aditivo, retrocompatible) | `sla_bounds_s`, `record_cycle_time()`, `latency_max_us`, `sla_compliance_pct`, `cycle_time_*` |
| `configs/xgpon.json` | ✅ nuevo | XG-PON1 G.987, 8 ONUs, T-CONTs ×8, tabla `sla`, bloques `ipact`/`giant` |
| `simulator/dba_giant.py` | ✅ nuevo, **bug corregido** | GPA/SPA con contadores SImax/SImin (ver §3) |
| `simulator/onu.py` | ✅ modificado (aditivo) | nuevo método `on_receive_gate` (no toca `on_receive_bwmap`) |
| `simulator/dba_ipact.py` | ✅ nuevo | `IpactDBA.allocate_onu()` |
| `simulator/olt_ipact.py` | ✅ nuevo | `OLTPolling` (ciclo variable round-robin) |
| `main_xgpon.py` | ✅ nuevo | CLI con `--algorithm {ipact,giant,qos}` |
| `configs/scenarios_xgpon.json` | ✅ nuevo | 9 escenarios (3 algos × loads {200,400,800} Mbps/ONU) |
| `run_experiments_xgpon.py` | ✅ nuevo | **paralelizado con multiprocessing** (9 procesos) |
| `analysis/analyze_xgpon.py` | ✅ escrito, **NO ejecutado aún** | 6 gráficos, espera `results/xgpon_results.csv` |
| `docs/PLAN_FASE3.md` | ✅ escrito | plan completo guardado |
| `docs/PARA_LA_PROFE_FASE3.md` | ✅ escrito (parcial) | falta tabla "Resultados clave" (§6, placeholders) |

Fase 2 (`configs/default.json`, `dba_basic.py`, `dba_qos.py`,
`scenarios.json`, `results/all_results.csv`, `figures/`, `entregas/Parte_2/`)
**no se tocó** — verificado con `python3 main.py --algorithm qos --load 50
--num-onus 32 --duration 2 --warmup 0.2` (funciona igual que antes).

### 2.2 Bug encontrado y corregido durante smoke tests

**`simulator/dba_giant.py`, fase SPA (T-CONT4):** el contador `_t4_counter`
se reseteaba a `si_min` (32 tramas) **incondicionalmente** tras cualquier
grant, incluso si la ONU seguía congestionada (`grant < demand`). Esto
generaba un "duty cycle" sincronizado: solo 8 de cada 32 tramas repartían
ancho de banda T4 (las otras 24 quedaban con `t4_grant=0` para las 8 ONUs).

**Fix aplicado** (líneas ~127-141 de `dba_giant.py`): el contador solo se
resetea a `si_min` si `grant >= demand` (cola drenada). Si sigue congestionada
(`grant < demand`), el contador queda en 0 → la ONU permanece elegible la
próxima trama → round-robin continuo bajo sobrecarga sostenida.

**Resultado del fix** (load=400 Mbps/ONU, duration=2s):

| Métrica | Antes del fix | Después del fix |
|---|---|---|
| Utilización canal | 36.2% | **99.3%** |
| T-CONT4 throughput | 485 Mbps | **2014 Mbps** |
| T-CONT4 latencia media | 260,835 μs | **63,400 μs** |

### 2.3 Smoke tests / verificación (todos pasaron)

**load=400, duration=2, warmup=0.2** (los 3 algoritmos corren sin
excepciones, utilización ≤100%):

```
qos:   T1=164.2us(100% SLA)  T2=458.3us(100% SLA)  T4=86401us  util=99.3%
giant: T1=164.2us(100% SLA)  T2=1010.8us(100% SLA) T4=63400us  util=99.3%
ipact: T1=1612.2us(88.5% SLA) T2=1635.8us(100% SLA) T4=60967us util=100.0%
                                                      cycle: mean=min=max=1008.0us (saturado)
```

**Variabilidad de ciclo IPACT a carga baja (80 Mbps/ONU, duration=2)**:
`cycle_time_min=9.03us, mean=54.66us, max=126.83us` — confirma ciclo
VARIABLE (vs 125us fijo de GIANT/QoSDBA), tal como exige el diseño.

**Overload check @ 800 Mbps/ONU (duration=3, warmup=0.5)** — los 3
algoritmos:

```
              T1 lat/SLA          T2 lat/SLA      T4 lat/loss        util
qos:   163.3us / 100.0%   455.0us / 100.0%   86039us / 0.7842   99.3%
giant: 163.3us / 100.0%  1005.3us / 100.0%   63475us / 0.7100   99.3%
ipact: 1613.4us / 88.3%  1636.1us / 100.0%   61057us / 0.6982  100.0%
                                              cycle=1008us (saturado)
```

**Hallazgo confirmado (esperado, documentado en el plan §3.5):** T-CONT1
bajo IPACT tiene SLA% ≈ 88% (vs 100% en GIANT/QoSDBA) porque IPACT asigna T1
*demand-based* a partir de un reporte con ~1 ciclo de antigüedad, mientras
GIANT/QoSDBA reservan T1 incondicionalmente cada trama. Max delay T1 bajo
IPACT (~2109us) excede levemente el SLA de 2000us — **es la comparación
exacta que pidió la profesora** (SR-DBA/GIANT con T1 pre-reservado vs
polling demand-based puro). Documentar como conclusión, no como bug.

**Backward-compat `MetricsCollector`:** verificado, `MetricsCollector(warmup_s=0.0)`
sin `sla_bounds_s` sigue funcionando igual que en Fase 2.

---

## 3. Qué se hizo después (pasos 1-4, completados)

### Paso 1 — Experimento completo (Task #10) ✅

```bash
python3 run_experiments_xgpon.py
```

Corrió los 9 escenarios × 10 repeticiones × 10s (paralelizado, 9 procesos).
Generó `results/xgpon_results.csv` (27 filas) y
`results/xgpon_cycle_times.csv` (716,731 muestras IPACT).

### Paso 2 — 6 gráficos (Task #11) ✅

```bash
python3 analysis/analyze_xgpon.py
```

Generó los 6 PNG en `figures/xgpon/`. Durante esta corrida se encontró y
corrigió el bug de unidades de `cycle_time_us` (ver §1).

### Paso 3 — `docs/PARA_LA_PROFE_FASE3.md` §6 ✅

Tabla "Resultados clave" completada con los valores de
`results/xgpon_results.csv` @ 800 Mbps/ONU.

### Paso 4 — `docs/DOCUMENTACION_TECNICA_FASE3.md` + `entregas/Parte_3/README.md` ✅

Documentación técnica completa (13 secciones, análoga a
`DOCUMENTACION_TECNICA.md` de Fase 2) y README de entrega escritos. Además
se creó [`COMO_FUNCIONA_FASE3.md`](COMO_FUNCIONA_FASE3.md) (explicación
accesible, no estaba en el plan original pero se agregó a pedido del
equipo).

---

## 4. Archivos nuevos/modificados (estado final)

```
 M metrics/collector.py
 M simulator/engine.py
 M simulator/onu.py
?? analysis/analyze_xgpon.py
?? configs/scenarios_xgpon.json
?? configs/xgpon.json
?? docs/COMO_FUNCIONA_FASE3.md
?? docs/DOCUMENTACION_TECNICA_FASE3.md
?? docs/ESTADO_FASE3.md
?? docs/PARA_LA_PROFE_FASE3.md
?? docs/PLAN_FASE3.md
?? entregas/Parte_3/README.md
?? figures/xgpon/*.png            (6 archivos)
?? main_xgpon.py
?? results/xgpon_cycle_times.csv
?? results/xgpon_results.csv
?? run_experiments_xgpon.py
?? simulator/dba_giant.py
?? simulator/dba_ipact.py
?? simulator/olt_ipact.py
```

Nada de esto se ha commiteado (no se pidió commit explícito).
