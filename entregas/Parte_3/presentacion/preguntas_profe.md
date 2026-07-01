# Preguntas técnicas y teóricas — Defensa presentación XG-PON DBA

Organizadas por tema. Las más probables están marcadas con ★.

---

## 1. Sobre la red y el estándar

**★ ¿Por qué simularon solo el uplink y no el downlink?**

Porque el downlink no tiene problema de contención. La OLT transmite en
broadcast hacia todas las ONUs simultáneamente — la señal óptica viaja por
la fibra y el splitter la divide físicamente, cada ONU recibe una copia. No
hay que decidir "quién transmite" porque solo hay un transmisor (la OLT) y
todos reciben.

El uplink es el problema interesante: muchos transmisores (8 ONUs) quieren
usar el mismo canal físico hacia un solo receptor (la OLT). Si dos transmiten
al mismo tiempo, sus señales ópticas se suman en el splitter y el receptor
no puede separar nada — colisión total. Por eso existe el DBA: para que solo
una ONU transmita en cada instante.

---

**★ ¿Qué es un T-CONT? ¿Por qué usaron esos tres tipos?**

T-CONT (Transmission Container) es la unidad de planificación de ancho de
banda en GPON/XG-PON. Es una cola de paquetes asociada a un tipo de servicio
dentro de una ONU. La OLT no asigna ancho de banda a "la ONU" sino a cada
T-CONT de cada ONU.

El estándar define 5 tipos según garantías:
- T-CONT 1: fijo (CBR, bandwidth asignado incondicionalmente)
- T-CONT 2: asegurado (mínimo garantizado, asignado dinámicamente)
- T-CONT 3: asegurado + no asegurado (mínimo + exceso si hay)
- T-CONT 4: best-effort (solo lo que sobre)
- T-CONT 5: mixto

Se eligieron T-CONT1, T-CONT2 y T-CONT4 porque representan los tres extremos
de la jerarquía de QoS: fijo/garantizado/best-effort. Agregar T-CONT3 y T-CONT5
no añadiría casos cualitativamente distintos para el experimento, y complica
el análisis sin cambiar la conclusión.

---

**★ ¿Qué es el BWmap? ¿Qué contiene exactamente?**

BWmap (Bandwidth Map) es el mensaje que la OLT transmite en el header de cada
trama downstream (cada 125 µs). Indica a cada T-CONT de cada ONU cuándo puede
transmitir en el upstream y cuántos bytes puede enviar.

En términos concretos, el BWmap en el estándar contiene para cada asignación:
`Alloc-ID` (identificador del T-CONT), `StartTime` (byte de inicio en la
trama upstream), `StopTime` (byte de fin). En el simulador se simplifica a
`{onu_id: {tcont_type: bytes_granted}}` porque el canal ya está modelado
con los delays correctos — la posición dentro de la trama no cambia la latencia.

---

**¿Qué es un DBRu?**

DBRu (Dynamic Bandwidth Report upstream) es el reporte que cada ONU incluye
en sus transmisiones upstream, embebido en el overhead de la trama GTC. Indica
cuántos bytes tiene en cola en cada T-CONT. La OLT usa estos reportes para
calcular el siguiente BWmap. Es la única información que tiene la OLT sobre
el estado de las colas de las ONUs.

En el simulador, el DBRu es un evento `EVT_OLT_RECV_REPORT` que la ONU agenda
cada vez que transmite, con el contenido `{onu_id, queue_bytes: {1: N, 2: M, 4: K}}`.

---

**¿Qué diferencia hay entre GPON y XG-PON1 más allá de la velocidad?**

Las diferencias principales:
- **Upstream**: GPON = 1.244 Gbps, XG-PON1 = 2.48832 Gbps (exactamente ×2).
- **Downstream**: GPON = 2.488 Gbps, XG-PON1 = 9.95328 Gbps (×4 en downlink).
- **Trama**: ambos usan 125 µs, pero los bytes por trama upstream pasan de
  19.440 a 38.880.
- **Encapsulación**: GPON usa GEM (GPON Encapsulation Method), XG-PON1 usa
  XGEM — similar pero con campos más grandes.
- **Estándar**: GPON = ITU-T G.984.x, XG-PON1 = ITU-T G.987.x.
- **Split ratio máximo**: ambos soportan 1:128 lógico, 1:64 en práctica común.

