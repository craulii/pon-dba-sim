# Guion interno — Presentación XG-PON DBA

## OmneTeam — esto NO es un libreto

No es para leer en voz alta. Es para repasar antes de la presentación y tener
el contexto completo. Incluye el "por qué" detrás de cada decisión, la
explicación técnica de cómo funciona el simulador por dentro, y las preguntas
más probables de la profesora.

---

## PRIMERO LO PRIMERO: ¿qué estamos simulando?

**Una sola oración:** estamos simulando el proceso de decisión que ocurre en
una central de fibra óptica cada 125 microsegundos — quién puede transmitir
y cuánto.

**Más largo:** la red XG-PON1 tiene un canal de subida compartido de 2.48 Gbps.
Cada 125 µs ese canal se "recarga" con 38.880 bytes disponibles. Alguien tiene
que decidir cómo repartirlos entre las 8 ONUs y sus 3 tipos de servicio.
Eso es el DBA. **No simulamos el tráfico** (los paquetes que llegan a los
buffers son la carga de trabajo que complica la decisión). **No simulamos la
fibra** (el canal siempre funciona igual). Lo que simulamos es el algoritmo
que toma esa decisión, y medimos la consecuencia: si el VoIP llega en menos
de 2 ms o no.

---

## Slide 1-2: Portada y Agenda

Nada especial. Si preguntan cuánto duró el proyecto: el semestre completo de
TEL-341. Si preguntan qué framework usaron: ninguno, todo desde cero en Python
puro — eso es un requisito explícito del curso.

---

## Slide 3: Motivación

Lo que hay que dejar claro: el problema no es la fibra, es el acceso al canal
upstream.

- **Downstream** (OLT → ONUs): la señal óptica llega a todos al mismo tiempo,
  como la radio. No hay contención.
- **Upstream** (ONUs → OLT): todas comparten el mismo cable físico después del
  splitter. Solo una puede transmitir a la vez porque hay un solo receptor en
  la OLT. Si dos transmiten simultáneo, las señales ópticas se suman y el
  receptor no puede distinguirlas (colisión).

La pregunta del proyecto es concreta: si por ese canal compartido pasan una
llamada de voz (que no puede esperar más de 2 ms) y una descarga pesada (que
puede esperar lo que sea), ¿cómo se decide quién transmite primero, y eso
afecta a la voz?

**Posible pregunta:** "¿Por qué no puede transmitir más de una ONU a la vez?"
→ Porque es TDMA: time division, un slot de tiempo por transmisor. Más de uno
simultáneo causaría colisión óptica — las señales se interfieren a nivel
físico en el splitter.

---

## Slide 4: ¿Qué estamos simulando?

Esta diapositiva es la hoja de ruta del proyecto en un vistazo.

- **Sistema**: red XG-PON1 con 8 ONUs, cada una generando 3 tipos de tráfico
  simultáneo por ONU.
- **Variable independiente**: el algoritmo DBA (cuál de los 3 usamos).
- **Variable de carga**: cuánto tráfico de datos (T-CONT4) genera cada ONU
  (200, 400 u 800 Mbps/ONU).
- **Variable dependiente (salida)**: latencia, cumplimiento SLA, throughput,
  tasa de pérdida.

Lo que diferencia a los 3 algoritmos es **cómo deciden** quién transmite y
cuánto, no la velocidad del canal (eso es siempre el mismo XG-PON1).

**El bloque al pie del slide** dice exactamente: no simulamos el tráfico en
sí, sino el proceso de decisión que ocurre cada 125 µs. El tráfico es la
carga que lo complica; los algoritmos DBA son las estrategias; la consecuencia
medida es si VoIP llega antes de 2 ms.

---

## Slide 5: La red que simulamos: XG-PON1

**Por qué XG-PON1 y no GPON:** XG-PON1 (ITU-T G.987) es el sucesor directo
de GPON (ITU-T G.984). La diferencia clave: el upstream sube de 1.244 Gbps a
2.488 Gbps. La trama sigue siendo 125 µs, así que caben el doble de bytes
(38.880 vs 19.440).

