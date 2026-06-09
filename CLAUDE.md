# CLAUDE.md — Simulador GPON DBA desde cero (SIN OMNeT++)

## CONTEXTO CRÍTICO

La profesora del curso TEL-341 (Simulación de Redes, UTFSM) revisó nuestro trabajo anterior y nos dio las siguientes correcciones:

1. **NO usar OMNeT++** — el simulador debe ser 100% propio, desde cero
2. **Investigar bien GPON** — usar el estándar real ITU-T G.984, no inventar parámetros
3. **Los tipos de tráfico son T-CONTs, no eMBB/URLLC/mMTC** — esas son categorías 5G, no GPON. GPON tiene 5 tipos de T-CONT definidos en el estándar
4. **IPACT es de EPON, no de GPON** — GPON usa DBA centralizado con Status Reporting, no polling estilo EPON
5. **Usar DBA centralizado, no polling** — en GPON la OLT asigna bandwidth basándose en los reportes de las ONUs, sin polling individual

## QUÉ DEBE HACER ESTE PROYECTO

### Simulador de eventos discretos propio en Python

Implementar desde cero (sin OMNeT++, sin SimPy, sin ningún framework de simulación):

1. **Motor de eventos discretos** — cola de eventos ordenada por tiempo, loop principal que saca el próximo evento y lo procesa
2. **Modelo de red GPON** según ITU-T G.984
3. **Algoritmos DBA centralizados** — uno básico (proporcional) y uno con diferenciación de QoS por T-CONT
4. **Generadores de tráfico** por tipo de T-CONT
5. **Recolección de métricas** y generación de gráficos

---

## ESPECIFICACIONES TÉCNICAS GPON (ITU-T G.984)

### Parámetros reales de GPON (INVESTIGAR Y VERIFICAR)

```
Downstream: 2.488 Gbps
Upstream:   1.244 Gbps
Trama GTC:  125 μs (8000 tramas por segundo)
Alcance:    hasta 20 km (lógico), 60 km (físico con extensión)
Split ratio: 1:32 o 1:64 (usar 1:32 para nuestro caso)
Encapsulación: GEM (GPON Encapsulation Method)
```

### Los 5 tipos de T-CONT en GPON

GPON clasifica el tráfico usando **T-CONTs (Transmission Containers)**. Cada ONU puede tener uno o más T-CONTs. Los 5 tipos son:

| Tipo | Nombre | Asignación | Descripción | Ejemplo de uso |
|------|--------|------------|-------------|----------------|
| T-CONT 1 | Fixed bandwidth | Fija (CBR) | Bandwidth reservado permanentemente, siempre disponible | VoIP, videoconferencia, TDM |
| T-CONT 2 | Assured bandwidth | Garantizada | Bandwidth garantizado pero asignado dinámicamente | Video streaming, datos críticos |
| T-CONT 3 | Assured + non-assured | Mínimo garantizado + extra si hay disponible | Parte garantizada, parte best-effort | Navegación web premium |
| T-CONT 4 | Best effort | Solo si sobra | Sin garantía, usa lo que queda | Descargas, P2P, correo |
| T-CONT 5 | Mixed | Combinación | Mezcla de todos los anteriores | Uso general |

**DECISIÓN DEL EQUIPO:** Usar T-CONT 1, T-CONT 2 y T-CONT 4 (fijo, garantizado y best-effort) para tener 3 clases claramente diferenciadas. O usar los 5 si la profesora lo pide. VERIFICAR CON LA PROFESORA cuántos usar.

### Mecanismo DBA en GPON (CENTRALIZADO, NO POLLING)

En GPON el DBA es **centralizado y basado en Status Reporting (SR-DBA)**:

1. La OLT envía un **BWmap (Bandwidth Map)** en cada trama downstream (cada 125 μs)
2. El BWmap indica a cada T-CONT/ONU cuándo y cuánto puede transmitir en upstream
3. Las ONUs envían **DBRu (Dynamic Bandwidth Report upstream)** dentro de sus tramas upstream, reportando el estado de sus buffers
4. La OLT recibe los DBRu y recalcula el BWmap para la siguiente trama
5. **NO hay polling individual** — el BWmap es broadcast y los reportes van embebidos en el tráfico upstream

