# Guion interno — Presentación XG-PON (Fase 3)

## OmneTeam — esto NO es un libreto

Este documento no es para leer en voz alta. Es para repasar antes de la
presentación y tenerlo a mano durante la sesión de preguntas, por si la
profesora pregunta algo que la diapositiva no cubre del todo. Las
diapositivas dicen lo justo para que se entienda rápido; acá está el
contexto completo, el "por qué" detrás de cada decisión, y las preguntas
que más probablemente nos van a hacer.

---

## Slides 1-2: Portada y agenda

No hay mucho que agregar. Si preguntan por qué solo aparecen 3 nombres y
no se menciona Fase 1/Fase 2: el proyecto pasó por 3 etapas (OMNeT++
rechazado, GPON G.984 en Python, y esta, XG-PON). Esta presentación es
solo de la fase actual porque es la que la profesora pidió ver.

## Slide 3: El problema

Punto clave que no está en el slide: la fibra en sí no es el cuello de
botella, es el **protocolo de acceso al medio en upstream**. El downstream
es broadcast (todas las ONUs reciben la misma señal óptica y filtran lo
que es para ellas), así que ahí no hay contención. El problema entero del
proyecto vive en upstream.

**Posible pregunta:** "¿Por qué no puede transmitir más de una ONU a la
vez?" → Porque todas comparten la misma fibra física hacia la OLT
(después del splitter), es un solo receptor óptico del lado de la OLT. Es
TDMA: time division multiple access, un slot de tiempo por transmisor.

## Slide 4: La red (XG-PON1)

Por qué elegimos XG-PON y no nos quedamos en GPON: fue un pedido explícito
de la profesora en la reunión del 9/6. XG-PON1 (ITU-T G.987) es
básicamente GPON pero al doble de velocidad upstream y cuádruple en
downstream, misma estructura de trama de 125 microsegundos.

**Por qué 8 ONUs y no 32 (como en la fase anterior):** también pedido de
la profesora, para poder enfocarse en el algoritmo de DBA en vez de en la
escala.

**Posible pregunta:** "¿Por qué 20 km?" → Es la distancia que ya
veníamos usando en la fase anterior, y corresponde a la clase de alcance
nominal N1 del estándar G.987.2. La mantuvimos para poder comparar el RTT
entre fases.

## Slide 5: T-CONTs

Punto importante: el estándar define 5 tipos de T-CONT (1 al 5), nosotros
usamos solo 3 (1, 2 y 4) para tener clases bien diferenciadas: fija,
garantizada y best-effort. Si preguntan por qué no usamos los 5: lo
decidimos en la fase anterior para no complicar el análisis con clases
redundantes (T-CONT 3 y 5 son combinaciones de las otras).

**Por qué cada tasa:** T-CONT1 (VoIP) usa 1 Mbps fijo porque es lo mismo
que en la fase anterior (la voz no cambia entre estándares). T-CONT2 y
T-CONT4 se escalaron x8 respecto a la fase anterior porque la capacidad
total de XG-PON es x8 por ONU (2488.32/8 vs 1244.16/32).

## Slide 6: El SLA

Esta es la diapositiva más importante para que quede clara la diferencia
entre los 3 números: el de T-CONT1 (2 ms) es un requisito real, puesto
por la profesora. Los de T-CONT2 (20 ms) y T-CONT4 (500 ms) los pusimos
nosotros como referencia razonable, no son normas ITU-T. Si la profesora
pregunta por qué 20 ms y no otro número para T-CONT2: es el rango típico
para video interactivo/baja latencia, no hay una cifra oficial del
estándar para eso.

**Posible pregunta:** "¿Qué pasa si un paquete no cumple el SLA, se
descarta?" → No, igual se entrega, solo se cuenta como una violación de
SLA para la métrica `sla_compliance_pct`. El descarte real (pérdida) pasa
aparte, cuando el buffer de la ONU se llena.

## Slide 7-8: El problema del DBA y las 2 arquitecturas

Acá es donde hay que tener más cuidado con el framing. En la Fase 2
dijimos explícitamente "no usar IPACT porque es de EPON, no de GPON". En
esta fase lo usamos de nuevo, pero como punto de comparación declarado,
no como si fuera nativo de GPON/XG-PON. Si preguntan por esa
contradicción: la profesora pidió explícitamente esta comparación en la
reunión del 9/6, es un giro intencional del enfoque, no un error de
diseño.

