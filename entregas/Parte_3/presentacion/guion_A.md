# Guion — Presentador A (slides 1-7)

**Tu parte:** introducción, motivación, la red, el tráfico y los algoritmos.
Es la parte más conceptual — no hay código ni fórmulas, pero sí hay que tener
claros los conceptos de red para responder preguntas.

**Transición de entrada:** tú abres la presentación.
**Transición de salida:** al terminar slide 7 (Los 3 algoritmos), presentas
al integrante B diciendo algo como: "Ahora [nombre] nos explica cómo funciona
el simulador por dentro."

---

## Lo que hay que saber antes de empezar

**Una oración para describir el proyecto completo:**
Comparamos 3 algoritmos de asignación de ancho de banda en una red XG-PON1
simulada, midiendo si el VoIP cumple su SLA de 2 ms bajo distintas cargas.

**Si preguntan qué framework usaron:** ninguno — todo desde cero en Python puro,
es un requisito explícito del curso. El motor de eventos, los modelos de red,
los algoritmos: código propio.

---

## Slide 1-2: Portada y Agenda

Nada especial. Presentate, presenta al equipo, menciona el curso (TEL-341).

La agenda muestra la estructura: motivación → simulador → experimentos →
resultados → conclusiones. Si preguntan por qué ese orden: primero explicamos
el problema, luego la herramienta, luego los resultados.

---

## Slide 3: Motivación

**Idea central:** el problema no es la fibra, es quién puede usarla para subir
datos en cada instante.

- **Downstream** (OLT → ONUs): la OLT transmite en broadcast, la señal llega
  a todos al mismo tiempo, como una radio. No hay contención — no hay que
  decidir nada.
- **Upstream** (ONUs → OLT): todas comparten el mismo cable físico después del
  splitter. Solo una puede transmitir a la vez porque hay un solo receptor en
  la OLT. Si dos transmiten simultáneo, las señales ópticas se suman en el
  splitter y el receptor no puede distinguir nada — colisión total.

La pregunta concreta del proyecto: si por ese canal compiten una llamada de
voz (que no puede esperar más de 2 ms) y una descarga pesada (que puede
esperar lo que sea), ¿el algoritmo que decide quién transmite importa para
que la voz llegue a tiempo?

**Posible pregunta:** "¿Por qué no pueden transmitir varias ONUs al mismo
tiempo?" → Porque es TDMA — un slot de tiempo por transmisor. Más de uno
simultáneo causa colisión óptica: las señales se interfieren físicamente en
el splitter y el receptor no puede separar ninguna.

**Posible pregunta:** "¿Qué es el splitter pasivo?" → Un divisor óptico que
divide la señal de luz sin electrónica. Es pasivo porque no consume energía ni
toma ninguna decisión — simplemente divide la potencia óptica entre las ONUs.

---

## Slide 4: ¿Qué estamos simulando?

Este slide es el mapa completo del proyecto en un vistazo. Úsalo para
orientar a la audiencia antes de entrar al detalle.

- **Sistema**: red XG-PON1 con 1 OLT y 8 ONUs. Cada ONU genera 3 tipos de
  tráfico simultáneamente (VoIP, Video, Datos).
- **Variable independiente**: el algoritmo DBA — cuál de los 3 usamos.
- **Variable de carga**: cuánto tráfico de datos (T-CONT4) genera cada ONU:
  200, 400 u 800 Mbps/ONU.
- **Salidas medidas**: latencia por T-CONT, cumplimiento del SLA, throughput,
  tasa de pérdida.

**El bloque al pie del slide** resume la esencia: no simulamos el tráfico en
sí — los paquetes son la carga de trabajo que complica la decisión. No
simulamos la fibra — el canal siempre funciona igual. Lo que simulamos es
el **proceso de decisión** que ocurre cada 125 µs: ¿cuánto le doy a cada ONU?
Y medimos la consecuencia: si VoIP llega antes de 2 ms o no.

---

## Slide 5: La red que simulamos: XG-PON1

**Por qué XG-PON1 y no GPON:** XG-PON1 (ITU-T G.987) es el sucesor directo
de GPON (ITU-T G.984). El upstream sube de 1.244 Gbps a 2.488 Gbps — el doble.
La trama sigue siendo 125 µs, así que caben el doble de bytes por trama
(38.880 vs 19.440). El estándar de referencia es ITU-T G.987.

