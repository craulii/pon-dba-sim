# Plan Fase 3 — XG-PON, IPACT vs GIANT vs QoSDBA, SLA-driven (8 ONUs)

> Documento de planificación guardado como referencia. Resume el pivote
> pedido por la profesora tras la reunión del 9/6/2026 y el diseño técnico
> acordado antes de implementar.

## Contexto

La profesora revisó el proyecto (Fase 2: GPON G.984, 32 ONUs, SR-DBA
centralizado, BasicDBA/QoSDBA — **completo y entregado, no se toca**) y dio
nueva retroalimentación que pivota significativamente el enfoque para una
nueva fase:

- Migrar a **XG-PON** (ITU-T G.987) en vez de GPON G.984.
- **8 ONUs, todas idénticas** (mismo mix de tráfico/T-CONTs).
- Confirmar foco **upstream-only** (ya es así en Fase 2).
- El problema central es **cumplir SLA**, con un **delay máximo de 2 ms**
  como meta explícita para el tráfico más exigente.
- Sobre el mecanismo DBA: la profesora discutió "polling vs centralizado",
  concluyó que polling es más eficiente, y pidió **quedarse con IPACT**
  (probarlo con distintos tráficos) y **probar GIANT** (algoritmo nativo de
  GPON). Esto **revierte** la postura de Fase 2 ("por qué no IPACT") — ahora
  es justamente la comparación pedida.
- Tráfico: cada ONU genera **varios tipos de tráfico simultáneos** (ya
  ocurre: T-CONT1/2/4), pero ahora **definidos en función de SLA** con un
  delay máximo por tipo, y métricas centradas en **delay máximo observado
  por tipo de tráfico** + tasa de transmisión.
- Topología "súper bien descrita" (distancia, etc.).

### Por qué antes era "NO IPACT" (Fase 2) y por qué ahora sí

En Fase 2 el simulador modelaba **GPON puro (ITU-T G.984)**. IPACT es el
protocolo de DBA de **EPON (IEEE 802.3ah)** — un estándar de otra
organización (IEEE vs ITU-T). Usar IPACT para "modelar GPON" habría sido
mezclar conceptos de estándares incompatibles, exactamente el error del
simulador OMNeT++ original que el equipo reemplazó.

En Fase 3 el encuadre cambia: ya no es "modelar GPON con IPACT", sino
**comparar explícitamente** un algoritmo de polling clásico (IPACT, **
adaptado y declarado como tal**, ver simplificaciones §3.5) contra uno
nativo de GPON/XG-PON (GIANT) — IPACT es el algoritmo de referencia estándar
en la literatura de DBA para PON. Se mantiene la honestidad conceptual:
IPACT se presenta como adaptación con fines comparativos, no como mecanismo
real de un OLT XG-PON.

**Decisiones confirmadas con el equipo:**
1. **Aditivo** — Fase 2 (configs/default.json, dba_basic.py, dba_qos.py,
   scenarios.json, results/, figures/, docs/, entregas/Parte_2/) **no se
   modifica**. Todo lo nuevo va en archivos nuevos.
2. **IPACT fiel**: ciclo de polling de duración **variable** (round-robin
   secuencial, "limited service" grant = min(demanda, B_max)), no el marco
   fijo de 125 µs.
3. **SLA**: mantener T-CONT1 (CBR/voz) / T-CONT2 (Poisson/video) / T-CONT4
   (Pareto/datos), agregar tabla de cotas SLA por tipo + nueva métrica
   `sla_compliance_pct` y `latency_max_us`.
4. **Algoritmos a comparar**: IPACT + GIANT + QoSDBA (re-parametrizado a
   XG-PON/8 ONUs) como referencia de Fase 2.

---

## 0. Resumen arquitectónico

| Algoritmo | Arquitectura | Archivo nuevo |
|---|---|---|
| **GIANT** | Reusa `OLT`/BWmap broadcast fijo cada 125 µs (sin cambios de engine) | `simulator/dba_giant.py` |
| **QoSDBA** | Reusa `OLT` + `dba_qos.py` tal cual, solo re-parametrizado | (ninguno — reuso) |
| **IPACT** | Nueva clase `OLTPolling`, polling round-robin secuencial, ciclo variable | `simulator/olt_ipact.py` + `simulator/dba_ipact.py` |

3 nuevos tipos de evento en `engine.py` (aditivos, no se tocan los
existentes): `EVT_OLT_SEND_GATE`, `EVT_ONU_RECV_GATE`, `EVT_OLT_POLL_NEXT`.

`metrics/collector.py` se extiende de forma retrocompatible:
`MetricsCollector(warmup_s, sla_bounds_s=None)`, nuevo método
`record_cycle_time()`, nuevos campos en `summary()`/`export_csv()`:
`latency_max_us`, `sla_bound_us`, `sla_compliance_pct`,
`cycle_time_mean/p99/min/max_us`.

---

## 1. `configs/xgpon.json` (NUEVO)