**Diferencia clave a tener clara:** broadcast (SR-DBA) decide para las 8
ONUs de una vez, cada trama fija. Polling decide ONU por ONU, en orden, y
el ciclo dura lo que tarde en recorrerlas a todas.

## Slide 9: Los 3 algoritmos

Detalles que no entran en la tabla pero pueden preguntar:

- **GIANT**: el contador SImax (8 tramas = 1 ms) es para T-CONT2, el
  SImin (32 tramas = 4 ms) es para T-CONT4. La idea es que T-CONT2 tiene
  garantía de servicio más frecuente que T-CONT4 (jerarquía GPA por
  encima de SPA).
- **QoSDBA**: no tiene contadores de servicio, es prioridad pura. Por eso
  es más simple, pero también por eso es menos eficiente con el tráfico
  de datos (ver el apéndice de eficiencia).
- **IPACT**: el "guard time" de 1 microsegundo es el tiempo muerto entre
  ONUs consecutivas (tiempo de cambio de transmisor), valor típico de la
  literatura de EPON.

**Posible pregunta:** "¿Por qué el ciclo máximo de IPACT es exactamente
1008 microsegundos?" → 8 ONUs x (125 us de transmisión máxima + 1 us de
guard time) = 8 x 126 = 1008 us.

## Slide 10: Arquitectura del simulador

Si preguntan "¿usaron algún framework de simulación?": no, el motor de
eventos, la red, los algoritmos, todo está escrito desde cero en Python
puro. Es uno de los requisitos explícitos del curso.

## Slides 11-12: Motor de eventos y generación de tráfico

Estas son las diapositivas que más le importan a la profesora según lo
que pidió: el cómo, no el resultado. Vale la pena remarcar en voz alta el
punto del reloj que "salta" en vez de avanzar de a poco, porque es la
diferencia conceptual central entre un simulador de eventos discretos y
una simulación de pasos fijos (time-stepped).

**Sobre el self-scheduling:** la razón de que cada paquete agende su
propio sucesor (en vez de tener un proceso "generador" separado
corriendo todo el tiempo) es que en un simulador de eventos discretos no
existe "todo el tiempo" corriendo, solo existen los momentos en que algo
pasa. Si no hay un evento programado, no hay nada que computar en el
medio.

**Posible pregunta:** "¿Cómo garantizan que el orden de los eventos sea
determinístico?" → Cada evento tiene un número de secuencia además del
tiempo, así que si dos eventos caen exactamente en el mismo instante, el
orden de desempate es siempre el mismo (el que se agendó primero se
procesa primero). Eso hace que correr con la misma semilla dé siempre el
mismo resultado.

## Slide 13: Tráfico simulado (la figura)

Ojo con esto: la figura usa una tasa **inventada** (1 ms de media para
los 3 T-CONTs) solo para que se vea la forma de cada distribución en el
mismo eje. Las tasas reales de la simulación son muy distintas entre
T-CONTs (1 Mbps vs 40 Mbps vs 200-800 Mbps), así que no se podrían
comparar visualmente en una sola figura sin normalizar.

**Por qué Pareto para T-CONT4 y no otra distribución de cola pesada:** es
la misma fórmula que se usó en el simulador anterior (la versión Python
de GPON), se mantuvo por consistencia. Alpha=1.5 es un valor típico para
modelar tráfico de datos con ráfagas (self-similarity).

## Slide 14: Diseño experimental

Por qué esas 3 cargas (200, 400, 800 Mbps/ONU): corresponden a
aproximadamente el mismo porcentaje de sobrecarga que se usó en la fase
anterior (64%, 129%, 257%), para poder comparar el comportamiento bajo
subcarga, carga límite y sobrecarga severa.

**Posible pregunta:** "¿10 repeticiones son suficientes?" → Es lo mismo
que se usó en la fase anterior y alcanza para que los intervalos de
confianza al 95% sean chicos comparados con las diferencias que estamos
viendo (88% vs 100% es una diferencia grande, no es ruido estadístico).

## Slides 15-17: Los resultados (el núcleo de la presentación)

Esta es la parte donde hay que estar más preparados, porque es el
resultado central del proyecto.

**La idea en una frase:** GIANT y QoSDBA reservan el ancho de banda de
voz sin condiciones, en cada trama, así que no les importa qué tan
cargada esté la red. IPACT decide cuánto darle a la voz mirando el último
reporte que tiene, y ese reporte puede tener casi un ciclo completo de
antigüedad. Bajo carga alta, ese ciclo se estira hasta 1008
microsegundos, y ahí es donde la voz empieza a esperar casi 2 ciclos
completos: justo por encima del límite de 2 ms.

