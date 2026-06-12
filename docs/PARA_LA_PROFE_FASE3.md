# Fase 3 — XG-PON, IPACT vs GIANT vs QoSDBA, SLA
## OmneTeam · TEL-341 · UTFSM 2026

---

## 1. Qué cambió y por qué

En la reunión del 9/6/2026 la profesora dio nueva retroalimentación que
pivota el enfoque de la Fase 2 (GPON G.984, 32 ONUs, SR-DBA centralizado,
BasicDBA/QoSDBA):

1. **Migrar a XG-PON** (ITU-T G.987) — el sucesor 10G de GPON.
2. **8 ONUs, todas idénticas** (en vez de 32).
3. **Foco upstream-only** (ya era así en Fase 2).
4. **El problema central pasa a ser cumplir SLA**, con un **delay máximo de
   2 ms** como meta explícita para el tráfico más exigente.
5. **DBA**: en vez de quedarnos solo con SR-DBA centralizado (BasicDBA/
   QoSDBA), comparar explícitamente **IPACT** (polling de ciclo variable,
   adaptado de EPON) y **GIANT** (algoritmo nativo de GPON/XG-PON,
   GPA+SPA), manteniendo **QoSDBA** como referencia de Fase 2.
6. **Tráfico multi-clase con SLA**: cada ONU sigue generando 3 tipos de
   tráfico simultáneos (T-CONT1/2/4), pero ahora con una **tabla de cotas
   SLA por tipo** y nuevas métricas de **delay máximo observado** y
   **% de cumplimiento SLA**.

### Sobre el giro "antes no IPACT, ahora sí"

En Fase 2 argumentamos explícitamente "por qué no IPACT": IPACT es el
protocolo de DBA de **EPON (IEEE 802.3ah)**, un estándar distinto (IEEE) al
de GPON (ITU-T). Usarlo para "modelar GPON" mezclaría conceptos
incompatibles — ese era justamente el error del simulador OMNeT++ original.

En esta fase el encuadre es distinto: **no estamos modelando XG-PON con
IPACT**, sino **comparando explícitamente** un algoritmo de polling clásico
de la literatura (IPACT, declarado y adaptado como tal) contra un algoritmo
**nativo de GPON/XG-PON** (GIANT), bajo los mismos parámetros físicos
XG-PON. Es un ejercicio de benchmarking, no una afirmación de que un OLT
XG-PON real ejecute IPACT.

---

## 2. La red — XG-PON1 (ITU-T G.987)

| Parámetro | Valor | Fuente |
|---|---|---|
| Downstream | **9.95328 Gbps** | G.987.2 |
| Upstream | **2.48832 Gbps** (= 2× GPON G.984) | G.987.2 |
| Trama | **125 μs** (8.000 tramas/s, misma estructura que GPON) | G.987.3 |
| Capacidad bruta upstream/trama | **38.880 bytes** = 2.48832e9 × 125e-6 / 8 | calculado (= 2× los 19.440 B de Fase 2) |
| Split ratio | **1:8** | requerimiento Fase 3 |
| Alcance | 20 km (Nominal Differential Reach Class N1) | G.987.2 |
| Delay propagación | 5 μs/km → **100 μs** (200 μs RTT) | igual que Fase 2 |
| Guard band | 32 bytes/ONU | igual que Fase 2 (G.984.3 §8.2, conservador) |

**Por qué se mantiene la topología de 20km/100μs:** permite comparar
directamente el RTT con Fase 2; 20km corresponde a la clase de alcance
nominal N1 de G.987.2.

### Topología

```
OLT (central del proveedor)
 │  feeder fiber 20 km, 100 μs delay
 │
Splitter 1:8  ← pasivo
 │
 ├─ ONU 0  ┐
 ├─ ONU 1  │ todas idénticas: T-CONT 1 + T-CONT 2 + T-CONT 4
 │  ...    │ mismas tasas, mismo buffer, misma distancia
 └─ ONU 7  ┘
```

Upstream = TDMA: una sola ONU transmite a la vez. La diferencia entre
algoritmos está en **cómo y cuándo** la OLT coordina esas transmisiones.

---

## 3. T-CONTs reescalados (×8)

Fair-share por ONU: Fase 2 = 1244.16/32 = 38.88 Mbps; Fase 3 =
2488.32/8 = 311.04 Mbps → factor **×8**.