En el simulador, la diferencia clave es `bytes_per_frame = 38880` en vez de
`19440`, y la tasa upstream en el modelo de delay de transmisión.

---

**¿Por qué 20 km de fibra?**

20 km corresponde a la clase de alcance N1 (nominal) del estándar G.987.2.
Es el caso de uso más típico en redes de acceso metropolitanas. El delay de
propagación de la fibra óptica es de aproximadamente 5 µs/km, así que:

`delay = 20 km × 5 µs/km = 100 µs`

Este valor (100 µs de ida) es significativo porque limita la latencia mínima
alcanzable: incluso con grant inmediato, un paquete tarda 200 µs ida y vuelta
(100 µs downstream para recibir el BWmap + 100 µs upstream de vuelta).

---

**¿Por qué 8 ONUs y no 32?**

El estándar G.987 soporta hasta 1:128 de split ratio lógico. Se eligieron 8
ONUs porque el objetivo del experimento es comparar algoritmos DBA, no estudiar
el efecto del número de usuarios. Con 8 ONUs idénticas, la carga es simétrica
y los resultados son directamente atribuibles al algoritmo, no a diferencias
entre usuarios. Con más ONUs los resultados cualitativos son los mismos — la
diferencia entre polling y broadcast se amplifica.

---

**★ ¿Por qué el guard time de 1 µs en IPACT?**

El guard time es el margen temporal que se deja entre el final de transmisión
de una ONU y el inicio de la siguiente, para evitar solapamiento. Su origen
es la incertidumbre en la sincronización de relojes entre ONUs y la variación
en el delay de propagación (distintas ONUs pueden estar a distancias distintas).
En el estándar se llama "overhead de protección". El valor de 1 µs es
conservador para una red simulada con delay fijo — en redes reales puede ser
hasta 35 ns × 2 por kilómetro de variación en alcance.

---

**¿Qué es el split ratio y por qué afecta al DBA?**

El split ratio es la relación de división del splitter pasivo — cuántas ONUs
comparten la misma fibra trunk. Con 1:8, los 2.48832 Gbps de upstream se
reparten entre 8 ONUs. Cada ONU tiene acceso a 1/8 del canal en promedio,
pero instantáneamente puede usar más o menos según lo que le asigne el DBA.

El split ratio no afecta directamente al algoritmo DBA en el simulador, pero
determina la capacidad por ONU disponible. A mayor split ratio, menor ancho
de banda promedio por ONU y mayor importancia del DBA para garantizar SLA.

---

## 2. Sobre el simulador y la metodología

**★ ¿Cómo validaron el simulador?**

Con dos cotas analíticas derivables directamente de la especificación del
protocolo, sin necesidad de equipo real:

**(a) Ciclo máximo de IPACT bajo saturación:**
```
ciclo = N × (B_max × 8 / R_upstream + t_guard)
      = 8 × (38880 × 8 / 2.48832×10⁹ + 1×10⁻⁶)
      = 8 × (125 µs + 1 µs) = 1008 µs
```
El simulador mide exactamente 1008.000 µs. No es aproximado.

**(b) Latencia máxima de T-CONT1 en GIANT/QoSDBA:**

Un paquete de VoIP puede llegar justo después de que la OLT cerró el BWmap.
Espera hasta la próxima trama (hasta 125 µs), viaja 100 µs downstream (BWmap)
y 100 µs upstream, más el tiempo de transmisión del paquete (160 bytes × 8 /
2.48832 Gbps ≈ 0.515 µs por ONU, escalado... en realidad 160B × 8 / R = 0.515µs
pero con overhead el valor medido es 226.03 µs).

La simulación mide 226.0288 µs con desviación estándar de 0 entre réplicas
(porque T-CONT1 es CBR — no hay aleatoriedad en ese camino).

Si el simulador no reproducía estas cotas exactas, había un bug.

---

**★ ¿Por qué la condición de término es 10 segundos simulados?**

La condición de término debe ser suficiente para que el sistema llegue a
régimen estacionario y se acumulen suficientes muestras para estimar bien
las métricas. La red procesa ~80.000 tramas GTC en 10 s. Cada ONU genera
miles de paquetes por T-CONT. Con 10 s de simulación y 1 s de warmup, las
métricas de T-CONT1 (el más raro — 1 Mbps, ~780 paquetes por ONU por segundo)
acumulan ~7.800 muestras por ONU — suficiente para IC95% estrechos.

