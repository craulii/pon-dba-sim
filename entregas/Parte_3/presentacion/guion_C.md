# Guion — Presentador C (slides 15-21)

**Tu parte:** experimentos, validación, resultados, estadística y conclusiones.
Es la parte que tiene gráficos para apoyarte. Los slides más difíciles son el
16 (validación, hay que saber derivar las cotas) y el 18 (por qué falla IPACT,
hay que explicar el mecanismo causal). El resto se explica señalando gráficos.

**Transición de entrada:** recibes la posta de B al final del slide 14.
**Transición de salida:** tú cierras la presentación con las conclusiones y
quedas al frente para coordinar las preguntas.

---

## Lo que hay que saber antes de empezar

**La pregunta que más te van a hacer:** "¿cómo validaron el simulador?"

Respuesta: con dos cotas analíticas derivadas del estándar:

1. **Ciclo máximo de IPACT:** `8 × (125 µs + 1 µs) = 1008 µs`
   → el simulador mide exactamente 1008.000 µs bajo saturación.

2. **Latencia máxima de T-CONT1 en GIANT/QosDBA:** `125 + 100 + 100 + 1.03 ≈ 226 µs`
   → el simulador mide 226.0288 µs con IC95% = 0 (sin aleatoriedad en ese camino).

Si hubiera discrepancia, habría un bug. Coinciden exactamente → el motor,
el modelo de propagación y la lógica de asignación son correctos.

**También te preguntarán:** "¿qué significa el 88.4%?" → El 11.6% de los
paquetes de VoIP bajo IPACT a 800 Mbps/ONU tardaron más de 2 ms. El 88.4%
llegó dentro del SLA.

---

## Slide 15: Entradas del simulador y diseño experimental

Los parámetros físicos de la red vienen todos del estándar ITU-T G.987 — no
se inventó ningún número. Las únicas decisiones propias del equipo fueron:

- Las tasas de T-CONT4 (200 / 400 / 800 Mbps/ONU) como barrido de carga.
  Representan 64%, 129% y 257% de la capacidad upstream.
- Los SLA de T-CONT2 (20 ms) y T-CONT4 (500 ms). El de T-CONT1 (2 ms) fue
  pedido explícito.
- Los contadores SImax=8 y SImin=32 de GIANT. El estándar define un rango,
  no valores únicos — se eligieron valores típicos de la literatura.

**Diseño experimental:**
- 9 escenarios = 3 algoritmos × 3 cargas.
- 10 réplicas por escenario, seeds 6767 a 6776.
- 10 s simulados, 1 s de warmup descartado.
- Tiempo total de CPU: ~5 minutos.

**Posible pregunta:** "¿Por qué esas tres cargas específicas (200/400/800)?"
→ Para barrer subcarga (64%), sobrecarga leve (129%) y sobrecarga severa (257%).
Se eligieron en escala ×2 para capturar el punto de cruce donde IPACT empieza
a fallar (ocurre entre 200 y 400 Mbps/ONU).

---

## Slide 16: Validación — cotas teóricas vs. simulación

Este es el slide más importante de robustez. Sin red real ni simulador de
referencia, la única forma de validar es verificar que el simulador reproduce
valores que se pueden calcular analíticamente desde el estándar.

### Cota (a): Ciclo máximo de IPACT bajo saturación

Cuando el canal está saturado, cada ONU siempre recibe su grant máximo de
b_max = 38.880 bytes = 125 µs de transmisión. Más 1 µs de guard time por ONU:

```
ciclo = N × (B_max × 8 / R + t_guard)
      = 8 × (38880 × 8 / 2.48832×10⁹  +  1×10⁻⁶)
      = 8 × (125 µs + 1 µs)
      = 8 × 126 µs = 1008 µs
```

El simulador mide exactamente **1008.000 µs**. No es aproximado, es exacto
al µs. Si hubiera dado distinto, habría un bug en la lógica de polling.

### Cota (b): Latencia máxima de T-CONT1 en GIANT/QosDBA

Peor caso: el paquete llega justo después de que se cerró el BWmap. Espera
hasta la siguiente trama (hasta 125 µs). Después:

```
latencia_max = espera_trama + prop_BWmap + prop_datos + tx
             = 125 µs + 100 µs + 100 µs + 1.03 µs
             = 226.03 µs
```