Diferencia clave con EPON/IPACT:
- EPON/IPACT: la OLT hace polling individual ONU por ONU (ida y vuelta por cada ONU)
- GPON: la OLT manda un BWmap broadcast y recibe reportes embebidos (más eficiente)

---

## ESTRUCTURA DEL SIMULADOR (Python puro)

```
gpon-dba-sim/
├── simulator/
│   ├── __init__.py
│   ├── engine.py           # Motor de eventos discretos (cola de eventos, loop principal)
│   ├── event.py            # Clase Event con timestamp, tipo, datos
│   ├── gpon_network.py     # Red GPON: OLT, Splitter, ONUs, canal
│   ├── olt.py              # OLT con motor DBA, generación de BWmap
│   ├── onu.py              # ONU con T-CONTs, buffers, generación de tráfico
│   ├── dba_basic.py        # Algoritmo DBA básico (proporcional sin QoS)
│   ├── dba_qos.py          # Algoritmo DBA con diferenciación por T-CONT
│   ├── traffic.py          # Generadores de tráfico por tipo de T-CONT
│   ├── channel.py          # Canal óptico con delay de propagación
│   └── metrics.py          # Recolección de estadísticas
├── analysis/
│   ├── analyze.py          # Procesamiento de resultados y gráficos
│   └── requirements.txt    # matplotlib, numpy, scipy, pandas
├── configs/
│   ├── default.json        # Parámetros por defecto de GPON
│   └── scenarios.json      # Escenarios experimentales
├── results/                # Resultados de las corridas (CSV)
├── figures/                # Gráficos generados
├── main.py                 # Punto de entrada principal
├── run_experiments.py      # Ejecuta todos los escenarios
└── README.md
```

---

## IMPLEMENTACIÓN DETALLADA

### 1. Motor de eventos discretos (engine.py)

```python
import heapq
from dataclasses import dataclass, field
from typing import Any

@dataclass(order=True)
class Event:
    time: float
    priority: int = field(compare=True, default=0)
    event_type: str = field(compare=False, default="")
    data: Any = field(compare=False, default=None)

class SimulationEngine:
    def __init__(self):
        self.event_queue = []  # min-heap ordenado por tiempo
        self.current_time = 0.0
        self.event_handlers = {}  # tipo -> función handler

    def schedule_event(self, time, event_type, data=None, priority=0):
        event = Event(time=time, priority=priority, event_type=event_type, data=data)
        heapq.heappush(self.event_queue, event)

    def register_handler(self, event_type, handler_fn):
        self.event_handlers[event_type] = handler_fn

    def run(self, until):
        while self.event_queue:
            event = heapq.heappop(self.event_queue)
            if event.time > until:
                break
            self.current_time = event.time
            handler = self.event_handlers.get(event.event_type)
            if handler:
                handler(event)

    @property
    def now(self):
        return self.current_time
```

### 2. Modelo OLT con DBA centralizado (olt.py)

La OLT debe:
- Cada 125 μs generar un BWmap (bandwidth map)
- Recibir DBRu (reportes) de las ONUs
- Ejecutar el algoritmo DBA para calcular el siguiente BWmap
- Registrar métricas (paquetes recibidos, latencia, throughput)

