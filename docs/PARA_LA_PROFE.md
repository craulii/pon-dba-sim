# Explicación del proyecto para la profesora
## OmneTeam · TEL-341 · UTFSM 2026

---

## 1. Qué simulamos y por qué

Simulamos cómo una red de fibra óptica **GPON** reparte el ancho de banda upstream entre múltiples usuarios que compiten por el mismo canal compartido, y comparamos si conviene repartirlo sin diferenciar el tipo de tráfico o respetando prioridades según la clase de servicio.

**El problema concreto:** 32 usuarios comparten 1.244 Gbps de upstream. Uno hace VoIP (necesita llegar en microsegundos). Otro baja una película (puede esperar). ¿Cómo asignas el canal para que la llamada no se corte?

---

## 2. La red — GPON ITU-T G.984

### Estándar exacto

**GPON — Gigabit-capable Passive Optical Network, ITU-T G.984.**

| Documento | Qué define |
|---|---|
| G.984.1 (2008) | Arquitectura general, split ratios, distancias |
| G.984.2 (2003/2006) | Tasas de línea, longitudes de onda |
| G.984.3 (2004/2008) | Tramas GTC, T-CONTs, BWmap, mecanismo DBA |

No es EPON (IEEE 802.3ah). No es PON genérico. No es XG-PON.

### Parámetros físicos — todos derivados de G.984

| Parámetro | Valor | Fuente |
|---|---|---|
| Upstream | **1.24416 Gbps** | G.984.2 §7.1 |
| Downstream | **2.48832 Gbps** | G.984.2 §7.1 |
| Trama GTC | **125 μs** (8.000 tramas/s) | G.984.3 §B.2 |
| Capacidad bruta upstream/trama | **19.440 bytes** | = 1,244×10⁹ × 125×10⁻⁶ / 8 |
| Alcance | **20 km** (Clase B+) | G.984.2 §7.2 |
| Split ratio | **1:32** | G.984.1 §6.1 |
| Delay propagación | **5 μs/km → 100 μs** a 20 km | velocidad luz en fibra ≈ 2×10⁸ m/s |
| Longitud onda upstream | **1310 nm** | G.984.2 §6 |
| Longitud onda downstream | **1490 nm** | G.984.2 §6 |
| Guard band | **32 bytes/ONU** (valor conservador) | G.984.3 §8.2 |

> **Sobre los 19.440 bytes:** es la **capacidad bruta teórica** por trama, antes de overhead GTC y guard bands. La capacidad efectiva disponible para datos es menor (restamos 32 bytes × 32 ONUs = 1.024 bytes de guard overhead).

### Topología

```
OLT (central del proveedor)
 │  feeder fiber 20 km, 100 μs delay
 │
Splitter 1:32  ← pasivo, sin alimentación eléctrica
 │
 ├─ ONU 0  ┐
 ├─ ONU 1  │ cada ONU tiene T-CONT 1 + T-CONT 2 + T-CONT 4
 │  ...    │
 └─ ONU 31 ┘
```

Upstream = **TDMA**: solo una ONU transmite a la vez. La OLT coordina quién transmite y cuándo mediante el **BWmap**, enviado cada 125 μs.

---

## 3. Clases de tráfico — T-CONTs (no eMBB/URLLC/mMTC)

eMBB, URLLC, mMTC son categorías de **5G**, no de GPON. En GPON el tráfico se clasifica en **T-CONTs** (Transmission Containers), definidos en G.984.3 §9.

### Los 5 tipos del estándar

| Tipo | Nombre | Asignación | Reporte DBRu |
|---|---|---|---|
| **T-CONT 1** | Fixed | Fija, pre-reservada cada trama | No necesario |
| **T-CONT 2** | Assured | Garantía mínima, demand-based | Obligatorio |
| T-CONT 3 | Non-assured | Mínimo garantizado + extra si sobra | Obligatorio |
| **T-CONT 4** | Best Effort | Solo lo que sobra tras 1, 2 y 3 | Obligatorio |
| T-CONT 5 | Mixed | Combinación de todos | Obligatorio |

### T-CONTs usados: 1, 2 y 4

Capturan los tres comportamientos fundamentalmente distintos (CBR puro / garantizado demand-based / best-effort). T-CONT 3 es mezcla de 2+4; T-CONT 5 es mezcla de todos.

### Configuración de cada T-CONT

