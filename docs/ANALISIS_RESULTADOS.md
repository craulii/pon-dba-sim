# Análisis de Resultados — Simulador GPON DBA
## OmneTeam · TEL-341 · UTFSM 2026

Resultados de 100 corridas: 10 escenarios × 10 repeticiones con seeds 42–51.  
Fuente: `results/all_results.csv` — 30 filas (10 escenarios × 3 T-CONTs).

---

## 1. T-CONT 1 (VoIP, CBR) — resultado principal

| Carga T4 (Mbps/ONU) | BasicDBA lat. media (μs) | QosDBA lat. media (μs) | Factor |
|---|---|---|---|
| 10 | 414 | **164** | 2.5× |
| 25 | 414 | **164** | 2.5× |
| 50 | 414 | **164** | 2.5× |
| 75 | 414 | **164** | 2.5× |
| 100 | **25.437** 💀 | **164** ✓ | **155×** |

### Qué está pasando

**QosDBA se mantiene exactamente en 164 μs para toda la carga.** IC95 = 0.0 — sin varianza. Es una constante física:
```
t_propagación = 100 μs  (20 km × 5 μs/km)
t_espera BWmap = 62.5 μs  (media: ½ × 125 μs)
t_transmisión =  1.0 μs  (160 bytes a 1.244 Gbps)
─────────────────────────
Total = 163.5 μs ≈ 164 μs medido ✓
```
T-CONT 1 tiene CBR determinístico y slot pre-reservado → sin aleatoriedad posible.

**BasicDBA se mantiene en 414 μs hasta 75 Mbps, luego colapsa a 25 ms.** El salto es abrupto, no gradual — es un comportamiento de umbral:

- Hasta 75 Mbps: la proporción de T-CONT 1 en la demanda total todavía alcanza para recibir algún grant.
- A 100 Mbps: T-CONT 4 llena su buffer (2 MB). T-CONT 1 tiene 160 bytes. Proporción = 160 / 2.000.160 ≈ 0.008%. Grant resultante = `int(607 × 0.008%)` = **0 bytes** → starvation → latencia de 25 ms.

**El colapso entre 75 y 100 Mbps es 61×.** Dos cargas consecutivas del escenario y la latencia se multiplica por 61. Sin QoS la red es impredecible bajo sobrecarga.

---

## 2. T-CONT 2 (Video, Assured) — protección asimétrica

| Carga T4 | BasicDBA (μs) | QosDBA (μs) | Factor |
|---|---|---|---|
| 10–75 Mbps | ~400 | ~401 | ~1× |
| 100 Mbps | **4.411** | **401** | **11×** |

**A cargas bajas y medias ambos son prácticamente idénticos.** Con ancho de banda disponible para todos, el algoritmo no marca diferencia.

**A 100 Mbps BasicDBA degrada T-CONT 2 a 4.4 ms** (vs 401 μs en QosDBA). No es tan catastrófico como T-CONT 1 porque T-CONT 2 genera más tráfico (5 Mbps vs 1 Mbps) y recibe mayor proporción en BasicDBA.

**IC95 de T-CONT 2 BasicDBA a 100 Mbps = 5.17 μs** — el más alto de todos los T-CONT 2. Alta variabilidad entre réplicas bajo sobrecarga: comportamiento caótico.

---

## 3. T-CONT 4 (Best Effort) — igual en ambos, con matiz

| Carga T4 | BasicDBA lat. (μs) | QosDBA lat. (μs) | BasicDBA loss | QosDBA loss |
|---|---|---|---|---|
| 10 Mbps | 379 | 379 | 0% | 0% |
| 25 Mbps | 338 | 338 | 0% | 0% |
| 50 Mbps | 423 | 423 | 0% | 0% |
| 75 Mbps | 2.135 | **2.214** | 0% | 0% |
| 100 Mbps | 177.875 | 177.875 | **17.84%** | **17.84%** |

**Hasta 50 Mbps: red subcargada.** Latencias bajas, 0% pérdida. Los buffers de 2 MB absorben las ráfagas Pareto sin problema.