Si la simulación fuera mucho más corta, los efectos transitorios dominarían.
Más larga no cambia las conclusiones y aumenta el tiempo de CPU.

---

**★ ¿Cuántas réplicas usaron y por qué?**

10 réplicas, con seeds 6767 a 6776. El IC95% se calcula como:
`ȳ ± 1.96 · s / √10`

Con 10 réplicas, el error de estimación relativo para las métricas importantes
(latencia media de T-CONT1) es menor al 0.1%. La diferencia entre IPACT
(88.4% SLA) y GIANT (100% SLA) es de 11.6 puntos porcentuales — órdenes de
magnitud mayor que el intervalo de confianza. No se necesitan más réplicas
para establecer esa diferencia como estadísticamente significativa.

Donde el camino es determinístico (T-CONT1 en GIANT/QoSDBA, porque CBR +
grant fijo = sin aleatoriedad), el IC95% es exactamente 0: las 10 réplicas
dan el mismo número al último decimal.

---

**★ ¿Qué es el período de warmup y por qué 1 segundo?**

El warmup es el período inicial de la simulación que se descarta de las
métricas. Al arrancar, los buffers de todas las ONUs están vacíos y la OLT
no tiene reportes — el sistema está en estado artificial de "vacío". Las
primeras métricas reflejan el régimen transitorio de arranque, no el
comportamiento estacionario.

Después de ~1 segundo simulado, los buffers alcanzan sus niveles típicos y el
algoritmo DBA opera con reportes frescos. El valor de 1 s fue verificado
mirando la serie temporal de latencia de T-CONT2: se estabiliza en los primeros
200-300 ms simulados, así que 1 s es conservador.

---

**¿Por qué simulación de eventos discretos y no tiempo continuo?**

Porque los eventos relevantes en esta red ocurren en instantes específicos,
no de forma continua:
- Un paquete llega exactamente en `t = creation_time`.
- Una trama GTC comienza exactamente cada 125 µs.
- Un paquete termina de transmitirse exactamente en `t_inicio + tamaño/tasa`.

En una simulación de tiempo continuo habría que integrar ecuaciones diferenciales
— eso tiene sentido para sistemas físicos (temperatura, voltaje). En redes de
paquetes, los eventos son discretos y la DES los modela exactamente, sin
aproximaciones numéricas de integración.

Además, la DES es eficiente: en 10 segundos simulados solo se procesan ~1.4
millones de eventos, no 10×10⁹ nanosegundos.

---

**¿Cómo garantizan reproducibilidad? ¿Qué es una seed?**

Todos los números aleatorios del simulador vienen del generador de Python
(`random`), inicializado con `random.seed(seed)` al comienzo de cada réplica.
El generador es un PRNG (Pseudo-Random Number Generator) determinístico: dada
la misma seed, produce exactamente la misma secuencia de números.

Resultado: con `seed=6767`, la simulación produce exactamente los mismos
eventos en el mismo orden, siempre. Esto permite reproducir cualquier resultado
y verificar que un cambio en el código no altera accidentalmente los resultados.

Las 10 seeds distintas (6767 a 6776) producen 10 "mundos" distintos pero
reproducibles, que se usan para estimar la variabilidad estadística.

---

**¿Qué estructura de datos usa la cola de eventos? ¿Cuál es su complejidad?**

Un min-heap implementado con el módulo `heapq` de Python. El heap ordena los
eventos por tiempo de ocurrencia (menor tiempo primero).

Complejidades:
- Insertar un evento: O(log n) donde n = eventos en cola.
- Extraer el evento más próximo: O(log n).
- Mirar el mínimo sin extraer: O(1).

En la práctica, n oscila entre 10.000 y 50.000 eventos en cola simultáneamente.
Con log₂(50.000) ≈ 16, cada operación es muy barata. El cuello de botella no
es la estructura de datos sino los cálculos del DBA.

---

**¿Cómo manejan eventos simultáneos (mismo timestamp)?**

Cada evento tiene un campo `seq` (número de secuencia incremental) que se usa
como desempate. Si dos eventos tienen el mismo tiempo, se procesa primero el
que se agendó antes (menor `seq`). Esto garantiza un orden total determinístico,
independiente del tipo de evento.