| | T-CONT1 (VoIP/control) | T-CONT2 (Video) | T-CONT4 (Best Effort) |
|---|---|---|---|
| Tráfico | CBR | Poisson | Pareto α=1.5 |
| Tasa | 1 Mbps (igual Fase 2 — VoIP es VoIP) | **40 Mbps** (×8, mantiene 12.86% de capacidad) | 200/400/800 Mbps/ONU según escenario (×8 del barrido 25/50/100 de Fase 2) |
| Paquete | 160 B | 1000 B | 1400 B |
| Buffer | 10.000 B | 200.000 B | 2.000.000 B |
| Grant fijo/asegurado | 160 B/trama (T1, incondicional) | 1000 B/trama (igual Fase 2: 64Mbps >> 40Mbps medio) | — |

---

## 4. Tabla SLA

| Tipo | SLA (delay máx) | Justificación |
|---|---|---|
| **T-CONT1** (VoIP/control) | **≤ 2 ms** | Instrucción explícita de la profesora |
| T-CONT2 (Video) | ≤ 20 ms | Meta de proyecto, rango típico 10–20ms para video interactivo/baja latencia. No es una norma ITU-T específica de PON |
| T-CONT4 (Best Effort) | ≤ 500 ms | Cota laxa/diagnóstica — best-effort no tiene SLA de latencia en ITU-T. El foco es `latency_max` y `loss_rate` |

Nueva métrica: **`sla_compliance_pct`** = % de paquetes entregados con
`latencia ≤ cota_SLA`, calculada por (ONU, T-CONT).

---

## 5. Algoritmos comparados

### IPACT — polling de ciclo variable (adaptado de EPON, declarado)

La OLT recorre las 8 ONUs en round-robin secuencial. Para cada ONU calcula
un grant **"limited service"**: `grant_total = min(demanda_reportada,
B_max)`, con `B_max = 38.880 bytes` (= 1 trama XG-PON = 125 μs de
transmisión). Dentro del grant, sub-asignación T1 > T2 > T4 (misma
prioridad que QoSDBA, para aislar la variable "timing/bw por ONU").

El ciclo completo (recorrer las 8 ONUs y volver a la 0) tiene duración
**variable**: `cycle_time = Σ(grant_time_i + guard_time)`, con
`guard_time = 1 μs`.

- Ciclo mínimo (colas vacías) = 8 × 1 μs = **8 μs**
- Ciclo máximo (saturación) = 8 × (125+1) μs = **1.008 ms**

### GIANT — GPA + SPA (nativo GPON/XG-PON)

Encaja en la trama fija de 125 μs (broadcast BWmap, igual mecanismo que
SR-DBA de Fase 2):

- **GPA (Guaranteed Phase Allocation):** T-CONT1 fijo (160 B/trama,
  incondicional) + T-CONT2 asegurado mediante contadores **SImax** (cada 8
  tramas = 1ms, una ONU es elegible para un grant "catch-up" de hasta
  `assured_bytes_per_frame × SImax = 8000 B`).
- **SPA (Surplus Phase Allocation):** T-CONT4 con contadores **SImin** (32
  tramas = 4ms) + round-robin entre ONUs elegibles, repartiendo lo que sobra
  de GPA.

### QoSDBA (referencia Fase 2, re-parametrizado)

Mismo algoritmo de Fase 2 (T1 fijo → T2 asegurado demand-based → T4
proporcional al sobrante), corriendo sobre los parámetros XG-PON/8 ONUs.

---

## 6. Resultados clave

Corrida completa: 9 escenarios (3 algoritmos × 3 cargas T-CONT4) × 10
repeticiones × 10 s de simulación (1 s de warmup). Resultados completos en
`results/xgpon_results.csv` y `results/xgpon_cycle_times.csv`, gráficos en
`figures/xgpon/`.

| Métrica @ 800 Mbps/ONU (sobrecarga ~257%) | IPACT | GIANT | QoSDBA |
|---|---|---|---|
| T-CONT1 SLA% (≤2ms) | **88.4%** | 100.0% | 100.0% |
| T-CONT1 delay máximo (μs) | **2109.0** | 226.0 | 226.0 |
| T-CONT2 SLA% (≤20ms) | 100.0% | 100.0% | 100.0% |
| T-CONT4 delay máximo (ms) | 63.5 | 65.9 | 87.8 |
| T-CONT4 loss rate | 0.703 | 0.714 | 0.789 |
| Throughput agregado (Mbps) | 2424.5 | 2343.3 | 1812.6 |
| Cycle time (IPACT) mean/min/max (μs) | 1008.0 / 1008.0 / 1008.0 | n/a (125μs fijo) | n/a (125μs fijo) |