```json
{
    "gpon": {
        "standard":                "XG-PON1 (ITU-T G.987)",
        "upstream_rate_bps":       2488320000,
        "downstream_rate_bps":     9953280000,
        "frame_duration_s":        0.000125,
        "bytes_per_frame":         38880,
        "num_onus":                8,
        "fiber_length_km":         20,
        "prop_delay_s_per_km":     0.000005,
        "guard_bytes_per_onu":     32,
        "split_ratio":             8
    },
    "tconts": {
        "1": {
            "name":                    "Fixed (CBR) - VoIP/control",
            "traffic":                 "cbr",
            "rate_bps":                1000000,
            "pkt_size":                160,
            "buffer_bytes":            10000,
            "fixed_bytes_per_frame":   160
        },
        "2": {
            "name":                    "Assured - Video Streaming",
            "traffic":                 "poisson",
            "rate_bps":                40000000,
            "pkt_size":                1000,
            "buffer_bytes":            200000,
            "assured_bytes_per_frame": 1000
        },
        "4": {
            "name":                    "Best Effort - Data/Downloads",
            "traffic":                 "pareto",
            "rate_bps":                400000000,
            "pkt_size":                1400,
            "buffer_bytes":            2000000,
            "pareto_alpha":            1.5
        }
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
        "duration_s":   10.0,
        "warmup_s":     1.0,
        "repetitions":  10,
        "seed_base":    6767
    }
}
```

### Derivaciones (documentar en Fase 3 docs)

- **Tasas XG-PON1 (ITU-T G.987.2):** downstream 9.95328 Gbps, upstream
  2.48832 Gbps = exactamente 2× el upstream de GPON G.984 (1.24416 Gbps).
- **bytes_per_frame:** `2.48832e9 × 125e-6 / 8 = 38,880 bytes` (2× los
  19,440 de Fase 2; misma trama de 125 µs, estructura GTC análoga según
  G.987.3).
- **8 ONUs, todas iguales:** requerimiento nuevo de la profesora.
- **Topología/distancia:** mantener 20 km, 5 µs/km → 100 µs one-way (200 µs
  RTT) — igual que Fase 2, consistente con Nominal Differential Reach Class
  N1 (20 km) de G.987.2, y permite comparar RTT de forma directa con Fase 2.
- **T-CONT2/T-CONT4 escalados ×8:** fair-share por ONU en Fase 2 =
  1244.16/32 = 38.88 Mbps; en Fase 3 = 2488.32/8 = 311.04 Mbps → factor 8×.
  Aplicar el mismo factor a la tasa media de T2 (5→40 Mbps, mantiene 12.86%
  de la capacidad) y al barrido de cargas T4 ({10,25,50,75,100}→
  {80,200,400,600,800} Mbps/ONU), preservando las mismas razones de
  sobrecarga (p.ej. 800 Mbps/ONU = 257% sobrecarga, igual que 100 Mbps/ONU
  en Fase 2).
- **`assured_bytes_per_frame = 1000`** (igual constante que Fase 2, NO
  escalar): a 1000 B/trama × 8000 tramas/s = 64 Mbps, sigue siendo >> 40 Mbps
  medio de T2 — mismo margen relativo que Fase 2 (1000B/frame=64Mbps >> 5Mbps).
- **Tabla SLA:**
  - T-CONT1 ≤ **2 ms**: instrucción explícita de la profesora.
  - T-CONT2 ≤ **20 ms**: meta de proyecto (rango típico 10–20 ms para video
    interactivo/baja latencia); declarar que NO es una norma ITU-T
    específica de PON, sino un objetivo razonable y justificado del proyecto.
  - T-CONT4 ≤ **500 ms**: cota laxa/diagnóstica (best-effort no tiene SLA de
    latencia en ITU-T); el foco para T4 es `latency_max_us` y `loss_rate`,
    no el % de cumplimiento.

---

## 2. `simulator/dba_giant.py` (NUEVO) — GIANT (GPA + SPA)

Encaja en la arquitectura existente: `allocate(onu_reports,
total_capacity_bytes, num_onus, config) -> {onu_id: {tcont_type: bytes}}`,
misma firma que `QoSDBA`. Una instancia de `GiantDBA` se crea una vez por
corrida (igual que `QoSDBA()`/`BasicDBA()` en `main.py`), así que el estado
persistente (contadores SI) vive como atributos de instancia.

**Fases:**
- **GPA (Guaranteed Phase Allocation):**
  - T-CONT1 (Fixed): igual que `QoSDBA` paso 1 — `fixed_bytes_per_frame` por
    ONU, incondicional, cada trama.
  - T-CONT2 (Assured): contador `_t2_counter[onu_id]` (down-counter de
    `si_max_frames["2"]`, default 8). Cuando llega a 0, la ONU es elegible:
    `grant = min(demand, assured_bytes_per_frame * si_max, remaining)`,
    luego resetear contador a `si_max`. Si no es elegible, grant=0 y
    decrementar contador.

- **SPA (Surplus Phase Allocation):**
  - T-CONT4 (Non-assured): contador `_t4_counter[onu_id]` (down-counter de
    `si_min_frames["4"]`, default 32). ONUs con contador==0 y demanda>0 son
    "elegibles" este frame → conjunto round-robin. Repartir `remaining`
    round-robin (un ONU a la vez, partiendo de `_spa_rr_ptr`) hasta agotar
    `remaining` o servir a todos los elegibles. Elegibles servidos
    (grant>0) resetean su contador a `si_min`. Elegibles con demanda==0
    también resetean (evitar elegibilidad perpetua en T4 inactivo). Resto
    decrementa.