**Por qué 8 ONUs:** para que el experimento se concentre en el algoritmo DBA,
no en diferencias entre usuarios. 8 ONUs idénticas dan carga simétrica y
facilitan el análisis.

**Por qué 20 km de fibra:** corresponde a la clase de alcance N1 del estándar
G.987.2. El delay de propagación es 5 µs/km × 20 km = 100 µs (solo ida). Ese
delay aparece dos veces en la latencia de un paquete: 100 µs cuando el BWmap
baja de OLT a ONU, y 100 µs cuando los datos suben de ONU a OLT.

**Por qué 2.48832 Gbps y no "2.5 Gbps":** el estándar define exactamente
2.48832 Gbps = 155.52 Mbps × 16. Siempre citar el valor exacto del estándar.

**Posible pregunta:** "¿Qué es OLT y qué es ONU?" → OLT (Optical Line Terminal)
es la central, el equipo del proveedor. ONU (Optical Network Unit) es el
equipo en casa del usuario. La fibra va de la OLT a un splitter, y del
splitter a cada ONU.

---

## Slide 6: Tráfico simulado y SLA

### Los T-CONTs

T-CONT (Transmission Container) es una cola de paquetes separada por tipo de
servicio dentro de cada ONU. En vez de mezclar todo en una sola cola, cada ONU
tiene 3 colas independientes, cada una con su propio generador de tráfico y
su propio buffer:

- **T-CONT1 (VoIP)**: paquetes de 160 bytes, tasa exactamente constante de
  1 Mbps. CBR = Constant Bit Rate. El intervalo entre paquetes es siempre
  1.28 ms, sin variación. Es el más sensible a latencia.

- **T-CONT2 (Video)**: paquetes de 1000 bytes, llegadas aleatorias con
  distribución Poisson (40 Mbps medio). Los intervalos son exponenciales —
  sin memoria: el tiempo al próximo paquete no depende del anterior.

- **T-CONT4 (Datos)**: paquetes de 1400 bytes, distribución Pareto α=1.5.
  La carga varía entre escenarios: 200, 400 u 800 Mbps/ONU.

**Qué es "cola pesada" (Pareto α=1.5):** la mayoría de los intervalos son
cortos (paquetes que llegan juntos, en ráfaga), pero de vez en cuando hay un
silencio muy largo. A diferencia de Poisson, Pareto tiene varianza infinita:
puede generar silencios de cualquier longitud con probabilidad no despreciable.
Modela el tráfico real de internet, que llega en rachas, no de forma uniforme.

### El SLA

SLA = cota máxima de latencia. Un paquete que llega tarde igual se entrega,
pero cuenta como violación en la métrica de cumplimiento.

| T-CONT | SLA | Origen |
|---|---|---|
| T-CONT1 (VoIP) | ≤ 2 ms | Pedido explícito del experimento |
| T-CONT2 (Video) | ≤ 20 ms | Rango típico video interactivo |
| T-CONT4 (Datos) | ≤ 500 ms | Cota laxa de diagnóstico |

**Posible pregunta:** "¿Un paquete fuera de SLA se descarta?" → No. El descarte
ocurre solo cuando el buffer de la ONU se llena (buffer overflow). El SLA es
una métrica de calidad, no una acción de red. El paquete igual llega, solo que
tarde.

**Posible pregunta:** "¿Por qué esos tres tipos de T-CONT y no los 5 del
estándar?" → Los 5 tipos del estándar cubren casos intermedios (T-CONT3 =
asegurado + no asegurado, T-CONT5 = mixto). Con T-CONT1, T-CONT2 y T-CONT4
se tienen los tres extremos de la jerarquía QoS (fijo, garantizado, best-effort),
que es suficiente para comparar los algoritmos.

---

## Slide 7: Los 3 algoritmos comparados

### 2 mecanismos, 3 algoritmos

Hay dos formas distintas de coordinar el canal upstream:

**Mecanismo 1 — Broadcast (GIANT y QosDBA):**
La OLT calcula la asignación para las 8 ONUs de una sola vez y la manda en un
único mensaje (BWmap) cada 125 µs exactos. Todas las ONUs reciben su asignación
simultáneamente. El ciclo es fijo: siempre 125 µs.

**Mecanismo 2 — Polling (IPACT):**
La OLT atiende las ONUs una por una, en ronda. Le manda un GATE a la ONU 0,
luego a la ONU 1, y así hasta la 7, y vuelve a empezar. El ciclo es variable:
depende de cuánto se le asignó a cada ONU.