El simulador mide **226.0288 µs** con IC95% de ancho = 0 — las 10 réplicas
dan exactamente el mismo número porque T-CONT1 es CBR (sin aleatoriedad) y
GIANT reserva 160 bytes fijos por trama (sin aleatoriedad). Un camino 100%
determinístico produce varianza 0.

**Si preguntan "¿por qué 226 y no 325?"** → El delay del BWmap (100 µs) no
se suma linealmente — el paquete espera en el buffer mientras el BWmap ya
está en camino. Lo que se mide es el tiempo desde que el paquete llega al
buffer hasta que la OLT lo recibe: ese es `engine.now - creation_time`.

---

## Slide 17: Resultado central — cumplimiento del SLA

El gráfico de barras es el resultado más directo. Señalar y explicar:

- Todas las barras están en 100% excepto una: **T-CONT1 bajo IPACT a
  800 Mbps/ONU = 88.4%**.
- GIANT y QosDBA: 100% en T-CONT1 para las 3 cargas, sin excepción.
- T-CONT2 y T-CONT4: todos en 100% también (sus SLA son más laxos).

**Por qué 88.4% y no 100%:**
A 800 Mbps/ONU la demanda supera ampliamente la capacidad. El ciclo de IPACT
se satura en 1008 µs. Un paquete de VoIP puede acumular hasta ~2 ciclos de
espera antes de que le toque transmitir → latencia máxima ~2.1 ms → viola el
SLA de 2 ms. El 11.6% de los paquetes T-CONT1 de IPACT superan ese umbral.

**Por qué GIANT y QosDBA dan siempre 100%:**
Ambos reservan 160 bytes para T-CONT1 incondicionalmente en cada BWmap — sin
importar cuánto tráfico haya de T-CONT4. La VoIP siempre tiene su slot
garantizado cada 125 µs → latencia máxima de 226 µs, muy por debajo de 2 ms.
La carga de datos no puede "robarle" el turno al VoIP.

**Posible pregunta:** "¿Por qué GIANT y QosDBA dan exactamente el mismo
resultado para T-CONT1?" → Porque los dos reservan T-CONT1 de la misma forma:
160 bytes fijos por trama, sin condición. Se diferencian en cómo tratan T-CONT2
y T-CONT4, no en VoIP.

---

## Slide 18: Por qué falla IPACT

El gráfico muestra el delay máximo de T-CONT1 vs. carga T-CONT4:

- **200 Mbps/ONU (64%)**: IPACT da ~820 µs máximo. Ya es 3.6× peor que GIANT
  (226 µs), pero aún dentro del SLA de 2000 µs.
- **400 Mbps/ONU (129%)**: el ciclo de IPACT se satura → delay máximo = 2109 µs.
  Cruza el umbral de 2 ms. Aquí empieza a fallar el SLA.
- **800 Mbps/ONU (257%)**: igual que 400 Mbps — saturado en 1008 µs de ciclo,
  misma latencia máxima. No empeora porque el ciclo ya estaba en su límite.

GIANT y QosDBA: línea plana en 226 µs para las 3 cargas. La reserva
incondicional desacopla completamente T-CONT1 del resto del tráfico.

**El mecanismo técnico del fallo — esto es lo que hay que explicar bien:**

IPACT calcula el grant para cada ONU mirando el último reporte (DBRu) que
tiene de esa ONU. Bajo saturación, ese reporte puede tener hasta 1 ciclo
(1008 µs) de antigüedad. En ese tiempo, la ONU puede haber recibido paquetes
de T-CONT1 nuevos que todavía no aparecen en el reporte. Esos paquetes esperan
hasta el próximo GATE de esa ONU → latencia acumulada que supera 2 ms.

GIANT no tiene ese problema: el BWmap se emite cada 125 µs y T-CONT1 siempre
tiene sus 160 bytes reservados, independientemente de reportes.

**Posible pregunta:** "¿Por qué no sube la latencia entre 400 y 800 Mbps/ONU?"
→ Porque el ciclo de IPACT ya está completamente saturado en 1008 µs desde los
400 Mbps/ONU. El límite físico del ciclo es 1008 µs — más demanda no produce
ciclos más largos.

---

## Slide 19: El mecanismo detrás (histogramas de ciclo)

