# Guion — Presentador B (slides 8-14)

**Tu parte:** cómo funciona el simulador por dentro — el ciclo completo de la
red, la arquitectura, las entidades, la FEL, el loop del motor y la generación
de tráfico. Es la parte más técnica y abstracta. Requiere entender DES a fondo.

**Transición de entrada:** recibes la posta de A al final del slide 7.
**Transición de salida:** al terminar slide 14, presentas a C: "Ahora [nombre]
nos muestra los resultados de los 9 escenarios que corrimos."

---

## Lo que hay que saber antes de empezar

**La pregunta que más te van a hacer:** "¿cómo simulan el proceso de decisión?"

Respuesta corta: el proceso de decisión es literalmente **una llamada a función**
que ocurre como evento en el motor cada 125 µs (broadcast) o una vez por ONU
por ciclo (polling):

```
bwmap = dba.allocate(onu_reports, total_capacity=38880, ...)
```

Eso es todo. Inputs = reportes de buffer de cada ONU + bytes disponibles.
Output = cuánto le toca a cada ONU y T-CONT. La consecuencia se mide cuando
el paquete llega: `latencia = engine.now - pkt["creation_time"]`.

**Lo que NO usamos:** ningún framework de simulación. Solo Python puro y
`heapq` de la librería estándar para la cola de prioridad.

---

## Slide 8: ¿Cómo funciona el sistema? Un ciclo completo

### Broadcast (GIANT y QosDBA) — cada 125 µs exactos

1. La OLT mira los últimos reportes recibidos de cada ONU: cuántos bytes tiene
   cada una en cola por T-CONT (eso es el DBRu).
2. Ejecuta el algoritmo DBA → calcula el BWmap: cuántos bytes le asigna a cada
   ONU y cada T-CONT.
3. Manda el BWmap por fibra → llega a las 8 ONUs con 100 µs de delay.
4. Cada ONU vacía sus colas en orden de prioridad hasta agotar su asignación.
5. Junto con los datos, la ONU incluye un nuevo DBRu (cuánto le queda en cola).
6. Los datos llegan a la OLT 100 µs después → mide latencia, guarda el reporte.
7. A los 125 µs del paso 1, el ciclo se reinicia con los reportes frescos.

**En código (simulator/olt.py):**
```
Evento EVT_OLT_BWMAP → on_generate_bwmap()
  ├─ bwmap = dba.allocate(onu_reports, total_capacity=38880, ...)
  │    Inputs:  {0: {1: 320B, 2: 5000B, 4: 120000B}, 1: ..., ...}
  │    Output:  {0: {1: 160B, 2: 4000B, 4: 12000B}, 1: ..., ...}
  ├─ Para cada ONU: agenda EVT_ONU_RECV_BWMAP con delay=100µs
  └─ Agenda el próximo EVT_OLT_BWMAP con delay=125µs
```

### Polling (IPACT) — una ONU a la vez

1. OLT manda GATE a ONU 0 con su asignación (según último reporte conocido).
2. Calcula cuánto tarda esa ONU en transmitir: `grant_bytes × 8 / 2.48832 Gbps`.
3. Espera ese tiempo + 1 µs de guard → atiende a ONU 1. Repite hasta ONU 7.
4. Un ciclo completo = recorrer las 8 ONUs.
5. Si una ONU acumuló paquetes mientras esperaba, los reporta en el próximo
   GATE → latencia acumulada.

**En código (simulator/olt_ipact.py):**
```
Evento EVT_OLT_SEND_GATE(onu_id=3) → on_send_gate()
  ├─ allocation = dba.allocate_onu(onu_id=3, report, b_max=38880)
  │    → {1: 160B, 2: 4000B, 4: 34720B}  (suma ≤ 38.880)
  ├─ grant_time = bytes × 8 / 2.48832 Gbps ≈ 112 µs
  ├─ Agenda EVT_ONU_RECV_GATE(onu_id=3) con delay=100µs
  └─ Agenda EVT_OLT_POLL_NEXT con delay=grant_time + 1µs (guard)
       → avanza puntero: 3+1=4 → agenda GATE para ONU 4
```