| | T-CONT 1 (VoIP) | T-CONT 2 (Video) | T-CONT 4 (Datos) |
|---|---|---|---|
| Tasa | 1 Mbps | 5 Mbps | 10–100 Mbps/escenario |
| Paquete | 160 bytes | 1.000 bytes | 1.400 bytes |
| Buffer | 10.000 bytes | 200.000 bytes | 2.000.000 bytes |
| Distribución | **CBR** (determinístico, 1.28 ms) | **Poisson** (media 1.6 ms) | **Pareto α=1.5** |
| Inter-arrival | Fijo: 160×8/1.000.000 = 1,28 ms | Exponencial | Heavy-tailed |

**T-CONT 1 en el simulador:** la OLT pre-reserva un slot por trama por ONU sin consultar el DBRu — ancho de banda fijo independiente de la carga. Esto es el comportamiento Fixed de G.984.3 §9.2.1.

**T-CONT 2 — Poisson:** usamos proceso de Poisson como modelo simplificado para tráfico con tasa media garantizada, estándar en literatura académica de análisis de colas. Video real puede ser más bursty; el objetivo del proyecto es comparar algoritmos DBA, no modelar un codec específico.

**T-CONT 4 — Pareto α=1.5:** Leland et al. (1994) demostraron que el tráfico de Internet presenta self-similarity — ráfagas correlacionadas a múltiples escalas de tiempo que Poisson no captura. Pareto con cola pesada produce ese comportamiento. Usamos α=1.5 como valor de referencia de la literatura.

---

## 4. Mecanismo DBA — SR-DBA centralizado

### Por qué no IPACT

IPACT (Interleaved Polling with Adaptive Cycle Time) es el protocolo de asignación de **EPON (IEEE 802.3ah)**. EPON y GPON son estándares distintos de organizaciones distintas (IEEE vs ITU-T). Usar IPACT para modelar GPON sería mezclar conceptos incompatibles.

### SR-DBA (Status Reporting DBA) — G.984.3 §9.3

| | IPACT (EPON) | SR-DBA (GPON) |
|---|---|---|
| Mecanismo | Polling individual ONU por ONU | **BWmap broadcast** a todas las ONUs a la vez |
| Período | Variable, crece con N ONUs | **Fijo: 125 μs**, independiente de N |
| Reporte | Mensaje REPORT separado | **DBRu embebido** en el burst upstream |

### Flujo por trama (cada 125 μs)

```
t = 0:       OLT calcula asignaciones con los últimos DBRu recibidos
             OLT envía BWmap broadcast downstream
t = 100 μs:  Todas las ONUs reciben el BWmap simultáneamente
             Cada ONU transmite su burst según el slot asignado
             Cada ONU envía su DBRu embebido en ese burst
t = 200 μs:  OLT recibe datos + DBRu upstream
t = 125 μs:  OLT ya calcula el siguiente BWmap (ciclos solapados)
```

**BWmap:** se transmite en el PCBd (Physical Control Block downstream) de cada trama GTC. Indica a cada T-CONT cuándo y cuántos bytes puede transmitir.

**DBRu:** embebido en el header del burst upstream (G.984.3 §9.3.2). Reporta bytes pendientes por T-CONT. La OLT siempre trabaja con información de ≥200 μs de antigüedad (1 RTT) — esto es inherente al sistema y correcto.

---

## 5. Algoritmos implementados

### BasicDBA — proporcional sin QoS

Reparte el canal proporcionalmente a la demanda, sin diferenciar el tipo de T-CONT.

```
capacidad_efectiva = 19.440 − 32 × 32 (guard) = 18.416 bytes

Para cada ONU:
  demanda = cola_tcont1 + cola_tcont2 + cola_tcont4
  share = capacidad_efectiva × demanda / demanda_total_red
  grant[tcont_j] = share × cola[tcont_j] / demanda
```

**Por qué falla a plena carga:** con 100 Mbps/ONU de T-CONT 4, la cola BE se llena (2 MB). T-CONT 1 tiene 160 bytes. Su proporción es 160/2.000.160 ≈ 0,008% → grant ≈ 0 → la ONU de VoIP no puede transmitir → latencia de 25 ms.

### QosDBA — algoritmo propio de prioridades por T-CONT

> **Aclaración importante:** G.984.3 define los **tipos de T-CONT** y el mecanismo SR-DBA. No especifica un algoritmo de asignación obligatorio — los vendors implementan los suyos. QosDBA es un algoritmo propio inspirado en la jerarquía de prioridades que implica la definición de los T-CONTs en el estándar.

