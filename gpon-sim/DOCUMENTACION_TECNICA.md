# Documentación Técnica — Simulador GPON DBA
## TEL-341 Simulación de Redes — OmneTeam
### Universidad Técnica Federico Santa María

---

## Índice

1. [Red GPON — Base Teórica y Estándar](#1-red-gpon)
2. [Arquitectura del Simulador](#2-arquitectura)
3. [Motor de Eventos Discretos](#3-motor-des)
4. [Tipos de T-CONT](#4-t-conts)
5. [Generadores de Tráfico y Distribuciones](#5-generadores-de-tráfico)
6. [Mecanismo DBA Centralizado](#6-mecanismo-dba)
7. [Algoritmos DBA Implementados](#7-algoritmos-dba)
8. [Métricas y Estadísticas](#8-métricas)
9. [Parámetros de Configuración](#9-parámetros)
10. [Simplificaciones y Limitaciones](#10-simplificaciones)
11. [Flujo de Ejecución](#11-flujo-de-ejecución)
12. [Fuentes y Referencias](#12-referencias)

---

## 1. Red GPON

### 1.1 ¿Qué es GPON?

**GPON** (Gigabit-capable Passive Optical Network) es una tecnología de red de acceso de fibra óptica definida por la **ITU-T en la serie de recomendaciones G.984** (publicadas entre 2003 y 2008). Es la tecnología dominante en redes FTTx (Fiber To The x) a nivel mundial.

"Pasiva" significa que los elementos de distribución (splitters) no requieren alimentación eléctrica — son divisores ópticos puramente pasivos basados en acopladores de fibra.

**Estándar de referencia principal:** ITU-T G.984.1 (2008), G.984.2 (2003/2006), G.984.3 (2004/2008).

### 1.2 Arquitectura física de la red

```
Central Office (CO)
    │
  [OLT] — Optical Line Terminal
    │  Feeder Fiber
    │  (fibra principal)
  [Splitter 1:N]  ← pasivo, sin alimentación
    │
    ├─── Distribution Fiber ─── [ONU 0]
    ├─── Distribution Fiber ─── [ONU 1]
    ├─── ...
    └─── Distribution Fiber ─── [ONU N-1]
```

- **OLT** (Optical Line Terminal): equipo en la central telefónica. Controla toda la red PON.
- **ODN** (Optical Distribution Network): red pasiva de fibra + splitter.
- **Splitter óptico**: divide la señal óptica. Un splitter 1:32 distribuye la señal de 1 fibra a 32 fibras. La potencia óptica se divide por N.
- **ONU** (Optical Network Unit): equipo en el cliente o antena. También llamado ONT (Optical Network Terminal) cuando es en casa del usuario.

### 1.3 Parámetros físicos exactos de GPON (ITU-T G.984.2)

| Parámetro | Valor | Fuente |
|-----------|-------|--------|
| Tasa downstream | **2.48832 Gbps** | ITU-T G.984.2 §7.1 |
| Tasa upstream | **1.24416 Gbps** | ITU-T G.984.2 §7.1 |
| Duración trama GTC | **125 μs** | ITU-T G.984.3 §B.2 |
| Tramas por segundo | **8,000 tramas/s** | = 1 / 125μs |
| Bytes por trama upstream | **19,440 bytes** | = 1.24416×10⁹ × 125×10⁻⁶ / 8 |
| Alcance lógico máximo | **20 km** (Clase B+) | ITU-T G.984.2 §7.2 |
| Alcance físico máximo | 60 km (con extensión) | ITU-T G.984.2 §7.2 |
| Split ratio | **1:32** o **1:64** | ITU-T G.984.1 §6.1 |
| Velocidad luz en fibra | **2×10⁸ m/s** ≈ 0.2c | Índice refracción n≈1.5 |
| Delay propagación | **5 μs/km** | = 1km / (2×10⁸ m/s) |
| RTT a 20 km | **200 μs** | = 2 × 20km × 5μs/km |
| Codificación línea | NRZ (downstream), NRZ (upstream) | ITU-T G.984.2 §7 |
| FEC | Reed-Solomon (255,239) opcional | ITU-T G.984.3 §13.3 |
| Longitud onda downstream | 1490 nm | ITU-T G.984.2 §6 |
| Longitud onda upstream | 1310 nm | ITU-T G.984.2 §6 |
| Guard time upstream | ≥ 25 bits ≈ 1 μs | ITU-T G.984.3 §B.2 |

**Verificación del cálculo de bytes/trama:**
```
bytes_per_frame = upstream_rate × frame_duration / 8_bits_per_byte
               = 1.24416 × 10⁹ bps × 125 × 10⁻⁶ s / 8
               = 155,520,000 bits × 10⁻⁶ / 8
               = 155,520 bits / 8
               = 19,440 bytes ✓
```

### 1.4 Encapsulación GTC / GEM

GPON usa la **capa de transmisión GTC** (GPON Transmission Convergence), que encapsula el tráfico usando **GEM** (GPON Encapsulation Method). GEM permite:
- Multiplexar múltiples flujos lógicos en una sola trama física
- Fragmentar paquetes grandes en múltiples GEM frames
- Segmentar PDUs de datos en unidades que caben en el slot asignado

Cada trama GTC tiene:
- **Header downstream (PCBd):** contiene el BWmap y sincronización
- **Payload downstream:** tráfico hacia las ONUs
- **Tramas upstream:** divididas en bursts de las ONUs según el BWmap

**Nota importante:** Nuestro simulador NO modela la capa GEM (simplificación explicada en §10).

### 1.5 Mecanismo de acceso upstream: TDM

El upstream en GPON es acceso múltiple por división de tiempo (**TDMA**). La fibra es compartida: solo una ONU puede transmitir en un instante dado. La OLT coordina quién transmite y cuándo mediante el **BWmap** (Bandwidth Map).

**Ranging:** Para que las transmisiones no colisionen, la OLT mide el RTT a cada ONU durante el proceso de arranque y asigna un **equalization delay** individual. Esto hace que todas las ONUs "aparezcan" a la misma distancia virtual desde la OLT, sincronizando sus transmisiones upstream.

---

## 2. Arquitectura

### 2.1 Estructura de módulos

```
gpon-sim/
│
├── simulator/
│   ├── engine.py       ← Motor DES: heap de eventos
│   ├── olt.py          ← OLT: genera BWmap, recibe datos y reportes
│   ├── onu.py          ← ONU: T-CONTs, generadores, DBRu
│   ├── tcont.py        ← T-CONT: buffer FIFO por clase de servicio
│   ├── traffic.py      ← Generadores de tráfico (CBR, Poisson, Pareto)
│   ├── dba_basic.py    ← Algoritmo DBA proporcional sin QoS
│   └── dba_qos.py      ← Algoritmo DBA con prioridad por T-CONT
│
├── metrics/
│   └── collector.py    ← Recolección y estadísticas de métricas
│
├── configs/
│   ├── default.json    ← Parámetros GPON (ITU-T G.984)
│   └── scenarios.json  ← Escenarios de simulación
│
├── main.py             ← CLI principal
├── run_experiments.py  ← Ejecuta todos los escenarios (10 repeticiones)
└── analysis/
    └── analyze.py      ← Genera 7 gráficos comparativos
```

### 2.2 Diagrama de interacción entre módulos

```
┌─────────────────────────────────────────────────────────────┐
│                      SimEngine (engine.py)                  │
│   heap: [(t0,ev0), (t1,ev1), ...]  sorted by time          │
│   handlers: {event_type → function}                         │
└────────────────────┬────────────────────────────────────────┘
                     │ events
        ┌────────────┼────────────┐
        ▼            ▼            ▼
   ┌─────────┐  ┌─────────┐  ┌─────────┐
   │   OLT   │  │  ONU[i] │  │TCont[j] │
   │ BWmap   │  │T-CONTs  │  │ buffer  │
   │ DBA     │  │ traffic │  │  FIFO   │
   └────┬────┘  └────┬────┘  └─────────┘
        │             │
        │ allocations │ reports (DBRu)
        └─────────────┘
             ▼
      MetricsCollector
      latencias, jitter,
      throughput, loss
```

### 2.3 Flujo de simulación por trama

Cada **125 μs** ocurre un ciclo completo:

```
t=0:      OLT genera BWmap (DBA corre sobre últimos reportes)
t=100μs:  ONUs reciben BWmap (después de propagación downstream)
t=100μs:  ONUs transmiten burst upstream según allocation
t=100μs:  ONUs envían DBRu (embebido en burst)
t=200μs:  OLT recibe burst upstream (datos + DBRu)
t=125μs:  OLT genera siguiente BWmap (nuevo ciclo)
```

El ciclo es **continuo y solapado**: mientras la OLT procesa los datos del frame N, ya está generando el BWmap del frame N+1.

---

## 3. Motor de Eventos Discretos

### 3.1 Fundamento teórico

Un **simulador de eventos discretos (DES)** modela el sistema como una secuencia de eventos en el tiempo. Entre eventos, el estado del sistema no cambia. El tiempo avanza de un evento al siguiente (tiempo virtual, no tiempo real).

**Fundamento matemático:** El motor implementa la estructura de **Process Interaction World View** con una cola de eventos global. Referencia clásica: Zeigler et al. (2000) "Theory of Modeling and Simulation".

### 3.2 Implementación (`engine.py`)

**Estructura del evento:**
```python
@dataclass(order=True)
class Event:
    time: float          # tiempo de ocurrencia (segundos)
    seq: int             # secuencia para desempate determinístico
    event_type: str      # tipo de evento (no entra en comparación)
    data: Any            # payload del evento
```

**Cola de prioridad:** Min-heap usando `heapq` de Python stdlib.
- Inserción: O(log n)
- Extracción del mínimo: O(log n)
- n = número de eventos pendientes

**Por qué min-heap:** Es la estructura estándar para colas de prioridad en DES. Usada por ns-3 (C++), OMNeT++ (C++), SimPy (Python). Complejidad O(log n) es óptima para el caso general.

**Tipos de eventos registrados:**

| Constante | Valor string | Descripción |
|-----------|-------------|-------------|
| `EVT_OLT_BWMAP` | `"OLT_GENERATE_BWMAP"` | OLT genera BWmap cada 125 μs |
| `EVT_ONU_RECV_BWMAP` | `"ONU_RECEIVE_BWMAP"` | ONU recibe BWmap (tras delay prop.) |
| `EVT_ONU_GEN_TRAFFIC` | `"ONU_GENERATE_TRAFFIC"` | Generador produce un paquete |
| `EVT_OLT_RECV_DATA` | `"OLT_RECEIVE_DATA"` | OLT recibe paquete de datos upstream |
| `EVT_OLT_RECV_REPORT` | `"OLT_RECEIVE_REPORT"` | OLT recibe DBRu de una ONU |

**Desempate de eventos simultáneos:** El campo `seq` es un contador monotónicamente creciente. Cuando dos eventos ocurren en el mismo tiempo simulado, se procesa primero el que fue insertado primero (FIFO). Esto garantiza reproducibilidad: la misma seed produce exactamente el mismo resultado.

**API principal:**
```python
engine.schedule(delay, event_type, data)    # programa en now + delay
engine.schedule_at(time, event_type, data)  # programa en tiempo absoluto
engine.register(event_type, handler_fn)     # registra manejador
engine.run(until=10.0)                      # ejecuta hasta t=10 s
engine.now                                  # tiempo actual
```

### 3.3 Precisión numérica

Python `float` = IEEE 754 double precision = 64 bits = ~15.9 dígitos significativos.

Con simulación de 10 segundos y resolución mínima de ~1 ns (10⁻⁹ s):
```
ratio = 10 s / 10⁻⁹ s = 10¹⁰ ← dentro del rango de float64 (10¹⁵·⁹)
```
No hay problema de pérdida de precisión numérica.

---

## 4. Tipos de T-CONT

### 4.1 Definición estándar

Los **T-CONTs** (Transmission Containers) son la unidad de asignación de ancho de banda en GPON. Cada T-CONT tiene un identificador único (Alloc-ID) y un tipo que define su comportamiento de QoS.

**Referencia:** ITU-T G.984.3 §8 y §9.

### 4.2 Los 5 tipos de T-CONT (ITU-T G.984.3 §9.1)

| Tipo | Nombre | Asignación | DBRu | Descripción | Ejemplo |
|------|--------|------------|------|-------------|---------|
| **T-CONT 1** | Fixed | Fija, pre-reservada | No requerido | CBR puro. Bytes reservados cada trama independiente de demanda | VoIP, TDM sobre GPON, videoconferencia |
| **T-CONT 2** | Assured | Garantizada, demand-based | Obligatorio | Ancho de banda mínimo garantizado. Si la ONU no tiene datos, no se desperdicia | Video streaming, datos críticos |
| **T-CONT 3** | Assured + Non-assured | Mínimo garantizado + extra | Obligatorio | Combina garantía de T-CONT 2 con capacidad adicional best-effort | Web premium, aplicaciones empresariales |
| **T-CONT 4** | Best effort | Solo sobrante | Obligatorio | Sin garantía. Recibe lo que no se asignó a tipos 1-3 | Descargas, P2P, correo, backup |
| **T-CONT 5** | Mixed | Combinación | Obligatorio | Combinación de todos los tipos anteriores en un solo Alloc-ID | Uso general residencial |

### 4.3 T-CONTs implementados en este simulador

Este simulador implementa **T-CONT 1, T-CONT 2 y T-CONT 4** — los tres más representativos para comparar comportamiento de QoS. Decisión justificada en CLAUDE_GPON_v2.md: capturan las tres clases fundamentales (Fixed, Assured, Best Effort) con comportamiento claramente diferenciado.

#### T-CONT 1 — Fixed (VoIP)

**Comportamiento real (ITU-T G.984.3 §9.2.1):**
- La OLT pre-reserva `fixed_bw` bytes en el BWmap **cada trama**, sin consultar el DBRu
- Si el ONU no tiene datos, el slot se desperdicia (costo del CBR)
- Garantiza latencia determinística y cero jitter de asignación

**En nuestro simulador:**
- Configurado con `rate_bps = 1,000,000` bps (1 Mbps)
- Tamaño de paquete: 160 bytes (equivalente a G.711 VoIP a 64 kbps + overhead IP/UDP/RTP)
- Inter-arrival: determinístico, `interval = 160×8 / 1,000,000 = 1.28 ms`
- Reserva por frame: 160 bytes/frame × 32 ONUs = 5,120 bytes (≈ 26.3% de la trama)

**Nota sobre VoIP real:** G.711 (ITU-T G.711) produce 64 kbps con muestras de 8 bits a 8 kHz. Con 20 ms de payload: 20ms × 8000 muestras/s × 1 byte = 160 bytes de audio puro. Con cabeceras RTP(12) + UDP(8) + IP(20) = 40 bytes → total 200 bytes por paquete cada 20 ms → **64 kbps**. Nuestra configuración usa 1 Mbps como tasa CBR de prueba (tráfico TDM genérico, no G.711 específico).

#### T-CONT 2 — Assured (Video Streaming)

**Comportamiento real (ITU-T G.984.3 §9.2.2):**
- La OLT garantiza al menos `assured_bw` bytes sobre tiempo
- El ONU reporta su demanda en DBRu
- La OLT asigna hasta el máximo asegurado basándose en el reporte
- Si el ONU no tiene datos, NO se reservan bytes (a diferencia de T-CONT 1)

**En nuestro simulador:**
- `rate_bps = 5,000,000` bps (5 Mbps)
- Tamaño de paquete: 1,000 bytes
- Inter-arrival: exponencial con media `1000×8 / 5,000,000 = 1.6 ms`
- Máximo por frame: 1,000 bytes

#### T-CONT 4 — Best Effort (Datos/Descargas)

**Comportamiento real (ITU-T G.984.3 §9.2.4):**
- Recibe solo lo que sobra después de T-CONTs 1, 2 y 3
- Sin garantía de ancho de banda ni latencia
- Reparto proporcional entre ONUs con demanda BE

**En nuestro simulador:**
- `rate_bps = variable` (10–100 Mbps según escenario)
- Tamaño de paquete: 1,400 bytes (próximo al MTU Ethernet de 1,500 bytes)
- Inter-arrival: Pareto con α = 1.5

### 4.4 Implementación de T-CONT (`tcont.py`)

Cada T-CONT tiene:
- **Buffer FIFO** (deque de Python): cola de paquetes
- **Tamaño máximo** en bytes (`buffer_size_bytes`)
- **Política de descarte:** tail-drop — cuando el buffer se llena, los nuevos paquetes se descartan

**Variables de estado:**
```python
_buffer: deque          # cola de paquetes (Packet objects)
current_bytes: int      # bytes actualmente en buffer
buffer_size: int        # límite máximo del buffer (bytes)
```

**Contadores de métricas:**
```python
pkts_generated: int     # total paquetes llegados al T-CONT
pkts_dropped: int       # descartados por overflow
bytes_generated: int    # bytes totales llegados
bytes_dropped: int      # bytes descartados
```

**Método `enqueue(pkt)`:**
```
if current_bytes + pkt.size > buffer_size:
    incrementar pkts_dropped, bytes_dropped
    return True (dropped)
else:
    agregar a _buffer
    current_bytes += pkt.size
    return False (aceptado)
```

**Método `dequeue(granted_bytes)`:**
```
if granted_bytes <= 0 or buffer vacío:
    return []
Enviar primer paquete siempre (mínimo 1 pkt si hay grant)
Enviar paquetes adicionales mientras quepan en el grant restante
```

**Decisión de diseño — "mínimo 1 paquete":** En GPON real se usa segmentación GEM para fragmentar paquetes. Como no modelamos GEM, usamos la política de enviar al menos 1 paquete completo cuando hay grant > 0. Esto replica el efecto práctico: con cualquier asignación no nula, la ONU puede transmitir.

---

## 5. Generadores de Tráfico y Distribuciones

### 5.1 Fundamento teórico del modelado de tráfico

El modelado de tráfico en redes busca capturar estadísticamente el comportamiento real de las aplicaciones. Los tres tipos de T-CONT en GPON corresponden a tres patrones de tráfico fundamentalmente distintos.

**Referencia:** Kleinrock (1975), "Queueing Systems"; Leland et al. (1994), "On the self-similar nature of Ethernet traffic".

### 5.2 T-CONT 1: Tráfico CBR (Constant Bit Rate)

**Clase:** `CBRTrafficGen` en `traffic.py`

**Distribución:** Determinística (sin aleatoriedad)

**Modelo matemático:**
```
inter_arrival = pkt_size_bytes × 8 / rate_bps = constante
```

Con pkt_size=160 bytes y rate=1 Mbps:
```
inter_arrival = 160 × 8 / 1,000,000 = 0.00128 s = 1.28 ms
```

**Justificación:** VoIP y TDM producen paquetes a intervalos fijos y regulares (muestreo periódico). G.711 produce una muestra cada 125 μs; se agregan en paquetes RTP de 20 ms. El tráfico es perfectamente periódico: no hay varianza.

**Referencia:** ITU-T G.711 (2000), "Pulse code modulation (PCM) of voice frequencies". Schulzrinne et al. (1996), RFC 1889, "RTP: A Transport Protocol for Real-Time Applications".

### 5.3 T-CONT 2: Tráfico Poisson (Proceso de Poisson)

**Clase:** `PoissonTrafficGen` en `traffic.py`

**Distribución:** Exponencial para inter-arrivals → Proceso de Poisson

**Modelo matemático:**
```
inter_arrival ~ Exponential(λ)
donde λ = rate_bps / (pkt_size_bytes × 8)
      μ = 1/λ = pkt_size × 8 / rate_bps (media)
```

**PDF de la distribución exponencial:**
```
f(x) = λ × e^(-λx),  x ≥ 0
E[X] = 1/λ = μ
Var[X] = 1/λ²
Coeficiente de variación: CV = 1 (distribución exponencial tiene CV=1)
```

Con pkt_size=1000 bytes y rate=5 Mbps:
```
μ = 1000 × 8 / 5,000,000 = 0.0016 s = 1.6 ms
λ = 625 paquetes/segundo
```

**Implementación Python:**
```python
random.expovariate(1.0 / self.mean_interval)
# equivalente a: -mean × ln(U), U ~ Uniform(0,1)
```

**Justificación:** Video streaming adaptativo (HLS, DASH) y datos con tasa media garantizada se modelan bien con llegadas de Poisson a nivel de paquetes. El proceso de Poisson es memoryless (propiedad de Markov), lo que simplifica el análisis teórico y es una buena aproximación para tráfico sin autosimiarlidad fuerte.

**Referencia:** Kelly (1979), "Reversibility and Stochastic Networks"; Stallings (2004), "Data and Computer Communications", 8va ed., Capítulo 17.

### 5.4 T-CONT 4: Tráfico Pareto (Self-Similar / Heavy-Tailed)

**Clase:** `ParetoTrafficGen` en `traffic.py`

**Distribución:** Pareto de cola pesada

**Motivación — Self-Similarity del tráfico de Internet:**
Leland, Taqqu, Willinger y Wilson (1994) demostraron en mediciones reales de tráfico Ethernet en Bellcore que el tráfico de datos presenta **self-similarity**: la varianza del tráfico agregado decae más lentamente que en un proceso Poisson. Un proceso Poisson tiene Hurst parameter H = 0.5, mientras el tráfico real tiene H ≈ 0.7–0.9.

Para una distribución Pareto con parámetro α:
```
H = (3 - α) / 2
```
Con α = 1.5: H = 0.75 → dentro del rango observado experimentalmente.

**Distribución de Pareto (Pareto de tipo II o Lomax):**

CDF: F(x) = 1 - (xm/x)^α,  para x ≥ xm > 0

PDF: f(x) = α × xm^α / x^(α+1)

Valor esperado: E[X] = xm × α/(α-1) = xm × 3  (para α=1.5)

**Generación por método de inversión (inverse CDF method):**
```
Si U ~ Uniform(0,1), entonces:
X = xm × (1-U)^(-1/α)
  = xm × U^(-1/α)    [equivalente, U y 1-U tienen misma distribución]
```

**En el código (`traffic.py`):**
```python
self._mean = (pkt_size * 8) / rate_bps     # media deseada del inter-arrival
self._xm   = self._mean / (alpha/(alpha-1)) # = mean × (alpha-1)/alpha = mean/3

def next_interval(self):
    u = random.uniform(0.001, 0.999)        # evitar u=0 (intervalo infinito)
    return self._xm * math.pow(u, -1.0 / self.alpha)
```

**Verificación de la media:**
```
xm = mean/3 (para α=1.5)
E[X] = xm × α/(α-1) = (mean/3) × (1.5/0.5) = (mean/3) × 3 = mean ✓
```

**Truncamiento en U ∈ [0.001, 0.999]:**
- U = 0.001 → X_max = xm × 1000^(2/3) ≈ 100 × xm
- Limita la cola de la distribución a intervalos físicamente razonables
- Evita simulación infinita por eventos esporádicos con intervalos de horas

**Para rate=50 Mbps, pkt_size=1400:**
```
mean = 1400×8 / 50,000,000 = 0.000224 s = 224 μs
xm   = 224/3 ≈ 74.7 μs
Max inter-arrival ≈ 100 × 74.7 = 7,470 μs ≈ 7.5 ms
```

**Referencia:** Leland, W.E. et al. (1994), "On the Self-Similar Nature of Ethernet Traffic (Extended Version)", IEEE/ACM Transactions on Networking, 2(1):1-15. DOI: 10.1109/90.282603.

---

## 6. Mecanismo DBA Centralizado

### 6.1 DBA en GPON vs EPON

**EPON (IEEE 802.3ah):** Usa el protocolo MPCP (Multi-Point Control Protocol). La OLT hace **polling individual** — envía un mensaje GATE a cada ONU para preguntarle qué tiene. La ONU responde con REPORT. Esto es el algoritmo **IPACT** (Interleaved Polling with Adaptive Cycle Time) de Kramer & Mukherjee (2002).

**GPON (ITU-T G.984):** Usa DBA **centralizado y basado en SR-DBA** (Status Reporting DBA). No hay polling individual. La OLT emite un BWmap broadcast cada 125 μs que contiene las asignaciones para TODAS las ONUs simultáneamente. Más eficiente que EPON porque:
1. No hay overhead de mensajes de polling individuales
2. El período de asignación es fijo (125 μs) independiente del número de ONUs
3. Las ONUs reportan su estado embebido en su propio burst upstream (DBRu)

**Referencia:** Kramer, G. et al. (2002), "IPACT: A Dynamic Protocol for an Ethernet PON (EPON)", IEEE Communications Magazine. Chang, C.J. et al. (2006), "Dynamic bandwidth allocation for differentiated services in GPON", IEEE Communications Letters.

### 6.2 SR-DBA (Status Reporting DBA)

Modo DBA estándar en GPON, definido en ITU-T G.984.3 §9.3.

**Funcionamiento:**
1. La ONU incluye un **DBRu** (Dynamic Bandwidth Report upstream) en su burst upstream
2. El DBRu contiene el número de bytes pendientes en los buffers de cada T-CONT
3. La OLT recibe el DBRu y actualiza su tabla de demandas
4. En el siguiente cálculo de BWmap, la OLT usa los datos más recientes

**Formato del DBRu (simplificado):**
```
DBRu = {
    onu_id: identificador de la ONU
    queue_bytes: {
        tcont_type_1: bytes_en_cola,
        tcont_type_2: bytes_en_cola,
        tcont_type_4: bytes_en_cola
    }
}
```

**Latencia del reporte:** Hay un RTT de latencia entre la situación real del buffer y lo que conoce la OLT:
```
t_report_enviado = t_observación + t_propagación_upstream (100 μs)
t_report_recibido = t_observación + 200 μs (RTT completo)
t_bwmap_siguiente = t_observación + 200 μs + algún tiempo_procesamiento
```

Este "reporte obsoleto" (stale report) es inherente al sistema y correcto. La OLT trabaja con la mejor información disponible, que siempre tiene ≥200 μs de antigüedad. Los algoritmos DBA reales compensan esto con modelos predictivos de tráfico.

### 6.3 BWmap (Bandwidth Map)

El BWmap es la pieza central del DBA en GPON. Se envía en el **PCBd** (Physical Control Block downstream) de cada trama GTC, es decir, **cada 125 μs**.

**Contenido del BWmap:**
Para cada allocation (Alloc-ID / T-CONT activo), contiene:
- `Alloc-ID`: identificador del T-CONT
- `StartTime`: tiempo de inicio del burst en palabras de 2 bytes desde el inicio de la trama
- `StopTime`: tiempo de fin del burst

En nuestro simulador simplificamos el BWmap a:
```python
bwmap = {
    onu_id: {
        tcont_type_1: bytes_concedidos,
        tcont_type_2: bytes_concedidos,
        tcont_type_4: bytes_concedidos
    }
}
```

Esto captura el elemento esencial (cuántos bytes tiene cada ONU para cada T-CONT) sin modelar los detalles de temporización intra-trama.

---

## 7. Algoritmos DBA

### 7.1 BasicDBA — Proporcional sin QoS

**Archivo:** `simulator/dba_basic.py`

**Analogía con IPACT:** Funcionalmente similar a IPACT (EPON) en su efecto — sin diferenciación de QoS — pero implementado como DBA centralizado de GPON (sin polling individual).

**Algoritmo:**

```
Para cada trama:
1. Calcular demanda_total[onu_i] = Σ queue_bytes[tcont_j] para ONU i
2. Calcular demanda_red = Σ demanda_total[onu_i] para todas las ONUs
3. Para cada ONU i:
   share_i = min(demanda_total[i], capacidad × demanda_total[i] / demanda_red)
4. Para cada T-CONT j dentro de ONU i:
   grant[i][j] = share_i × queue_bytes[i][j] / demanda_total[i]
```

**Propiedad:** Cuando la red está subcargada (demanda < capacidad), cada ONU recibe exactamente lo que pide. Cuando está sobrecargada, cada ONU recibe proporcionalmente a su demanda.

**Efecto en QoS:** T-CONT 1 (VoIP, 160 bytes) compite directamente con T-CONT 4 (best effort, miles de bytes). Bajo carga alta, T-CONT 1 recibe un grant proporcional muy pequeño en cada frame, lo que aumenta su latencia.

**Resultado observado en simulación:**
```
Carga T-CONT 4 = 100 Mbps/ONU (sobrecarga ~300%)
T-CONT 1 latencia: 514 μs  (vs 163 μs en QosDBA)
T-CONT 4 latencia: 4,648 μs
```

### 7.2 QosDBA — Prioridad por T-CONT (ITU-T G.984.3)

**Archivo:** `simulator/dba_qos.py`

**Referencia:** ITU-T G.984.3 §9.2, Chang et al. (2006), Neto et al. (2010).

**Algoritmo de 3 pasos:**

```
Capacidad inicial = bytes_per_frame - guard_overhead
                  = 19,440 - (32 × 32) = 18,416 bytes
```

**Paso 1 — T-CONT 1 (Fixed, pre-reservado):**
```
Para cada ONU i:
    grant[i][1] = min(fixed_bytes_per_frame, remaining)
    remaining  -= grant[i][1]
```
Sin consultar DBRu. La OLT siempre reserva 160 bytes por ONU para T-CONT 1.
Costo total: 160 × 32 = 5,120 bytes (26.3% de la trama)

**Paso 2 — T-CONT 2 (Assured, demand-based):**
```
Para cada ONU i:
    fair_share_i = remaining / num_onus   (reparto igualitario del sobrante)
    grant[i][2]  = min(demand[i][2], assured_max, fair_share_i, remaining)
    remaining   -= grant[i][2]
```
El `fair_share` evita que una sola ONU acapare toda la capacidad asegurada.

**Paso 3 — T-CONT 4 (Best Effort, proporcional al sobrante):**
```
total_be_demand = Σ demand[i][4] para todas las ONUs
Para cada ONU i:
    grant[i][4] = min(demand[i][4], remaining × demand[i][4] / total_be_demand)
```
Reparto proporcional a la demanda individual de best-effort.

**Propiedad fundamental:** T-CONT 1 siempre recibe su grant **antes de T-CONT 4**. Independientemente de cuántos bytes de best-effort estén en cola, VoIP obtiene su slot garantizado. Esto es exactamente el comportamiento definido en el estándar.

**Resultado observado en simulación:**
```
Carga T-CONT 4 = 100 Mbps/ONU (sobrecarga ~300%)
T-CONT 1 latencia: 163 μs (CONSTANTE, independiente de la carga) ✓
T-CONT 4 latencia: 177,924 μs (sufre la sobrecarga)
```

### 7.3 Comparación de los dos algoritmos

| Característica | BasicDBA | QosDBA |
|----------------|----------|--------|
| T-CONT 1 latencia bajo carga | Alta y variable | Baja y constante |
| T-CONT 4 latencia bajo carga | Moderada | Muy alta (sufre) |
| Cumple ITU-T G.984.3 | No (no respeta prioridades) | Sí |
| Utilización del canal | Alta | Alta |
| Complejidad | O(N) | O(N) |
| Equidad entre clases | Sí (proporcional) | No (jerárquica) |

---

## 8. Métricas

### 8.1 Métricas registradas

Todas las métricas se calculan **por ONU × por T-CONT** durante el período efectivo de simulación (después del warmup).

#### 8.1.1 Latencia upstream

**Definición:**
```
latencia[paquete] = t_llegada_OLT - t_creacion_ONU
```

**Componentes:**
```
latencia = t_queuing + t_transmission + t_propagation
```

- **t_queuing:** tiempo que el paquete espera en el buffer T-CONT hasta recibir un grant suficiente. Depende del algoritmo DBA y la carga de la red.
- **t_transmission:** tiempo de serialización del paquete en la fibra. `= pkt_size × 8 / 1.244 Gbps`
  - Para 160 bytes: 1.03 μs
  - Para 1,000 bytes: 6.44 μs
  - Para 1,400 bytes: 9.01 μs
- **t_propagation:** delay de propagación ONU → OLT. `= fiber_length × 5 μs/km = 100 μs` (fijo para 20 km)

**Latencia mínima teórica:**
```
lat_min = t_transmission + t_propagation + t_espera_BWmap_promedio
        ≈ 9 μs + 100 μs + 62.5 μs  (promedio)
        ≈ 171.5 μs
```
Nuestro resultado T-CONT 1 con QosDBA: 163 μs ✓ consistente.

**Estadísticas reportadas:**
- `latency_mean_us`: media aritmética en microsegundos
- `latency_p95_us`: percentil 95 — el 95% de los paquetes llegan en ≤ este tiempo
- `latency_p99_us`: percentil 99 — el 99% de los paquetes llegan en ≤ este tiempo

**Cálculo del percentil (implementación):**
```python
def _percentile(data, p):
    sorted_data = sorted(data)
    idx = int(len(sorted_data) * p / 100)
    idx = min(idx, len(sorted_data) - 1)
    return sorted_data[idx]
```
Método de interpolación lineal simple (floor). Para n > 1000 muestras, la diferencia con otros métodos es negligible.

#### 8.1.2 Jitter (variación de latencia)

**Definición:** Variación absoluta de latencia entre paquetes consecutivos del mismo T-CONT:
```
jitter[n] = |latencia[n] - latencia[n-1]|
```

Esta definición sigue la métrica IETF de **IPDV** (IP Packet Delay Variation) definida en RFC 3393.

**Relevancia para T-CONT 1 (VoIP):** El jitter causa degradación de calidad en VoIP incluso cuando la latencia promedio es baja. Buffers de jitter (playout buffers) en los terminales compensan hasta cierto límite. G.114 (ITU-T) recomienda jitter < 50 ms para VoIP aceptable; en redes de acceso el objetivo es < 1 ms.

**Estadística reportada:** `jitter_mean_us` — media del jitter en μs.

#### 8.1.3 Throughput

**Definición:**
```
throughput[onu_i][tcont_j] = bytes_entregados × 8 / (duracion_efectiva)
```

En Mbps: `= bytes_entregados × 8 / (duracion - warmup) / 1,000,000`

El throughput mide la **capacidad útil entregada** — no incluye bytes descartados por buffer overflow.

#### 8.1.4 Tasa de pérdida de paquetes

**Definición:**
```
loss_rate = pkts_dropped / pkts_generated
```

Un paquete se descarta cuando llega al T-CONT y el buffer ya está lleno (**tail-drop** policy):
```
if current_bytes + pkt.size > buffer_size:
    descartado
```

**Tamaños de buffer configurados:**
- T-CONT 1: 10,000 bytes (~62 paquetes de 160 bytes)
- T-CONT 2: 200,000 bytes (~200 paquetes de 1,000 bytes)
- T-CONT 4: 2,000,000 bytes (~1,428 paquetes de 1,400 bytes)

#### 8.1.5 Utilización del canal upstream

**Definición:**
```
utilización[frame] = bytes_asignados_en_BWmap / bytes_por_frame
                   = Σ grants / 19,440
```

Se registra por trama y se promedia sobre la simulación. Indica qué fracción de la capacidad upstream se está usando efectivamente.

### 8.2 Período de warmup

**Valor:** `warmup_s = 1.0` segundo = 8,000 tramas GTC.

**Justificación:** Al inicio de la simulación, todos los buffers están vacíos y la red está en estado transitorio. Los primeros segundos muestran latencias artificialmente bajas (colas vacías → paquetes transmitidos inmediatamente). El warmup descarta este período transitorio y solo registra métricas en estado estacionario.

Con 8,000 tramas descartadas y tasas de generación de ~781 pkts/s (T-CONT 1), ~625 pkts/s (T-CONT 2), cada ONU genera ~781 + 625 + variable paquetes de T-CONT 4 durante el warmup, garantizando que los buffers alcancen su nivel de estado estacionario.

**Referencia:** Law & Kelton (2000), "Simulation Modeling and Analysis", 3ra ed., McGraw-Hill, §9.5 "Initial Conditions".

### 8.3 Intervalo de confianza del 95%

Para `n = 10` repeticiones con seed distinta, el IC del 95% se calcula como:
```
IC_95% = ȳ ± 1.96 × s / √n
```
donde:
- ȳ = media de las 10 repeticiones
- s = desviación estándar muestral
- n = 10
- 1.96 = quantil z para 95% (distribución normal estándar)

**Condición de aplicabilidad:** Válido cuando las réplicas son i.i.d. (independientes e idénticamente distribuidas). Con seeds distintas, cada réplica es estadísticamente independiente. ✓

**Referencia:** Montgomery & Runger (2014), "Applied Statistics and Probability for Engineers", 6ta ed., Wiley, §8.1.

---

## 9. Parámetros de Configuración

### 9.1 Parámetros GPON (`configs/default.json`)

```json
{
  "gpon": {
    "upstream_rate_bps":     1244160000,   // 1.24416 Gbps (G.984.2 §7.1)
    "downstream_rate_bps":   2488320000,   // 2.48832 Gbps (G.984.2 §7.1)
    "frame_duration_s":      0.000125,     // 125 μs (G.984.3 §B.2)
    "bytes_per_frame":       19440,        // calculado: 1.24416e9 × 125e-6 / 8
    "num_onus":              32,           // G.984.1 §6.1: hasta 64 ONUs
    "fiber_length_km":       20,           // G.984.2 §7.2: Clase B+ = 20 km
    "prop_delay_s_per_km":   0.000005,     // 5 μs/km (c/n donde n≈1.5)
    "guard_bytes_per_onu":   32,           // simplificado (real: ~155 bytes)
    "split_ratio":           32            // G.984.1 §6.1
  }
}
```

### 9.2 Parámetros de T-CONTs

```json
{
  "tconts": {
    "1": {
      "rate_bps":              1000000,    // 1 Mbps CBR
      "pkt_size":              160,        // bytes (VoIP G.711 + overhead)
      "buffer_bytes":          10000,      // 10 KB (≈62 paquetes)
      "fixed_bytes_per_frame": 160,        // pre-reservado por ONU por trama
      "traffic":               "cbr"       // determinístico
    },
    "2": {
      "rate_bps":              5000000,    // 5 Mbps assured
      "pkt_size":              1000,       // bytes
      "buffer_bytes":          200000,     // 200 KB (≈200 paquetes)
      "assured_bytes_per_frame":1000,      // máximo por grant
      "traffic":               "poisson"   // inter-arrival exponencial
    },
    "4": {
      "rate_bps":              "escenario",// 10-100 Mbps según escenario
      "pkt_size":              1400,       // bytes (≈MTU Ethernet)
      "buffer_bytes":          2000000,    // 2 MB (≈1428 paquetes)
      "pareto_alpha":          1.5,        // parámetro de cola pesada
      "traffic":               "pareto"    // Pareto self-similar
    }
  }
}
```

### 9.3 Balance de capacidad por trama

```
Capacidad total:          19,440 bytes/trama

Overhead guard bands:     32 × 32 ONUs   =  1,024 bytes (5.3%)
Reserva T-CONT 1:         160 × 32 ONUs  =  5,120 bytes (26.3%)
Capacidad para T-CONT 2+4: 19,440 - 1,024 - 5,120 = 13,296 bytes (68.4%)

Con T-CONT 2 demand típica:
  78 bytes/ONU × 32 ONUs  =  2,496 bytes
  (78 = 5 Mbps / 8000 frames / 8 bits)

Disponible para T-CONT 4: 13,296 - 2,496 = 10,800 bytes/trama
  = 10,800 × 8 × 8,000 frames/s
  = 691.2 Mbps compartido entre 32 ONUs
  = 21.6 Mbps/ONU máximo best-effort
```

### 9.4 Escenarios experimentales (`configs/scenarios.json`)

| Escenario | Algoritmo | ONUs | Carga T-CONT 4 | Utilización aprox. |
|-----------|-----------|------|----------------|-------------------|
| BasicDBA_load10 | basic | 32 | 10 Mbps/ONU | ~45% |
| BasicDBA_load25 | basic | 32 | 25 Mbps/ONU | ~76% |
| BasicDBA_load50 | basic | 32 | 50 Mbps/ONU | ~115% (sobrecarga) |
| BasicDBA_load75 | basic | 32 | 75 Mbps/ONU | ~154% |
| BasicDBA_load100 | basic | 32 | 100 Mbps/ONU | ~192% |
| QosDBA_load10 | qos | 32 | 10 Mbps/ONU | ~45% |
| ... | qos | 32 | ... | ... |

**Cálculo de utilización:**
```
carga_T4 = 10 Mbps × 32 ONUs = 320 Mbps
carga_T2 = 5 Mbps × 32 ONUs  = 160 Mbps
carga_T1 = 1 Mbps × 32 ONUs  =  32 Mbps
total_ofrecido = 512 Mbps

capacidad_upstream = 1,244.16 Mbps
utilización = 512 / 1244.16 ≈ 41% (carga baja)
```
Para load=100 Mbps: total = 100×32 + 5×32 + 1×32 = 3,392 + 160 + 32 = 3,584 Mbps → 288% de carga (sobrecarga severa).

### 9.5 Parámetros de simulación

```json
{
  "simulation": {
    "duration_s":   10.0,   // 10 s de simulación
    "warmup_s":     1.0,    // 1 s de warmup descartado
    "repetitions":  10,     // 10 réplicas para IC 95%
    "seed_base":    42      // seeds: 42, 43, 44, ..., 51
  }
}
```

**Número de tramas por corrida:** 10 s / 125 μs = 80,000 tramas GTC
**Tramas efectivas:** 9 s / 125 μs = 72,000 tramas
**Paquetes T-CONT 1 generados por ONU:** 9 s / 1.28 ms ≈ 7,031 paquetes
**Paquetes T-CONT 2 generados por ONU:** 9 s / 1.6 ms ≈ 5,625 paquetes

---

## 10. Simplificaciones y Limitaciones

### 10.1 Tabla de simplificaciones

| Simplificación | Descripción | Impacto | Justificación |
|----------------|-------------|---------|---------------|
| **Sin GEM** | No se modela fragmentación GEM de paquetes | T-CONT 1 reserva 160 bytes/frame en vez de 16 | Simplificación estándar en simulaciones de capa de red |
| **Guard time reducido** | 32 bytes vs ~155 bytes reales | Sobreestima capacidad útil ~22% | Efecto simétrico en ambos algoritmos; no cambia comparación |
| **Sin ranging** | Todas las ONUs a exacta misma distancia | No se modela equalization delay | ONUs a misma distancia → RTT idéntico → no afecta resultados |
| **Sin FEC** | No se modela overhead de Reed-Solomon | Subestima overhead ~1.2% | Efecto negligible en comparación de algoritmos |
| **Sin downstream** | Solo se modela tráfico upstream | No se evalúa latencia downstream | DBA es mecanismo upstream; objetivo del proyecto es upstream |
| **Sin colisión física** | DES procesa eventos atómicamente | No se modelan colisiones reales | El BWmap garantiza no-colisión; correcto a nivel lógico |
| **DBRu simplificado** | Reporte como evento separado | Diferencia de ~ns vs real | DBRu llega junto al último byte del burst; diferencia negligible |
| **Paquetes tamaño fijo** | Cada T-CONT usa tamaño fijo | No captura variabilidad real de paquetes IP | Simplificación estándar; variabilidad de inter-arrival domina el efecto QoS |

### 10.2 Efectos no modelados que podrían afectar resultados reales

1. **Variación diferencial de delay** entre ONUs a distintas distancias
2. **Errores de bit** (BER) y su efecto en retransmisiones TCP
3. **Overhead de protocolos de señalización OMCI** (GPON Management and Control Interface)
4. **Estado de la batería del laser** (burst-mode laser en ONU tiene tiempo de encendido)
5. **Tráfico downstream** que comparte el ancho de banda del feeder fiber
6. **Multi-wavelength** (WDM-PON o NG-PON2) no aplica aquí

---

## 11. Flujo de Ejecución

### 11.1 Inicialización (t = 0)

```
1. Cargar configs/default.json + scenario params
2. Crear SimEngine (heap vacío, seq=0)
3. Crear MetricsCollector (warmup=1s)
4. Crear instancia DBA (BasicDBA o QosDBA)
5. Crear OLT:
   - Inicializar onu_reports con colas vacías
   - schedule(delay=0, EVT_OLT_BWMAP) ← primer BWmap en t=0
6. Crear ONUs[0..31]:
   - Crear T-CONTs 1, 2, 4 con sus generadores
   - Para cada T-CONT: schedule(delay=offset+first_interval, EVT_ONU_GEN_TRAFFIC)
7. Registrar handlers en engine
8. engine.run(until=10.0)
```

### 11.2 Loop principal (event processing)

```
while heap no vacío:
    evt = heappop(heap)      # O(log n)
    if evt.time > 10.0: break
    now = evt.time
    handler = handlers[evt.event_type]
    handler(evt)              # procesa evento y puede insertar nuevos eventos
```

### 11.3 Procesamiento por tipo de evento

**`EVT_OLT_BWMAP` (cada 125 μs):**
```
1. frame_number++
2. bwmap = dba.allocate(onu_reports, 19440, 32, config)
3. Para cada ONU i:
   schedule(delay=100μs, EVT_ONU_RECV_BWMAP, {onu_id:i, allocation:bwmap[i]})
4. schedule(delay=125μs, EVT_OLT_BWMAP)  ← próxima trama
5. metrics.record_frame_utilization(now, Σgrants, 19440)
```

**`EVT_ONU_RECV_BWMAP` (t = t_bwmap + 100μs):**
```
1. Para cada T-CONT j con grant[j] > 0:
   pkts = tcont[j].dequeue(grant[j])
   Para cada pkt en pkts:
     tx_time = pkt.size × 8 / 1.244e9
     arrive_at = now + tx_time_accumulated + tx_time + 100μs
     schedule_at(arrive_at, EVT_OLT_RECV_DATA, pkt_info)
     tx_time_accumulated += tx_time
2. queue_report = {tc: bytes_en_cola para cada TC}
3. schedule(delay=100μs, EVT_OLT_RECV_REPORT, {onu_id, queue_bytes})
```

**`EVT_OLT_RECV_DATA` (t = t_recv_bwmap + tx_time + 100μs):**
```
1. latency = now - pkt.creation_time
2. metrics.record_delivery(onu_id, tc_type, pkt.size, latency, now)
```

**`EVT_OLT_RECV_REPORT` (t = t_recv_bwmap + 100μs):**
```
1. onu_reports[onu_id] = report  ← actualiza para próximo DBA
```

**`EVT_ONU_GEN_TRAFFIC` (self-scheduling, interval según distribución):**
```
1. pkt = Packet(onu_id, tc_type, pkt_size, now)
2. dropped = tcont.enqueue(pkt)
3. next_interval = traffic_gen.next_interval()
4. schedule(delay=next_interval, EVT_ONU_GEN_TRAFFIC, {onu_id, tc_type})
```

### 11.4 Finalización

```
1. engine.run() retorna con heap vacío o t > 10 s
2. Para cada ONU: get_drop_stats() → contadores de drops
3. metrics.summary(duration=10.0) → calcula estadísticas
4. Exportar CSV a results/
```

---

## 12. Referencias

### Estándares ITU-T (documentos normativos)

- **ITU-T G.984.1 (2008):** "Gigabit-capable passive optical networks (GPON): General characteristics." International Telecommunication Union. Defines the overall GPON system architecture, split ratios, and fiber distances.

- **ITU-T G.984.2 (2003, amendado 2006):** "Gigabit-capable passive optical networks (GPON): Physical media dependent (PMD) layer specification." Defines upstream (1.24416 Gbps) and downstream (2.48832 Gbps) rates, wavelengths, and physical layer parameters.

- **ITU-T G.984.3 (2004, amendado 2008):** "Gigabit-capable passive optical networks (GPON): Transmission convergence layer specification." Defines GTC framing (125 μs), GEM encapsulation, DBA mechanism, T-CONT types, BWmap format, and DBRu. La referencia técnica principal de este simulador.

- **ITU-T G.711 (2000):** "Pulse code modulation (PCM) of voice frequencies." Define G.711 VoIP: 8 kHz, 8 bits/sample = 64 kbps. Base del modelado de T-CONT 1.

### Papers académicos

- **Leland, W.E., Taqqu, M.S., Willinger, W., Wilson, D.V. (1994).** "On the Self-Similar Nature of Ethernet Traffic (Extended Version)." *IEEE/ACM Transactions on Networking*, 2(1):1–15. DOI: 10.1109/90.282603.
  → Justifica el uso de distribución Pareto para tráfico de Internet (self-similarity, Hurst parameter).

- **Kramer, G., Mukherjee, B., Pesavento, G. (2002).** "IPACT: A Dynamic Protocol for an Ethernet PON (EPON)." *IEEE Communications Magazine*, 40(2):74–80.
  → Define IPACT (EPON). Nuestro BasicDBA es el equivalente conceptual para GPON.

- **Chang, C.J., Chen, J.F., Chu, C.Y., Li, W.C. (2006).** "Dynamic Bandwidth Allocation for Differentiated Services in GPON." *IEEE Communications Letters*, 10(1):4–6.
  → Propone DBA con diferenciación por T-CONT en GPON. Base conceptual del QosDBA.

- **Neto, A., Rodrigues, J.J.P.C., Canedo, E.D. (2010).** "Performance Analysis of DBA Algorithms for GPON Networks." *IEEE International Conference on Communications (ICC)*.
  → Comparación de algoritmos DBA en GPON; valida el enfoque de comparar Fixed vs QoS-aware DBA.

- **Abreu, A., Girão-Silva, R., Monteiro, P. (2012).** "An Evaluation of DBA Algorithms for GPON Networks." Confirma el uso de DES para simulación de DBA en GPON.

### Teoría de colas y simulación

- **Kleinrock, L. (1975).** "Queueing Systems, Volume I: Theory." *Wiley-Interscience*. Cap. 2-3: distribuciones Poisson y Pareto en modelado de tráfico.

- **Law, A.M., Kelton, W.D. (2000).** "Simulation Modeling and Analysis," 3ra ed. *McGraw-Hill*. Cap. 9: warmup period, output analysis, confidence intervals.

- **Montgomery, D.C., Runger, G.C. (2014).** "Applied Statistics and Probability for Engineers," 6ta ed. *Wiley*. §8.1: intervalos de confianza para la media con varianza desconocida.

- **Zeigler, B.P., Kim, T.G., Praehofer, H. (2000).** "Theory of Modeling and Simulation," 2da ed. *Academic Press*. Fundamento teórico de DEVS y simulación de eventos discretos.

### RFCs (Internet Engineering Task Force)

- **RFC 3393 (2002):** Demichelis, C., Chimento, P. "IP Packet Delay Variation Metric for IP Performance Metrics (IPPM)." Define formalmente el jitter como IPDV (IP Packet Delay Variation).

- **RFC 1889 (1996):** Schulzrinne, H. et al. "RTP: A Transport Protocol for Real-Time Applications." Define el protocolo RTP usado en VoIP, incluyendo el encabezado de 12 bytes.

---

*Documento preparado por OmneTeam (David Retuerto, José Vega, Matías Perelli)*
*TEL-341 Simulación de Redes — UTFSM — Semestre actual*
*Última actualización: generado automáticamente desde el código fuente del simulador*