**Diferencia clave en código:** en broadcast, el próximo BWmap es siempre
`now + 125µs`, sin importar nada. En polling, el próximo gate depende de
cuánto se le otorgó a la ONU anterior — por eso el ciclo es variable.

### Cómo se mide la latencia

Cuando un paquete llega a la OLT (`EVT_OLT_RECV_DATA`):
```python
latency = engine.now - pkt["creation_time"]
```
`creation_time` se grabó cuando el paquete llegó al buffer de la ONU. Esa
resta es la latencia end-to-end. Se compara con el SLA del T-CONT para
calcular el % de cumplimiento.

---

## Slide 9: Arquitectura del simulador

Lo que más le importa a la profesora: **no se usó ningún framework**. Todo
está implementado en Python puro usando solo `heapq` de la librería estándar.

Cada módulo tiene una responsabilidad única:

| Módulo | Qué hace |
|---|---|
| `simulator/engine.py` | Motor DES: heap de eventos + tabla de handlers. El corazón del simulador. |
| `simulator/olt.py` | OLT broadcast: genera BWmap cada 125 µs exactos |
| `simulator/olt_ipact.py` | OLT polling: round-robin ONU por ONU |
| `simulator/onu.py` | ONU: 3 buffers T-CONT, generación de tráfico, DBRu |
| `simulator/dba_giant.py` | Algoritmo GIANT: reserva fija + contadores SI |
| `simulator/dba_qos.py` | Algoritmo QosDBA: prioridad estricta T1>T2>T4 |
| `simulator/dba_ipact.py` | Algoritmo IPACT: limited service, sin distinción T-CONT |
| `metrics/collector.py` | Acumula latencias, bytes, utilización; calcula resumen |

El flujo de datos: ONU genera tráfico → encola en buffer → OLT genera BWmap
(dba.allocate) → ONU recibe asignación y transmite → datos llegan a OLT
(se mide latencia) → ONU envía DBRu → OLT actualiza reportes → siguiente BWmap.

---

## Slide 10: Estado del sistema y entidades

Este slide muestra los objetos que existen en memoria durante la simulación.

- **OLT**: guarda el último DBRu de cada ONU (`_onu_reports: dict`) y el número
  de trama actual. Es todo lo que el DBA necesita para decidir.

- **ONU**: tiene 3 objetos TCont (uno por tipo de tráfico) y se comunica con
  la OLT únicamente a través del motor de eventos.

- **TCont**: es el corazón de la ONU. Contiene:
  - Un buffer FIFO con los paquetes esperando transmisión.
  - Un generador de tráfico (CBR / Poisson / Pareto).
  - Contadores de drops por buffer overflow.

- **Paquete**: objeto mínimo. Solo guarda: ONU de origen, tipo T-CONT, tamaño
  en bytes, y `creation_time` (el único campo que se necesita para calcular
  la latencia al llegar).

**El "estado del sistema" en cualquier instante t:** la ocupación de los
24 buffers (8 ONUs × 3 T-CONTs), los últimos reportes que la OLT tiene de
cada ONU, y la posición del algoritmo (número de trama si es broadcast, índice
de ONU si es polling).

---

## Slide 11: Eventos futuros (FEL) y condición de término

**La FEL (Future Event List)** es la cola de prioridad del motor. Todos los
eventos pendientes viven ahí ordenados por tiempo. El motor siempre saca el
de menor tiempo primero.

**Los 6 tipos de evento del simulador:**

| Evento | Quién lo agenda | Qué hace |
|---|---|---|
| `ONU_GENERATE_TRAFFIC` | Sí mismo (self-scheduling) | Genera un paquete y agenda el siguiente |
| `OLT_GENERATE_BWMAP` | La OLT cada 125 µs | Calcula asignación y envía a todas las ONUs |
| `ONU_RECEIVE_BWMAP` | OLT con delay 100 µs | ONU transmite según su asignación |
| `OLT_SEND_GATE` / `POLL_NEXT` | Equivalente IPACT, uno por ONU | Polling round-robin |
| `OLT_RECEIVE_DATA` | ONU con delay 100 µs | OLT recibe burst, mide latencia |
| `OLT_RECEIVE_REPORT` | ONU junto con datos | OLT actualiza reporte de esa ONU |