**⚠️ Dos correcciones de equidad respecto al diseño inicial (importantes —
sin esto, ONUs con índice alto quedan sistemáticamente perjudicadas):**

1. **Escalonar `_t2_counter` inicial**: `self._t2_counter[onu_id] = onu_id %
   si_max` (NO todos en 0). Si todos parten en 0, las 8 ONUs son elegibles
   simultáneamente en la trama 1 y cada 8 tramas después; con
   `cap = assured_bpf * si_max = 8000` bytes y `remaining_after_T1 ≈ 37,344`
   bytes, la demanda total de las 8 ONUs (~40,000 B si cada una pide ~5,000B)
   excede `remaining`, y el orden de iteración (ONU 0..7, fijo) deja a las
   últimas ONUs sistemáticamente con grants truncados cada ciclo — un sesgo
   artificial por orden de iteración, no una propiedad real de GIANT.
   Escalonando los contadores (0,1,2,3,4,5,6,7 para si_max=8), en estado
   estable solo **una** ONU es elegible por trama, `cap=8000` cabe
   holgadamente en `remaining≈37,344`, y las 8 ONUs reciben servicio
   uniforme — más realista y fiel a la idea de "service interval" de GIANT.

2. **Corregir avance de `_spa_rr_ptr`**: en el diseño inicial se actualizaba
   a `(ordered[-1] + 1) % n` (último elemento del conjunto elegible
   *ordenado*, exista o no haya sido servido). Si `remaining` se agota antes
   de recorrer todo `ordered`, las ONUs no servidas NO resetean su contador
   (queda en 0 → vuelven a ser elegibles la próxima trama) pero el puntero
   ya avanzó más allá de ellas → quedan **perpetuamente pospuestas** bajo
   sobrecarga sostenida (el escenario de 800 Mbps/ONU es exactamente esto).
   **Fix:** trackear `last_serviced_onu_id` (la última ONU que efectivamente
   recibió `grant>0` dentro del loop) y avanzar
   `self._spa_rr_ptr = (last_serviced_onu_id + 1) % n` solo si hubo al menos
   un servicio. Así, la próxima trama el RR retoma justo después de la
   última servida, dando prioridad a las que quedaron pendientes.

```python
class GiantDBA:
    def __init__(self):
        self._initialized = False
        self._t2_counter = {}
        self._t4_counter = {}
        self._spa_rr_ptr = 0

    def _ensure_init(self, onu_reports, config):
        if self._initialized:
            return
        self._si_max = config.get("giant", {}).get("si_max_frames", {}).get("2", 8)
        self._si_min = config.get("giant", {}).get("si_min_frames", {}).get("4", 32)
        for onu_id in onu_reports:
            self._t2_counter[onu_id] = onu_id % self._si_max   # escalonado
            self._t4_counter[onu_id] = 0
        self._initialized = True

    def allocate(self, onu_reports, total_capacity_bytes, num_onus, config):
        self._ensure_init(onu_reports, config)
        bwmap = {onu_id: {1: 0, 2: 0, 4: 0} for onu_id in onu_reports}

        guard_overhead = 32 * num_onus
        remaining = max(0, total_capacity_bytes - guard_overhead)

        fixed_bytes = config["tconts"]["1"].get("fixed_bytes_per_frame", 160)
        assured_bpf = config["tconts"]["2"].get("assured_bytes_per_frame", 1000)

        # GPA paso 1: T-CONT1 fijo (igual QoSDBA)
        for onu_id in onu_reports:
            grant = min(fixed_bytes, remaining)
            bwmap[onu_id][1] = grant
            remaining -= grant

        # GPA paso 2: T-CONT2 asegurado, contadores SImax escalonados
        for onu_id, report in onu_reports.items():
            demand = report["queue_bytes"].get(2, 0)
            if self._t2_counter[onu_id] == 0:
                cap = assured_bpf * self._si_max
                grant = max(0, min(demand, cap, remaining))
                bwmap[onu_id][2] = grant
                remaining -= grant
                self._t2_counter[onu_id] = self._si_max
            else:
                self._t2_counter[onu_id] -= 1

        # SPA: T-CONT4, contadores SImin + round robin con puntero corregido
        onu_ids = sorted(onu_reports.keys())
        n = len(onu_ids)
        eligible = []
        for onu_id in onu_ids:
            demand4 = onu_reports[onu_id]["queue_bytes"].get(4, 0)
            if self._t4_counter[onu_id] == 0:
                if demand4 > 0:
                    eligible.append(onu_id)
                else:
                    self._t4_counter[onu_id] = self._si_min
            else:
                self._t4_counter[onu_id] -= 1

        last_serviced = None
        if eligible and remaining > 0:
            ordered = sorted(eligible, key=lambda x: (x - self._spa_rr_ptr) % n)
            for onu_id in ordered:
                if remaining <= 0:
                    break
                demand4 = onu_reports[onu_id]["queue_bytes"].get(4, 0)
                grant = min(demand4, remaining)
                bwmap[onu_id][4] = grant
                remaining -= grant
                self._t4_counter[onu_id] = self._si_min
                last_serviced = onu_id
        if last_serviced is not None:
            self._spa_rr_ptr = (last_serviced + 1) % n

        return bwmap
```