**Por qué 8 ONUs:** para que el experimento se concentre en el algoritmo DBA,
no en diferencias entre usuarios. 8 ONUs idénticas dan carga simétrica.

**Por qué 20 km:** clase de alcance N1 del estándar G.987.2. El delay de
propagación de 100 µs viene de 5 µs/km × 20 km (ida). En el simulador, cuando
la OLT manda el BWmap, agenda el evento de recepción en la ONU con 100 µs de
delay. Lo mismo en el camino de vuelta.

**Posible pregunta:** "¿Qué es el splitter pasivo?" → Un divisor óptico que
reparte la señal de fibra sin electrónica, simplemente dividiendo la luz. Es
pasivo porque no consume energía ni toma decisiones. En el simulador no tiene
modelo propio — el delay de propagación ya lo incluye.

---

## Slide 6: Tráfico simulado y SLA

### Los T-CONTs

Un T-CONT es simplemente una cola de paquetes separada por tipo de servicio
dentro de cada ONU. En vez de mezclar todos en una sola cola, cada ONU tiene
3 colas independientes con sus propios generadores de tráfico:

- **T-CONT1 (VoIP)**: paquetes de 160 bytes a intervalos exactamente iguales
  (CBR = Constant Bit Rate, 1 Mbps fijo). Determinístico: no hay aleatoriedad.
  Intervalo = 160 bytes × 8 bits / 1 Mbps = 1.28 ms entre paquetes.

- **T-CONT2 (Video)**: paquetes de 1000 bytes con llegadas distribuidas como
  Poisson (distribución exponencial de intervalos, 40 Mbps medio). Sin memoria:
  el tiempo al próximo paquete no depende del anterior.

- **T-CONT4 (Datos)**: paquetes de 1400 bytes con distribución Pareto α=1.5.
  Ver explicación de "cola pesada" abajo.

### Qué es "cola pesada" (Pareto α=1.5)

La distribución Pareto con α=1.5 tiene una cola que no decae rápido. En la
práctica: la mayoría de los intervalos entre paquetes son muy cortos (llegan
en ráfaga), pero de vez en cuando hay un silencio extremadamente largo. Esto
modela el tráfico real de internet, que llega en "rachas" (burst), no uniforme.

Comparación con Poisson: con Poisson cada intervalo es independiente y sin
memoria, la varianza es finita. Con Pareto α=1.5, la varianza es **infinita**
matemáticamente — hay probabilidad no despreciable de silencios de cualquier
longitud. Por eso se llama "cola pesada": la función de distribución acumulada
cae despacio, no exponencialmente.

En el simulador: `random.paretovariate(1.5)` devuelve un número ≥ 1; se
escala al intervalo medio según la carga pedida. El intervalo real puede ser
10× o 100× el promedio con probabilidad no trivial.

### El SLA

SLA aquí = cota máxima de latencia. Un paquete que llega tarde igual se
entrega, pero cuenta como violación en la métrica `sla_compliance_pct`.

- T-CONT1: ≤ 2 ms → la más importante, fue pedido explícito.
- T-CONT2: ≤ 20 ms → rango típico para video interactivo, meta del equipo.
- T-CONT4: ≤ 500 ms → cota laxa para diagnóstico, el estándar no tiene req.

**Posible pregunta:** "¿Un paquete fuera de SLA se descarta?" → No. El
descarte ocurre solo cuando el buffer de la ONU se llena (buffer overflow).
El SLA es solo una métrica de calidad, no una acción en la red.

---

## Slide 7: Los 3 algoritmos comparados

### 2 mecanismos, 3 algoritmos — qué significa eso

Hay **dos formas** de coordinar el canal:

1. **Broadcast**: la OLT calcula la asignación para las 8 ONUs de una sola
   vez y la manda en un solo mensaje (BWmap) cada 125 µs exactos. Todos
   reciben su asignación al mismo tiempo. Lo usan: **GIANT** y **QoSDBA**.

2. **Polling**: la OLT atiende las ONUs una por una, en ronda (round-robin).
   Le manda un GATE a la ONU 0, espera que "le llegue el turno" a la ONU 1,
   etc. El ciclo completo dura lo que tarden las 8 en recibir su grant y
   transmitir. Lo usa: **IPACT**.

