# Documentación Técnica — Fase 3 (XG-PON, IPACT vs GIANT vs QoSDBA)
## TEL-341 Simulación de Redes — OmneTeam
### Universidad Técnica Federico Santa María

---

> Este documento es el **análogo de Fase 3** de
> [`DOCUMENTACION_TECNICA.md`](DOCUMENTACION_TECNICA.md) (Fase 2, GPON
> G.984). Describe **solo lo que cambia o se agrega** respecto a Fase 2;
> donde el mecanismo se reutiliza sin cambios (motor DES, generadores de
> tráfico, formato de T-CONT), se referencia la sección correspondiente de
> Fase 2 en vez de repetirla.
>
> Para una explicación accesible/sin jerga del mismo contenido, ver
> [`COMO_FUNCIONA_FASE3.md`](COMO_FUNCIONA_FASE3.md). Para el resumen
> ejecutivo orientado a la profesora, ver
> [`PARA_LA_PROFE_FASE3.md`](PARA_LA_PROFE_FASE3.md).

---

## Índice

1. [Red XG-PON1 — Base Teórica y Estándar (ITU-T G.987)](#1-red-xg-pon1)
2. [Arquitectura del Simulador — Cambios de Fase 3](#2-arquitectura)
3. [Motor de Eventos Discretos — Extensión Fase 3](#3-motor-des)
4. [T-CONTs Reescalados ×8](#4-t-conts)
5. [Generadores de Tráfico (reuso de Fase 2)](#5-generadores-de-tráfico)
6. [Mecanismo DBA — SR-DBA Broadcast vs Polling](#6-mecanismo-dba)
7. [Algoritmos DBA Implementados](#7-algoritmos-dba)
8. [Métricas — Extensión Fase 3 (SLA)](#8-métricas)
9. [Parámetros de Configuración](#9-parámetros)
10. [Simplificaciones y Limitaciones](#10-simplificaciones)
11. [Flujo de Ejecución](#11-flujo-de-ejecución)
12. [Fuentes y Referencias](#12-referencias)
13. [Apéndice — Resultados de la Corrida Completa](#13-apéndice)

---

## 1. Red XG-PON1

### 1.1 ¿Qué es XG-PON?

**XG-PON1** (10-Gigabit-capable Passive Optical Network, primera
generación) es el sucesor directo de GPON, definido por la **ITU-T en la
serie G.987** (G.987.1, G.987.2, G.987.3; primeras versiones ~2010,
amendadas ~2012). Mantiene la misma arquitectura de árbol óptico pasivo y la
misma estructura de trama de 125 μs que GPON (G.984.3), pero con tasas de
línea mayores: downstream 4× y upstream 2× respecto a GPON G.984.

**Por qué se eligió XG-PON1 para esta fase:** la profesora pidió migrar de
GPON a XG-PON manteniendo el resto del diseño (mismo `frame_duration`, mismo
mecanismo TDMA upstream, misma topología de 20 km) para que los resultados de
Fase 2 y Fase 3 sean directamente comparables salvo por las variables que
cambian a propósito (número de ONUs, algoritmo DBA, tasas).

**Estándar de referencia principal:** ITU-T G.987.1, G.987.2, G.987.3.

### 1.2 Arquitectura física de la red (Fase 3)

```
Central Office (CO)
    │
  [OLT] — Optical Line Terminal (XG-PON1)
    │  Feeder Fiber, 20 km, 100 μs one-way
  [Splitter 1:8]  ← pasivo, sin alimentación
    │
    ├─── ONU 0 ──┐
    ├─── ONU 1   │
    ├─── ONU 2   │  8 ONUs idénticas:
    ├─── ONU 3   │  T-CONT1 (CBR) + T-CONT2 (Poisson) + T-CONT4 (Pareto)
    ├─── ONU 4   │  mismas tasas, mismo buffer, misma distancia (20 km)
    ├─── ONU 5   │
    ├─── ONU 6   │
    └─── ONU 7 ──┘
```

Cambios respecto a Fase 2 (`DOCUMENTACION_TECNICA.md` §1.2): split ratio
1:32 → **1:8**, y se elimina la heterogeneidad de tasas de T-CONT4 entre
ONUs (en Fase 2 cada ONU podía tener distinta tasa de best-effort; en Fase 3
**las 8 ONUs son idénticas**, requerimiento explícito de la profesora).

### 1.3 Parámetros físicos exactos de XG-PON1 (ITU-T G.987.2)

| Parámetro | Valor | Fuente |
|-----------|-------|--------|
| Tasa downstream | **9.95328 Gbps** | ITU-T G.987.2 |
| Tasa upstream | **2.48832 Gbps** | ITU-T G.987.2 |
| Duración trama GTC | **125 μs** (igual que G.984.3) | ITU-T G.987.3 |
| Tramas por segundo | **8,000 tramas/s** | = 1 / 125μs |
| Bytes por trama upstream | **38,880 bytes** | = 2.48832×10⁹ × 125×10⁻⁶ / 8 |
| Split ratio | **1:8** | requerimiento Fase 3 |
| Alcance (Nominal Differential Reach) | **20 km**, Clase N1 | ITU-T G.987.2 |
| Delay propagación | **5 μs/km** | igual modelo que Fase 2 |
| RTT a 20 km | **200 μs** | = 2 × 20km × 5μs/km |
| Guard band | 32 bytes/ONU | igual que Fase 2 (simplificación, ver §10) |

**Verificación del cálculo de bytes/trama:**
```
bytes_per_frame = upstream_rate × frame_duration / 8_bits_per_byte
               = 2.48832 × 10⁹ bps × 125 × 10⁻⁶ s / 8
               = 311,040,000 × 10⁻⁶ bits / 8
               = 311,040 bits / 8
               = 38,880 bytes ✓  (= 2 × 19,440 bytes de Fase 2)
```

### 1.4 Comparación XG-PON1 (Fase 3) vs GPON G.984 (Fase 2)

| Parámetro | GPON G.984 (Fase 2) | XG-PON1 G.987 (Fase 3) | Factor |
|---|---|---|---|
| Downstream | 2.48832 Gbps | 9.95328 Gbps | ×4 |
| Upstream | 1.24416 Gbps | 2.48832 Gbps | ×2 |
| Bytes/trama upstream | 19,440 | 38,880 | ×2 |
| Trama GTC | 125 μs | 125 μs | = |
| Split ratio | 1:32 | 1:8 | ÷4 |
| Número de ONUs simuladas | 32 | 8 | ÷4 |
| Fair-share upstream/ONU | 38.88 Mbps | 311.04 Mbps | ×8 |
| Topología (distancia/RTT) | 20 km / 200 μs | 20 km / 200 μs | = |

El upstream de XG-PON1 (2.48832 Gbps) **coincide numéricamente** con el
downstream de GPON G.984 — no es coincidencia: XG-PON1 define un upstream
"2.5G" simétrico al downstream "10G" mediante un factor 4:1, mientras GPON
G.984 usa un downstream "2.5G" con upstream "1.25G" (factor 2:1).

### 1.5 Mecanismo de acceso upstream

Sin cambios respecto a Fase 2 (`DOCUMENTACION_TECNICA.md` §1.5): TDMA,
coordinado por la OLT. Lo que cambia en Fase 3 es **cómo** la OLT coordina
ese acceso — broadcast de BWmap (GIANT/QoSDBA) vs. polling secuencial
(IPACT), ver §6.

---

## 2. Arquitectura

### 2.1 Módulos nuevos/modificados en Fase 3

| Módulo | Estado | Descripción |
|---|---|---|
| `simulator/engine.py` | Modificado (aditivo) | +3 constantes de evento: `EVT_OLT_SEND_GATE`, `EVT_ONU_RECV_GATE`, `EVT_OLT_POLL_NEXT` |
| `simulator/onu.py` | Modificado (aditivo) | +método `on_receive_gate()` (camino IPACT), sin tocar `on_receive_bwmap()` |
| `metrics/collector.py` | Modificado (aditivo, retrocompatible) | +`sla_bounds_s`, +`record_cycle_time()`, +campos `latency_max_us`, `sla_bound_us`, `sla_compliance_pct`, `cycle_time_*` |
| `simulator/dba_giant.py` | **Nuevo** | GIANT: GPA (T1 fijo + T2 vía SImax) + SPA (T4 vía SImin + round-robin) |
| `simulator/dba_ipact.py` | **Nuevo** | `IpactDBA.allocate_onu()`: grant "limited service" por ONU |
| `simulator/olt_ipact.py` | **Nuevo** | `OLTPolling`: polling round-robin de ciclo variable |
| `simulator/dba_qos.py` | Sin cambios de código | Reutilizado tal cual, re-parametrizado vía `configs/xgpon.json` |
| `simulator/olt.py`, `tcont.py`, `traffic.py` | Sin cambios | Reutilizados tal cual (Fase 2) |
| `configs/xgpon.json` | **Nuevo** | Parámetros XG-PON1, T-CONTs ×8, tabla `sla`, bloques `ipact`/`giant` |
| `configs/scenarios_xgpon.json` | **Nuevo** | 9 escenarios (3 algoritmos × 3 cargas T-CONT4) |
| `main_xgpon.py` | **Nuevo** | CLI `--algorithm {ipact,giant,qos}`, wiring condicional (ver §11) |
| `run_experiments_xgpon.py` | **Nuevo** | Corre los 9 escenarios × 10 repeticiones (paralelizado) |
| `analysis/analyze_xgpon.py` | **Nuevo** | 6 gráficos en `figures/xgpon/` |

Todos los archivos de Fase 2 (`configs/default.json`, `dba_basic.py`,
`dba_qos.py`, `scenarios.json`, `main.py`, `run_experiments.py`,
`analysis/analyze.py`, `results/all_results.csv`, `figures/*.png`,
`entregas/Parte_2/`) permanecen **sin modificar** — verificado ejecutando
`python3 main.py --algorithm qos --load 50 --num-onus 32` tras todos los
cambios de Fase 3.

### 2.2 Dos caminos de ejecución

Fase 3 introduce una **bifurcación arquitectónica** en `main_xgpon.py`,
según el algoritmo:

```
                    ┌─────────────┐
                    │  main_xgpon  │
                    └──────┬───────┘
                           │
            algoritmo == "ipact" ?
                    │              │
                   sí              no (giant | qos)
                    │              │
                    ▼              ▼
            ┌───────────────┐  ┌──────────────────┐
            │  OLTPolling    │  │  OLT (Fase 2)     │
            │  + IpactDBA    │  │  + GiantDBA/QoSDBA│
            │  GATE/poll     │  │  BWmap broadcast  │
            │  individual    │  │  cada 125 μs      │
            └───────┬────────┘  └─────────┬─────────┘
                    │                      │
                    ▼                      ▼
            ONU.on_receive_gate    ONU.on_receive_bwmap
            (nuevo, Fase 3)        (Fase 2, sin cambios)
```

Las 8 instancias de `ONU` y sus `TCont`/generadores de tráfico son
**idénticas** en ambos caminos — lo único que cambia es qué evento recibe la
ONU (`ONU_RECEIVE_GATE` vs `ONU_RECEIVE_BWMAP`) y quién en la OLT decide el
contenido de ese mensaje.

---

## 3. Motor DES

### 3.1 Eventos reutilizados de Fase 2 (sin cambios)

| Constante | Valor | Uso |
|---|---|---|
| `EVT_OLT_BWMAP` | `"OLT_GENERATE_BWMAP"` | OLT genera BWmap cada 125 μs (camino broadcast) |
| `EVT_ONU_RECV_BWMAP` | `"ONU_RECEIVE_BWMAP"` | ONU recibe BWmap tras `prop_delay` |
| `EVT_ONU_GEN_TRAFFIC` | `"ONU_GENERATE_TRAFFIC"` | Generador de paquetes (self-scheduling) |
| `EVT_OLT_RECV_DATA` | `"OLT_RECEIVE_DATA"` | OLT recibe burst upstream |
| `EVT_OLT_RECV_REPORT` | `"OLT_RECEIVE_REPORT"` | OLT recibe DBRu |

### 3.2 Eventos nuevos de Fase 3 (camino IPACT)

Agregados a `simulator/engine.py` sin alterar los anteriores:

```python
EVT_OLT_SEND_GATE = "OLT_SEND_GATE"     # OLT envía GATE (poll) a una ONU
EVT_ONU_RECV_GATE = "ONU_RECEIVE_GATE"  # ONU recibe GATE, transmite y reporta
EVT_OLT_POLL_NEXT = "OLT_POLL_NEXT"     # OLT avanza al siguiente ONU del ciclo
```

El motor (`SimEngine`, heap de eventos + `run(until)`) en sí **no cambia**:
estos son simplemente 3 nuevos `event_type` con sus handlers registrados
condicionalmente (§11).

---

## 4. T-CONTs

### 4.1 Tabla de parámetros (Fase 3, `configs/xgpon.json`)

| | T-CONT1 (VoIP/control) | T-CONT2 (Video) | T-CONT4 (Best Effort) |
|---|---|---|---|
| Tráfico | CBR | Poisson | Pareto α=1.5 |
| Tasa | 1 Mbps | 40 Mbps | 200 / 400 / 800 Mbps/ONU (según escenario) |
| Tamaño paquete | 160 B | 1000 B | 1400 B |
| Buffer | 10,000 B | 200,000 B | 2,000,000 B |
| Grant fijo/asegurado | 160 B/trama (incondicional) | 1000 B/trama (cap demand-based) | — |

### 4.2 Derivación del factor ×8

- **Fair-share por ONU**: Fase 2 = 1244.16/32 = 38.88 Mbps; Fase 3 =
  2488.32/8 = 311.04 Mbps → factor **×8**.
- **T-CONT1**: sin cambio (1 Mbps, 160 B) — "VoIP es VoIP", no escala con la
  capacidad del enlace.
- **T-CONT2**: 5 Mbps (Fase 2) → **40 Mbps** (Fase 3) = ×8, manteniendo
  **12.86%** de la capacidad total en ambas fases (5×32/1244.16 =
  40×8/2488.32 = 12.86%).
- **`assured_bytes_per_frame = 1000`**: misma constante que Fase 2 (NO se
  escala). 1000 B/trama × 8000 tramas/s = 64 Mbps >> 40 Mbps medio de T2 —
  mismo margen relativo que Fase 2 (64 Mbps >> 5 Mbps).
- **T-CONT4**: barrido {10,25,50,75,100} Mbps/ONU (Fase 2) → ×8 =
  {80,200,400,600,800} Mbps/ONU. Los 9 escenarios de Fase 3 usan el
  subconjunto representativo **{200, 400, 800}**, preservando las mismas
  razones de sobrecarga relativas (p.ej. 800 Mbps/ONU × 8 ONUs / 2488.32 Mbps
  = **257%**, igual que 100 Mbps/ONU × 32 / 1244.16 Mbps = 257% en Fase 2).

### 4.3 Tabla SLA (nueva en Fase 3)

| Tipo | SLA (delay máx) | Justificación |
|---|---|---|
| **T-CONT1** (VoIP/control) | **≤ 2 ms** | Instrucción explícita de la profesora |
| T-CONT2 (Video) | ≤ 20 ms | Meta de proyecto (rango típico 10–20 ms para video interactivo/baja latencia); no es norma ITU-T específica de PON |
| T-CONT4 (Best Effort) | ≤ 500 ms | Cota laxa/diagnóstica — best-effort no tiene SLA de latencia en ITU-T. Foco: `latency_max_us` y `loss_rate` |

Implementación: `simulator/tcont.py` y los generadores de tráfico
(`simulator/traffic.py`, CBR/Poisson/Pareto) **no cambian** respecto a Fase 2
— ver §5.

---

## 5. Generadores de Tráfico

Sin cambios de código respecto a Fase 2
(`DOCUMENTACION_TECNICA.md` §5: `CBRTrafficGen`, `PoissonTrafficGen`,
`ParetoTrafficGen` en `simulator/traffic.py`). Lo que cambia son los
**parámetros** (tasas ×8 para T2/T4, ver §4.2), pasados vía
`configs/xgpon.json`.

Recordatorio de las 3 distribuciones:

- **T-CONT1 (CBR)**: `interval = pkt_size×8 / rate_bps` — determinístico. Con
  160 B y 1 Mbps → 1.28 ms entre paquetes.
- **T-CONT2 (Poisson)**: `next_interval() = random.expovariate(1/mean_interval)`
  — llegadas exponenciales, media constante.
- **T-CONT4 (Pareto, α=1.5)**: heavy-tailed — modela el tráfico
  self-similar de datos/Internet (Leland et al. 1994, ya citado en Fase 2).

---

## 6. Mecanismo DBA

### 6.1 Camino "broadcast" — SR-DBA (GIANT y QoSDBA)

Reutiliza `simulator/olt.py` (`OLT`, sin cambios) y el handler
`ONU.on_receive_bwmap()` (sin cambios). Cada 125 μs:

```
1. OLT.on_generate_bwmap():
   bwmap = dba.allocate(onu_reports, capacity=38880, num_onus=8, config)
   broadcast: schedule(EVT_ONU_RECV_BWMAP, delay=100μs) para cada ONU
   metrics.record_frame_utilization(now, Σgrants, 38880)
   schedule(EVT_OLT_BWMAP, delay=125μs)  ← próxima trama

2. ONU.on_receive_bwmap() (t = t_bwmap + 100μs):
   para cada T-CONT con grant>0: dequeue + transmitir (tx_time + 100μs)
   schedule(EVT_OLT_RECV_REPORT, delay=100μs)  ← DBRu
```

La OLT nunca espera — usa el `onu_reports` más reciente disponible (típicamente
~1-2 tramas de antigüedad por el RTT de 200 μs).

### 6.2 Camino "polling" — IPACT

Implementado en `simulator/olt_ipact.py` (`OLTPolling`) +
`simulator/dba_ipact.py` (`IpactDBA`) + `ONU.on_receive_gate()` (nuevo). La
OLT recorre las 8 ONUs round-robin:

```
1. OLTPolling.on_send_gate(onu_i):
   allocation = dba.allocate_onu(onu_i, último_reporte[onu_i], B_max=38880, config)
   grant_time = Σ(allocation.values()) × 8 / upstream_rate_bps
   schedule(EVT_ONU_RECV_GATE, delay=100μs)             ← GATE a la ONU
   schedule(EVT_OLT_POLL_NEXT, delay=grant_time+guard_time)  ← sin esperar respuesta

2. OLTPolling.on_poll_next():
   poll_ptr = (poll_ptr + 1) % 8
   schedule(EVT_OLT_SEND_GATE, {"onu_id": poll_ptr})    ← inmediato

3. ONU.on_receive_gate() (t = t_gate + 100μs):
   idéntico a on_receive_bwmap(): dequeue + transmitir + DBRu
```

`cycle_time = Σ_{i=0..7}(grant_time_i + guard_time_i)`:
- Mínimo (colas vacías): 8 × 1μs = **8 μs**
- Máximo (saturación, B_max=38880B cada poll): 8 × (125+1)μs = **1008 μs**

### 6.3 Comparación conceptual

| | SR-DBA broadcast (GIANT/QoSDBA) | Polling (IPACT) |
|---|---|---|
| Mensaje OLT→ONUs | 1 BWmap broadcast (todas las ONUs a la vez) | N GATEs individuales (1 por ONU) |
| Periodicidad | Fija: 125 μs | Variable: `cycle_time` ∈ [8μs, 1008μs] |
| Antigüedad del reporte usado | ~1-2 tramas (~125-250 μs) | ~1 ciclo (~hasta ~1ms bajo saturación) |
| T-CONT1 | Reserva incondicional cada trama | Demand-based desde último reporte |
| Origen conceptual | Nativo GPON/XG-PON (G.984.3/G.987.3 §9, "Status Reporting") | Adaptado de EPON IEEE 802.3ah (Kramer et al. 2002) |

---

## 7. Algoritmos DBA

### 7.1 IPACT — `simulator/dba_ipact.py` + `simulator/olt_ipact.py`

**Referencia:** Kramer, Mukherjee, Pesavento (2002), "IPACT: A Dynamic
Protocol for an Ethernet PON (EPON)" — ya citado en Fase 2 §12 como base
conceptual de BasicDBA. En Fase 3 se implementa IPACT de forma más fiel: el
ciclo es de **duración variable** (no la trama fija de 125 μs), con servicio
**"limited"**.

**Pseudocódigo — `IpactDBA.allocate_onu()`** (llamado una vez por poll, para
UNA sola ONU — interfaz distinta a `BasicDBA`/`QoSDBA`/`GiantDBA`, que
asignan para todas las ONUs por trama):

```
allocate_onu(onu_id, report, B_max, config):
    total_demand = Σ report.queue_bytes[tc] para tc en {1,2,4}
    grant_total  = min(total_demand, B_max)          # "limited service"

    result, remaining = {1:0, 2:0, 4:0}, grant_total
    para tc en (1, 2, 4):                            # prioridad T1>T2>T4
        grant       = min(report.queue_bytes[tc], remaining)
        result[tc]  = grant
        remaining  -= grant
    retornar result   # Σ result.values() <= B_max
```

**Pseudocódigo — `OLTPolling` (ciclo de polling)**:

```
on_send_gate(onu_i):
    allocation  = dba.allocate_onu(onu_i, onu_reports[onu_i], B_max, config)
    grant_time  = Σ(allocation.values()) × 8 / upstream_rate

    si onu_i == 0 y no es el primer ciclo:
        record_cycle_time(now - cycle_start)
        record_frame_utilization(cycle_used_bytes, B_max × 8)
        cycle_start = now

    schedule(ONU_RECEIVE_GATE, delay=prop_delay, {onu_id:onu_i, allocation})
    schedule(OLT_POLL_NEXT, delay=grant_time + guard_time)  # NO espera respuesta

on_poll_next():
    poll_ptr = (poll_ptr + 1) mod 8
    schedule(OLT_SEND_GATE, {onu_id: poll_ptr})
```

**Parámetros** (`configs/xgpon.json` → `ipact`):
- `b_max_bytes = 38880` (= 1 trama XG-PON = 125 μs de transmisión)
- `guard_time_s = 1e-6` (1 μs, valor típico de guard band EPON/IPACT)

**Ciclo máximo numérico:** `B_max × 8 / upstream_rate = 38880×8/2.48832e9 =
125 μs` por ONU; ciclo completo saturado = `8 × (125+1) μs = 1008 μs` — buena
justificación numérica para `B_max = 38880` (1 trama exacta).

#### 7.1.1 Staleness de reportes y su efecto en el SLA de T-CONT1

A diferencia de GIANT/QoSDBA (T-CONT1 reservado **incondicionalmente**, sin
mirar el reporte — §7.2/§7.3), IPACT asigna T1 *demand-based* a partir del
**último reporte conocido**, que en el peor caso tiene ~1 ciclo de
antigüedad (hasta ~1008 μs bajo saturación + 100 μs de propagación ≈ ~1.1
ms). Esto puede producir, en el peor caso de alineación de fases, latencias
de T1 cercanas a **~2 ciclos** (~2.0–2.2 ms) — **resultado confirmado en
§13**: `latency_max_us(T1, IPACT, ≥400Mbps/ONU) = 2109.0 μs > 2000 μs (SLA)`,
con `sla_compliance_pct = 88.4%`.

Esta es **la comparación central que pidió la profesora**: SR-DBA con T1
pre-reservado (GIANT/QoSDBA, 100% SLA siempre) vs. polling demand-based puro
(IPACT, SLA puede degradarse bajo saturación). Se documenta como **hallazgo
esperado**, no como error de implementación.

---

### 7.2 GIANT — `simulator/dba_giant.py`

**Concepto:** GIANT (*Guaranteed + Surplus*) divide cada trama en dos fases:

- **GPA (Guaranteed Phase Allocation)**: T-CONT1 (Fixed) + T-CONT2 (Assured).
- **SPA (Surplus Phase Allocation)**: T-CONT4 (Non-assured/best-effort), con
  lo que sobra de GPA.

**Pseudocódigo:**

```
allocate(onu_reports, capacity=38880, num_onus=8, config):
    remaining = capacity - 32×num_onus                 # guard overhead

    # GPA paso 1 — T-CONT1 (Fixed): igual que QoSDBA, incondicional
    para cada onu_i:
        grant = min(fixed_bytes_per_frame=160, remaining)
        bwmap[onu_i][1] = grant; remaining -= grant

    # GPA paso 2 — T-CONT2 (Assured): contador SImax escalonado
    para cada onu_i:
        si t2_counter[onu_i] == 0:
            cap   = assured_bytes_per_frame(1000) × SImax(8) = 8000
            grant = min(demand_t2[onu_i], cap, remaining)
            bwmap[onu_i][2] = grant; remaining -= grant
            t2_counter[onu_i] = SImax
        sino:
            t2_counter[onu_i] -= 1

    # SPA — T-CONT4 (Non-assured): contador SImin + round-robin
    eligible = [onu_i : t4_counter[onu_i]==0 y demand_t4[onu_i]>0]
    ordered  = sort(eligible, key = (onu_i - spa_rr_ptr) mod 8)
    para onu_i en ordered (mientras remaining > 0):
        grant = min(demand_t4[onu_i], remaining)
        bwmap[onu_i][4] = grant; remaining -= grant
        si grant >= demand_t4[onu_i]:
            t4_counter[onu_i] = SImin     # cola drenada -> espera SImin tramas
        # si no, counter queda en 0 -> elegible de nuevo la próxima trama
        last_serviced = onu_i
    spa_rr_ptr = (last_serviced + 1) mod 8
```

**Parámetros** (`configs/xgpon.json` → `giant`): `SImax=8` tramas (1 ms) para
T-CONT2, `SImin=32` tramas (4 ms) para T-CONT4. Jerarquía `SImax << SImin`
(GPA > SPA).

#### 7.2.1 Dos correcciones de equidad (decisiones de diseño propias)

Documentadas explícitamente porque **sin ellas el algoritmo produce sesgos
artificiales por orden de iteración**, no propiedades reales de GIANT:

1. **Escalonamiento inicial de `_t2_counter`**:
   `_t2_counter[onu_id] = onu_id % SImax` (no todos en 0). Si las 8 ONUs
   parten con contador 0, todas son elegibles simultáneamente en la trama 1
   y cada `SImax` tramas después; con `cap = 8000` bytes y
   `remaining_after_T1 ≈ 37,344` bytes, la demanda conjunta de 8 ONUs
   (~40,000 B si cada una pide ~5,000 B) excede `remaining`, y el orden de
   iteración fijo (ONU 0..7) deja a las últimas ONUs sistemáticamente con
   grants truncados. Escalonando los contadores, en régimen estable **solo
   una ONU es elegible por trama**, `cap=8000` cabe holgadamente en
   `remaining≈37,344`, y las 8 ONUs reciben servicio uniforme.

2. **Corrección del puntero `_spa_rr_ptr`**: avanza solo hasta la **última
   ONU efectivamente servida** (`last_serviced`), no hasta el final del
   conjunto elegible. Si `remaining` se agota antes de recorrer todo
   `ordered`, las ONUs no servidas permanecen con `t4_counter==0` (elegibles
   la próxima trama) y el puntero retoma justo después de la última servida
   — evita que queden **perpetuamente pospuestas** bajo sobrecarga
   sostenida (el escenario de 800 Mbps/ONU es exactamente esto).

#### 7.2.2 Bug encontrado y corregido durante smoke tests

**Síntoma:** con el diseño inicial, `_t4_counter[onu_id]` se reseteaba a
`SImin` (32 tramas) **incondicionalmente** tras cualquier grant>0, incluso
si la ONU seguía congestionada (`grant < demand`). Esto generaba un "duty
cycle" sincronizado: solo 8 de cada 32 tramas repartían ancho de banda T4
entre las 8 ONUs (las otras 24 quedaban con `t4_grant=0` para todas).

**Fix** (líneas 134-139 de `dba_giant.py`): el contador solo se resetea a
`SImin` si `grant >= demand` (cola drenada). Si sigue congestionada
(`grant < demand`), el contador queda en 0 → la ONU permanece elegible la
próxima trama → round-robin continuo bajo sobrecarga sostenida.

**Resultado del fix** (load=400 Mbps/ONU, duration=2s, smoke test):

| Métrica | Antes del fix | Después del fix |
|---|---|---|
| Utilización canal | 36.2% | **99.3%** |
| T-CONT4 throughput | 485 Mbps | **2014 Mbps** |
| T-CONT4 latencia media | 260,835 μs | **63,400 μs** |

#### 7.2.3 Simplificaciones declaradas de GIANT

- GIANT real opera **por T-CONT** (una ONU puede tener varios T-CONTs del
  mismo tipo); aquí cada ONU tiene exactamente un T-CONT de cada tipo
  1/2/4, así que por-ONU == por-T-CONT.
- El tamaño "catch-up" (`assured_bytes_per_frame × SImax = 8000 B`) es la
  **interpretación propia del equipo** de la semántica SImax de GIANT — no
  hay un valor único especificado en G.984.3/G.987.3 para esto.

---

### 7.3 QoSDBA (reutilizado, re-parametrizado)

**Sin cambios de código** respecto a Fase 2 (`simulator/dba_qos.py`,
documentado en `DOCUMENTACION_TECNICA.md` §7.2). Mismo algoritmo de 3 pasos
(T1 fijo incondicional → T2 demand-based con `fair_share = remaining/num_onus`
→ T4 proporcional a la demanda). Lo que cambia son los **parámetros** vía
`configs/xgpon.json`:

| Parámetro | Fase 2 | Fase 3 |
|---|---|---|
| `fixed_bytes_per_frame` (T1) | 160 | 160 (sin cambio) |
| `assured_bytes_per_frame` (T2) | 78 | 1000 |
| `num_onus` | 32 | 8 |
| `total_capacity_bytes` | 19,440 | 38,880 |

Sirve como **referencia de Fase 2**: el algoritmo "SR-DBA con prioridad
jerárquica T1>T2>T4" frente a GIANT (SR-DBA con contadores de servicio) e
IPACT (polling).

---

## 8. Métricas

### 8.1 `MetricsCollector` — extensión retrocompatible

```python
MetricsCollector(warmup_s: float = 1.0,
                 sla_bounds_s: Optional[Dict[int, float]] = None)
```

- `sla_bounds_s`: `{tcont_type: max_delay_s}`, p.ej.
  `{1: 0.002, 2: 0.020, 4: 0.500}`. Si se omite (`None` → `{}`), el
  comportamiento es **idéntico a Fase 2** (`sla_compliance_pct = None`
  siempre).
- Nuevo método `record_cycle_time(sim_time, cycle_time_s)`: respeta
  `warmup_s`, llamado solo desde `OLTPolling.on_send_gate()` (IPACT). Para
  GIANT/QoSDBA, `self._cycle_times` queda vacío.

### 8.2 Campos nuevos en `summary()`

Por cada `(onu_id, tcont_type)`:

| Campo | Descripción |
|---|---|
| `latency_max_us` | `max(latencias) × 1e6` — siempre poblado (incluso sin `sla_bounds_s`) |
| `sla_bound_us` | Cota SLA en μs para ese T-CONT, o `None` si no hay cota configurada |
| `sla_compliance_pct` | % de paquetes con `latencia ≤ sla_bound`, o `None` si `sla_bound` no está configurado |

Globales (solo si `record_cycle_time()` fue llamado, i.e. solo IPACT):

| Campo | Descripción |
|---|---|
| `cycle_time_mean_us` / `_p99_us` / `_min_us` / `_max_us` | Estadísticas del ciclo de polling |
| `cycle_time_samples` | Lista cruda (segundos) — usada para el histograma de `cycle_time_distribution.png` |

`export_csv()` agrega `latency_max_us`, `sla_bound_us`,
`sla_compliance_pct` a cada fila por-paquete (mismo patrón que
`bytes_delivered`, ya repetido por fila en Fase 2). `cycle_time_samples` NO
va en `export_csv()` por fila (es global) — se exporta aparte en
`results/xgpon_cycle_times.csv` vía `run_experiments_xgpon.py`.

**Nota de implementación (bug corregido durante este trabajo):**
`cycle_time_samples` se almacena internamente en **segundos**
(`self._cycle_times.append((sim_time, cycle_time_s))`,
`metrics/collector.py` línea 59), mientras que `cycle_time_mean_us` etc. ya
vienen multiplicados por `1e6`. `run_experiments_xgpon.py` debe multiplicar
cada muestra de `cycle_time_samples` por `1e6` al escribir
`xgpon_cycle_times.csv` (columna `cycle_time_us`) — la primera versión del
script no lo hacía, lo que dejaba `cycle_time_distribution.png` vacío (todas
las muestras ≈0 en una escala de microsegundos). Corregido antes de generar
los gráficos finales (§13).

### 8.3 Verificación de retrocompatibilidad

`MetricsCollector(warmup_s=0.0)` (estilo Fase 2, sin `sla_bounds_s`) →
`sla_compliance_pct is None` para todo `(onu_id, tcont_type)`,
`latency_max_us > 0` tras `record_delivery()`. Verificado: `main.py` (Fase
2) sigue produciendo exactamente los mismos resultados que antes de estos
cambios.

---

## 9. Parámetros de Configuración

### 9.1 `configs/xgpon.json` — bloques nuevos/relevantes

```json
{
  "gpon": {
    "standard": "XG-PON1 (ITU-T G.987)",
    "upstream_rate_bps": 2488320000,
    "downstream_rate_bps": 9953280000,
    "frame_duration_s": 0.000125,
    "bytes_per_frame": 38880,
    "num_onus": 8,
    "fiber_length_km": 20,
    "prop_delay_s_per_km": 0.000005,
    "guard_bytes_per_onu": 32,
    "split_ratio": 8
  },
  "sla": {
    "1": {"max_delay_s": 0.002, "name": "T-CONT1 (VoIP/control)"},
    "2": {"max_delay_s": 0.020, "name": "T-CONT2 (Video)"},
    "4": {"max_delay_s": 0.500, "name": "T-CONT4 (Best Effort)"}
  },
  "ipact": {
    "b_max_bytes": 38880,
    "guard_time_s": 0.000001
  },
  "giant": {
    "si_max_frames": {"2": 8},
    "si_min_frames": {"4": 32}
  },
  "simulation": {
    "duration_s": 10.0,
    "warmup_s": 1.0,
    "repetitions": 10,
    "seed_base": 6767
  }
}
```

Bloques `gpon`/`tconts` para T-CONT1/2/4 documentados en §1/§4. `sla`,
`ipact`, `giant` son **nuevos** respecto a `configs/default.json` (Fase 2).

### 9.2 `configs/scenarios_xgpon.json` — 9 escenarios

3 algoritmos × 3 cargas de T-CONT4 (subconjunto representativo del barrido
×8 de Fase 2, ver §4.2):

| Escenario | Algoritmo | Carga T4/ONU | % de capacidad total (8×carga/2488.32) |
|---|---|---|---|
| `{IPACT,GIANT,QoSDBA}_load200` | ipact / giant / qos | 200 Mbps | ~64% (subcargado) |
| `{IPACT,GIANT,QoSDBA}_load400` | ipact / giant / qos | 400 Mbps | ~129% (al límite) |
| `{IPACT,GIANT,QoSDBA}_load800` | ipact / giant / qos | 800 Mbps | ~257% (sobrecarga severa) |

9 escenarios × 10 repeticiones (`seed = seed_base + rep`, `seed_base=6767`) ×
10 s de simulación (1 s warmup) = 90 corridas, paralelizadas con
`multiprocessing.Pool` (9 procesos).

---

## 10. Simplificaciones y Limitaciones

### 10.1 Tabla de simplificaciones (Fase 3, adicionales a las de Fase 2 §10.1)

| Simplificación | Descripción | Justificación |
|---|---|---|
| Sub-asignación intra-ONU de IPACT | T1 > T2 > T4, igual que QoSDBA | Aísla la variable "cómo/cuándo se calcula el grant por ONU" (lo que realmente difiere entre algoritmos) del "orden de prioridad intra-ONU" (constante, ya evaluado en Fase 2) |
| "Catch-up" sizing de GIANT (SImax) | `assured_bytes_per_frame × SImax = 8000 B` | Interpretación propia del equipo de la semántica SImax — G.984.3/G.987.3 no fijan un valor único |
| Contadores T2 escalonados en GIANT | `_t2_counter[onu] = onu_id % SImax` | Evita que las 8 ONUs compitan simultáneamente cada SImax tramas (sesgo por orden de iteración), ver §7.2.1 |
| Corrección del puntero RR de SPA en GIANT | Avanza solo hasta la última ONU servida | Evita postergación perpetua bajo sobrecarga sostenida, ver §7.2.1 |
| Reset condicional del contador T4 (GIANT) | Solo se reinicia si `grant >= demand` | Evita "tramas muertas" (duty cycle 1/4 observado antes del fix), ver §7.2.2 |
| OLT no espera REPORT antes de re-pollear (IPACT) | Usa el último reporte disponible (~1 ciclo de antigüedad) | Idealización estándar de IPACT — análogo a cómo SR-DBA usa reportes ~RTT-antiguos |
| Topología 8 ONUs idénticas | Mismas tasas/buffers/distancia para las 8 | Requerimiento explícito de la profesora para esta fase |
| IPACT declarado como adaptación de EPON | No se afirma que un OLT XG-PON real ejecute IPACT | Ejercicio de benchmarking explícito pedido por la profesora — ver §0 de `PARA_LA_PROFE_FASE3.md` |

Las simplificaciones de Fase 2 (§10.1 de `DOCUMENTACION_TECNICA.md`: sin
GEM, guard time reducido, sin ranging, sin FEC, sin downstream, sin colisión
física, DBRu simplificado, paquetes de tamaño fijo) **siguen aplicando sin
cambios** — son parte del motor reutilizado.

### 10.2 Efectos no modelados (adicional a Fase 2 §10.2)

- **Variabilidad de `B_max`/guard_time entre fabricantes de OLT EPON real**
  (IPACT permite varias políticas de servicio — aquí se usa "limited
  service" únicamente, la más simple y citada).
- **Múltiples T-CONTs del mismo tipo por ONU** (GIANT real opera a nivel
  T-CONT, no ONU — aquí coinciden 1:1, ver §7.2.3).

---

## 11. Flujo de Ejecución

### 11.1 Wiring condicional en `main_xgpon.py::run_simulation()`

```python
# Común a los 3 algoritmos:
engine  = SimEngine()
metrics = MetricsCollector(warmup_s=warmup, sla_bounds_s=sla_bounds)
onus    = [ONU(i, engine, config, metrics) for i in range(num_onus)]
engine.register(EVT_ONU_GEN_TRAFFIC, dispatch_traffic)

if algorithm == "ipact":
    dba = IpactDBA()
    olt = OLTPolling(engine, num_onus, dba, config, metrics)
    engine.register(EVT_OLT_SEND_GATE,   olt.on_send_gate)
    engine.register(EVT_OLT_POLL_NEXT,   olt.on_poll_next)
    engine.register(EVT_OLT_RECV_DATA,   olt.on_receive_data)
    engine.register(EVT_OLT_RECV_REPORT, olt.on_receive_report)
    engine.register(EVT_ONU_RECV_GATE,   dispatch_gate)   # -> onu.on_receive_gate

else:  # "giant" | "qos"
    dba = {"giant": GiantDBA, "qos": QoSDBA}[algorithm]()
    olt = OLT(engine, num_onus, dba, config, metrics)
    engine.register(EVT_OLT_BWMAP,       olt.on_generate_bwmap)
    engine.register(EVT_OLT_RECV_DATA,   olt.on_receive_data)
    engine.register(EVT_OLT_RECV_REPORT, olt.on_receive_report)
    engine.register(EVT_ONU_RECV_BWMAP,  dispatch_bwmap)  # -> onu.on_receive_bwmap

engine.run(until=duration)
summary = metrics.summary(duration)  # incluye drop_stats por ONU/T-CONT
```

Nótese que **`EVT_OLT_SEND_GATE`/`EVT_OLT_POLL_NEXT`/`EVT_ONU_RECV_GATE`** y
**`EVT_OLT_BWMAP`/`EVT_ONU_RECV_BWMAP`** son **mutuamente excluyentes**: solo
un conjunto de handlers se registra por corrida, según `algorithm`.

### 11.2 Inicialización y finalización

Idéntico a Fase 2 (`DOCUMENTACION_TECNICA.md` §11.1/§11.4), salvo:
- `sla_bounds = {int(k): v["max_delay_s"] for k,v in config["sla"].items()}`
  se pasa a `MetricsCollector`.
- `summary["drop_stats"]` se agrega igual que en Fase 2.
- Para IPACT, `OLTPolling.__init__` agenda el primer `EVT_OLT_SEND_GATE`
  para la ONU 0 en `t=0` (en vez de `EVT_OLT_BWMAP`).

### 11.3 Ejecución de experimentos (`run_experiments_xgpon.py`)

Por cada uno de los 9 escenarios (`configs/scenarios_xgpon.json`), corre 10
repeticiones (`seed = 6767 + rep`) vía `main_xgpon.run_simulation()`,
paralelizado con `multiprocessing.Pool(processes=9)`. Agrega resultados por
`(scenario, tcont_type)` con media + IC95% sobre las 10 repeticiones →
`results/xgpon_results.csv` (27 filas = 9 escenarios × 3 T-CONT). Para
escenarios `ipact`, además vuelca `cycle_time_samples` (×1e6 para
microsegundos) a `results/xgpon_cycle_times.csv`.

---

## 12. Referencias

### Estándares ITU-T

- **ITU-T G.987.1**: "10-Gigabit-capable passive optical networks (XG-PON):
  General requirements." Define los requerimientos generales de XG-PON1,
  incluyendo clases de alcance (Nominal Differential Reach).

- **ITU-T G.987.2**: "10-Gigabit-capable passive optical networks (XG-PON):
  Physical media dependent (PMD) layer specification." Define las tasas
  upstream (2.48832 Gbps) y downstream (9.95328 Gbps) de XG-PON1, y las
  clases de alcance (N1 = 20 km).

- **ITU-T G.987.3**: "10-Gigabit-capable passive optical networks (XG-PON):
  Transmission convergence (TC) layer specification." Define la trama GTC de
  125 μs (análoga a G.984.3), el mecanismo de DBA/Status-Reporting, y la
  semántica de T-CONT — base de §6.1 y de GIANT (§7.2).

Referencias de Fase 2 que siguen aplicando sin cambios (T-CONT, GEM, BWmap,
DBRu, G.984.3 §9): ver `DOCUMENTACION_TECNICA.md` §12.

### Papers académicos — DBA / polling

- **Kramer, G., Mukherjee, B., Pesavento, G. (2002).** "IPACT: A Dynamic
  Protocol for an Ethernet PON (EPON)." *IEEE Communications Magazine*,
  40(2):74–80. — Define IPACT (servicio "limited", ciclo variable, B_max).
  Ya citado en Fase 2 §12 como base conceptual de BasicDBA; en Fase 3 se
  implementa de forma más fiel (`simulator/dba_ipact.py` +
  `simulator/olt_ipact.py`), declarado explícitamente como adaptación de
  EPON con fines comparativos (§3.5 de `PLAN_FASE3.md`).

- **GIANT (Guaranteed + Surplus Allocation Technique)**: mecanismo GPA/SPA
  con contadores de service-interval (SImax/SImin) alineado a la semántica
  de T-CONT de ITU-T G.984.3 §9 / G.987.3, según material de cátedra del
  curso TEL-341. Refinamientos relacionados en la literatura:
  - Horvath, A. et al., "A Methodology for Calculating the Service Cycle
    Length of GPON-XGPON-... DBA Algorithms" / trabajos relacionados sobre
    "Modified GIANT DBA Algorithm for NG-PON" — discuten extensiones del
    esquema GPA/SPA a XG-PON/NG-PON2.
  - Las dos correcciones de equidad (§7.2.1) y el bug-fix del contador T4
    (§7.2.2) son **contribuciones propias del equipo** para esta
    implementación, documentadas explícitamente como tales.

- **Leland, Taqqu, Willinger, Wilson (1994)**, **Chang et al. (2006)**,
  **Neto et al. (2010)** — ya citados en Fase 2 §12, siguen siendo la base
  de los generadores Pareto/T2-T4 y del diseño jerárquico de QoSDBA,
  reutilizados sin cambios.

---

## 13. Apéndice — Resultados de la Corrida Completa

Corrida: 9 escenarios × 10 repeticiones × 10 s (1 s warmup), seeds
`6767..6776`. Fuente: `results/xgpon_results.csv`,
`results/xgpon_cycle_times.csv`. Gráficos: `figures/xgpon/*.png` (6
archivos). Tabla resumen @ 800 Mbps/ONU y discusión completa en
[`PARA_LA_PROFE_FASE3.md`](PARA_LA_PROFE_FASE3.md) §6.

**Resumen de hallazgos:**

1. T-CONT1 bajo GIANT/QoSDBA: latencia constante (164.3/226.0 μs
   media/máx), **100% SLA** en las 3 cargas — reserva incondicional cumple
   el SLA de 2 ms con amplio margen.
2. T-CONT1 bajo IPACT: a partir de 400 Mbps/ONU el ciclo se satura en
   **1008.0 μs constantes**, `latency_max_us = 2109.0 > 2000` (SLA) →
   **88.4% compliance** — hallazgo esperado de §7.1.1.
3. T-CONT2/T-CONT4: 100% SLA en los 3 algoritmos y las 3 cargas (cotas de
   20 ms / 500 ms muy holgadas frente a los valores observados, ≤3.1 ms y
   ≤88 ms respectivamente).
4. Cycle time IPACT: variable (16.2–413.7 μs, media 167.2 μs) a 200
   Mbps/ONU; constante en 1008.0 μs (máximo teórico) a 400/800 Mbps/ONU
   — confirma el contraste "ciclo variable vs trama fija de 125 μs".
5. Eficiencia agregada: IPACT/GIANT entregan ~94-97% de la capacidad
   (2488.32 Mbps) a 800 Mbps/ONU; QoSDBA se estanca en ~73% — su reparto
   proporcional de T-CONT4 es menos eficiente (`loss_rate` T4 más alto en
   las 3 cargas, incluyendo la subcargada).

---

*Documento preparado por OmneTeam (David Retuerto, José Vega, Matías Perelli)*
*TEL-341 Simulación de Redes — UTFSM — 2026*