```python
class OLT:
    def __init__(self, engine, num_onus, dba_algorithm):
        self.engine = engine
        self.num_onus = num_onus
        self.dba = dba_algorithm
        self.frame_duration = 125e-6  # 125 μs por trama GTC
        self.upstream_rate = 1.244e9  # 1.244 Gbps upstream
        self.upstream_capacity_per_frame = int(self.upstream_rate * self.frame_duration / 8)  # bytes por trama
        # Estado
        self.onu_reports = {}  # último reporte de cada ONU
        self.metrics = MetricsCollector()

    def generate_bwmap(self, event):
        """Cada 125 μs: calcula BWmap basado en reportes y algoritmo DBA"""
        bwmap = self.dba.allocate(
            onu_reports=self.onu_reports,
            total_capacity=self.upstream_capacity_per_frame,
            num_onus=self.num_onus
        )
        # Enviar BWmap a todas las ONUs (broadcast)
        for onu_id, allocation in bwmap.items():
            self.engine.schedule_event(
                time=self.engine.now + self.propagation_delay,
                event_type="onu_receive_bwmap",
                data={"onu_id": onu_id, "allocation": allocation}
            )
        # Programar siguiente BWmap
        self.engine.schedule_event(
            time=self.engine.now + self.frame_duration,
            event_type="olt_generate_bwmap"
        )

    def receive_data(self, event):
        """Recibe paquete de datos de una ONU"""
        packet = event.data
        latency = self.engine.now - packet["creation_time"]
        self.metrics.record_latency(packet["tcont_type"], latency)
        self.metrics.record_packet_received(packet["tcont_type"], packet["size"])

    def receive_report(self, event):
        """Recibe DBRu de una ONU"""
        report = event.data
        self.onu_reports[report["onu_id"]] = report
```

### 3. Modelo ONU con T-CONTs (onu.py)

Cada ONU tiene:
- Múltiples T-CONTs (cada uno con su buffer/cola)
- Generadores de tráfico por T-CONT
- Lógica de transmisión cuando recibe BWmap

```python
class ONU:
    def __init__(self, onu_id, engine, tcont_configs):
        self.onu_id = onu_id
        self.engine = engine
        self.tconts = {}  # tipo -> TCont object
        self.metrics = MetricsCollector()

        for tc_config in tcont_configs:
            self.tconts[tc_config["type"]] = TCont(
                tcont_type=tc_config["type"],
                buffer_size=tc_config["buffer_size"],
                traffic_gen=tc_config["traffic_generator"]
            )

    def receive_bwmap(self, event):
        """Recibe BWmap de la OLT, transmite según allocation"""
        allocation = event.data["allocation"]
        for tcont_type, granted_bytes in allocation.items():
            if tcont_type in self.tconts:
                packets = self.tconts[tcont_type].dequeue(granted_bytes)
                for pkt in packets:
                    self.engine.schedule_event(
                        time=self.engine.now + self.transmission_time(pkt["size"]),
                        event_type="olt_receive_data",
                        data=pkt
                    )
        # Enviar DBRu (reporte de estado de buffers)
        self.send_report()

    def send_report(self):
        """Enviar DBRu embebido en tráfico upstream"""
        report = {
            "onu_id": self.onu_id,
            "queue_sizes": {t: tc.queue_size for t, tc in self.tconts.items()}
        }
        self.engine.schedule_event(
            time=self.engine.now + self.propagation_delay,
            event_type="olt_receive_report",
            data=report
        )

    def generate_traffic(self, event):
        """Genera tráfico según el tipo de T-CONT"""
        tcont_type = event.data["tcont_type"]
        tcont = self.tconts[tcont_type]
        packet = tcont.traffic_gen.generate(self.engine.now)
        dropped = tcont.enqueue(packet)
        if dropped:
            self.metrics.record_packet_dropped(tcont_type, packet["size"])
        # Programar próxima generación
        next_time = self.engine.now + tcont.traffic_gen.next_interval()
        self.engine.schedule_event(
            time=next_time,
            event_type="onu_generate_traffic",
            data={"onu_id": self.onu_id, "tcont_type": tcont_type}
        )
```

### 4. Algoritmos DBA