**Condición de término:** el reloj simulado supera 10 s. El motor sale del
loop y se calculan las métricas. El primer segundo (warmup) se ignora en los
cálculos para descartar el régimen transitorio de arranque — al principio
todos los buffers están vacíos y los reportes están inicializados en cero.

**Posible pregunta:** "¿Por qué 10 segundos?" → Es suficiente para que el
sistema llegue a régimen estacionario y acumule miles de muestras por T-CONT.
Más tiempo no cambia las conclusiones; menos tiempo introduce efectos
transitorios.

**Posible pregunta:** "¿Qué es el warmup y por qué 1 segundo?" → Al arrancar,
todas las colas están vacías y la OLT no tiene reportes reales. Las primeras
métricas reflejan ese estado artificial. Después de ~200-300 ms simulados el
sistema llega a régimen. Descartar 1 s es conservador — cubre bien el
transitorio.

---

## Slide 12: El loop del simulador

El loop del motor en prosa:

"El simulador arranca, carga la configuración, crea la OLT y las 8 ONUs, y
agenda los primeros eventos de generación de tráfico. Después entra en el
loop: saca el evento con el tiempo más chico de la cola, avanza el reloj a
ese tiempo — el reloj **no avanza de a poco, salta directo al siguiente
evento** — y ejecuta el handler correspondiente. Ese handler puede agendar
nuevos eventos. El loop termina cuando la cola está vacía o el tiempo supera
el límite."

En código, es solo esto:
```python
while heap no vacío:
    evt = heappop(heap)        # saca el de menor tiempo
    if evt.time > until: break
    now = evt.time             # el reloj salta aquí
    handlers[evt.type](evt)    # ejecuta la acción
```

**Por qué es eficiente:** en 10 segundos de red real hay ~10 × 10⁹ nanosegundos.
Pero el motor solo procesa ~1.4 millones de eventos — únicamente los instantes
en que algo relevante ocurre. No hay que simular "cada nanosegundo".

---

## Slide 13: El motor de eventos discretos

El pseudocódigo muestra exactamente lo mismo que el loop, formalizado. La
línea clave es `reloj_actual = evento.tiempo`: el reloj no es un contador que
va de a uno, es una variable que salta al siguiente instante relevante.

**Posible pregunta:** "¿Cómo garantizan que dos eventos simultáneos se procesan
en orden determinístico?" → Cada evento tiene un campo `seq` (número de
secuencia incremental) además del tiempo. La comparación es `(time, seq)`.
Si dos eventos tienen el mismo tiempo, se procesa primero el que se agendó
antes (menor `seq`). Con la misma seed, el resultado es siempre idéntico
bit a bit.

**Posible pregunta:** "¿El motor puede simular eventos en paralelo?" → No, y
no hace falta. Los eventos discretos son por definición secuenciales — ocurren
en instantes distintos. El paralelismo en los resultados viene de correr
réplicas distintas en paralelo (eso lo hace `run_experiments.py` con
`multiprocessing`).

**Posible pregunta:** "¿Por qué Python y no C++?" → Para un simulador de esta
escala (~1.4M eventos, ~5 min de CPU total), Python es suficiente. La ventaja
es velocidad de desarrollo y legibilidad, que facilita verificar que el código
es correcto. Si la escala fuera 100× mayor, C++ sería necesario.

**Posible pregunta:** "¿Qué complejidad tiene la cola de eventos?" → Min-heap
con `heapq`: insertar y extraer en O(log n), mirar el mínimo en O(1). Con
n ≈ 50.000 eventos en cola simultáneamente, log₂(50.000) ≈ 16 — muy barato.

---

## Slide 14: Generación de tráfico: self-scheduling

**El patrón self-scheduling:** cada vez que se genera un paquete, ese mismo
handler agenda cuándo viene el próximo. No hay un proceso separado que
"maneje" la fuente — la fuente se maneja sola indefinidamente.