### Hallazgos

1. **T-CONT1 (SLA 2ms) — la comparación central**: bajo GIANT y QoSDBA, T1
   tiene latencia **constante e independiente de la carga** (164.3 μs media,
   226.0 μs peor caso, 100% SLA en las 3 cargas) gracias a la reserva
   incondicional de 160 B/trama. Bajo IPACT, a partir de 400 Mbps/ONU el
   ciclo de polling se satura en 1008 μs constantes y el delay máximo de T1
   llega a **2109 μs**, superando la cota de 2 ms → **88.4% de cumplimiento
   SLA** (11.6% de los paquetes de voz violan el SLA). Es exactamente el
   contraste que pidió la profesora: SR-DBA/GIANT con reserva garantizada vs.
   polling demand-based con reporte ~1 ciclo de antigüedad.

2. **Ciclo de polling IPACT (`cycle_time_distribution.png`)**: a 200
   Mbps/ONU (subcarga) el ciclo es **variable**, entre 16.2 μs y 413.7 μs
   (media 167.2 μs) — cerca pero distinto de la trama fija de 125 μs de
   GIANT/QoSDBA. A 400 y 800 Mbps/ONU el ciclo se vuelve **constante en
   1008.0 μs** (= 8×(125+1) μs, el máximo teórico): saturación total.

3. **T-CONT2/T-CONT4 cumplen SLA siempre** (100% en T2 ≤20ms; T4 nunca supera
   ~88 ms vs. cota de 500 ms) — el problema de SLA en esta fase está
   concentrado exclusivamente en T-CONT1 bajo IPACT.

4. **Eficiencia agregada (hallazgo secundario)**: a 800 Mbps/ONU, IPACT y
   GIANT entregan ~2.34-2.42 Gbps (94-97% de los 2488.32 Mbps de capacidad),
   mientras QoSDBA se estanca en ~1.81 Gbps (73%) — su reparto proporcional
   de T-CONT4 deja capacidad sin usar. Esto también se ve en `loss_rate` de
   T4: QoSDBA ya pierde 15.1% a 200 Mbps/ONU (subcarga global ~64%) mientras
   GIANT/IPACT tienen 0% pérdida en ese mismo escenario.

---

## 7. Simplificaciones declaradas

| Simplificación | Descripción |
|---|---|
| Sub-asignación intra-ONU de IPACT | T1 > T2 > T4, igual que QoSDBA — aísla la variable "cómo se determina el bw/timing por ONU" del "orden intra-ONU" |
| "Catch-up" sizing de GIANT (SImax) | `assured_bytes_per_frame × SImax` — interpretación propia del equipo de la semántica SImax |
| Contadores T2 escalonados en GIANT | `_t2_counter[onu] = onu_id % SImax` — evita que las 8 ONUs compitan simultáneamente cada SImax tramas (sesgo por orden de iteración) |
| SPA round-robin de GIANT | El contador SImin solo se reinicia si la cola quedó drenada (`grant >= demand`); si sigue congestionada, la ONU permanece elegible inmediatamente — evita "tramas muertas" bajo sobrecarga sostenida |
| OLT no espera REPORT antes de re-pollear (IPACT) | Usa el último reporte disponible (~RTT de antigüedad), igual que SR-DBA — idealización estándar de IPACT |
| Topología | 8 ONUs idénticas a 20km (igual Fase 2: "todas a igual distancia") |

### Hallazgo esperado: T-CONT1 bajo IPACT

A diferencia de GIANT/QoSDBA (T-CONT1 reservado **incondicionalmente**, sin
mirar el reporte), IPACT asigna T1 *demand-based* a partir del último
reporte (~1 ciclo de antigüedad). Bajo saturación esto puede producir
latencias de T1 cercanas a ~2 ciclos (~2.0–2.2 ms), violando ocasionalmente
el SLA de 2ms — **es precisamente la comparación que pidió la profesora**:
SR-DBA/GIANT con T1 pre-reservado vs polling demand-based puro.

---

*OmneTeam — David Retuerto · José Vega · Matías Perelli — TEL-341 UTFSM 2026*