```
remaining = 18.416 bytes (capacidad efectiva)

Paso 1 — T-CONT 1 (ancho de banda fijo):
  Cada ONU recibe 160 bytes, sin consultar el DBRu
  Costo: 160 × 32 = 5.120 bytes → remaining = 13.296 bytes

Paso 2 — T-CONT 2 (garantía mínima, demand-based):
  grant = min(demanda, max_asegurado, fair_share, remaining)
  fair_share = remaining / 32 (evita acaparamiento)

Paso 3 — T-CONT 4 (best-effort, proporcional al sobrante):
  grant = remaining × demanda_be_onu / demanda_be_total
```

**Propiedad:** T-CONT 1 siempre recibe su slot antes que T-CONT 4, independientemente de cuántos bytes de descargas haya en cola.

---

## 6. Resultados

### A carga máxima: 100 Mbps/ONU × 32 ONUs = 3.200 Mbps demanda vs 1.244 Mbps capacidad (sobrecarga 257%)

| | BasicDBA | QosDBA |
|---|---|---|
| **T-CONT 1 latencia media** | **25.437 μs** (25 ms) | **164 μs** ✓ |
| T-CONT 1 latencia P99 | 26.076 μs | 226 μs |
| T-CONT 2 latencia media | 4.411 μs | 401 μs |
| **T-CONT 4 latencia** | 177.875 μs | 177.875 μs |
| **T-CONT 4 pérdida** | **17,8%** | **17,8%** |
| Utilización canal | ~100% | ~100% |

**T-CONT 4 igual en ambos algoritmos:** correcto y esperado. Ambos usan el mismo canal. La diferencia está en quién absorbe la congestión: BasicDBA la reparte entre todos; QosDBA la concentra en T-CONT 4 y protege T-CONT 1 y 2.

**Latencia mínima teórica T-CONT 1:**
```
t_propagación = 100 μs  (20 km × 5 μs/km)
t_espera BWmap = 62,5 μs  (media: ½ × 125 μs)
t_transmisión = 1,03 μs  (160 bytes a 1,244 Gbps)
─────────────────────────
Total mínimo ≈ 163,5 μs
Resultado QosDBA: 164,3 μs ✓  (consistente)
```

### Por carga — T-CONT 1 latencia media

| Carga T-CONT 4 | BasicDBA | QosDBA |
|---|---|---|
| 10 Mbps/ONU | 414 μs | **164 μs** |
| 25 Mbps/ONU | 414 μs | **164 μs** |
| 50 Mbps/ONU | 414 μs | **164 μs** |
| 75 Mbps/ONU | 414 μs | **164 μs** |
| 100 Mbps/ONU | **25.437 μs** | **164 μs** |

QosDBA mantiene T-CONT 1 constante a 164 μs sin importar la carga.

---

## 7. Metodología

- **Simulador:** eventos discretos propio en Python (heapq stdlib, sin frameworks externos)
- **Escenarios:** 10 (5 cargas × 2 algoritmos), T-CONT 4 en {10, 25, 50, 75, 100} Mbps/ONU
- **Repeticiones:** 10 por escenario con seeds 42–51
- **IC 95%:** ȳ ± 1,96 × s / √10 (réplicas i.i.d.)
- **Warmup:** 1 segundo descartado (estado transitorio), 9 segundos efectivos
- **Total corridas:** 100

---

## 8. Simplificaciones declaradas

| Simplificación | Descripción | Impacto |
|---|---|---|
| Sin fragmentación GEM | No fragmentamos paquetes en celdas del slot | T-CONT 1 reserva 160 B/trama en vez de ~16 B; comparación sigue siendo válida |
| Guard time = 32 bytes/ONU | Valor conservador | G.984.3 especifica overhead mínimo; usamos valor fijo simétrico |
| Todas las ONUs a igual distancia | No modelamos ranging ni equalization delay | Sin impacto en comparación de algoritmos DBA |
| Solo upstream | No modelamos downstream | DBA es mecanismo upstream |
| Sin FEC | No modelamos Reed-Solomon opcional | Overhead ~7%, negligible |
| Paquetes tamaño fijo | Sin variabilidad de tamaño por T-CONT | Simplificación estándar en literatura de DBA |

---

## 9. Por qué Python y no OMNeT++

La profesora solicitó un simulador 100% propio. El motor de eventos discretos es nuestro: cola de prioridad min-heap (`heapq` de Python stdlib), sin SimPy, sin OMNeT++, sin ningún framework externo. Además, el simulador anterior mezclaba EPON (IPACT), GPON y clases 5G — conceptos de tres estándares distintos. Este simulador implementa un único estándar correctamente: GPON ITU-T G.984.

---

*OmneTeam — David Retuerto · José Vega · Matías Perelli — TEL-341 UTFSM 2026*