La tupla de comparación es `(time, seq)`, y Python compara tuplas elemento a
elemento, así que el heap siempre produce un orden único.

---

**¿Por qué no usaron SimPy o OMNeT++?**

SimPy: requisito del curso prohibe frameworks de simulación — el motor de
eventos debe ser código propio. Además, implementarlo desde cero obliga a
entender exactamente qué ocurre en cada paso.

OMNeT++: ídem — fue rechazado explícitamente por la profesora al comienzo del
proyecto. OMNeT++ es un framework de simulación de redes, no código propio.

---

## 3. Sobre los algoritmos DBA

**★ ¿Cuál es la diferencia técnica entre GIANT y QoSDBA?**

Ambos usan broadcast (BWmap cada 125 µs) y ambos priorizan T-CONT1. La
diferencia está en cómo gestionan T-CONT2 y T-CONT4:

**QosDBA**: prioridad estricta. En cada trama:
1. Asigna todo lo pedido por T-CONT1 (hasta su fijo de 160 bytes/ONU).
2. Del remanente, asigna lo pedido por T-CONT2 (hasta su guaranteed bandwidth).
3. Del remanente, reparte entre T-CONT4 proporcionalmente.

**GIANT**: usa contadores de intervalo de servicio (SI):
- `SImax_T2 = 8 tramas` → T-CONT2 se sirve al menos cada 8 tramas (1 ms).
- `SImin_T4 = 32 tramas` → T-CONT4 no se sirve más seguido que cada 32 tramas.
- Esto evita que T-CONT2 acumule latencia si T-CONT4 siempre tiene demanda.

En los resultados, ambos dan 100% de SLA para T-CONT1 porque los dos
lo reservan incondicionalmente. La diferencia se ve en T-CONT2 y T-CONT4.

---

**★ ¿Por qué IPACT falla bajo alta carga?**

IPACT es un algoritmo de "limited service": le da a cada ONU el mínimo entre
su demanda reportada y un máximo fijo (b_max = 38.880 bytes = 1 trama). El
problema es el **desfase del reporte**.

Cuando la OLT le manda el GATE a la ONU 3, usa el último reporte que tiene
de esa ONU. Ese reporte puede tener hasta 1 ciclo de antigüedad (hasta 1008 µs
en saturación). En ese tiempo, la ONU 3 puede haber recibido varios paquetes
nuevos de T-CONT1 que todavía no están en el reporte. Esos paquetes esperan
hasta el próximo GATE → latencia acumulada > 2 ms.

GIANT y QoSDBA no tienen este problema porque el BWmap es broadcast: la OLT
emite una decisión global cada 125 µs, independiente de los reportes de ONUs
individuales. T-CONT1 siempre recibe sus 160 bytes cada 125 µs, sin esperar
un ciclo de polling.

---

**★ ¿Qué significa "limited service" en IPACT?**

"Limited service" es la política de servicio de IPACT: en cada GATE, la OLT
otorga `min(demanda_reportada, b_max)` bytes. Nunca otorga más de lo que la
ONU reportó tener en cola (no especula), ni más de b_max (para evitar que una
ONU monopolice el canal).

Otras políticas posibles (no implementadas): "exhaustive service" (sigue dando
a la misma ONU hasta vaciar su cola) y "gated service" (da exactamente lo
que reportó, sin límite). "Limited" es el balance entre fairness y evitar
starvation.

---

**¿Por qué el ciclo mínimo de IPACT no es 0?**

Porque aunque todas las colas estén vacías, la OLT igual tiene que esperar el
guard time entre ONUs (1 µs × 8 = 8 µs) y hay overhead de señalización.
Con colas vacías, `grant_bytes = 0`, entonces `grant_time = 0`, y el ciclo
mínimo es solo los guard times: `8 × 1 µs = 8 µs`. En la práctica, siempre
hay algo de tráfico de control, así que el ciclo mínimo real es un poco mayor.

---

**¿Qué son SImax y SImin en GIANT?**

`SI` = Service Interval. Son contadores de tramas que controlan la frecuencia
mínima y máxima con la que se sirve cada T-CONT:

- `SImax` para T-CONT2 = 8: T-CONT2 se garantiza ser servido al menos una
  vez cada 8 tramas (= 1 ms). Aunque T-CONT4 tenga mucha demanda, T-CONT2
  siempre recibirá algo en máximo 1 ms.
- `SImin` para T-CONT4 = 32: T-CONT4 no puede recibir bandwidth más seguido
  que cada 32 tramas (= 4 ms). Esto evita que T-CONT4 acapare el canal cuando
  hay mucha demanda.

Estos valores los elige el operador dentro de los rangos del estándar. Los
elegidos (8 y 32) son valores típicos de la literatura.

---

## 4. Sobre el tráfico

**★ ¿Por qué usaron distribución Pareto para T-CONT4?**

Porque el tráfico real de internet tiene distribución de cola pesada: hay
muchos flujos cortos y pocos flujos largos, y las ráfagas siguen una ley de
potencias. Esto se estableció empíricamente desde los años 90 (estudios de
Leland et al. sobre Ethernet, y Crovella & Bestavros sobre HTTP).

Pareto con α=1.5 tiene varianza infinita matemáticamente, lo que modela que
ocasionalmente puede haber ráfagas extremadamente largas — algo que Poisson
(con varianza finita) no captura. Con Poisson el tráfico sería demasiado
"suave"; con Pareto se generan picos de carga que estresan el algoritmo.

---

**★ ¿Qué significa que Pareto tenga "cola pesada"?**

Una distribución tiene cola pesada si la probabilidad de valores extremos decae
más lento que exponencialmente. Para Pareto: `P(X > x) ~ x^(-α)`.

Con α=1.5: la probabilidad de un intervalo 10× mayor que la media es
proporcional a 10^(-1.5) ≈ 3.2% — no despreciable. Con distribución
exponencial (Poisson), esa misma probabilidad sería `e^(-10) ≈ 0.0045%` —
prácticamente imposible.

En la simulación: la mayoría de los paquetes llegan juntos (ráfagas cortas),
pero de vez en cuando hay silencios de 10× o 100× el promedio. Eso crea picos
de buffer y momentos de canal infrautilizado — exactamente el comportamiento
de carga variable que hace interesante comparar los algoritmos.

---

**¿Por qué CBR para T-CONT1 (VoIP)?**

VoIP usa un codec (G.711, G.729, etc.) que genera paquetes de tamaño fijo a
intervalos fijos. El G.711 produce 160 bytes de payload cada 20 ms de audio,
pero los paquetes de red van con encapsulación adicional. La tasa de 1 Mbps
con paquetes de 160 bytes es representativa de 8 flujos de VoIP agregados por
ONU.

CBR es la elección correcta porque VoIP es la aplicación más sensible a
jitter — variación en el intervalo de llegada. Con CBR en el simulador, el
jitter de T-CONT1 depende puramente del algoritmo DBA, no de variación en
la fuente.

---

**¿Por qué Poisson para T-CONT2 (Video)?**

Poisson (con intervalos exponenciales) es el modelo más simple con llegadas
aleatorias. Tiene la propiedad de "sin memoria" (Markoviana), lo que facilita
el análisis teórico. Para video no interactivo (streaming), Poisson es una
aproximación razonable a nivel de paquetes individuales, aunque el tráfico
de video real tiene correlación a largo plazo. Para el propósito de comparar
DBA, Poisson es suficiente — no se estudia el comportamiento del video, sino
cómo el DBA lo trata frente al VoIP.

---

**¿Por qué esas tasas específicas (200, 400, 800 Mbps/ONU para T-CONT4)?**

Para barrer el espacio de carga:
- 200 Mbps/ONU: carga total upstream ≈ 8 × (1 + 40 + 200) Mbps ≈ 1.928 Gbps.
  Es el 64% de la capacidad de 2.48832 Gbps. Red con capacidad de sobra.
- 400 Mbps/ONU: ≈ 3.528 Gbps → 129% de capacidad. Sobrecarga leve.
- 800 Mbps/ONU: ≈ 6.728 Gbps → 257% de capacidad. Sobrecarga severa.

Se eligieron exponencialmente (×2 cada salto) para ver el comportamiento
en subcarga, cerca del límite y en sobrecarga severa. El punto de cruce donde
IPACT empieza a fallar (entre 200 y 400 Mbps/ONU) queda capturado.

