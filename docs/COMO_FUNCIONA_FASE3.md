# Cómo funciona el simulador — Fase 3 (XG-PON)

## Guía explicativa, sin jerga, paso a paso

> Este documento explica **en español sencillo** qué hace el simulador, cómo
> está armada la "red" que simula, cómo viaja el tráfico, y cómo deciden los
> 3 algoritmos (IPACT, GIANT, QoSDBA) quién transmite y cuándo. Está pensado
> para que cualquier persona del equipo —sin necesariamente haber leído el
> código— pueda entender el funcionamiento completo y explicarlo a la
> profesora o en una presentación.
>
> Para la documentación técnica formal (con referencias a normas ITU-T,
> pseudocódigo, fórmulas), ver
> [`DOCUMENTACION_TECNICA_FASE3.md`](DOCUMENTACION_TECNICA_FASE3.md). Este
> documento es el complemento "para entender la idea".

---

## 0. La idea en una frase

> Simulamos 8 casas (ONUs) conectadas por fibra óptica a una central (OLT) a
> 20 km de distancia, compartiendo el mismo "carril" de subida hacia
> internet. El simulador genera tráfico falso pero realista (llamadas,
> video, descargas) en cada casa, y compara **3 formas distintas de repartir
> ese carril compartido** para ver cuál cumple mejor los compromisos de
> calidad (SLA) — especialmente que las llamadas de voz nunca tarden más de
> 2 milisegundos.

---

## 1. ¿Qué red física estamos simulando?

```
                    Internet / proveedor
                          │
                         OLT   (la "central")
                          │
                          │  fibra óptica, 20 km
                          │  (la luz tarda 100 microsegundos
                          │   en recorrerla, en cada sentido)
                          │
                     ┌────┴────┐
                     │ Splitter │  (divisor óptico pasivo 1:8 —
                     │   1:8    │   reparte la señal entre 8 fibras
                     └────┬────┘   más cortas, sin electrónica)
          ┌───┬───┬───┬───┴───┬───┬───┬───┐
        ONU0 ONU1 ONU2 ONU3 ONU4 ONU5 ONU6 ONU7
       (casa)(casa)...                    (casa)
```

- **OLT** (*Optical Line Terminal*): el equipo en la central del proveedor.
  Es el "jefe" — decide quién puede transmitir y cuándo.
- **ONU** (*Optical Network Unit*): el equipo en cada casa/usuario. Genera
  tráfico (llamadas, video, descargas) y lo envía hacia la OLT cuando se le
  da permiso.
- **8 ONUs, todas idénticas**: mismas distancias, mismas tasas de tráfico,
  mismos buffers. Esto es lo que pidió la profesora para esta fase (antes
  eran 32, ahora 8).
- **20 km de fibra, 5 μs por km → 100 μs de viaje en cada sentido**
  (ida ≠ vuelta: la luz tarda lo mismo yendo que viniendo, pero cada
  trayecto cuenta su propio 100 μs). Ida + vuelta = **200 μs de "RTT"**
  (round-trip time, tiempo de ida y vuelta).
- **El "carril" compartido (upstream)**: todas las 8 ONUs transmiten hacia
  la OLT por el mismo medio óptico compartido. Es como un walkie-talkie de
  grupo: **solo una persona puede hablar a la vez** sin que se mezclen las
  voces. La OLT es quien reparte los turnos.
- **Capacidad del carril**: 2.48832 Gbps (~2.5 mil millones de bits por
  segundo) — esto es el estándar XG-PON1 (el sucesor "10G" de GPON).

---

## 2. ¿Qué es un "simulador de eventos discretos"? (y por qué no usamos OMNeT++/SimPy)

Imagina que en vez de mirar un reloj que avanza segundo a segundo (la
mayoría del tiempo "no pasa nada"), tenés una **agenda de citas**: una lista
de "cosas que van a pasar" ordenadas por hora, y un asistente que:

1. Mira la próxima cita en la agenda (la más próxima en el tiempo).
2. Salta el reloj directamente a esa hora (sin importar cuánto falte).
3. Atiende esa cita — lo cual puede generar **nuevas citas futuras** (por
   ejemplo, "llamada generada a las 10:00:00.005" puede agendar "siguiente
   llamada a las 10:00:01.285").
4. Repite hasta que la agenda se vacía o se acaba el tiempo de simulación.

Eso es literalmente lo que hace `simulator/engine.py`: una "agenda"
implementada como un **heap** (estructura de datos ordenada eficientemente
por tiempo) llamada `event_queue`, y un bucle (`run()`) que sacaca el
próximo evento, avanza el reloj de la simulación a ese instante, y llama a
la función que sabe qué hacer con ese tipo de evento (`handler`).

**Por qué esto es importante**: nos permite simular 10 segundos completos de
tráfico de red, con resolución de microsegundos (¡millones de eventos!), en
pocos segundos de cómputo real — porque nunca "perdemos tiempo" en instantes
donde no pasa nada. Y todo esto es **código propio en Python puro**, sin
OMNeT++ ni SimPy, como pidió la profesora.

---

## 3. ¿Cómo viaja la información por la fibra? (el modelo del "canal")

**Dato importante**: el simulador **no tiene un objeto "Canal" o
"Splitter"** como tal en el código. En vez de eso, el comportamiento del
canal compartido se logra combinando 3 ingredientes simples:

### 3.1 El "turno para hablar" (TDMA — Time Division Multiple Access)

La OLT decide, en cada momento, **qué ONU(s) pueden transmitir y cuántos
bytes**. El simulador nunca genera dos transmisiones que se superpongan en
el tiempo desde ONUs distintas — exactamente como en la fibra real, donde el
splitter óptico pasivo no puede "separar" dos señales que llegan al mismo
tiempo: si dos ONUs transmitieran a la vez, se destruirían mutuamente
(colisión). Acá, en cambio, el algoritmo de reparto (DBA) **evita que esto
pase por diseño**, así que el simulador no necesita "detectar colisiones" —
simplemente no las genera.

### 3.2 El retraso de propagación (los 100 μs)

Cada vez que algo viaja por la fibra (una orden de la OLT hacia una ONU, o
datos/un reporte de una ONU hacia la OLT), el simulador le suma
**100 microsegundos** antes de que "llegue" al otro lado. Es el tiempo que
tarda la luz en recorrer los 20 km de fibra. No importa qué tan rápido sea
el contenido — el viaje físico siempre tarda esos 100 μs.

### 3.3 El tiempo de "salida" del paquete (tiempo de transmisión)

Además del viaje, **poner el paquete en la fibra toma tiempo**, proporcional
a su tamaño: un paquete más grande "sale" más lento.

```
tiempo_transmisión = (tamaño_del_paquete_en_bytes × 8) / velocidad_del_enlace
```

Ejemplo: un paquete de 1400 bytes a 2.48832 Gbps tarda ≈ 4.5 microsegundos
en "salir" completamente de la ONU.

### Resumiendo: ¿cuándo llega un paquete a la OLT?

```
hora_de_llegada_a_la_OLT = hora_en_que_empieza_a_transmitir
                          + tiempo_de_transmisión (según su tamaño)
                          + 100 μs (viaje por la fibra)
```

**Lo que el simulador NO modela** (a propósito, porque no es el objetivo del
proyecto): errores de bits, pérdida de potencia óptica, dispersión de la
fibra, ruido. Es un modelo de **desempeño/tráfico**, no de capa física —
igual que en Fase 2.

---

## 4. ¿Qué tráfico generan las ONUs? Los 3 tipos de T-CONT

Cada ONU genera **3 tipos de tráfico al mismo tiempo**, simulando 3
servicios distintos que corren simultáneamente en una conexión real (como tu
router de casa: llamadas, Netflix, y descargas, todo junto). Cada tipo de
tráfico va a su propia "cola" (`T-CONT`, *Transmission Container* — el
nombre que usa el estándar GPON/XG-PON para estas colas).

| | T-CONT 1 (VoIP/control) | T-CONT 2 (Video) | T-CONT 4 (Best Effort) |
|---|---|---|---|
| **Qué simula** | Llamadas de voz / señalización | Video streaming | Descargas, P2P, navegación pesada |
| **Patrón** | Como un metrónomo: un paquetito cada 1.28 ms, siempre igual | Llegan "al azar" pero con un promedio estable (estadística de Poisson) | Rachas: a veces no llega nada por un rato, y de repente llega una ráfaga grande (Pareto, "cola pesada") |
| **Tamaño de paquete** | 160 bytes (chico) | 1000 bytes | 1400 bytes |
| **Tasa promedio** | 1 Mbps (fijo) | 40 Mbps | 200 / 400 / 800 Mbps por ONU según el escenario |
| **SLA (límite de demora aceptable)** | **2 ms** — el más exigente, "tiempo real" | 20 ms | 500 ms (laxo, best-effort no tiene garantía real) |

**Analogía**: T-CONT1 es como un reloj que hace "tic" cada 1.28ms — siempre
manda algo, pase lo que pase (igual que una llamada de voz necesita enviar
audio constantemente). T-CONT2 es como gente llegando a una fila de forma
aleatoria pero con un ritmo promedio predecible (cada cierto tiempo llega
alguien, en promedio). T-CONT4 es como recibir mensajes de WhatsApp: a veces
pasan horas sin nada, y de repente te llega un álbum de 50 fotos de golpe.

Cada cola tiene un **buffer (espacio limitado)**. Si llega un paquete y el
buffer ya está lleno, el paquete se **descarta** (esto es lo que mide
`loss_rate`, la tasa de pérdida).

---

## 5. ¿Quién decide quién transmite? Los 3 algoritmos DBA

**DBA = Dynamic Bandwidth Allocation** (asignación dinámica de ancho de
banda). Es el "árbitro" que vive en la OLT y decide, constantemente, cómo se
reparte el carril compartido entre las 8 ONUs y sus 3 tipos de tráfico cada
una (24 "colas" en total compitiendo por el mismo recurso).

El proyecto compara **3 formas distintas** de hacer este reparto. Las tres
respetan la misma regla de prioridad dentro de cada ONU: **primero T-CONT1,
después T-CONT2, y lo que sobre para T-CONT4** (T1 > T2 > T4) — esto se
mantiene igual en los 3 algoritmos a propósito, para que la comparación sea
justa: lo único que cambia es *cómo y cuándo* se calcula cuánto puede
transmitir cada ONU, no el orden de prioridades.

### 5.1 Camino "broadcast" — GIANT y QoSDBA

**Analogía**: es como un profesor que, **cada 125 microsegundos** (8000
veces por segundo), le grita a *toda la clase a la vez*: "¡Atención! Juan
puede hablar 2 segundos, María 1 segundo, Pedro nada esta vez...". Todos
escuchan el mismo anuncio (broadcast) y cada uno transmite en el momento y
por el tiempo que le tocó.

Paso a paso:

1. Cada 125 μs, la OLT calcula un **"mapa de ancho de banda" (BWmap)**:
   cuántos bytes puede enviar cada ONU, separado por tipo de tráfico (T1,
   T2, T4). Para calcularlo, usa el **último reporte que recibió de cada
   ONU** (de hace ~1-2 "tramas" — ~100-250 μs — porque viajar también toma
   tiempo).
2. La OLT manda ese BWmap a todas las ONUs (llega 100 μs después, por la
   fibra).
3. Cada ONU, al recibirlo, saca de sus colas (T1, T2, T4) la cantidad de
   bytes que le tocaron y los transmite. Cada paquete tarda en llegar a la
   OLT: su tiempo de transmisión + 100 μs.
4. Junto con sus datos, cada ONU también manda un **reporte (DBRu)**: "así
   están mis colas ahora" — para que la OLT lo use en el próximo cálculo
   (paso 1 de la siguiente trama).
5. Se repite, para siempre, cada 125 μs.

**Diferencia entre GIANT y QoSDBA**: ambos usan este mismo marco de "trama
fija cada 125 μs + broadcast", pero calculan el reparto de forma distinta
(ver §6).

### 5.2 Camino "polling" — IPACT

**Analogía**: en vez de gritarle a toda la clase, el profesor va **banco por
banco, alumno por alumno**, en ronda: "Juan, ¿cuánto necesitás? Ok, tenés
permiso, habla." Espera (en el sentido de que el reloj avanza lo justo) y
pasa al siguiente alumno, y así hasta volver a Juan.

Paso a paso:

1. La OLT le pregunta/avisa a la ONU 0: "según tu último reporte, te doy
   permiso para mandar X bytes" (con un tope máximo `B_max` = 38,880 bytes,
   equivalente a una trama completa de 125 μs de transmisión).