#### DBA Básico — Proporcional sin QoS (dba_basic.py)
```python
class BasicDBA:
    """DBA que reparte proporcional al reporte, sin diferenciar T-CONT"""
    def allocate(self, onu_reports, total_capacity, num_onus):
        bwmap = {}
        # Calcular total demandado
        total_demanded = sum(
            sum(report["queue_sizes"].values())
            for report in onu_reports.values()
        )
        for onu_id, report in onu_reports.items():
            onu_demand = sum(report["queue_sizes"].values())
            if total_demanded > 0:
                share = min(onu_demand, total_capacity * onu_demand / total_demanded)
            else:
                share = total_capacity / num_onus
            # Repartir entre T-CONTs proporcionalmente
            onu_total = sum(report["queue_sizes"].values())
            bwmap[onu_id] = {}
            for tcont_type, queue_size in report["queue_sizes"].items():
                if onu_total > 0:
                    bwmap[onu_id][tcont_type] = int(share * queue_size / onu_total)
                else:
                    bwmap[onu_id][tcont_type] = 0
        return bwmap
```

#### DBA con QoS — Prioridad por T-CONT (dba_qos.py)
```python
class QoSDBA:
    """DBA que respeta prioridades de T-CONT según ITU-T G.984"""
    def allocate(self, onu_reports, total_capacity, num_onus):
        bwmap = {onu_id: {} for onu_id in onu_reports}
        remaining = total_capacity

        # Paso 1: T-CONT 1 (Fixed) — asignación fija garantizada
        for onu_id, report in onu_reports.items():
            t1_demand = report["queue_sizes"].get("TCONT1", 0)
            grant = min(t1_demand, self.fixed_bw_per_onu)
            bwmap[onu_id]["TCONT1"] = grant
            remaining -= grant

        # Paso 2: T-CONT 2 (Assured) — bandwidth garantizado
        for onu_id, report in onu_reports.items():
            t2_demand = report["queue_sizes"].get("TCONT2", 0)
            grant = min(t2_demand, self.assured_bw_per_onu, remaining // num_onus)
            bwmap[onu_id]["TCONT2"] = grant
            remaining -= grant

        # Paso 3: T-CONT 3 (Assured + Non-assured) — mínimo + extra
        # ... (si se usan 5 T-CONTs)

        # Paso 4: T-CONT 4 (Best effort) — lo que sobra
        total_t4_demand = sum(
            report["queue_sizes"].get("TCONT4", 0)
            for report in onu_reports.values()
        )
        for onu_id, report in onu_reports.items():
            t4_demand = report["queue_sizes"].get("TCONT4", 0)
            if total_t4_demand > 0 and remaining > 0:
                grant = min(t4_demand, int(remaining * t4_demand / total_t4_demand))
            else:
                grant = 0
            bwmap[onu_id]["TCONT4"] = grant

        return bwmap
```

### 5. Generadores de tráfico (traffic.py)

```python
import random
import math

class FixedTrafficGen:
    """T-CONT 1: tráfico CBR (Constant Bit Rate) — VoIP, TDM"""
    def __init__(self, rate_bps, packet_size=160):
        self.interval = packet_size * 8 / rate_bps  # intervalo entre paquetes
        self.packet_size = packet_size

    def next_interval(self):
        return self.interval  # determinístico

class AssuredTrafficGen:
    """T-CONT 2: tráfico variable con tasa media garantizada"""
    def __init__(self, mean_rate_bps, packet_size=1000):
        self.mean_interval = packet_size * 8 / mean_rate_bps
        self.packet_size = packet_size

    def next_interval(self):
        return random.expovariate(1.0 / self.mean_interval)  # Poisson

class BestEffortTrafficGen:
    """T-CONT 4: tráfico best-effort, ráfagas Pareto"""
    def __init__(self, mean_rate_bps, packet_size=1400, pareto_alpha=1.5):
        self.mean_interval = packet_size * 8 / mean_rate_bps
        self.packet_size = packet_size
        self.alpha = pareto_alpha

    def next_interval(self):
        # Pareto: heavy-tailed, genera ráfagas
        return (random.paretovariate(self.alpha)) * self.mean_interval / (self.alpha / (self.alpha - 1))
```

---

## PARÁMETROS DE GPON (configs/default.json)