El gráfico muestra la distribución del tiempo de ciclo de IPACT:

- **200 Mbps/ONU**: histograma distribuido entre 16 y ~400 µs. El canal tiene
  capacidad de sobra — el ciclo varía según la carga instantánea.
- **400 Mbps/ONU**: una sola barra en 1008 µs. Histograma degenerado. El canal
  está saturado el 100% del tiempo.
- **800 Mbps/ONU**: idéntico al de 400 Mbps. No hay diferencia porque el sistema
  ya estaba saturado.

GIANT y QosDBA siempre operan a 125 µs — se muestra con la línea punteada de
referencia, no como histograma (sería una línea vertical en 125 µs).

**Qué dice esto:** la transición entre 200 y 400 Mbps/ONU no es gradual — el
sistema pasa de "variable" a "siempre saturado". Es un comportamiento de
saturación abrupta, no una degradación suave.

---

## Slide 20: Confiabilidad estadística

**IC95%:** con 10 réplicas, el intervalo de confianza al 95% se calcula como:
```
IC95% = ȳ ± 1.96 · s / √10
```
donde `ȳ` es la media de las 10 réplicas y `s` es la desviación estándar
muestral.

**Dos casos distintos:**

1. **Camino determinístico** (T-CONT1 en GIANT/QosDBA): CBR + grant fijo =
   sin aleatoriedad en ningún paso. Las 10 réplicas dan exactamente el mismo
   número → `s = 0` → IC95% = 0. No es un error — es la naturaleza del
   sistema.

2. **Camino con aleatoriedad** (todo lo que involucra Pareto o IPACT):
   variabilidad entre réplicas existe, pero es pequeña — error relativo
   < 0.1% para latencia media. Los gráficos muestran los IC95% como barras
   de error (en algunos casos son tan pequeños que no se ven).

**¿Son suficientes 10 réplicas?** Sí. La diferencia entre IPACT (88.4%) y
GIANT (100%) es de 11.6 puntos porcentuales. El IC95% del 88.4% es de ±0.3%.
La diferencia es 38× mayor que el margen de error → la conclusión es sólida
con 10 réplicas.

**Posible pregunta:** "¿No deberían usar t de Student con n=10?" → Estrictamente
sí, con t₀.₀₂₅,₉ = 2.262 en vez de 1.96 (z₀.₀₂₅). En la práctica la diferencia
entre usar 1.96 y 2.262 es pequeña, y la práctica habitual en simulación de
redes usa 1.96. Las conclusiones no cambian.

---

## Slide 21: Conclusiones

El mensaje central: **cumplir un SLA estricto de latencia no es automático —
el algoritmo DBA importa, y de forma fundamental.**

Tres puntos que hay que dejar claros:

1. **Reservar incondicionalmente (GIANT, QosDBA) = SLA garantizado en cualquier
   carga.** No importa cuánto tráfico de datos haya — la VoIP siempre tiene su
   slot. La latencia máxima de T-CONT1 es 226 µs en todos los escenarios.

2. **Asignar según demanda reportada (IPACT) = fallo bajo sobrecarga.** El
   reporte siempre tiene al menos un ciclo de retraso. Bajo saturación ese
   retraso supera 2 ms para el 11.6% de los paquetes VoIP.

3. **Hay un trade-off:** QosDBA protege mejor T-CONT1 y T-CONT2 pero pierde
   eficiencia en T-CONT4 (73% de utilización vs 94-97% de IPACT/GIANT). No
   existe un algoritmo que sea simultáneamente el mejor en todo.

**Si preguntan qué recomendarían para una red real:**
→ GIANT o QosDBA para cualquier red con SLA de VoIP. IPACT puede ser
suficiente en redes muy subcargadas, pero falla exactamente cuando más se
necesita (bajo sobrecarga), que es el peor momento posible para fallar.

---

## Demo en vivo (si se hace durante tu parte)

Para mostrar el simulador corriendo y ver la diferencia en tiempo real.
Abrir dos terminales antes de presentar:

```bash
# Terminal 1 — GIANT, VoIP siempre estable en ~165µs
python main.py --algorithm giant --load 800 --demo

# Terminal 2 — IPACT, VoIP sube hasta ~2000µs bajo saturación
python main.py --algorithm ipact --load 800 --demo
```