Por eso hay **2 mecanismos pero 3 algoritmos**: GIANT y QosDBA usan el mismo
mecanismo de broadcast, pero difieren en cómo distribuyen el ancho de banda:

| Algoritmo | Mecanismo | Cómo asigna T-CONT1 | Cómo asigna T-CONT4 |
|---|---|---|---|
| GIANT | Broadcast | Reserva fija incondicional | Contador SImin=32 tramas |
| QosDBA | Broadcast | Reserva fija incondicional | Prioridad estricta, lo que sobre |
| IPACT | Polling | min(demanda, b_max), sin distinción | min(demanda, b_max), sin distinción |

**Por qué incluir IPACT si es de EPON:** IPACT (IEEE 802.3ah) es el algoritmo
de polling más estudiado. Lo incluimos como referencia de benchmarking para
mostrar la diferencia entre polling y broadcast. El informe lo documenta
explícitamente como adaptación de EPON, no como nativo XG-PON.

**El ciclo máximo de IPACT — cómo sale el 1008 µs:**
Con 8 ONUs, cada una puede recibir hasta b_max = 38.880 bytes = 125 µs de
transmisión. Más 1 µs de guard time para evitar solapamiento:
`8 × (125 µs + 1 µs) = 8 × 126 µs = 1008 µs`
Cuando el canal está saturado, el ciclo siempre dura exactamente esto.

**Transición a B:** "Ahora [nombre] nos explica cómo está construido el
simulador y cómo se implementan estos dos mecanismos en el código."

---

## Tus preguntas más probables

**"¿Por qué simularon solo el uplink y no el downlink?"**
→ Porque el downlink no tiene problema de contención. La OLT transmite en
broadcast hacia todas las ONUs — no hay que decidir quién puede usar el canal
porque solo hay un transmisor. El problema interesante es el uplink, donde
muchos transmisores compiten por un solo canal.

**"¿Qué es un T-CONT?"**
→ Una cola de paquetes separada por tipo de servicio dentro de una ONU. La OLT
asigna ancho de banda por T-CONT, no por ONU entera. Cada ONU tiene 3 T-CONTs
con colas y generadores de tráfico independientes.

**"¿Por qué XG-PON1 y no GPON?"**
→ XG-PON1 es el sucesor directo, upstream 2× más rápido (2.48 Gbps vs
1.24 Gbps). Es más representativo del estado actual de las redes PON.

**"¿Por qué 8 ONUs y no 32?"**
→ Para que el análisis se concentre en los algoritmos, no en efectos de escala.
Con 8 ONUs idénticas la carga es simétrica y los resultados son directamente
atribuibles al algoritmo. Cualitativamente, con más ONUs la diferencia entre
polling y broadcast se amplifica — no se revierte.

**"¿Qué diferencia hay entre GIANT y QosDBA?"**
→ Ambos usan broadcast y reservan T-CONT1 incondicionalmente (por eso los
dos dan 100% de SLA para VoIP). Se diferencian en cómo tratan T-CONT2 y T4:
GIANT usa contadores de intervalo de servicio (SImax=8, SImin=32); QosDBA
usa prioridad estricta. El resultado para T-CONT1 es idéntico en los dos.

**"¿Un paquete fuera de SLA se descarta?"**
→ No. El descarte ocurre solo por buffer overflow. El SLA es una métrica,
no una acción de red.

---

## Números que debes tener frescos

| Concepto | Valor |
|---|---|
| Upstream XG-PON1 | 2.48832 Gbps |
| Trama | 125 µs |
| Bytes por trama | 38.880 bytes |
| ONUs | 8 |
| Delay propagación (ida) | 100 µs (20 km × 5 µs/km) |
| SLA T-CONT1 | ≤ 2 ms |
| SLA T-CONT2 | ≤ 20 ms |
| SLA T-CONT4 | ≤ 500 ms |
| Carga 200 Mbps/ONU | 64% de capacidad |
| Carga 400 Mbps/ONU | 129% de capacidad |
| Carga 800 Mbps/ONU | 257% de capacidad |
| Ciclo IPACT saturado | 1008 µs = 8 × 126 µs |
| SLA T-CONT1 GIANT/QosDBA | 100% siempre |
| SLA T-CONT1 IPACT @ 800 Mbps/ONU | 88.4% |