2. Calcula cuánto tiempo le tomará a esa ONU transmitir eso
   (`tiempo_de_transmisión`), y **sin esperar la respuesta de la ONU**, pasa
   inmediatamente a calcular el permiso para la ONU 1, luego la 2, ... hasta
   la 7, y vuelve a la 0.
3. Cada ONU, cuando recibe su "permiso" (100 μs después), transmite igual
   que en el camino broadcast (dequeue + transmitir + mandar reporte).

**La diferencia clave**: el "ciclo completo" (recorrer las 8 ONUs y volver a
la primera) **no tiene una duración fija** — depende de cuánto tenían para
transmitir las ONUs:

- Si todas las colas están vacías: el ciclo dura solo **8 microsegundos**
  (8 ONUs × 1 μs de "tiempo de guarda" entre una y otra, sin transmitir
  nada).
- Si todas están saturadas (cada una usa su tope máximo de 38,880 bytes =
  125 μs de transmisión): el ciclo dura **8 × (125+1) μs ≈ 1008
  microsegundos ≈ 1 milisegundo**.

Esta variabilidad (8 μs a 1 ms) es justamente lo que se compara contra la
"trama fija de 125 μs" de GIANT/QoSDBA en el gráfico
`cycle_time_distribution.png`.

---

## 6. Las 3 "reglas de reparto" en detalle (qué cambia entre algoritmos)