Por eso hay 2 mecanismos pero 3 algoritmos: GIANT y QoSDBA usan broadcast,
pero deciden *cómo repartir el ancho de banda* de formas distintas:

- **GIANT**: reserva T-CONT1 siempre (incondicionalmente), y para T-CONT2/T4
  usa contadores de turno (SImax=8 tramas para T2, SImin=32 para T4). Origen:
  GPA/SPA, algoritmo nativo de GPON/XG-PON según G.987.
- **QoSDBA**: prioridad estricta T-CONT1 > T-CONT2 > T-CONT4, sin contadores.
  Variante simplificada del DBA con QoS descrito en G.984.
- **IPACT**: otorga el mínimo entre lo que la ONU reportó y un máximo fijo
  (b_max = 38.880 bytes), sin diferenciar por tipo de T-CONT dentro de la ONU.
  Adaptado de EPON (no nativo XG-PON) — se usa como referencia de benchmark.

**Por qué incluir IPACT si es de EPON:** se usa como referencia de comparación
explícita para mostrar la diferencia de mecanismo. La profesora sabe que es
de EPON; está documentado así en el informe.

### Cómo funciona el ciclo máximo de IPACT

Con 8 ONUs, cada una puede recibir hasta b_max = 38.880 bytes = 125 µs de
transmisión. Más 1 µs de guard time por ONU para evitar solapamiento:

`ciclo_máximo = 8 × (125 µs + 1 µs) = 8 × 126 µs = 1008 µs`

Cuando el canal está saturado (más demanda que capacidad), cada ONU siempre
recibe su grant máximo → el ciclo siempre dura exactamente 1008 µs.

---

## Slide 8: ¿Cómo funciona el sistema? Un ciclo completo

### Broadcast en lenguaje natural (GIANT y QoSDBA)

Cada 125 µs exactos:
1. La OLT mira los últimos DBRu recibidos de cada ONU (cuántos bytes tiene
   cada una en cola por T-CONT).
2. Calcula el BWmap: ejecuta el algoritmo DBA y decide cuántos bytes le
   asigna a cada ONU y cada T-CONT.
3. Manda el BWmap por fibra → llega a las 8 ONUs 100 µs después.
4. Cada ONU vacía sus colas en el orden de prioridad hasta agotar su asignación.
5. Junto con los datos, la ONU incluye un DBRu (reporte de cuánto queda en cola).
6. Los datos llegan a la OLT 100 µs después → mide latencia, guarda el reporte.
7. A los 125 µs del paso 1, el ciclo se reinicia con los reportes frescos.

### Broadcast en código (lo que realmente pasa en simulator/olt.py)

```
Evento EVT_OLT_BWMAP → on_generate_bwmap()
  ├─ bwmap = dba.allocate(onu_reports, total_capacity=38880, ...)
  │    Inputs:  onu_reports = {0: {1: 320B, 2: 5000B, 4: 120000B}, 1: ..., ...}
  │    Output:  bwmap       = {0: {1: 160B, 2: 4000B, 4: 12000B}, 1: ..., ...}
  ├─ Para cada ONU: agenda EVT_ONU_RECV_BWMAP con delay=100µs
  └─ Agenda el próximo EVT_OLT_BWMAP con delay=125µs
```

Eso es literalmente todo. La "decisión" = una llamada a `dba.allocate()`.
La asignación es el resultado que devuelve esa función.

### Polling en lenguaje natural (IPACT)

La OLT atiende una ONU a la vez, en ronda:
1. OLT manda GATE a ONU 0 con su asignación (según último reporte conocido).
2. Calcula cuánto tarda esa ONU en transmitir: `grant_bytes × 8 / 2.48832 Gbps`.
3. Espera ese tiempo + 1 µs de guardia → atiende a ONU 1.
4. Repite para ONUs 2, 3, 4, 5, 6, 7 → vuelve a ONU 0. Un ciclo completo.
5. Si la ONU 0 acumuló paquetes mientras esperaba su turno, los reportará
   recién en el próximo GATE → latencia acumulada.