Lo que muestra cada actualización:
- `t=X.XXXs (YY.Y%)` — tiempo simulado y progreso
- `evts=N` — eventos procesados por el motor DES
- `T1: XXXµs✓` — latencia media de VoIP con marca SLA
- `T2: XXXXµs✓` — latencia media de Video
- `T4: XXXXXµs✓` — latencia media de Datos

GIANT mostrará T1 siempre en ~165 µs ✓.
IPACT mostrará T1 subiendo progresivamente hasta ~1600-2000 µs, con ✗ cuando
supera 2000 µs.

---

## Tus preguntas más probables

**"¿Cómo validaron el simulador?"**
→ Dos cotas analíticas: (a) ciclo máximo IPACT = 1008 µs exactos; (b) latencia
máxima T-CONT1 en GIANT = 226.03 µs. El simulador reproduce ambas exactamente.
Si hubiera discrepancia, habría un bug demostrable.

**"¿Por qué la condición de término es 10 segundos?"**
→ Suficiente para régimen estacionario y miles de muestras por T-CONT. Con
menos tiempo los efectos del warmup dominan. Con más, las conclusiones no
cambian y el CPU tarda más.

**"¿Cuántas réplicas usaron y por qué?"**
→ 10 réplicas, seeds 6767 a 6776. IC95% = ȳ ± 1.96·s/√10. El error relativo
es < 0.1% para latencia media. La diferencia entre IPACT y GIANT (11.6 puntos)
es 38× mayor que el margen de error — 10 réplicas son más que suficientes.

**"¿Qué significa el 88.4%?"**
→ El 11.6% de los paquetes VoIP bajo IPACT a 800 Mbps/ONU tardaron más de
2 ms. El 88.4% llegó dentro del SLA. Los paquetes tardíos no se descartan —
llegan igual, pero fuera del límite de calidad.

**"¿Por qué no sube la latencia de IPACT entre 400 y 800 Mbps/ONU?"**
→ Porque el ciclo ya estaba completamente saturado en 1008 µs desde los
400 Mbps/ONU. Es el límite físico del protocolo — más demanda no produce
ciclos más largos.

**"¿Por qué GIANT y QosDBA dan exactamente el mismo número para T-CONT1?"**
→ Porque los dos reservan T-CONT1 de la misma forma: 160 bytes fijos por
trama, sin condición. Se diferencian en T-CONT2 y T-CONT4, no en VoIP.

**"¿10 réplicas son suficientes?"**
→ Sí para esta diferencia. El IC95% de la diferencia (11.6%) es mucho mayor
que el margen de error (±0.3%). Con más réplicas los intervalos se achicarían,
pero la conclusión no cambia.

**"¿Cuál recomendarían para una red real?"**
→ GIANT o QosDBA para cualquier red con SLA de VoIP. IPACT puede funcionar
en redes subcargadas pero falla exactamente cuando la red más lo necesita.

---

## Números que debes tener frescos

| Concepto | Valor |
|---|---|
| Upstream XG-PON1 | 2.48832 Gbps |
| Trama | 125 µs |
| Bytes por trama | 38.880 bytes |
| ONUs | 8 |
| Delay propagación (ida) | 100 µs |
| SLA T-CONT1 | ≤ 2 ms |
| SLA T-CONT2 | ≤ 20 ms |
| SLA T-CONT4 | ≤ 500 ms |
| Carga 200 Mbps/ONU | 64% de capacidad |
| Carga 400 Mbps/ONU | 129% de capacidad |
| Carga 800 Mbps/ONU | 257% de capacidad |
| SLA T-CONT1 IPACT @ 800 Mbps/ONU | 88.4% |
| SLA T-CONT1 GIANT/QosDBA | 100% siempre |
| Delay máx T-CONT1 IPACT @ 400+ Mbps | 2109 µs |
| Delay máx T-CONT1 GIANT/QosDBA | 226 µs siempre |
| Ciclo IPACT saturado | 1008 µs = 8 × 126 µs |
| Throughput IPACT/GIANT @ 800 Mbps/ONU | 94 a 97% |
| Throughput QosDBA @ 800 Mbps/ONU | 73% |
| Réplicas por escenario | 10 (seeds 6767 a 6776) |
| Duración simulada | 10 s (1 s warmup) |
| IC95% fórmula | ȳ ± 1.96 · s / √10 |