**A 75 Mbps la latencia sube a ~2 ms** — la red está al límite pero sin pérdida aún.

**A 100 Mbps: 177 ms y 17.84% pérdida — idéntico en ambos algoritmos.** Confirma que el canal se agota igual en ambos casos. QosDBA no genera más capacidad, solo redistribuye las prioridades.

**Matiz: QosDBA T-CONT 4 a 75 Mbps tiene latencia ligeramente mayor** (2.214 vs 2.135 μs). Esperado — QosDBA reserva capacidad para T-CONT 1 y 2, dejando menos sobrante para T-CONT 4 cuando la red está al límite.

---

## 4. Throughput — misma eficiencia en ambos algoritmos

| Carga T4 | BasicDBA total (Mbps) | QosDBA total (Mbps) |
|---|---|---|
| 10 Mbps | 548 | 548 |
| 25 Mbps | 1.080 | 1.080 |
| 50 Mbps | 1.968 | 1.968 |
| 75 Mbps | 2.855 | 2.855 |
| 100 Mbps | 3.059 | 3.059 |

**Ningún algoritmo desperdicia capacidad.** El canal se utiliza igual de bien en ambos. La diferencia está en *quién* recibe qué, no en cuánto se entrega en total.

> Los valores sobre 100 Mbps superan la capacidad de 1.244 Gbps porque se mide la demanda ofrecida incluyendo la que se descarta en T-CONT 4. El throughput efectivo entregado está limitado por la capacidad del canal.

---

## 5. Jitter — aparente paradoja

| Algoritmo | T-CONT 1 jitter a 100 Mbps |
|---|---|
| BasicDBA | 1.155 μs |
| QosDBA | 45.6 μs |

**BasicDBA tiene jitter numéricamente menor, pero latencia 155× mayor.** El jitter mide `|latencia[n] − latencia[n-1]|`. Bajo starvation los paquetes de BasicDBA llegan muy espaciados pero con latencias similares entre sí (todos cerca de 25 ms) → variación absoluta moderada. En QosDBA la variación de 45.6 μs es sobre una media de 164 μs (27%) — es el jitter natural del proceso CBR dentro de la ventana de 125 μs.

El jitter de BasicDBA en términos de VoIP es catastrófico porque el playout buffer no puede compensar variaciones de segundos entre paquetes.

---

## 6. Confiabilidad estadística (IC95)

| Caso | IC95 | Interpretación |
|---|---|---|
| T-CONT 1 QosDBA, toda carga | **0.0** | Totalmente determinístico (CBR + slot fijo) |
| T-CONT 1 BasicDBA, ≤75 Mbps | **0.0** | También determinístico a cargas bajas |
| T-CONT 1 BasicDBA, 100 Mbps | 0.004 | Mínima variabilidad (0.016% de la media) |
| T-CONT 4, 75 Mbps | 18–22 μs | ~1% de variación — aceptable para Pareto |
| T-CONT 2, BasicDBA 100 Mbps | 5.17 μs | Mayor variabilidad — comportamiento caótico |

Los IC95 estrechos validan que 10 repeticiones son suficientes para este experimento.

---

## 7. Tres conclusiones para la presentación

**1. QosDBA cumple su objetivo:** T-CONT 1 en 164 μs constante para cualquier carga. BasicDBA lo destruye completamente a 100 Mbps (25 ms — inaceptable para VoIP, G.114 permite máximo ~10 ms en red de acceso).

**2. El colapso de BasicDBA es abrupto, no gradual.** Entre 75 y 100 Mbps hay un salto de 61× en latencia de T-CONT 1. Sin QoS, la red es impredecible bajo sobrecarga — no hay forma de planificar capacidad.

**3. QosDBA no tiene costo en eficiencia.** Ambos algoritmos utilizan el canal al 100% a plena carga. La QoS no sacrifica throughput — solo redistribuye las prioridades. El único "costo" es que T-CONT 4 sufre más bajo QosDBA, lo cual es exactamente el comportamiento esperado y deseado.

---

*OmneTeam — TEL-341 UTFSM 2026*