### Polling en código (simulator/olt_ipact.py)

```
Evento EVT_OLT_SEND_GATE(onu_id=3) → on_send_gate()
  ├─ allocation = dba.allocate_onu(onu_id=3, report, b_max=38880)
  │    → {1: 160B, 2: 4000B, 4: 34720B}  (suma ≤ 38.880)
  ├─ grant_time = 34880 bytes × 8 / 2.48832 Gbps = ~112 µs
  ├─ Agenda EVT_ONU_RECV_GATE(onu_id=3) con delay=100µs
  └─ Agenda EVT_OLT_POLL_NEXT con delay=grant_time + 1µs (guard)
       → on_poll_next() avanza puntero: poll_ptr = (3+1) % 8 = 4
       → Agenda EVT_OLT_SEND_GATE(onu_id=4) con delay=0
```

La diferencia clave con broadcast: en polling, el próximo evento de la OLT
depende de cuánto le otorgó a la ONU anterior. En broadcast, el próximo evento
de la OLT es siempre en `now + 125µs`, sin importar nada.

### Cómo se mide la latencia (en ambos casos)

Cuando un paquete llega a la OLT (`EVT_OLT_RECV_DATA`):
```python
latency = engine.now - pkt["creation_time"]
```
`creation_time` se grabó cuando el paquete se generó en la ONU. Esa resta
es la latencia end-to-end. Se acumula en el MetricsCollector y al final se
calcula media, P99, máximo, y % que superó la cota SLA.

---

## Slide 9: Arquitectura del simulador

Lo que más le importa a la profesora: **no se usó ningún framework de
simulación**. El motor de eventos (cola ordenada por tiempo), los modelos de
red, los algoritmos DBA, los generadores de tráfico: todo código propio en
Python, usando solo `heapq` de la librería estándar.

Módulos activos:

| Módulo | Qué hace |
|---|---|
| `simulator/engine.py` | Motor DES: heap de eventos + tabla de handlers |
| `simulator/olt.py` | OLT broadcast (GIANT/QoSDBA): genera BWmap cada 125µs |
| `simulator/olt_ipact.py` | OLT polling (IPACT): round-robin por ONU |
| `simulator/onu.py` | ONU: 3 buffers T-CONT, generación de tráfico, reportes |
| `simulator/dba_giant.py` | Algoritmo GIANT (GPA/SPA, contadores SI) |
| `simulator/dba_qos.py` | Algoritmo QoSDBA (prioridad estricta) |
| `simulator/dba_ipact.py` | Algoritmo IPACT (limited service, b_max) |
| `metrics/collector.py` | Acumula latencias, bytes, utilización; calcula resumen |

---

## Slide 10: Estado del sistema y entidades

Este slide describe los objetos que existen en memoria durante la simulación.

- **OLT**: tiene el último DBRu de cada ONU (`_onu_reports: dict`) y el
  número de trama actual. Es lo único que el algoritmo DBA necesita para
  decidir.
- **ONU**: tiene 3 TCont (uno por tipo de tráfico). Más el canal de
  comunicación con la OLT (a través del motor de eventos).
- **TCont**: es el corazón de la ONU. Tiene un buffer FIFO con los paquetes
  esperando transmisión, y contadores de drops (buffer overflow).
- **Paquete**: objeto mínimo. Guarda ONU de origen, tipo T-CONT, tamaño en
  bytes, y `creation_time` (para calcular latencia cuando llega).

El "estado del sistema" en cualquier instante t es la ocupación de los 24
buffers (8 ONUs × 3 T-CONTs), los reportes que la OLT tiene de cada ONU, y
la posición del algoritmo (número de trama, o índice de ONU si es IPACT).

---

## Slide 11: Eventos futuros (FEL) y condición de término

La FEL (Future Event List) es la cola de prioridad del motor. Todos los eventos
pendientes viven ahí, ordenados por tiempo. El motor saca siempre el menor.

Los tipos de evento son las "acciones" que pueden pasar:

- `ONU_GENERATE_TRAFFIC`: un T-CONT genera un nuevo paquete. Al procesarse,
  encola el paquete y agenda el **siguiente** `ONU_GENERATE_TRAFFIC` para ese
  mismo T-CONT (self-scheduling). Así funciona indefinidamente.
- `OLT_GENERATE_BWMAP`: disparado cada 125 µs exactos. Calcula y manda el BWmap.
- `ONU_RECEIVE_BWMAP`: la ONU recibe su asignación 100 µs después y transmite.
- `OLT_SEND_GATE` / `OLT_POLL_NEXT`: versión IPACT de lo anterior, por ONU.
- `OLT_RECEIVE_DATA`: el dato llegó. Se mide la latencia.
- `OLT_RECEIVE_REPORT`: la OLT actualiza su conocimiento del estado de esa ONU.

**Condición de término:** cuando el reloj de simulación supera 10 s. El primer
segundo (warmup) se ignora en métricas para evitar el régimen transitorio de
arranque. No hay otra condición de término.

**Posible pregunta:** "¿Por qué 10 réplicas?" → Con 10 réplicas y semillas
distintas (6767 a 6776), los IC95% quedan en menos del 0.1% de error relativo
para las métricas importantes. La diferencia entre IPACT (88.4%) y GIANT
(100%) es tan grande que no se necesitan más réplicas para verla.

---

## Slide 12: El loop del simulador

El motor en prosa: "El simulador arranca, carga la configuración, crea la OLT
y las 8 ONUs, y agenda los primeros eventos de generación de tráfico. Después
entra en el loop: saca el evento con el tiempo más chico de la cola, avanza el
reloj a ese tiempo (el reloj no avanza de a poco, salta directo al siguiente
evento), y ejecuta el handler correspondiente. Ese handler puede agendar nuevos
eventos. El loop termina cuando la cola está vacía o el tiempo supera el límite."

La línea clave del motor en código:

```python
while heap no vacío:
    evt = heappop(heap)        # saca el evento de menor tiempo
    if evt.time > until: break
    now = evt.time             # el reloj salta directo aquí
    handlers[evt.type](evt)    # ejecuta la acción
```

En 10 segundos de red real hay ~80.000 tramas GTC. Pero el motor procesa
~1.4 millones de eventos en total (tramas + paquetes + datos + reportes).

---

## Slide 13: El motor de eventos discretos

El pseudocódigo en 6 líneas muestra la esencia. La línea clave es
`reloj_actual = evento.tiempo`: el reloj no avanza de a 1 nanosegundo, salta
directamente al próximo momento relevante. Eso es lo que hace eficiente la
simulación de eventos discretos.

**Posible pregunta:** "¿Cómo garantizan que dos eventos simultáneos se
procesan en orden determinístico?" → Cada evento tiene un número de secuencia
(`seq`) además del tiempo. Si dos eventos caen exactamente en el mismo
instante, el que se agendó primero (menor `seq`) se procesa primero. Con la
misma semilla, el resultado es siempre idéntico bit a bit.

**Posible pregunta:** "¿El motor puede simular eventos en paralelo?" → No, y
no hace falta. Los eventos discretos son secuenciales por definición — ocurren
en instantes distintos, y el motor los procesa en orden. El paralelismo en
los resultados viene de correr réplicas distintas en paralelo (lo hace
`run_experiments.py`).

---

## Slide 14: Generación de tráfico: self-scheduling

El patrón self-scheduling: cada vez que se genera un paquete, ese mismo
handler agenda el próximo evento de generación para ese T-CONT. No hay un
proceso separado que "maneje" la fuente — la fuente se maneja sola.

```
on_generate_traffic(evt):
  pkt = generar paquete con creation_time = now
  tcont.enqueue(pkt)             # poner en buffer
  next_interval = traffic_gen.next_interval()  # CBR / Poisson / Pareto
  engine.schedule(next_interval, ONU_GENERATE_TRAFFIC, ...)  # el siguiente
```

Los tres generadores:

- **CBR (T-CONT1)**: `next_interval()` devuelve siempre 1.28 ms. No hay
  aleatoriedad. En el simulador, todos los eventos de T-CONT1 de todas las
  ONUs son perfectamente periódicos.

- **Poisson (T-CONT2)**: `next_interval()` = `random.expovariate(1/mean)`.
  Distribución exponencial — sin memoria, varianza finita.

- **Pareto (T-CONT4)**: `next_interval()` = `random.paretovariate(1.5)` ×
  escala. La mayoría de los intervalos son cortos (ráfagas), pero el
  simulador puede sacar un número 10× o 100× el promedio con probabilidad
  no despreciable. Eso es lo que crea los picos de carga que estresan el
  algoritmo.

---

## Slide 15: Entradas del simulador y diseño experimental

Los parámetros físicos vienen todos de ITU-T G.987 (el estándar real de
XG-PON1). No se inventó ningún número de la red.

Las únicas decisiones propias del equipo:
- Las tasas de T-CONT4 (200/400/800 Mbps/ONU) como barrido de carga.
  Representan 64%, 129% y 257% de la capacidad upstream respectivamente.
- Los SLA de T-CONT2 y T-CONT4 (el de T-CONT1 fue pedido explícito).
- Los contadores SImax=8 y SImin=32 de GIANT (el estándar deja un rango,
  no un valor único).

**9 escenarios** = 3 algoritmos × 3 niveles de carga. Cada uno corre 10
réplicas con semillas distintas (6767 a 6776). El tiempo total de simulación
en CPU es de unos 5 minutos.

---

## Slide 16: Validación — cotas teóricas vs. simulación

Este es el punto más importante de robustez. No teníamos una red real con qué
comparar, así que derivamos dos cotas analíticas (calculables a mano desde la
geometría del protocolo) y verificamos que la simulación las reproduce exactas:

**(a) Ciclo máximo de IPACT bajo saturación:**

```
ciclo = N × (B_max × 8 / R + t_guard)
      = 8 × (38880 × 8 / 2.48832×10⁹ + 1×10⁻⁶)
      = 8 × (125×10⁻⁶ + 1×10⁻⁶)
      = 8 × 126 µs = 1008 µs
```

La simulación mide exactamente 1008.000 µs bajo saturación — no es
aproximado, es exacto al µs. Si hubiera dado distinto, habría un bug en el
polling.

**(b) Latencia máxima de T-CONT1 en GIANT/QoSDBA:**

```
latencia_max = T_trama + T_prop_ida + T_prop_vuelta + T_tx
             = 125 µs + 100 µs + 100 µs + 1.03 µs
             = 226.03 µs
```

La simulación mide 226.0288 µs con IC95% de ancho prácticamente 0 (las 10
réplicas dan el mismo número porque T-CONT1 es CBR = no hay aleatoriedad en
ese camino).

Si la simulación no reproducía estas cotas exactas, había un bug. El hecho
de que coincidan exactamente valida el motor de eventos, el modelo de
propagación y la lógica de asignación.

---

## Slide 17: Resultado central — cumplimiento del SLA

**Lo que muestra el gráfico:** barras por T-CONT × algoritmo. La única barra
que no llega al 100% es T-CONT1 bajo IPACT a 800 Mbps/ONU: 88.4%.

**Por qué ese número:** bajo 800 Mbps/ONU, el canal está sobrecargado. El
ciclo de IPACT se satura en 1008 µs. Un paquete de VoIP puede esperar casi
2 ciclos antes de que le toque transmitir → latencia de ~2.1 ms → viola el
SLA de 2 ms. El 11.6% de los paquetes T-CONT1 de IPACT superan los 2 ms.

**Por qué GIANT y QoSDBA dan siempre 100%:** ambos reservan los 160 bytes de
T-CONT1 incondicionalmente en cada BWmap — sin importar cuánto tráfico haya
de T-CONT4. La VoIP siempre tiene su slot garantizado cada 125 µs → latencia
máxima de 226 µs, muy por debajo de 2 ms, sin importar la carga.