**Notas para docs (simplificaciones declaradas):**
- GIANT real opera por T-CONT (múltiples T-CONTs del mismo tipo por ONU);
  aquí cada ONU tiene exactamente un T-CONT de cada tipo 1/2/4, así que
  por-ONU == por-T-CONT.
- El tamaño "catch-up" (`assured_bpf * si_max`) es la interpretación propia
  del equipo de la semántica SImax de GIANT.
- El escalonamiento inicial de `_t2_counter` y la corrección del puntero RR
  de SPA son decisiones de diseño propias para que el algoritmo se comporte
  de forma justa y estable bajo régimen permanente — documentarlas
  explícitamente.

---

## 3. IPACT — `simulator/dba_ipact.py` + `simulator/olt_ipact.py` (NUEVO,
mayor riesgo)

### 3.1 Nuevos tipos de evento en `simulator/engine.py` (aditivo)

Agregar junto a las constantes existentes, sin tocar las actuales:

```python
EVT_OLT_SEND_GATE = "OLT_SEND_GATE"        # OLT envía GATE (poll) a una ONU
EVT_ONU_RECV_GATE = "ONU_RECEIVE_GATE"     # ONU recibe GATE, transmite y reporta
EVT_OLT_POLL_NEXT = "OLT_POLL_NEXT"        # OLT avanza al siguiente ONU del ciclo
```

`EVT_OLT_RECV_DATA` y `EVT_OLT_RECV_REPORT` se **reusan tal cual** (mismo
payload).

### 3.2 `simulator/dba_ipact.py` — `IpactDBA`

Interfaz **distinta** a `BasicDBA`/`QoSDBA`/`GiantDBA` (deliberado: IPACT
asigna por-ONU en cada poll, no por-trama para todas las ONUs). Servicio
"limited": `grant_total = min(demanda_total, B_max)`. Sub-asignación
intra-ONU con la MISMA prioridad T1>T2>T4 que QoSDBA, para aislar la
variable "cómo se determina el ancho de banda/timing por ONU" (lo que
realmente cambia entre algoritmos) del "orden intra-ONU" (constante,
ya evaluado con QoSDBA).

```python
class IpactDBA:
    def allocate_onu(self, onu_id, report, b_max_bytes, config):
        queue = report.get("queue_bytes", {1: 0, 2: 0, 4: 0})
        total_demand = sum(queue.values())
        grant_total = min(total_demand, b_max_bytes)

        result = {1: 0, 2: 0, 4: 0}
        remaining = grant_total
        for tc in (1, 2, 4):
            demand = queue.get(tc, 0)
            grant = min(demand, remaining)
            result[tc] = grant
            remaining -= grant
        return result
```

### 3.3 `simulator/olt_ipact.py` — `OLTPolling`

Clase separada de `OLT` (control flow fundamentalmente distinto: `OLT` es
disparado por timer fijo de 125 µs y hace broadcast; `OLTPolling` es
disparado por polling secuencial de ciclo variable). Round-robin sobre las
8 ONUs; el reloj de "siguiente poll" del OLT avanza en
`grant_time_i + guard_time` (NO espera la respuesta de la ONU — usa el
último reporte disponible, igual que SR-DBA usa reportes ~RTT antiguos).

```python
class OLTPolling:
    def __init__(self, engine, num_onus, dba_algorithm, config, metrics_collector):
        self.engine = engine
        self.num_onus = num_onus
        self.dba = dba_algorithm          # IpactDBA
        self.config = config
        self.metrics = metrics_collector

        gpon_cfg = config["gpon"]
        self.prop_delay = gpon_cfg["fiber_length_km"] * gpon_cfg["prop_delay_s_per_km"]

        ipact_cfg = config.get("ipact", {})
        self.b_max = ipact_cfg.get("b_max_bytes", 38880)
        self.guard_time = ipact_cfg.get("guard_time_s", 1e-6)
        self.upstream_rate_bps = gpon_cfg["upstream_rate_bps"]

        self._onu_reports = {
            i: {"onu_id": i, "queue_bytes": {1: 0, 2: 0, 4: 0}}
            for i in range(num_onus)
        }
        self._poll_ptr = 0
        self._cycle_start = 0.0
        self._cycle_count = 0
        self._cycle_used_bytes = 0   # acumulador para utilización por ciclo

        engine.schedule(0.0, EVT_OLT_SEND_GATE, {"onu_id": 0})

    def on_send_gate(self, evt):
        onu_id = evt.data["onu_id"]
        report = self._onu_reports[onu_id]

        allocation = self.dba.allocate_onu(
            onu_id=onu_id, report=report,
            b_max_bytes=self.b_max, config=self.config,
        )
        granted_total = sum(allocation.values())
        grant_time = (granted_total * 8) / self.upstream_rate_bps

        if onu_id == 0:
            now = self.engine.now
            if self._cycle_count > 0:
                cycle_time = now - self._cycle_start
                self.metrics.record_cycle_time(now, cycle_time)
                # capacidad de referencia: B_max * num_onus (ciclo máximo)
                self.metrics.record_frame_utilization(
                    now, self._cycle_used_bytes, self.b_max * self.num_onus)
            self._cycle_start = now
            self._cycle_count += 1
            self._cycle_used_bytes = 0

        self._cycle_used_bytes += granted_total

        self.engine.schedule(
            delay=self.prop_delay,
            event_type=EVT_ONU_RECV_GATE,
            data={"onu_id": onu_id, "allocation": allocation},
        )
        self.engine.schedule(
            delay=grant_time + self.guard_time,
            event_type=EVT_OLT_POLL_NEXT,
            data={},
        )

    def on_poll_next(self, evt):
        self._poll_ptr = (self._poll_ptr + 1) % self.num_onus
        self.engine.schedule(0.0, EVT_OLT_SEND_GATE, {"onu_id": self._poll_ptr})

    def on_receive_data(self, evt):
        d = evt.data
        latency = self.engine.now - d["creation_time"]
        self.metrics.record_delivery(
            onu_id=d["onu_id"], tcont_type=d["tcont_type"],
            pkt_size=d["size"], latency_s=latency, sim_time=self.engine.now,
        )

    def on_receive_report(self, evt):
        report = evt.data
        self._onu_reports[report["onu_id"]] = report
```