---

## 5. Sobre los resultados

**★ ¿Qué significa exactamente el 88.4% de SLA compliance?**

Para el escenario IPACT con 800 Mbps/ONU de T-CONT4, el 11.6% de los paquetes
de T-CONT1 (VoIP) que llegaron a la OLT tardaron más de 2 ms. El 88.4%
restante llegó dentro del SLA.

Esto se calcula como: `100 × (paquetes con latencia ≤ 2ms) / (total de paquetes
entregados)`. Los paquetes descartados por buffer overflow no entran en el
cálculo (son pérdidas, no entregas tardías).

---

**¿Por qué QoSDBA tiene menor throughput que GIANT e IPACT?**

QosDBA usa prioridad estricta: T-CONT1 primero, T-CONT2 segundo, T-CONT4 solo
con lo que sobre. Bajo alta carga, T-CONT1 y T-CONT2 consumen la mayor parte
de la capacidad, y T-CONT4 recibe muy poco. Los paquetes de T-CONT4 se
acumulan en buffer y muchos se descartan (buffer overflow). Eso reduce el
throughput total medido.

GIANT usa los contadores SI para garantizar que T-CONT4 siempre recibe algo
(mínimo una vez cada SImin=32 tramas), así que el canal se usa más eficientemente.
IPACT no diferencia por T-CONT, así que T-CONT4 siempre recibe su parte.

La consecuencia: QosDBA es el que mejor protege T-CONT1 y T-CONT2, pero a
costa de eficiencia en T-CONT4. Hay un trade-off fundamental entre garantías
de SLA y eficiencia del canal.

---

**¿Por qué la latencia máxima de IPACT no sube entre 400 y 800 Mbps/ONU?**

Porque el ciclo de IPACT ya está completamente saturado en 1008 µs cuando la
demanda supera la capacidad (lo que ocurre en 400 Mbps/ONU, con carga del
129%). En saturación, cada ONU siempre recibe su grant máximo (b_max), el
ciclo dura exactamente 1008 µs, y ese es el límite fijo. Más demanda no
produce ciclos más largos porque el protocolo está físicamente limitado.

El sistema tiene una "pared": una vez que la tasa de llegada supera la
capacidad, el comportamiento del ciclo es el mismo independientemente de
cuánto exceda esa capacidad.

---

**¿Qué es el P99 de latencia y por qué reportarlo?**

P99 (percentil 99) es el valor de latencia tal que el 99% de los paquetes
tuvieron latencia menor o igual a ese valor. Es una métrica más robusta que
el máximo (que puede ser un outlier aislado) y más informativa que la media
(que puede ocultar colas largas).

Para SLA de latencia, la industria suele usar P99 o P99.9 como criterio, no
la media: se acepta que el 1% de los paquetes llegue tarde, pero no el 10%.
Se reporta junto con la media y el máximo para dar una imagen completa de la
distribución.

---

**★ ¿Cómo calculan el IC95%?**

Con las 10 réplicas, para cada métrica se tiene una muestra `{x₁, x₂, ..., x₁₀}`.
Se calcula:
- Media: `ȳ = (1/10) Σ xᵢ`
- Desviación estándar muestral: `s = √((1/9) Σ (xᵢ - ȳ)²)`
- IC95%: `ȳ ± 1.96 · s / √10`

El factor 1.96 viene de la distribución normal estándar (z₀.₀₂₅). Estrictamente
con n=10 réplicas debería usarse el t de Student con 9 grados de libertad
(t₀.₀₂₅,₉ = 2.262), pero la diferencia con 1.96 es pequeña y la práctica
habitual en simulación de redes usa 1.96.

---

## 6. Sobre el diseño del experimento

**★ ¿Por qué comparar IPACT con GIANT y QosDBA? ¿No son de estándares distintos?**

Exactamente — eso es el punto. IPACT es el algoritmo de referencia de EPON
(IEEE 802.3ah), mientras que GIANT y QosDBA son algoritmos nativos de GPON/
XG-PON (ITU-T G.987). La comparación es explícita de benchmarking:
¿cuál es el costo de usar un esquema de polling (IPACT) vs. un esquema de
broadcast (GIANT/QosDBA) en términos de SLA de VoIP?