```json
{
    "gpon": {
        "upstream_rate_gbps": 1.244,
        "downstream_rate_gbps": 2.488,
        "frame_duration_us": 125,
        "num_onus": 32,
        "fiber_length_km": 20,
        "propagation_delay_us_per_km": 5,
        "split_ratio": 32
    },
    "tconts": {
        "TCONT1": {
            "name": "Fixed (CBR)",
            "rate_mbps": 1,
            "packet_size_bytes": 160,
            "buffer_size_bytes": 10000,
            "traffic_type": "fixed"
        },
        "TCONT2": {
            "name": "Assured",
            "rate_mbps": 10,
            "packet_size_bytes": 1000,
            "buffer_size_bytes": 100000,
            "traffic_type": "poisson"
        },
        "TCONT4": {
            "name": "Best Effort",
            "rate_mbps_per_onu": [10, 25, 50, 75, 100],
            "packet_size_bytes": 1400,
            "buffer_size_bytes": 1000000,
            "traffic_type": "pareto",
            "pareto_alpha": 1.5
        }
    },
    "simulation": {
        "duration_seconds": 10,
        "warmup_seconds": 1,
        "repetitions": 10,
        "seed_base": 67
    }
}
```

---

## ESCENARIOS EXPERIMENTALES

```json
{
    "scenarios": [
        {
            "name": "BasicDBA_32ONU",
            "algorithm": "basic",
            "num_onus": 32,
            "tcont4_rate_mbps": [10, 25, 50, 75, 100]
        },
        {
            "name": "QoSDBA_32ONU",
            "algorithm": "qos",
            "num_onus": 32,
            "tcont4_rate_mbps": [10, 25, 50, 75, 100]
        }
    ]
}
```

---

## MÉTRICAS A REGISTRAR

Por cada ONU y por cada tipo de T-CONT:
- **Latencia**: tiempo desde creación del paquete hasta recepción en OLT
- **Throughput**: bytes entregados exitosamente / tiempo
- **Tasa de pérdida**: paquetes descartados por buffer overflow / total generados
- **Jitter**: variación de latencia entre paquetes consecutivos
- **Utilización del canal**: tiempo ocupado / tiempo total por trama

---

## GRÁFICOS A GENERAR (analysis/analyze.py)

1. Latencia promedio por T-CONT (barras: BasicDBA vs QoS-DBA)
2. Tasa de pérdida por T-CONT (barras, escala log)
3. Throughput vs carga ofrecida (curvas)
4. CDF de latencia por T-CONT bajo carga alta
5. Heatmap de pérdida por T-CONT vs carga
6. Serie temporal de latencia T-CONT 1 (scatter)
7. Dashboard resumen (2x2 subplots)

Estilo: serif font, colores consistentes, IC 95%, 300 DPI.

---

## INSTRUCCIONES DE EJECUCIÓN

```bash
# Instalar dependencias
pip install matplotlib numpy scipy pandas

# Correr un escenario
python main.py --config configs/default.json --scenario BasicDBA_32ONU --load 50

# Correr todos los escenarios
python run_experiments.py

# Generar gráficos
python analysis/analyze.py
```

---

## PRIORIDADES

1. **Que funcione**: el motor de eventos debe procesar eventos correctamente en orden
2. **Que sea GPON real**: usar parámetros del estándar ITU-T G.984 (1.244 Gbps upstream, 125 μs por trama, T-CONTs)
3. **Que sea DBA centralizado**: BWmap broadcast + DBRu embebido, NO polling individual
4. **Que mida bien**: métricas por T-CONT con recolección correcta
5. **Que genere gráficos**: 7 gráficos comparando BasicDBA vs QoS-DBA

## NO HACER
- NO usar OMNeT++, SimPy, ni ningún framework de simulación
- NO usar IPACT (es de EPON, no GPON)
- NO llamar al tráfico eMBB/URLLC/mMTC — son categorías 5G, no GPON. Usar T-CONT 1/2/3/4/5
- NO usar polling individual — GPON es centralizado
- NO inventar parámetros — usar los de ITU-T G.984

## IMPORTANTE
Este simulador debe ser 100% código propio. El motor de eventos, la red, los algoritmos, todo.
La profesora es experta en PON y OMNeT++. Va a revisar que los conceptos sean correctos.