**Propiedades clave:** `cycle_time = sum_{i=0..7}(grant_time_i +
guard_time)`, variable. Ciclo mínimo (colas vacías) = 8 × 1 µs = 8 µs. Ciclo
máximo (saturación, B_max=38880 cada poll → grant_time=125 µs) = 8 ×
(125+1) µs = **1.008 ms** (≈ 8 tramas XG-PON). B_max=38880 bytes →
`grant_time_max = 38880×8/2.48832e9 = 125 µs` exactamente (= 1 trama
XG-PON), buena justificación numérica para el valor elegido.

### 3.4 `simulator/onu.py` — nuevo handler `on_receive_gate` (aditivo)

Agregar este método nuevo a la clase `ONU` existente, **sin tocar**
`on_receive_bwmap`. Es ~95% idéntico (duplicación intencional para no tocar
el camino de Fase 2):

```python
def on_receive_gate(self, evt) -> None:
    d = evt.data
    if d["onu_id"] != self.onu_id:
        return
    allocation = d["allocation"]

    total_tx_bytes = 0
    tx_time_acc = 0.0
    for tc_type, granted_bytes in allocation.items():
        tcont = self.tconts.get(tc_type)
        if tcont is None or granted_bytes <= 0:
            continue
        pkts = tcont.dequeue(granted_bytes)
        for pkt in pkts:
            tx_time = (pkt.size * 8) / UPSTREAM_RATE_BPS
            arrive_at = self.engine.now + tx_time_acc + tx_time + self.prop_delay
            self.engine.schedule_at(
                time=arrive_at, event_type=EVT_OLT_RECV_DATA,
                data={"onu_id": self.onu_id, "tcont_type": tc_type,
                      "size": pkt.size, "creation_time": pkt.creation_time},
            )
            tx_time_acc += tx_time
            total_tx_bytes += pkt.size

    queue_report = {tc: t.queue_bytes() for tc, t in self.tconts.items()}
    self.engine.schedule(
        delay=self.prop_delay, event_type=EVT_OLT_RECV_REPORT,
        data={"onu_id": self.onu_id, "queue_bytes": queue_report},
    )
```

### 3.5 Sobre staleness de reportes y SLA de T-CONT1 bajo IPACT (anotar en docs)

A diferencia de GIANT/QoSDBA (T-CONT1 reservado **incondicionalmente**, sin
mirar el reporte), IPACT asigna T1 *demand-based* a partir del último
reporte (potencialmente ~1 ciclo desactualizado). Esto puede producir, en el
peor caso de alineación de fases, latencias de T1 cercanas a ~2 ciclos
(~2.0–2.2 ms) bajo saturación — **es un hallazgo esperado y pedagógicamente
relevante** (la comparación que pide la profesora: SR-DBA con T1
pre-reservado vs polling demand-based puro). Verificar en 9.4 que el
`sla_compliance_pct` de T1 bajo IPACT efectivamente refleja esto (puede ser
< 100%, a diferencia de GIANT/QoSDBA ≈ 100%) y documentarlo como conclusión,
no como bug.

---

## 4. `metrics/collector.py` (cambios aditivos, retrocompatibles)

- `__init__(self, warmup_s=1.0, sla_bounds_s: Optional[Dict[int,float]]=None)`
  — `self.sla_bounds_s = sla_bounds_s or {}`; nuevo `self._cycle_times = []`.