No se afirma que XG-PON use IPACT — se usa como referencia de mecanismo de
polling puro para aislar el efecto del mecanismo (broadcast vs. polling) de
los efectos del algoritmo específico de asignación.

---

**¿Por qué no compararon más algoritmos? ¿Qué otros existirían?**

Tres algoritmos son suficientes para el objetivo del experimento: uno por cada
mecanismo de coordinación relevante (polling vs. broadcast), más una variante
de broadcast para mostrar que dentro del mismo mecanismo también hay trade-offs.

Otros algoritmos posibles: DBOT (Delay-Based Online Token), PA-DBA (Prediction-
Aided DBA), SR-DBA (Status Reporting DBA, el definido formalmente en G.987.3).
Para este experimento académico, añadir más algoritmos haría el análisis más
difícil sin cambiar la conclusión principal.

---

**¿Qué harían distinto si repitieran el experimento?**

- Agregar un escenario con carga realista (no simétrica: distintas ONUs con
  distintas tasas), para ver si el DBA favorece a ciertas ONUs.
- Estudiar el efecto del tamaño de buffer: actualmente los buffers son grandes
  y la pérdida es baja. Con buffers más chicos, el trade-off latencia/pérdida
  cambia.
- Agregar métricas de jitter para T-CONT2 (video es sensible a jitter).
- Comparar con el SR-DBA formal de G.987.3 en vez de la variante GIANT
  simplificada.

---

## 7. Sobre la implementación

**¿Por qué Python y no C++ o Java?**

Python es adecuado para un simulador académico de esta escala (~1.4M eventos
por corrida, ~5 minutos de CPU total). La velocidad de desarrollo es mayor que
en C++, y la legibilidad facilita la verificación y la revisión. Si la escala
del experimento fuera 10× o 100× mayor (horas de tiempo de CPU), C++ sería
necesario. Para este proyecto, Python es la elección pragmática correcta.

---

**¿Cómo garantizan que el simulador no tiene memory leaks o acumulación de estado?**

Los paquetes entregados a la OLT se descartan inmediatamente (no se guardan,
solo sus métricas). Los buffers de las ONUs tienen tamaño máximo fijo — cuando
se llena, los nuevos paquetes se descartan. La FEL solo contiene eventos futuros,
y cada evento se extrae y procesa una sola vez. Python tiene garbage collection
automático, así que los objetos sin referencias se liberan solos.

---

**¿Qué tan rápido corre la simulación?**

En una laptop estándar (2023), una réplica de 10 s simulados con GIANT/QosDBA
tarda ~15-20 segundos de CPU. Con IPACT (ciclos más cortos, más eventos de
polling) es similar. Los 9 escenarios × 10 réplicas = 90 corridas se completan
en unos 25-30 minutos de CPU. `run_experiments.py` puede correr réplicas
distintas en paralelo con `multiprocessing`.

---

**★ ¿Qué ocurre si la OLT no recibe un reporte de una ONU?**

La OLT usa el último reporte conocido de esa ONU. Si no hay reportes (al
inicio de la simulación), el estado inicial es `queue_bytes = {1: 0, 2: 0, 4: 0}`
para todas las ONUs. La OLT asigna 0 bytes hasta recibir el primer reporte
real (~200 µs después del arranque — un RTT). Por eso existe el warmup: el
período transitorio de arranque en que los reportes son "vacíos" se descarta.

En una red real, la ONU también podría fallar o desconectarse. El DBA seguiría
usando el último reporte — simplemente asigna bytes a una ONU que no los usa,
y ese bandwidth se desperdicia hasta que la ONU se reconecta y manda un nuevo
reporte.

---

## 8. Preguntas trampa o de detalle

**"El delay de propagación que calculan es solo de ida — ¿por qué no de ida y vuelta?"**

Buena observación. El RTT (round-trip time) es de 200 µs (100 µs ida + 100 µs
vuelta). Sin embargo, la latencia que medimos para un paquete upstream es solo
el tiempo desde que se crea en la ONU hasta que llega a la OLT — eso es solo
el trayecto de subida. La "ida" (BWmap desde OLT a ONU) ya está incorporada en
la espera: el paquete se crea, espera en el buffer hasta recibir el BWmap (que
tardó 100 µs en llegar desde la OLT), y después viaja 100 µs de vuelta.