| | **QoSDBA** (heredado de Fase 2, re-ajustado) | **GIANT** (nativo de XG-PON/GPON) | **IPACT** (adaptado de EPON) |
|---|---|---|---|
| **T-CONT1 (voz)** | Cada ONU recibe **siempre** 160 bytes por trama, sin importar si los necesita o no — reserva fija e incondicional | Igual que QoSDBA: reserva fija de 160 bytes/trama, incondicional | **No** hay reserva fija — la OLT le da a T1 lo que pidió en su *último reporte* (que puede ser de hace ~1 ciclo) |
| **T-CONT2 (video)** | Cada trama, según lo que pidió, hasta un tope, repartiendo lo que sobra entre todas las ONUs en partes iguales | Cada ONU tiene un "turno especial" cada 8 tramas (~1 ms): cuando le toca, puede pedir una ráfaga más grande de una sola vez ("recuperar el atraso") | Igual que T1: según el último reporte, dentro del permiso total de la ONU |
| **T-CONT4 (datos)** | Lo que sobra después de T1+T2, repartido proporcionalmente a cuánto pidió cada ONU | Cada ONU tiene un "turno" cada 32 tramas (~4 ms) para competir por el sobrante; si sigue con cola llena después de su turno, **vuelve a competir el siguiente turno sin esperar** (para no dejarla esperando bajo mucha carga) | Igual: lo que sobra del permiso total de la ONU, según su último reporte |

**¿Por qué importa esto?** Porque T-CONT1 (voz) tiene el límite más
exigente: **2 milisegundos**. En GIANT y QoSDBA, como la reserva es
*incondicional* (la ONU siempre tiene ese espacio reservado, lo use o no),
la voz **nunca** tiene que esperar más de 1 trama (125 μs) + el viaje
(100 μs) ≈ poco más de 0.2 ms — muy por debajo del límite de 2 ms.

En IPACT, en cambio, como T1 depende del *último reporte* (que puede ser de
~1 ciclo de antigüedad, y el ciclo puede durar hasta ~1 ms bajo saturación),
en el **peor caso** un paquete de voz podría tener que esperar
**~2 ciclos completos** antes de ser transmitido — acercándose o incluso
superando el límite de 2 ms. **Esto es exactamente la comparación que pidió
la profesora**: "reserva garantizada siempre" (GIANT/QoSDBA) vs. "reparto
según demanda reportada" (IPACT) — no es un error del simulador, es el
resultado esperado y el punto central del análisis.

---

## 7. ¿Qué mide el simulador al final de cada corrida?

Por cada combinación (ONU, tipo de tráfico), después de descartar el primer
segundo (warmup, para que la simulación llegue a un "régimen estable"):