- Nuevo método `record_cycle_time(sim_time, cycle_time_s)` (respeta warmup).
- `summary()`:
  - por `(onu_id, tcont_type)`: agregar `latency_max_us = max(lats)*1e6`,
    `sla_bound_us`, `sla_compliance_pct` (= % de `lats` con
    `latency_s <= sla_bounds_s.get(tcont_type)`, o `None` si no hay cota
    configurada — preserva comportamiento de Fase 2 donde
    `sla_bounds_s={}`).
  - si `self._cycle_times` no está vacío, agregar claves globales
    `cycle_time_mean_us/p99_us/min_us/max_us` y `cycle_time_samples`
    (lista cruda, para histograma — excluir de `export_csv` por-fila, ver
    abajo).
- `export_csv()`: agregar columnas `latency_max_us`, `sla_bound_us`,
  `sla_compliance_pct` a cada fila por-paquete (igual patrón que el
  `bytes_delivered` ya repetido por fila). `cycle_time_samples` NO va en
  `export_csv` (es global, no por ONU/T-CONT) — se exporta aparte (ver §6.2).

Verificar que `MetricsCollector(warmup_s=0.0)` (llamada estilo Fase 2, sin
`sla_bounds_s`) sigue funcionando: `sla_compliance_pct=None`,
`latency_max_us` siempre poblado.

---

## 5. `configs/scenarios_xgpon.json` (NUEVO)

9 escenarios = 3 algoritmos × 3 niveles de carga T-CONT4 (subconjunto
representativo de los 5 reescalados, para mantener el tiempo total
razonable: 9×10 reps = 90 corridas):

- **200 Mbps/ONU** (T4 total=1600 Mbps, ~64% de 2488.32 Mbps — subcargado)
- **400 Mbps/ONU** (T4 total=3200 Mbps, ~129% — al límite)
- **800 Mbps/ONU** (T4 total=6400 Mbps, ~257% — sobrecarga severa, igual
  proporción que el escenario headline de Fase 2 a 100 Mbps/32 ONUs)

```json
{
  "scenarios": [
    {"name": "IPACT_load200",  "algorithm": "ipact", "num_onus": 8, "tcont4_rate_mbps": 200, "description": "IPACT (polling EPON-style), carga BE ~64%"},
    {"name": "IPACT_load400",  "algorithm": "ipact", "num_onus": 8, "tcont4_rate_mbps": 400, "description": "IPACT, carga BE ~129%"},
    {"name": "IPACT_load800",  "algorithm": "ipact", "num_onus": 8, "tcont4_rate_mbps": 800, "description": "IPACT, carga BE ~257% (sobrecarga severa)"},
    {"name": "GIANT_load200",  "algorithm": "giant", "num_onus": 8, "tcont4_rate_mbps": 200, "description": "GIANT (GPA/SPA), carga BE ~64%"},
    {"name": "GIANT_load400",  "algorithm": "giant", "num_onus": 8, "tcont4_rate_mbps": 400, "description": "GIANT, carga BE ~129%"},
    {"name": "GIANT_load800",  "algorithm": "giant", "num_onus": 8, "tcont4_rate_mbps": 800, "description": "GIANT, carga BE ~257% (sobrecarga severa)"},
    {"name": "QoSDBA_load200", "algorithm": "qos",   "num_onus": 8, "tcont4_rate_mbps": 200, "description": "QoSDBA (Fase 2 re-parametrizado), carga BE ~64%"},
    {"name": "QoSDBA_load400", "algorithm": "qos",   "num_onus": 8, "tcont4_rate_mbps": 400, "description": "QoSDBA, carga BE ~129%"},
    {"name": "QoSDBA_load800", "algorithm": "qos",   "num_onus": 8, "tcont4_rate_mbps": 800, "description": "QoSDBA, carga BE ~257% (sobrecarga severa)"}
  ]
}
```

(Opcional, si sobra tiempo: agregar 80 y 600 Mbps/ONU para igualar los 5
niveles de Fase 2 — no crítico.)

---

## 6. Puntos de entrada

### 6.1 `main_xgpon.py` (NUEVO, espejo de `main.py`)

- `CONFIG_PATH = configs/xgpon.json`.
- `--algorithm {ipact,giant,qos}`, `--load` (Mbps/ONU para T-CONT4),
  `--num-onus` default 8.
- `run_simulation()`: construye `sla_bounds = {int(k): v["max_delay_s"] for
  k,v in config["sla"].items()}`, pasa a `MetricsCollector(warmup_s,
  sla_bounds_s=sla_bounds)`.
- Ramifica wiring según algoritmo:
  - `ipact` → `IpactDBA()` + `OLTPolling(...)`, registra
    `EVT_OLT_SEND_GATE→on_send_gate`, `EVT_OLT_POLL_NEXT→on_poll_next`,
    `EVT_OLT_RECV_DATA→on_receive_data`, `EVT_OLT_RECV_REPORT→on_receive_report`,
    `EVT_ONU_RECV_GATE→dispatch_gate` (despacha a `onus[onu_id].on_receive_gate`).
    **No** registra/usa `EVT_OLT_BWMAP`/`EVT_ONU_RECV_BWMAP`.
  - `giant`/`qos` → `GiantDBA()`/`QoSDBA()` + `OLT(...)`, igual wiring que
    `main.py` actual (`EVT_OLT_BWMAP`, `EVT_ONU_RECV_BWMAP`, etc.)