**Posible pregunta:** "¿Por qué GIANT y QoSDBA dan exactamente el mismo número
para T-CONT1?" → Porque los dos reservan T-CONT1 de la misma forma: 160 bytes
fijos por trama, sin condición. Se diferencian en cómo tratan T-CONT2 y T4,
no en VoIP.

---

## Slide 18: Por qué falla IPACT

El gráfico muestra el delay máximo de T-CONT1 vs. la carga T-CONT4.

- A 200 Mbps/ONU (64% de carga): IPACT da ~820 µs máximo. Ya supera a GIANT
  (226 µs), pero está debajo del SLA de 2000 µs. El ciclo no está saturado.
- A 400 Mbps/ONU (129% de carga): el ciclo IPACT se satura → 2109 µs máximo.
  Cruza el SLA de 2 ms.
- A 800 Mbps/ONU (257% de carga): igual — saturado en 1008 µs de ciclo, misma
  latencia máxima. No empeora porque ya estaba saturado.

GIANT y QoSDBA: línea plana en 226 µs sin importar la carga. La reserva
incondicional desacopla completamente T-CONT1 del resto del tráfico.

**El mecanismo técnico del fallo:** IPACT decide el grant de T-CONT1 mirando
el último reporte recibido de esa ONU. Si el reporte tiene 1 ciclo de
antigüedad (hasta 1008 µs bajo saturación), la VoIP puede acumular paquetes
nuevos que todavía no estaban reportados → esos paquetes esperan hasta el
próximo ciclo → latencia acumulada > 2 ms.

---

## Slide 19: El mecanismo detrás (histogramas de ciclo)

El gráfico muestra la distribución del tiempo de ciclo de IPACT en las 3 cargas.

- **200 Mbps/ONU**: ciclo variable entre 16 y ~400 µs. El histograma se ve
  distribuido — el canal tiene capacidad de sobra, el ciclo varía según carga
  instantánea.
- **400 Mbps/ONU**: histograma degenerado en 1008 µs. Una sola barra.
  El canal está saturado el 100% del tiempo.
- **800 Mbps/ONU**: idéntico. No cambia porque ya estaba saturado al 100%.

GIANT y QoSDBA siempre operan a 125 µs de ciclo fijo — no aparecen en el
histograma variable; se muestra con la línea punteada de referencia.

---

## Slide 20: Confiabilidad estadística

- 10 réplicas con seeds distintas → IC95% = `ȳ ± 1.96 · s / √10`.
- Donde el camino es determinístico (T-CONT1 en GIANT/QoSDBA: CBR + grant
  fijo = sin aleatoriedad), el IC95% es exactamente 0. Las 10 réplicas dan
  el mismo número al último decimal.
- Donde hay aleatoriedad (IPACT + cargas Pareto), la variabilidad entre
  réplicas es pequeña: error relativo < 0.1% para latencia media.
- La diferencia entre IPACT (88.4%) y GIANT (100%) es de 11.6 puntos
  porcentuales, mucho mayor que cualquier IC95%. La conclusión es estadístico-
  mente sólida con 10 réplicas.

---

## Slide 21: Conclusiones

El mensaje central: **cumplir un SLA estricto de latencia no es gratis**.
El algoritmo de DBA importa, y de forma fundamental.

- Reservar sin condiciones (GIANT, QoSDBA) = SLA garantizado en cualquier
  carga. El tráfico de datos no puede "robarle" el turno al VoIP.
- Asignar según demanda reportada (IPACT) = puede fallar justo cuando la red
  está más cargada, porque el reporte siempre tiene al menos un ciclo de
  retraso.
- Hay un costo: QoSDBA pierde eficiencia en tráfico de datos (73% de
  utilización vs 94-97% de IPACT y GIANT). No todo es gratis.

---

## Demo en vivo: --demo

Para mostrar el simulador corriendo en terminal durante la presentación:

```bash
python main.py --algorithm giant --load 400 --demo
```

Lo que se ve: una línea que se actualiza en lugar mostrando el tiempo
simulado, % de progreso, y latencia media de cada T-CONT con marca ✓/✗
según su SLA. Durante el warmup (primer segundo simulado) los T-CONTs
muestran `---` porque las métricas no cuentan ese período. Después del
warmup aparecen los valores reales.