```python
on_generate_traffic(evt):
    pkt = Paquete(creation_time=now, tcont=tc, size=...)
    tcont.enqueue(pkt)                          # poner en buffer
    siguiente = traffic_gen.next_interval()     # CBR / Poisson / Pareto
    engine.schedule(siguiente, ONU_GENERATE_TRAFFIC, ...)  # el siguiente
```

**Los tres generadores en detalle:**

**CBR (T-CONT1 / VoIP):**
`next_interval()` devuelve siempre 1.28 ms = 160 bytes × 8 bits / 1 Mbps.
Es perfectamente periódico — no hay aleatoriedad. Todos los eventos de T-CONT1
de todas las ONUs son determinísticos y reproducibles sin importar la seed.

**Poisson (T-CONT2 / Video):**
`next_interval()` = `random.expovariate(1/media)`.
Distribución exponencial: sin memoria (propiedad Markoviana), varianza finita.
El tiempo al próximo paquete no depende del anterior.

**Pareto (T-CONT4 / Datos):**
`next_interval()` = `random.paretovariate(1.5) × escala`.
Cola pesada: la mayoría de los intervalos son cortos (ráfagas), pero
ocasionalmente hay silencios 10× o 100× el promedio. Eso crea picos de carga
que estresan el algoritmo DBA — si el tráfico fuera uniforme, todos los
algoritmos funcionarían igual y la comparación sería trivial.

**Transición a C:** "Ahora [nombre] nos muestra los experimentos y resultados
de correr estos 3 algoritmos bajo las 3 cargas."

---

## Tus preguntas más probables

**"¿Cómo simulan el proceso de decisión del DBA?"**
→ Es una llamada a función: `bwmap = dba.allocate(onu_reports, capacity, ...)`.
Inputs = estado de las colas reportado por las ONUs. Output = asignación por
ONU y T-CONT. Eso es el DBA — el motor lo ejecuta como un evento más.

**"¿Qué es la FEL?"**
→ Future Event List. La cola de prioridad donde viven todos los eventos
pendientes, ordenados por tiempo. El motor siempre procesa el de menor tiempo.

**"¿Cómo garantizan reproducibilidad?"**
→ `random.seed(seed)` al inicio de cada réplica. El PRNG de Python es
determinístico: misma seed = misma secuencia de números aleatorios = mismos
eventos = mismo resultado.

**"¿Por qué DES y no simulación de tiempo continuo?"**
→ Porque los eventos en esta red ocurren en instantes específicos (llegada de
paquete, inicio de trama, fin de transmisión). DES los modela exactamente sin
aproximaciones numéricas. Además es eficiente: solo se procesan ~1.4M eventos
en vez de simular cada nanosegundo.

**"¿Por qué no usaron SimPy o OMNeT++?"**
→ Requisito explícito del curso: el motor de eventos debe ser código propio.
Además, implementarlo desde cero obliga a entender exactamente qué ocurre.

**"¿Cómo manejan eventos con el mismo timestamp?"**
→ Cada evento tiene un campo `seq` incremental. La comparación es `(time, seq)`.
Mismo tiempo → se procesa primero el de menor `seq` (el que se agendó antes).

---

## Números que debes tener frescos

| Concepto | Valor |
|---|---|
| Upstream XG-PON1 | 2.48832 Gbps |
| Trama | 125 µs |
| Bytes por trama | 38.880 bytes |
| ONUs | 8 |
| Delay propagación (ida) | 100 µs |
| Intervalo T-CONT1 (CBR) | 1.28 ms |
| Eventos procesados por corrida | ~1.4 millones |
| Duración simulada | 10 s (1 s warmup) |
| Tipos de evento | 6 (BWMAP, RECV_BWMAP, GEN_TRAFFIC, RECV_DATA, RECV_REPORT, GATE/POLL) |
| Ciclo IPACT saturado | 1008 µs = 8 × 126 µs |
| Ciclo broadcast | siempre 125 µs |