- Tabla de salida por T-CONT: agregar columnas `Max(us)` (`latency_max_us`)
  y `SLA%` (`sla_compliance_pct`); si `summary` trae `cycle_time_*`, imprimir
  línea extra con mean/min/max del ciclo (solo aplica a IPACT).

### 6.2 `run_experiments_xgpon.py` (NUEVO, espejo de `run_experiments.py`)

- Lee `configs/xgpon.json` + `configs/scenarios_xgpon.json`, importa de
  `main_xgpon`.
- Por cada escenario/repetición agrega también `latency_max_us` y
  `sla_compliance_pct` (con CI95 igual que las métricas existentes).
- Escribe `results/xgpon_results.csv` (NO sobrescribe `all_results.csv`).
- Para escenarios `ipact`, recolecta `summary["cycle_time_samples"]` de cada
  repetición y escribe `results/xgpon_cycle_times.csv` (filas:
  `scenario, algorithm, load_mbps, seed, cycle_time_us`); para
  `giant`/`qos` esta lista queda vacía (no se llama `record_cycle_time`).

`run.py` (menú interactivo) **no se modifica** — es entregable de Fase 2.
Si sobra tiempo, opcionalmente crear `run_xgpon.py` espejo, pero no es
prioritario.

---

## 7. `analysis/analyze_xgpon.py` (NUEVO)

Mismo estilo/helpers que `analysis/analyze.py` (serif, IC95%, 300 DPI) —
duplicar los helpers `setup_style()`/`savefig()` (más simple que acoplar a
Fase 2). Lee `results/xgpon_results.csv` y `results/xgpon_cycle_times.csv`.
Salida en `figures/xgpon/` (subcarpeta nueva, no colisiona con Fase 2).

Gráficos:
1. **`sla_compliance_by_tcont.png`** (HEADLINE) — barras agrupadas, x=T-CONT
   {1,2,4}, grupos={ipact,giant,qos}, y=SLA compliance % con IC95, en el
   escenario de 800 Mbps/ONU (sobrecarga). Línea de referencia en 100%.
   Anotar la cota de 2 ms de T-CONT1 en el subtítulo.
2. **`max_delay_tcont1_vs_load.png`** — líneas, x=carga {200,400,800},
   y=`latency_max_us` de T-CONT1, una línea por algoritmo, línea punteada en
   2000 µs (cota SLA). "¿T-CONT1 supera alguna vez los 2ms?"
3. **`throughput_vs_load_xgpon.png`** — análogo a Fase 2, 3 algoritmos × 3
   cargas, línea de referencia en 2488.32 Mbps.
4. **`cycle_time_distribution.png`** (visual clave pedida por la profesora)
   — histograma/boxplot de `cycle_time_samples` de IPACT (1 subplot por
   nivel de carga) con línea vertical en 125 µs (trama fija de
   GIANT/QoSDBA). Título: "Polling de ciclo variable (IPACT) vs trama fija
   125µs (GIANT/QoSDBA)". Figura grande, p.ej. `figsize=(12,8)`.
5. **`sla_compliance_vs_load.png`** — líneas, x=carga, y=SLA compliance % de
   T-CONT1, una línea por algoritmo, ref en 100%.
6. **`summary_dashboard_xgpon.png`** — dashboard 2×2: (a) SLA compliance por
   T-CONT @800Mbps, (b) max delay T1 vs carga, (c) throughput vs carga, (d)
   distribución de cycle time (boxplot compacto por algoritmo).

---

## 8. Documentación Fase 3

- `docs/PARA_LA_PROFE_FASE3.md` (NUEVO) — mismo estilo/tono que
  `docs/PARA_LA_PROFE.md`: qué cambió y por qué (resumen del pivote),
  XG-PON1 G.987 (tabla de parámetros, derivación de 38,880 B/trama),
  topología (8 ONUs, 20km, 100µs — diagrama ASCII), T-CONTs reescalados
  (×8, justificación), tabla SLA (2/20/500 ms con justificación), los 3
  algoritmos (IPACT declarado como adaptación de EPON con simplificaciones,
  GIANT con GPA/SPA y SImax/SImin, QoSDBA reusado), resultados clave
  (completar tras correr experimentos), sección de simplificaciones
  declaradas (incluir: prioridad intra-ONU de IPACT = QoSDBA; "catch-up"
  sizing de SImax es interpretación propia; escalonamiento de contadores
  GIANT y fix del puntero RR; OLT no espera REPORT antes de re-pollear;
  topología con 8 ONUs idénticas a 20km).
- `docs/DOCUMENTACION_TECNICA_FASE3.md` (NUEVO) — análogo a
  `docs/DOCUMENTACION_TECNICA.md`: referencias G.987.1/.2/.3, pseudocódigo
  completo de GIANT (GPA/SPA + contadores) e IPACT (B_max, ciclo variable),
  campos nuevos de `metrics/collector.py`, referencias bibliográficas
  (IPACT: Kramer et al. 2002, ya citado en Fase 2; GIANT: si no se encuentra
  la cita exacta del "primer DBA ITU-compliant 2006" referenciada por la
  profesora, describir el mecanismo GPA/SPA de forma genérica fundamentado
  en ITU-T G.984.3/G.987.3 T-CONT semantics y citar como "GIANT (Guaranteed +
  Surplus, alineado a ITU-T) según material de cátedra").