| Métrica | Qué significa, en simple |
|---|---|
| **Latencia media / P95 / P99 / máxima** | Cuánto tiempo pasa, en promedio (o en el peor 5%/1%/caso absoluto), desde que se generó un paquete hasta que llegó a la OLT |
| **Jitter** | Cuánto "varía" la latencia de un paquete al siguiente — importante para voz/video, donde la variación se nota como "cortes" |
| **Throughput (Mbps)** | Cuántos datos efectivamente se entregaron por segundo |
| **Loss rate** | Qué porcentaje de los paquetes generados se perdieron por buffer lleno |
| **SLA compliance (%)** ⭐ NUEVO | De todos los paquetes, ¿qué porcentaje llegó **dentro** del límite permitido (2/20/500 ms según el tipo)? Idealmente 100% |
| **Latencia máxima (μs)** ⭐ NUEVO | El peor caso observado — ¿llegó alguna vez a superar el límite SLA? |
| **Utilización del canal/ciclo (%)** | Qué porcentaje de la capacidad disponible se usó realmente — útil para ver si el sistema está sobrecargado (cerca de 100%) o desaprovechado |
| **Tiempo de ciclo (solo IPACT)** | Duración real del "recorrido completo" de las 8 ONUs — entre 8 μs (vacío) y ~1008 μs (saturado) |

---

## 8. ¿Se cumple lo que pidió la profesora?

| Lo que pidió la profesora (reunión 9/6/2026) | ¿Se hizo? | Dónde |
|---|---|---|
| Cambiar de GPON (G.984) a **XG-PON (G.987)** | ✅ Sí | `configs/xgpon.json`: 2.48832/9.95328 Gbps, 38,880 bytes/trama |
| **8 ONUs idénticas** (antes 32) | ✅ Sí | `num_onus = 8`, mismas tasas/buffers para las 8 |
| Foco en **subida (upstream) solamente** | ✅ Sí | Igual que en Fase 2, sin cambios |
| El problema central es **cumplir un SLA**, con **T-CONT1 ≤ 2 ms** como meta principal | ✅ Sí | Tabla de SLA en config + nueva métrica `sla_compliance_pct` |
| Comparar **IPACT** (polling, adaptado de EPON, declarado como tal) vs **GIANT** (nativo de XG-PON) vs **QoSDBA** (de Fase 2, reajustado) | ✅ Sí | Los 3 algoritmos implementados y ejecutables |
| Cada ONU genera **varios tipos de tráfico a la vez**, con SLA por tipo, midiendo **demora máxima** y **tasa de transmisión** | ✅ Sí | T-CONT1/2/4 simultáneos, `latency_max_us` + `throughput_mbps` |
| Topología "muy bien descrita" (distancias, etc.) | ⚠️ En progreso | Descrita en `PARA_LA_PROFE_FASE3.md`; se está reforzando en `DOCUMENTACION_TECNICA_FASE3.md` |
| Fase 2 no se toca (es entregable ya evaluado) | ✅ Sí | Verificado: `main.py` sigue funcionando igual que antes |

---

## 9. Glosario rápido

- **OLT**: la central del proveedor (un equipo, no un edificio).
- **ONU**: el equipo en casa del usuario (la "roseta" óptica).
- **T-CONT**: una "cola" de tráfico de un tipo específico dentro de una ONU.
- **DBA**: el algoritmo que decide cómo repartir el ancho de banda compartido.
- **BWmap**: el "mapa de permisos" que la OLT manda a todas las ONUs (camino broadcast).
- **GATE**: el "permiso individual" que la OLT le manda a una ONU específica (camino IPACT/polling).
- **DBRu**: el reporte que cada ONU manda a la OLT diciendo cuánto tiene en sus colas.
- **SLA** (Service Level Agreement): el compromiso de calidad — "esto no debe demorar más de X".
- **RTT** (Round Trip Time): tiempo de ida y vuelta por la fibra (200 μs en este proyecto).
- **Upstream**: el sentido "subida" — de las ONUs hacia la OLT (el foco de este proyecto).
- **B_max**: el tope máximo de bytes que IPACT le permite transmitir a una ONU en un solo turno.
- **SImax / SImin**: los "contadores de turnos" de GIANT (cada cuántas tramas le toca a una ONU un permiso especial para T2/T4).

---

*OmneTeam — David Retuerto · José Vega · Matías Perelli — TEL-341 UTFSM 2026*