Para comparar IPACT vs GIANT en vivo, correr en terminales separadas:
```bash
# Terminal 1
python main.py --algorithm giant --load 800 --demo
# Terminal 2
python main.py --algorithm ipact --load 800 --demo
```

GIANT mostrará T1 siempre en ~165µs ✓. IPACT mostrará T1 subiendo hasta
~2000µs con algunos ✗.

---

## Preguntas difíciles transversales

**"¿Cómo validaron el simulador?"**
→ Cotas analíticas: (a) ciclo máximo de IPACT = 1008 µs exactos, (b)
latencia máxima de T-CONT1 en GIANT/QoSDBA = 226.03 µs. Ambas coinciden
exactamente con la teoría — si hubiera discrepancia, habría un bug.

**"¿Por qué solo 8 ONUs?"**
→ Para que el análisis se concentre en los algoritmos. Con más ONUs los
resultados cualitativos son los mismos; la diferencia IPACT vs broadcast
se amplifica, no se revierte.

**"¿Por qué IPACT si es de EPON?"**
→ Se usa como referencia de benchmarking explícita para mostrar la diferencia
de mecanismo (polling vs broadcast). Está documentado como tal en el informe.
No afirmamos que XG-PON use IPACT.

**"¿10 réplicas son suficientes?"**
→ Sí para esta diferencia (88% vs 100%). El IC95% es estrecho y la diferencia
es de 11.6 puntos. Con más réplicas los intervalos se achicarían, pero la
conclusión no cambia.

**"¿Cómo saben que el motor está bien implementado?"**
→ Es determinístico (mismo seed = mismo resultado), procesa eventos en orden
estricto de tiempo, y reproduce exactamente las cotas teóricas.

**"¿Por qué no usaron SimPy o OMNeT++?"**
→ Requisito del curso. Además, implementar el motor desde cero obliga a
entender exactamente qué está pasando — no hay magia de framework.

**"¿Cuál recomendarían para una red real?"**
→ GIANT o QoSDBA para cualquier red con SLA de VoIP. IPACT puede ser
suficiente en redes con mucha capacidad de sobra (subcargadas), pero falla
exactamente cuando más se necesita — bajo sobrecarga.

**"¿Qué pasa si una ONU no reporta nada?"**
→ La OLT tiene el último reporte conocido inicializado en colas vacías. En
el primer ciclo, todas las ONUs reciben una asignación mínima (o nula si el
algoritmo es conservador). Los paquetes empiezan a acumularse y el primer
reporte real llega un RTT después (~200 µs).

---

## Números para tener frescos

| Concepto | Valor |
|---|---|
| Upstream XG-PON1 | 2.48832 Gbps |
| Trama | 125 µs |
| Bytes por trama | 38.880 bytes |
| ONUs | 8 |
| Delay propagación (ida) | 100 µs (20 km × 5 µs/km) |
| SLA T-CONT1 | 2 ms |
| SLA T-CONT2 | 20 ms |
| SLA T-CONT4 | 500 ms |
| Carga 200 Mbps/ONU | 64% de capacidad |
| Carga 400 Mbps/ONU | 129% de capacidad |
| Carga 800 Mbps/ONU | 257% de capacidad |
| SLA T-CONT1 IPACT @ 800 Mbps/ONU | 88.4% |
| SLA T-CONT1 GIANT/QoSDBA (cualquier carga) | 100% |
| Delay máx T-CONT1 IPACT @ 400+ Mbps/ONU | 2109 µs |
| Delay máx T-CONT1 GIANT/QoSDBA (cualquier carga) | 226 µs |
| Ciclo IPACT saturado | 1008 µs = 8 × 126 µs |
| Throughput IPACT/GIANT @ 800 Mbps/ONU | 94 a 97% de capacidad |
| Throughput QoSDBA @ 800 Mbps/ONU | 73% de capacidad |
| Réplicas por escenario | 10 (seeds 6767 a 6776) |
| Duración simulada | 10 s (1 s warmup ignorado) |
| Eventos procesados por corrida | ~1.4 millones |