- `entregas/Parte_3/README.md` (NUEVO) — índice corto apuntando a los dos
  docs anteriores y a `figures/xgpon/`.

---

## 9. Plan de verificación

Ejecutar desde `/home/crauli/USM/Simula/pon-dba-sim`:

1. **Smoke tests** (uno por algoritmo, corrida corta):
   ```bash
   python3 main_xgpon.py --algorithm qos   --load 400 --duration 2 --warmup 0.2 --verbose
   python3 main_xgpon.py --algorithm giant --load 400 --duration 2 --warmup 0.2 --verbose
   python3 main_xgpon.py --algorithm ipact --load 400 --duration 2 --warmup 0.2 --verbose
   ```
   Verificar: sin excepciones, tabla imprime, utilización del canal entre 0%
   y 100% (nunca >100%).

2. **Variabilidad de ciclo IPACT**: correr una simulación corta vía script,
   verificar `cycle_time_max_us > cycle_time_min_us` y
   `cycle_time_max_us <= ~1008 + epsilon` (≈ 8×(125+1) µs).

3. **Regresión Fase 2**: `python3 main.py --algorithm qos --load 50
   --num-onus 32 --duration 2 --warmup 0.2 --verbose` y `--algorithm basic`
   — deben comportarse igual que antes (`git diff` en `simulator/`,
   `metrics/`, `main.py` no debe alterar ninguna línea del camino
   BasicDBA/QoSDBA/OLT/`on_receive_bwmap`).

4. **Sanidad SLA bajo sobrecarga (800 Mbps/ONU)**: correr los 3 algoritmos a
   `--load 800 --duration 5 --warmup 1`. Esperado: T-CONT1 SLA% cercano a
   100% en QoS/GIANT (T1 reservado siempre); en IPACT puede ser < 100% por
   la staleness de reportes (§3.5) — documentar como hallazgo, verificar que
   aun así `latency_max_us` de T1 se mantiene en un rango razonable
   (idealmente < ~2.2ms incluso en el peor caso).

5. **Pérdidas en T-CONT4 a 800 Mbps/ONU**: `loss_rate` de T4 > 0 (esperado
   bajo 257% de sobrecarga, comparable al 17.8% de Fase 2 en sobrecarga
   equivalente); T1/T2 `loss_rate` ≈ 0.

6. **Corrida completa + análisis** (al final):
   ```bash
   python3 run_experiments_xgpon.py
   python3 analysis/analyze_xgpon.py
   ls figures/xgpon/
   ```
   Verificar: `results/xgpon_results.csv` con 9 escenarios × 3 T-CONT (27
   filas + header), `results/xgpon_cycle_times.csv` con filas solo para los
   3 escenarios IPACT, `figures/xgpon/*.png` con 6 archivos, todos abren sin
   error.

7. **Compatibilidad de `MetricsCollector`**: `MetricsCollector(warmup_s=0.0)`
   (estilo Fase 2, sin `sla_bounds_s`) → `sla_compliance_pct is None`,
   `latency_max_us > 0` tras `record_delivery`.

---

## Orden de implementación sugerido

1. `simulator/engine.py` — 3 nuevas constantes EVT_* (sin cambio de
   comportamiento).
2. `metrics/collector.py` — campos/métodos aditivos. Verificar punto 9.7.
3. `configs/xgpon.json`.
4. `simulator/dba_giant.py` — probar primero con `main_xgpon.py` solo para
   `qos`/`giant` (reusa `OLT`, sin wiring nuevo) → camino más rápido a un
   baseline XG-PON funcionando.
5. `simulator/onu.py` — agregar `on_receive_gate` (método aditivo).
6. `simulator/dba_ipact.py`, `simulator/olt_ipact.py`.
7. `main_xgpon.py` completo (3 algoritmos).
8. Verificación 1–5.
9. `configs/scenarios_xgpon.json`, `run_experiments_xgpon.py`. Verificación 6.
10. `analysis/analyze_xgpon.py`.
11. `entregas/Parte_3/`, `docs/PARA_LA_PROFE_FASE3.md`,
    `docs/DOCUMENTACION_TECNICA_FASE3.md`.

---

## Archivos críticos

- `configs/xgpon.json` (NUEVO)
- `configs/scenarios_xgpon.json` (NUEVO)
- `simulator/engine.py` (aditivo: 3 constantes)
- `simulator/dba_giant.py` (NUEVO)
- `simulator/dba_ipact.py` (NUEVO)
- `simulator/olt_ipact.py` (NUEVO)
- `simulator/onu.py` (aditivo: método `on_receive_gate`)
- `metrics/collector.py` (aditivo)
- `main_xgpon.py` (NUEVO)
- `run_experiments_xgpon.py` (NUEVO)
- `analysis/analyze_xgpon.py` (NUEVO)
- `docs/PARA_LA_PROFE_FASE3.md`, `docs/DOCUMENTACION_TECNICA_FASE3.md`,
  `entregas/Parte_3/README.md` (NUEVOS)