**Posible pregunta:** "¿Por qué GIANT y QoSDBA dan exactamente el mismo
número (226 us) si son algoritmos distintos?" → Porque ambos reservan
T-CONT1 de la misma forma (160 bytes fijos cada trama, sin condición), la
diferencia entre GIANT y QoSDBA está en cómo reparten T-CONT2 y T-CONT4,
no en T-CONT1.

**Posible pregunta difícil:** "¿No es un poco injusto comparar un
algoritmo de otro estándar (IPACT/EPON) contra dos algoritmos pensados
para GPON?" → Es exactamente el punto. No estamos diciendo que IPACT sea
una mala implementación, estamos mostrando que el **mecanismo** de
asignar por demanda con un reporte desactualizado tiene una debilidad
estructural frente al SLA de voz, mientras que el mecanismo de reserva
incondicional no la tiene. Es una comparación de arquitecturas, no de qué
tan bien programado está cada uno.

## Slide 18: Conclusiones

El punto que no hay que perder: cumplir el SLA no depende de qué tan
"inteligente" sea el algoritmo, depende de si reserva sin condiciones o
no. Eso es contraintuitivo porque uno podría pensar que un algoritmo más
sofisticado (como IPACT, que ajusta dinámicamente según demanda) sería
mejor, pero para tráfico estricto en latencia, la simplicidad de "siempre
reservar" gana.

## Apéndice (solo si preguntan)

- **Dashboard:** es un resumen visual de las 4 figuras principales, útil
  si quieren ver todo junto sin pasar diapositiva por diapositiva.
- **Eficiencia agregada:** QoSDBA pierde eficiencia porque reparte
  T-CONT4 de forma proporcional a la demanda de cada ONU, lo que deja
  capacidad sin usar cuando algunas ONUs no tienen mucho que transmitir.
  GIANT usa round-robin entre las ONUs que sí tienen demanda, así que
  aprovecha mejor lo que sobra.

---

## Preguntas difíciles transversales

- **"¿Por qué en la fase anterior dijeron que IPACT no aplica a GPON y
  ahora lo usan?"** → El encuadre cambió. Antes el error habría sido usar
  IPACT para *modelar* GPON (mezclar conceptos de dos estándares
  distintos). Ahora lo usamos para *comparar contra* GPON/XG-PON, de
  forma explícita y declarada. Es un ejercicio de benchmarking, no una
  afirmación de que una OLT XG-PON real corra IPACT.
- **"¿Por qué T-CONT2 y T-CONT4 no tienen un SLA de un estándar real?"**
  → Porque el estándar no define cotas de latencia para tráfico
  garantizado o best-effort, solo para el tipo de tráfico de mayor
  prioridad (que en nuestro caso es T-CONT1). Las cotas que usamos son
  metas razonadas del equipo, lo decimos explícitamente en la
  diapositiva.
- **"¿Cómo saben que el motor de eventos está bien implementado?"** → Es
  determinístico (mismo seed, mismo resultado), procesa los eventos en
  orden estricto de tiempo, y los resultados son consistentes con lo que
  predice la teoría (por ejemplo, el ciclo máximo de IPACT calculado a
  mano coincide con lo que mide la simulación).
- **"¿Por qué no probaron con más ONUs o más cargas?"** → Por tiempo y
  porque el punto del proyecto era comparar mecanismos de DBA bajo un
  rango de carga representativo (subcarga, límite, sobrecarga severa),
  no hacer un barrido exhaustivo de parámetros.

---

## Números para tener frescos

| Cosa | Valor |
|---|---|
| Upstream XG-PON1 | 2.48832 Gbps |
| Trama | 125 $\mu$s |
| ONUs | 8 |
| SLA T-CONT1 | $\leq$ 2 ms (pedido de la profesora) |
| SLA T-CONT2 / T-CONT4 | $\leq$ 20 ms / $\leq$ 500 ms (metas del equipo) |
| Cumplimiento SLA T-CONT1 @ 800 Mbps/ONU | IPACT 88.4% / GIANT 100% / QoSDBA 100% |
| Delay máximo T-CONT1 @ 800 Mbps/ONU | IPACT 2109 $\mu$s / GIANT 226 $\mu$s / QoSDBA 226 $\mu$s |
| Ciclo IPACT (saturado) | 1008 $\mu$s = 8 $\times$ (125+1) $\mu$s |
| Throughput agregado @ 800 Mbps/ONU | IPACT 2424.5 / GIANT 2343.3 / QoSDBA 1812.6 Mbps |