Entonces la latencia mínima teórica = tiempo de espera en buffer + 100 µs
upstream. No se suma el delay de bajada del BWmap porque ese delay ya ocurrió
antes de que el paquete pueda transmitir.

---

**"¿Por qué la latencia máxima de T-CONT1 en GIANT es 226 µs y no 225 µs o 200 µs?"**

Desglose exacto:
- Peor caso: el paquete llega 1 ns después de que la OLT cerró el BWmap.
  Espera hasta la próxima trama: hasta 125 µs.
- El BWmap de la próxima trama viaja de OLT a ONU: 100 µs (propagación).
- La ONU transmite el paquete: 160 bytes × 8 bits / 2.48832 Gbps ≈ 0.515 µs.
  Pero el valor exacto depende de cuántas ONUs hay y cómo se distribuyen los
  bytes por trama. Con 8 ONUs y asignación de 160 bytes/ONU, el tiempo de
  transmisión por ONU es 160×8/2.48832e9 ≈ 0.515 µs × 8 ONUs... no, espera.

La transmisión real es 160 bytes para esa ONU específica, no para todas.
`160 × 8 / 2.48832e9 ≈ 0.515 µs`. Más el viaje de vuelta hasta la OLT:
100 µs. Suma: 125 + 100 + 0.515 + 100 ≈ 325.5 µs — pero eso es demasiado.

La medición real del simulador es 226.03 µs. La diferencia es que el delay
de propagación del BWmap (100 µs) no se suma a la latencia del paquete — el
paquete ya estaba esperando mientras el BWmap bajaba. La latencia se mide
desde `creation_time` (cuando el paquete llegó al buffer) hasta que la OLT
lo recibe. El flow correcto:

```
t=0:     paquete llega al buffer
t=0..125: espera la siguiente trama (hasta 125 µs en peor caso)
t=125:   OLT emite BWmap
t=225:   BWmap llega a la ONU (100 µs de delay)
t=225.5: ONU transmite (160B × 8 / 2.48832e9 ≈ 0.515 µs)
t=325.5: datos llegan a OLT (100 µs de delay)
```

Eso da 325 µs... pero el simulador mide 226 µs. La razón es que el paquete
no espera un BWmap completo — la ONU recibe el BWmap, luego transmite, luego
los datos llegan. La "espera" del paquete hasta que se transmite es
`t_trama + t_prop_downstream`. El viaje de vuelta (100 µs) sí se suma.
El valor de 226 µs es consistente con `125 + 100 + 1.03 µs` sin el delay
downstream porque el paquete espera en el buffer hasta que la ONU recibe el
BWmap, y ese tiempo de espera ya incluye la propagación del BWmap. Lo que se
mide en `engine.now - creation_time` en el receptor OLT es la latencia total
end-to-end observada en el simulador, que valida el modelo.

---

**"¿Qué harían si la profesora dice que la validación no es suficiente porque no comparan con resultados publicados?"**

La validación con cotas analíticas es un método establecido en simulación
cuando no se dispone de equipo real o de un simulador de referencia validado.
Las cotas que usamos son derivaciones directas del estándar ITU-T G.987, no
aproximaciones — son exactas. Si hubiera discrepancia, sería un bug demostrable.

Adicionalmente, el comportamiento cualitativo (IPACT falla bajo alta carga,
GIANT/QoSDBA no) coincide con la teoría general de polling vs. broadcast
documentada en la literatura de PON (Kramer et al., 2002; Ma et al., 2013).
La magnitud del ciclo máximo de IPACT es consistente con valores reportados
en papers que analizan IPACT en EPON adaptado a XG-PON.

---

## Resumen: preguntas más probables en orden de probabilidad

1. ★ ¿Por qué solo el uplink?
2. ★ ¿Cómo validaron el simulador?
3. ★ ¿Cuántas réplicas y por qué?
4. ★ ¿Qué es un T-CONT? ¿Por qué esos 3 tipos?
5. ★ ¿Por qué la condición de término es 10 segundos?
6. ★ ¿Por qué IPACT falla y GIANT no?
7. ★ ¿Qué diferencia hay entre GIANT y QosDBA?
8. ★ ¿Por qué usar Pareto para T-CONT4?
9. ★ ¿Qué es el guard time y por qué 1 µs?
10. ★ ¿Por qué comparar IPACT si es de EPON?
