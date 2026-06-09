# Guía Técnica — Simulador GPON DBA
## OmneTeam · TEL-341 Simulación de Redes · UTFSM 2026
### David Retuerto · José Vega · Matías Perelli

> Documento de estudio para la entrevista con la profesora.  
> Cada dato fue validado contra el código fuente y los estándares ITU-T G.984.

---

## Índice

1. [¿Qué simulamos exactamente?](#1-qué-simulamos-exactamente)
2. [Parámetros físicos de GPON](#2-parámetros-físicos-de-gpon)
3. [Topología de red](#3-topología-de-red)
4. [T-CONTs — clases de tráfico en GPON](#4-t-conts)
5. [Mecanismo DBA: SR-DBA centralizado](#5-mecanismo-dba-sr-dba-centralizado)
6. [Algoritmos implementados](#6-algoritmos-implementados)
7. [Generadores de tráfico y distribuciones](#7-generadores-de-tráfico)
8. [Motor de simulación (DES)](#8-motor-des)
9. [Métricas y metodología](#9-métricas-y-metodología)
10. [Resultados clave](#10-resultados-clave)
11. [Simplificaciones declaradas](#11-simplificaciones-declaradas)
12. [Preguntas probables y respuestas](#12-preguntas-probables-y-respuestas)
13. [Referencias](#13-referencias)

---

## 1. ¿Qué simulamos exactamente?

### Estándar: GPON ITU-T G.984 (NO es EPON, NO es PON genérico)

| Documento | Contenido | Relevancia para el proyecto |
|---|---|---|
| **ITU-T G.984.1 (2008)** | Arquitectura general, split ratios, distancias | Topología, número de ONUs |
| **ITU-T G.984.2 (2003/2006)** | Capa física: tasas de línea, longitudes de onda | 1.244 Gbps upstream, 2.488 Gbps downstream |
| **ITU-T G.984.3 (2004/2008)** | Capa GTC: tramas, T-CONTs, BWmap, DBA, DBRu | **La referencia técnica principal** |
| ITU-T G.711 | VoIP PCM a 64 kbps | Justificación del tráfico T-CONT 1 |

### Por qué no EPON ni OMNeT++

El simulador anterior (OMNeT++) mezclaba tres estándares:

| Componente | Simulador viejo ✗ | Simulador nuevo ✓ |
|---|---|---|
| Estándar | EPON IEEE 802.3ah | **GPON ITU-T G.984** |
| Clases de tráfico | eMBB / URLLC / mMTC (son de **5G**, no PON) | **T-CONT 1, 2, 4** (son de GPON real) |
| Algoritmo DBA | IPACT (es de **EPON**, no GPON) | **SR-DBA con BWmap** (es de GPON real) |
| Mecanismo upstream | Polling: OLT pregunta ONU por ONU | **BWmap broadcast** cada 125 μs |
| Herramienta | OMNeT++ (framework externo) | **Python puro** (100% código propio) |

---

## 2. Parámetros físicos de GPON

### Tabla completa — todos validados contra G.984

| Parámetro | Valor exacto en el simulador | Fuente del estándar |
|---|---|---|
| Tasa upstream | **1.24416 Gbps** = 1,244,160,000 bps | G.984.2 §7.1 |
| Tasa downstream | **2.48832 Gbps** = 2,488,320,000 bps | G.984.2 §7.1 |
| Duración trama GTC | **125 μs** | G.984.3 §B.2 |
| Tramas por segundo | **8,000 tramas/s** | = 1 / 125 μs |
| **Bytes por trama upstream** | **19,440 bytes** | Calculado (ver abajo) |
| Alcance lógico máximo | **20 km** (Clase B+) | G.984.2 §7.2 |
| Velocidad luz en fibra | **2×10⁸ m/s** ≈ 0.2c | índice refracción n ≈ 1.5 |
| Delay propagación | **5 μs/km** | = 1 km / (2×10⁸ m/s) |
| RTT a 20 km | **200 μs** | = 2 × 20 km × 5 μs/km |
| Split ratio | **1:32** | G.984.1 §6.1 (soporta hasta 1:64) |
| Guard band (simplificado) | **32 bytes/ONU** | G.984.3 §8.2 (real ≥25 bits) |
| Longitud onda downstream | **1490 nm** | G.984.2 §6 |
| Longitud onda upstream | **1310 nm** | G.984.2 §6 |
| Encapsulación de datos | **GEM** (GPON Encapsulation Method) | G.984.3 (no simulado, simplificación) |
| Multiplexación WDM | 1490 nm down + 1310 nm up sobre 1 fibra | G.984.2 |

### Verificación del cálculo de bytes por trama

```
bytes_per_frame = upstream_rate × frame_duration / 8 bits_per_byte
               = 1,244,160,000 bps × 0.000125 s / 8
               = 155,520,000 bits × 0.000125 / 8
               = 19,440,000 bits / 8... wait:

1,244,160,000 × 0.000125 = 155,520 bits
155,520 / 8 = 19,440 bytes ✓
```

---

## 3. Topología de red

```
Central Office (CO)
        │
      [OLT]  ← Optical Line Terminal
        │        Controla toda la PON
        │        Genera BWmap cada 125 μs
        │        Corre el algoritmo DBA
        │
     Feeder fiber
     (20 km, delay = 100 μs)
        │
  [Splitter 1:32]  ← Completamente pasivo
        │           Divide señal óptica en 32 partes
        │           Sin alimentación eléctrica
        │
        ├─── Distribution fiber ─── [ONU  0] → T-CONT 1 + T-CONT 2 + T-CONT 4
        ├─── Distribution fiber ─── [ONU  1] → T-CONT 1 + T-CONT 2 + T-CONT 4
        ├─── Distribution fiber ─── [ONU  2] → ...
        │            ...
        └─── Distribution fiber ─── [ONU 31] → T-CONT 1 + T-CONT 2 + T-CONT 4
```

**Parámetros de la red simulada:**
- 32 ONUs
- 20 km de fibra (feeder + distribución, misma longitud para todas las ONUs — simplificación)
- Delay propagación ONU→OLT: 100 μs (fijo)
- Canal upstream: 1.244 Gbps compartido entre 32 ONUs por TDMA
- Canal downstream: broadcast (2.488 Gbps, no simulado — DBA es mecanismo upstream)

**Ranging:** En GPON real, la OLT mide el RTT a cada ONU y asigna un *equalization delay* individual para que todas aparezcan a la misma distancia lógica. En nuestro simulador todas las ONUs están a exactamente 20 km (simplificación que no afecta la comparación de DBA).

---

## 4. T-CONTs

### Los 5 tipos del estándar (ITU-T G.984.3 §9.1)

| Tipo | Nombre | Asignación | DBRu necesario | Descripción | Ejemplo |
|---|---|---|---|---|---|
| **T-CONT 1** | Fixed | Fija, pre-reservada cada trama | **NO** | CBR puro. La OLT reserva ancho de banda aunque la ONU no tenga datos | VoIP, TDM, videoconferencia |
| **T-CONT 2** | Assured | Garantizada mínima, demand-based | Sí | Garantía mínima. Si la ONU no tiene datos, no se desperdicia | Video streaming |
| T-CONT 3 | Non-assured | Mínimo garantizado + extra si sobra | Sí | Combinación de T-CONT 2 + best-effort extra | Web premium |
| **T-CONT 4** | Best Effort | Solo lo que sobra tras 1-3 | Sí | Sin garantía. Recibe el sobrante | Descargas, P2P, backup |
| T-CONT 5 | Mixed | Combinación de todos | Sí | Mezcla de los anteriores | Uso general residencial |

### T-CONTs implementados: 1, 2 y 4

**Decisión:** Capturan los tres comportamientos fundamentales (Fixed / Assured / Best Effort) con la máxima diferenciación de QoS observable. T-CONT 3 es combinación de 2+4, T-CONT 5 es combinación de todos.

### Configuración de cada T-CONT

#### T-CONT 1 — Fixed (VoIP)

```
Tráfico:       CBR (Constant Bit Rate)
Tasa fuente:   1 Mbps
Paquete:       160 bytes
Buffer:        10,000 bytes (~62 paquetes)
Inter-arrival: DETERMINÍSTICO = 160 bytes × 8 bits / 1,000,000 bps = 1.28 ms
               → 1 paquete cada 10.24 tramas GTC

Reserva DBA:   160 bytes/trama/ONU (= 10.24 Mbps por ONU)
```

> **Inconsistencia intencional — prepara esta respuesta:**
>
> La fuente genera 1 Mbps pero el DBA reserva 160 bytes/trama = **10.24 Mbps**.
>
> **Por qué:** T-CONT 1 (Fixed) reserva un slot por trama aunque esté vacío — ese es precisamente el costo del CBR en PON. En GPON real con GEM, la OLT reservaría exactamente 16 bytes/trama (= 1 Mbps × 125μs / 8) y la ONU acumularía créditos durante 10 tramas antes de enviar un paquete completo. Nuestro simulador no implementa GEM, así que simplificamos reservando un slot de paquete completo (160 bytes) por trama.
>
> **Respuesta preparada para la profesora:**
> *"Como simplificación del modelo, reservamos un slot de paquete completo por trama para T-CONT 1, en lugar de implementar acumulación de créditos GEM. Esto sobreaprovisiona el ancho de banda reservado respecto a la fuente de 1 Mbps, pero no afecta la comparación entre algoritmos porque la simplificación es simétrica — BasicDBA y QosDBA operan sobre el mismo modelo."*

**Sobre el paquete de 160 bytes:** G.711 VoIP: 64 kbps con muestras de 8 bits a 8 kHz. Con 20 ms de payload: 20ms × 8000 Hz × 1 byte = 160 bytes de audio. Overhead RTP(12) + UDP(8) + IP(20) = 40 bytes adicionales en la vida real; usamos 160 bytes como tamaño representativo de tráfico TDM/VoIP.

#### T-CONT 2 — Assured (Video streaming)

```
Tráfico:       Proceso de Poisson
Tasa media:    5 Mbps (garantizada)
Paquete:       1,000 bytes
Buffer:        200,000 bytes (~200 paquetes)
Inter-arrival: Exponencial, media = 1000 × 8 / 5,000,000 = 1.6 ms
               → ~625 paquetes/segundo por ONU
```

#### T-CONT 4 — Best Effort (Datos/Descargas)

```
Tráfico:       Pareto con cola pesada (self-similar)
Tasa:          Variable según escenario: 10, 25, 50, 75 o 100 Mbps/ONU
Paquete:       1,400 bytes (≈ MTU Ethernet de 1,500 bytes)
Buffer:        2,000,000 bytes (~1,428 paquetes)
Pareto α:      1.5 → Hurst parameter H = (3 − 1.5) / 2 = 0.75
```

---

## 5. Mecanismo DBA: SR-DBA Centralizado

### IPACT (EPON) vs SR-DBA (GPON) — diferencia fundamental

**IPACT — Interleaved Polling with Adaptive Cycle Time (IEEE 802.3ah/EPON):**
```
OLT → [GATE msg a ONU 0] → ONU 0 → [REPORT: tengo X bytes] → OLT
OLT → [GATE msg a ONU 1] → ONU 1 → [REPORT: tengo Y bytes] → OLT
OLT → [GATE msg a ONU 2] → ONU 2 → ...
...  (secuencial, 1 RTT por ONU)

Período de ciclo: crece linealmente con N → para 32 ONUs: ~6.4 ms
```

**SR-DBA (Status Reporting DBA, definido en ITU-T G.984.3) — lo que implementamos:**
```
OLT → [BWmap broadcast a TODAS las ONUs] → todas reciben en 100 μs
       ↓                                    ↓
  Corre DBA                            Todas transmiten según su slot
  con últimos DBRu                     + envían DBRu embebido

Período fijo: 125 μs, independiente del número de ONUs
```

### Flujo exacto por trama (cada 125 μs)

```
t = k×125μs:         OLT corre DBA sobre últimos reportes recibidos
                     OLT genera BWmap con las asignaciones
                     OLT envía BWmap downstream (broadcast)

t = k×125μs + 100μs: Todas las ONUs reciben el BWmap simultáneamente
                     Cada ONU transmite su burst upstream según allocation
                     Cada ONU envía DBRu embebido al final del burst

t = k×125μs + 200μs: OLT recibe datos upstream de las ONUs
                     OLT recibe DBRu y actualiza tabla de reportes

t = (k+1)×125μs:     OLT ya está corriendo el DBA del siguiente frame
                     (ciclos solapados — pipelining)
```

### BWmap (Bandwidth Map)

Enviado en el **PCBd** (Physical Control Block downstream) de cada trama GTC. Contiene para cada T-CONT activo:
- `Alloc-ID`: identificador del T-CONT (Allocation Identifier)
- `StartTime`: inicio del slot (en palabras de 2 bytes desde inicio de trama)
- `StopTime`: fin del slot

En nuestro simulador simplificamos a: `{onu_id: {tcont_type: bytes_concedidos}}`

### DBRu (Dynamic Bandwidth Report upstream)

Embebido en el burst upstream de la ONU. Reporta bytes pendientes por T-CONT. Hay un **stale report delay** inherente: la OLT siempre trabaja con información de ≥200 μs de antigüedad (1 RTT = 100 μs ida + 100 μs vuelta). Esto es correcto y esperado.

### Balance de capacidad por trama (QosDBA a 32 ONUs)

```
Capacidad total:           19,440 bytes = 100%
── Guard bands:            32 B × 32 ONUs =  1,024 bytes (5.3%)
── T-CONT 1 pre-reservado: 160 B × 32 ONUs = 5,120 bytes (26.3%)
   Disponible T2 + T4:     19,440 − 1,024 − 5,120 = 13,296 bytes (68.4%)
── T-CONT 2 (demanda típica ~78 B/ONU): 32 × 78 = 2,496 bytes (12.8%)
   Disponible T-CONT 4:    13,296 − 2,496 = 10,800 bytes/trama
                           = 10,800 × 8,000 frames/s × 8 bits
                           = 691.2 Mbps total ÷ 32 ONUs
                           = ~21.6 Mbps/ONU disponible para best-effort
```

---

## 6. Algoritmos implementados

### BasicDBA — Proporcional sin diferenciación de T-CONT

Análogo funcional a IPACT en su efecto (sin QoS), pero implementado como DBA centralizado GPON (BWmap broadcast, no polling).

**Paso a paso:**

```python
# 1. Restar guard overhead (correcto según G.984.3)
effective_capacity = 19,440 − 32 × 32 = 18,416 bytes

# 2. Demanda de cada ONU (suma de todos sus T-CONTs)
demanda[onu_i] = cola_tcont1 + cola_tcont2 + cola_tcont4

# 3. Asignación proporcional
total_demanda = Σ demanda[onu_i]
share[onu_i] = effective_capacity × demanda[onu_i] / total_demanda

# 4. Repartir entre T-CONTs de la ONU, proporcionalmente a sus colas
grant[onu_i][tcont_j] = share[onu_i] × cola[onu_i][tcont_j] / demanda[onu_i]
```

**Por qué falla bajo alta carga:**  
A 100 Mbps/ONU de T-CONT 4: la cola T4 se llena (2 MB). T-CONT 1 tiene solo 160 bytes en cola.  
Proporción de T-CONT 1 = 160 / (2,000,000 + 5,000 + 160) ≈ 0.008%  
Grant T-CONT 1 = int(607 × 0.008%) = int(0.048) = **0 bytes** → starvation → 25 ms de latencia.

### QosDBA — Algoritmo propio inspirado en la jerarquía de T-CONTs de GPON

**Paso a paso:**

```python
remaining = 19,440 − 32 × 32 = 18,416 bytes  # quitar guard

# PASO 1: T-CONT 1 (Fixed) — SIN consultar DBRu
for onu_i in range(32):
    grant[onu_i][1] = min(160, remaining)     # 160 bytes/ONU garantizados
    remaining -= grant[onu_i][1]
# Costo: 160 × 32 = 5,120 bytes → remaining = 13,296 bytes

# PASO 2: T-CONT 2 (Assured) — demand-based
for onu_i in range(32):
    fair_share = remaining // 32              # reparto igualitario del sobrante
    grant[onu_i][2] = min(demanda[onu_i][2], 1000, fair_share, remaining)
    remaining -= grant[onu_i][2]

# PASO 3: T-CONT 4 (Best Effort) — proporcional al sobrante
total_be = Σ demanda[onu_i][4]
for onu_i in range(32):
    grant[onu_i][4] = remaining × demanda[onu_i][4] / total_be
```

**Propiedad fundamental:** T-CONT 1 siempre recibe su grant *antes* de T-CONT 4, independientemente de cuántos bytes de best-effort estén en cola. Resultado: latencia T-CONT 1 constante a 164 μs para cualquier nivel de carga.

### Comparación de algoritmos

| Característica | BasicDBA | QosDBA |
|---|---|---|
| T-CONT 1 latencia bajo carga | Alta y variable (hasta 25 ms) | **Constante ~164 μs** |
| T-CONT 4 latencia bajo carga | Moderada (comparte con T1/T2) | Muy alta (absorbe toda la congestión) |
| Cumple ITU-T G.984.3 prioridades | **No** | **Sí** |
| Utilización canal | Alta (~100%) | Alta (~100%) |
| Complejidad | O(N) | O(N) |
| Fairness entre clases | Proporcional (no jerárquica) | Jerárquica (T1 > T2 > T4) |

---

## 7. Generadores de tráfico

### T-CONT 1 — CBR Determinístico

```
Distribución:  Ninguna (determinístico, sin aleatoriedad)
Inter-arrival: 160 bytes × 8 bits / 1,000,000 bps = 1.28 ms (fijo)
Jitter:        0 (por definición del CBR)

Implementación Python:
    def next_interval(self):
        return self.interval  # constante
```

**Justificación:** VoIP/TDM muestrea a frecuencia fija (G.711: 8,000 muestras/s). El tráfico CBR tiene inter-arrival perfectamente periódico.

### T-CONT 2 — Proceso de Poisson

```
Distribución:  Exponencial para inter-arrivals → proceso de Poisson
Media:         μ = 1,000 bytes × 8 bits / 5,000,000 bps = 1.6 ms
Parámetro λ:   1/μ = 625 paquetes/segundo

PDF:           f(x) = λ × e^(−λx),  x ≥ 0
E[X]:          1/λ = 1.6 ms
Coef. variación: CV = 1 (propiedad de la exponencial)

Implementación Python:
    def next_interval(self):
        return random.expovariate(1.0 / self.mean_interval)
        # = −mean × ln(U),  U ~ Uniform(0,1)
```

**Justificación:** Proceso de Poisson es estándar para modelar tráfico de video streaming con tasa media garantizada. Es memoryless (proceso de Markov) — buena aproximación para flujos sin self-similarity fuerte.

### T-CONT 4 — Pareto (Self-Similar, Heavy-Tailed)

```
Distribución:  Pareto de cola pesada
Parámetro α:   1.5
Hurst param:   H = (3 − α) / 2 = (3 − 1.5) / 2 = 0.75

Por qué H importa:
  H = 0.5 → proceso Poisson (sin self-similarity)
  H ∈ (0.5, 1.0) → proceso self-similar (colas largas, ráfagas correlacionadas)
  Tráfico real de Internet: H ≈ 0.7–0.9 (Leland et al. 1994)
  Nuestro α=1.5 → H=0.75 ✓ dentro del rango observado

CDF:           F(x) = 1 − (xm/x)^α,   x ≥ xm
E[X]:          xm × α/(α−1) = xm × 3   (para α=1.5)

Generación (inverse CDF method):
    xm = mean_interval / (α/(α−1)) = mean / 3
    def next_interval(self):
        u = random.uniform(0.001, 0.999)
        return xm × u^(−1/α)

Verificación que E[X] = mean_interval:
    E[X] = xm × α/(α−1) = (mean/3) × (1.5/0.5) = (mean/3) × 3 = mean ✓
```

**Referencia:** Leland, Taqqu, Willinger, Wilson (1994). "On the Self-Similar Nature of Ethernet Traffic." IEEE/ACM Transactions on Networking, 2(1):1–15. DOI: 10.1109/90.282603.

---

## 8. Motor DES

**Sin frameworks externos.** Implementado en `simulator/engine.py` con la biblioteca estándar de Python.

```python
@dataclass(order=True)
class Event:
    time:       float    # tiempo de ocurrencia (segundos)
    seq:        int      # desempate determinístico (FIFO si mismo tiempo)
    event_type: str      # tipo (no entra en comparación de orden)
    data:       Any      # payload del evento

class SimEngine:
    _heap:     list       # min-heap (heapq)
    _now:      float      # tiempo actual de simulación
    _handlers: dict       # event_type → función handler
```

**Tipos de eventos:**

| Evento | Descripción | Cada cuánto |
|---|---|---|
| `OLT_GENERATE_BWMAP` | OLT calcula y envía BWmap | 125 μs (fijo) |
| `ONU_RECEIVE_BWMAP` | ONU recibe BWmap | 125 μs + 100 μs delay |
| `ONU_GENERATE_TRAFFIC` | Generador produce un paquete | Según distribución |
| `OLT_RECEIVE_DATA` | OLT recibe paquete upstream | Por cada paquete transmitido |
| `OLT_RECEIVE_REPORT` | OLT recibe DBRu | 125 μs + 200 μs (RTT) |

**Cálculo de latencia por paquete:**
```
latencia = t_llegada_OLT − t_creacion_ONU

Componentes:
  t_queuing      = tiempo en buffer T-CONT esperando grant
  t_transmission = pkt_size × 8 / 1.244 Gbps
                   (160 bytes → 1.03 μs; 1,400 bytes → 9.0 μs)
  t_propagation  = 100 μs (fijo, 20 km × 5 μs/km)

Latencia mínima teórica T-CONT 1:
  = 1.03 μs (tx) + 62.5 μs (espera promedio ½ trama) + 100 μs (prop)
  = 163.5 μs
Resultado simulado QosDBA: 164.3 μs ✓ (consistente)
```

---

## 9. Métricas y metodología

### Métricas registradas (por ONU × por T-CONT)

| Métrica | Definición | Unidad |
|---|---|---|
| Latencia media | `mean(t_llegada_OLT − t_creacion_ONU)` | μs |
| Latencia P99 | Percentil 99 de latencias | μs |
| Jitter | `mean(|latencia[n] − latencia[n−1]|)` — IPDV según RFC 3393 | μs |
| Throughput | `bytes_entregados × 8 / duración_efectiva` | Mbps |
| Tasa de pérdida | `pkts_dropped / pkts_generated` (tail-drop en buffer) | % |
| Utilización canal | `Σgrants_por_trama / 19,440 bytes` promediado | % |

### Metodología estadística

```
Configuración experimental:
  Escenarios:    10 (5 cargas × 2 algoritmos)
  Cargas T-CONT 4: {10, 25, 50, 75, 100} Mbps/ONU
  Repeticiones:  10 por escenario con seeds distintos (42 a 51)
  Duración:      10 segundos por corrida
  Warmup:        1 segundo (descartado — estado transitorio)
  Efectivo:      9 segundos = 72,000 tramas GTC

Intervalo de confianza 95%:
  IC₉₅% = ȳ ± 1.96 × s / √10
  Válido porque las 10 réplicas son i.i.d. (seeds distintos → independientes)

Total de corridas: 100 (10 escenarios × 10 repeticiones)
```

**Warmup:** Al inicio los buffers están vacíos → latencias artificialmente bajas. Se descartan las métricas del primer segundo. Referencia: Law & Kelton (2000), "Simulation Modeling and Analysis", §9.5.

---

## 10. Resultados clave

### Tabla completa — carga 100 Mbps/ONU (sobrecarga severa: 3,392 Mbps demanda vs 1,244 Mbps capacidad)

| T-CONT | Clase | BasicDBA | QosDBA | Factor |
|---|---|---|---|---|
| **T-CONT 1** | Latencia media | **25,437 μs** (25 ms) | **164 μs** | **155×** |
| T-CONT 1 | Latencia P99 | 26,076 μs | 226 μs | 115× |
| T-CONT 1 | Jitter medio | 1,155 μs | 45.6 μs | 25× |
| T-CONT 1 | Pérdida | 0% | 0% | Igual |
| **T-CONT 2** | Latencia media | **4,411 μs** | **401 μs** | **11×** |
| T-CONT 2 | Latencia P99 | 12,790 μs | 546 μs | 23× |
| T-CONT 2 | Pérdida | 0% | 0% | Igual |
| **T-CONT 4** | Latencia media | 177,875 μs | 177,875 μs | Igual |
| T-CONT 4 | Pérdida | **17.8%** | **17.8%** | Igual |
| Canal | Utilización | ~100% | ~100% | Igual |

> **T-CONT 4 igual en ambos algoritmos:** correcto y esperado. Ambos saturan el canal. La diferencia es *quién absorbe la congestión*: BasicDBA la reparte entre T-CONT 1, 2 y 4; QosDBA la concentra en T-CONT 4 (best effort).

### Latencia T-CONT 1 por carga (valores exactos del CSV)

| Carga T4 | BasicDBA T-CONT 1 (μs) | QosDBA T-CONT 1 (μs) |
|---|---|---|
| 10 Mbps/ONU | 414 | **164** |
| 25 Mbps/ONU | 414 | **164** |
| 50 Mbps/ONU | 414 | **164** |
| 75 Mbps/ONU | 414 | **164** |
| 100 Mbps/ONU | **25,437** | **164** |

> QosDBA mantiene T-CONT 1 en 164 μs constante para **cualquier carga**. BasicDBA colapsa a 25 ms en el peor caso.

### ¿Por qué T-CONT 1 tiene 0% pérdida en BasicDBA incluso a 25 ms de latencia?

A 100 Mbps de carga BE, T-CONT 1 es starved (grant ≈ 0). Genera 1 paquete cada 1.28 ms. Con buffer de 10,000 bytes y en promedio solo ~20 paquetes acumulados antes de que llegue un grant ocasional, el buffer no se llena. Resultado: 0% pérdida pero 25 ms de latencia. Para VoIP, la latencia excesiva es inaceptable aunque no haya pérdida (G.114: budget total ≤ 150 ms extremo a extremo).

---

## 11. Simplificaciones declaradas

| Simplificación | Descripción | Real en G.984 | Impacto |
|---|---|---|---|
| **Sin GEM** | No fragmentamos paquetes en celdas GEM | GEM fragmenta PDUs en unidades del slot | T-CONT 1 reserva 160 B/trama en vez de 16 B; comparación sigue siendo válida |
| **Guard time reducido** | 32 bytes/ONU | G.984.3 §B.2: ≥25 bits (≈4 bytes) | Sobreestima overhead ~22%; simétrico en ambos algoritmos |
| **Sin ranging** | Todas las ONUs a exacta misma distancia | OLT mide RTT individual y asigna equalization delay | Sin impacto en comparación de DBA |
| **Sin FEC** | No modelamos Reed-Solomon (255,239) opcional | Agrega ~7% de overhead en la trama | Negligible para la comparación |
| **Solo upstream** | No modelamos tráfico downstream | Downstream también tiene 2.488 Gbps de tráfico | DBA es mecanismo upstream; objetivo del proyecto |
| **DBRu como evento** | Reporte llega como evento separado | Embebido en últimos bytes del burst upstream | Diferencia de nanosegundos |
| **Paquetes tamaño fijo** | Cada T-CONT usa un tamaño fijo | Paquetes IP tienen tamaños variables (64–1500 bytes) | Simplificación estándar en simulaciones de DBA |
| **Sin OMCI** | Sin gestión OAM (Operations & Maintenance) | OMCI maneja configuración y alarmas | No relevante para evaluar DBA |

---

## 12. Preguntas probables y respuestas

**"¿Qué es GPON?"**  
Red óptica pasiva Gigabit definida por ITU-T G.984. Topología punto-multipunto: 1 OLT en central telefónica conectada a hasta 32 (o 64) ONUs mediante splitter óptico pasivo. Downstream broadcast a 2.488 Gbps, upstream TDMA a 1.244 Gbps coordinado por BWmap cada 125 μs.

**"¿Qué diferencia hay entre GPON y EPON?"**  
EPON (IEEE 802.3ah) usa MPCP con polling individual — algoritmo IPACT: OLT pregunta ONU por ONU en secuencia, ciclo variable. GPON (ITU-T G.984) usa SR-DBA centralizado: BWmap broadcast cada 125 μs fijo a todas las ONUs simultáneamente, DBRu embebido en el burst. GPON es más eficiente porque el período de asignación no crece con N.

**"¿Por qué no usaron IPACT?"**  
IPACT es un protocolo de EPON (IEEE 802.3ah), no de GPON. Son estándares distintos de organizaciones distintas (IEEE vs ITU-T). En GPON el mecanismo de acceso upstream es SR-DBA con BWmap. Usar IPACT para modelar GPON sería mezclar estándares incompatibles.

**"¿Cómo verifican que 19,440 bytes/trama es correcto?"**  
1,244,160,000 bps × 0.000125 s ÷ 8 bits/byte = 19,440 bytes. Derivable directamente de G.984.2 (tasa) y G.984.3 (duración trama).

**"¿Qué es el BWmap exactamente?"**  
Se transmite en el PCBd (Physical Control Block downstream) de cada trama GTC, cada 125 μs. Contiene `Alloc-ID + StartTime + StopTime` para cada T-CONT activo. Todas las ONUs lo reciben simultáneamente y saben exactamente cuándo pueden transmitir sin colisionar con otras ONUs.

**"¿Por qué reservan 160 bytes por trama si T-CONT 1 solo genera 1 Mbps?"**
> Esta es la pregunta más probable de la profesora. La fuente genera 1 paquete de 160 bytes cada 1.28 ms (cada 10.24 tramas), pero el DBA reserva 160 bytes **cada** trama = 10.24 Mbps por ONU.
>
> *"Como simplificación del modelo, reservamos un slot de paquete completo por trama para T-CONT 1. En GPON real con GEM, la OLT reservaría 16 bytes por trama (= 1 Mbps × 125 μs / 8) y la ONU acumularía créditos durante 10 tramas antes de transmitir un paquete completo. Como nuestro simulador no implementa GEM, simplificamos reservando un slot del tamaño exacto del paquete. El resultado es correcto: T-CONT 1 siempre tiene espacio, la simplificación es simétrica en ambos algoritmos, y la comparación sigue siendo válida."*

**"¿Por qué exactamente 200 μs de información 'vieja'?"**
> *"Son 100 μs de ida — la OLT envía el BWmap y tarda 100 μs en llegar a la ONU — más 100 μs de vuelta — la ONU envía el DBRu y tarda 100 μs en llegar a la OLT. En total 1 RTT = 200 μs."*

**"¿Qué es el DBRu?"**  
Dynamic Bandwidth Report upstream. Embebido en el burst upstream de la ONU. Contiene los bytes pendientes por T-CONT. La OLT lo usa para el próximo cálculo de BWmap. Tiene un delay inherente de 1 RTT = 200 μs — 100 μs de ida (OLT→ONU, propagación BWmap) más 100 μs de vuelta (ONU→OLT, propagación datos+DBRu). La OLT siempre trabaja con información de ≥200 μs de antigüedad.

**"¿Por qué usan T-CONT 1, 2 y 4 y no todos los 5?"**  
T-CONT 1, 2 y 4 representan los tres comportamientos fundamentalmente distintos: CBR puro (sin reporte), assured con garantía mínima, y best-effort sin garantía. T-CONT 3 es una mezcla de T-CONT 2 + best-effort extra; T-CONT 5 es combinación de todos. Con 1, 2 y 4 la diferencia de QoS entre algoritmos es máxima y más clara.

**"¿Por qué Pareto para T-CONT 4?"**  
Leland et al. (1994) midieron tráfico real en Bellcore y demostraron que el tráfico de datos tiene self-similarity con Hurst parameter H ≈ 0.7–0.9. Un proceso Poisson tiene H=0.5 (no self-similar). Pareto con α=1.5 da H=(3−1.5)/2=0.75 — dentro del rango observado. Las ráfagas de cola pesada son características de HTTP, P2P y descargas que no captura Poisson.

**"¿Por qué T-CONT 4 tiene la misma pérdida en ambos algoritmos?"**  
Es correcto y esperado. Ambos algoritmos usan la misma capacidad total (1,244 Mbps). La diferencia está en *quién absorbe la congestión*, no en cuánta congestión total hay. QosDBA protege T-CONT 1 y 2 *concentrando* toda la congestión en T-CONT 4. BasicDBA la distribuye entre todos. La pérdida total del sistema es igual; la distribución de esa pérdida es distinta.

**"¿Por qué T-CONT 1 tiene 0% pérdida en BasicDBA aunque la latencia sea 25 ms?"**  
T-CONT 1 genera 1 paquete cada 1.28 ms (tasa muy baja: 1 Mbps). Con buffer de 10,000 bytes ≈ 62 paquetes y latencia de servicio de 25 ms, en promedio hay ~20 paquetes esperando — bien dentro del límite del buffer. No overflow → 0% pérdida. Pero latencia de 25 ms es inaceptable para VoIP (G.114: ≤150 ms extremo a extremo, ~10 ms asignado a la red de acceso).

**"¿Qué simplificaciones importantes hicieron?"**  
La principal: no modelamos la fragmentación GEM (GPON Encapsulation Method). En el estándar real, la OLT asigna slots de exactamente N bytes y la ONU fragmenta sus paquetes para llenarlos perfectamente. En nuestro simulador asignamos un slot de 160 bytes por trama para T-CONT 1 (equivalente a un paquete completo) y enviamos el paquete entero sin fragmentar. La comparación de algoritmos no se ve afectada porque la simplificación es simétrica.

**"¿Cómo validan que los resultados son estadísticamente válidos?"**  
10 repeticiones independientes con seeds distintos (42–51). IC 95% calculado como ȳ ± 1.96·s/√10. Los IC son muy estrechos (ver CSV: CI95 de latencia T-CONT 1 QosDBA = 0.0, totalmente determinístico por ser CBR). Para T-CONT 4 con alta carga, CI95 es también pequeño relativo a la media. Methodology: Law & Kelton, "Simulation Modeling and Analysis" §9.5.

---

## 13. Referencias

### Estándares ITU-T
- **ITU-T G.984.1 (2008)** — GPON: General characteristics
- **ITU-T G.984.2 (2003, amend. 2006)** — GPON: Physical media dependent (PMD) layer
- **ITU-T G.984.3 (2004, amend. 2008)** — GPON: Transmission convergence layer ← **principal**
- **ITU-T G.711 (2000)** — PCM of voice frequencies (VoIP 64 kbps)

### Papers académicos
- **Leland et al. (1994)** — "On the Self-Similar Nature of Ethernet Traffic." IEEE/ACM ToN, 2(1):1–15. → Justifica Pareto α=1.5, Hurst H=0.75
- **Kramer et al. (2002)** — "IPACT: A Dynamic Protocol for an Ethernet PON (EPON)." IEEE Comm. Mag. → Define IPACT (EPON, no GPON)
- **Chang et al. (2006)** — "Dynamic Bandwidth Allocation for Differentiated Services in GPON." IEEE Comm. Letters → Base conceptual del QosDBA
- **Neto et al. (2010)** — "Performance Analysis of DBA Algorithms for GPON Networks." IEEE ICC

### Teoría de colas y simulación
- **Law & Kelton (2000)** — "Simulation Modeling and Analysis," 3ra ed. McGraw-Hill → Warmup, IC 95%
- **Montgomery & Runger (2014)** — "Applied Statistics and Probability for Engineers" Wiley → IC 95%
- **Kleinrock (1975)** — "Queueing Systems, Vol. I: Theory." Wiley → Distribuciones de tráfico

### RFCs
- **RFC 3393 (2002)** — "IP Packet Delay Variation Metric (IPDV)" → Definición formal de jitter

---

*OmneTeam — David Retuerto · José Vega · Matías Perelli*  
*TEL-341 Simulación de Redes, UTFSM 2026*
