# Evaluación de Algoritmos DBA en Redes GPON bajo Tráfico Multi-Servicio
## OmneTeam — David Retuerto · José Vega · Matías Perelli
### TEL-341 Simulación de Redes · UTFSM · 2026

---

# Slide 1 — Portada

**Título:** Evaluación de Algoritmos DBA en Redes GPON bajo Tráfico Multi-Servicio

**Subtítulo:** Comparación BasicDBA vs QosDBA mediante simulación de eventos discretos

**Equipo:** OmneTeam — David Retuerto · José Vega · Matías Perelli

**Curso:** TEL-341 Simulación de Redes · UTFSM · 2026

---

# Slide 2 — Motivación y Problema

## ¿Por qué importa cómo se asigna el ancho de banda en fibra óptica?

En una red GPON, **32 usuarios comparten 1.244 Gbps de upstream** sobre la misma fibra.

Simultáneamente coexisten:
- **VoIP** → necesita llegar en microsegundos o la llamada se corta
- **Video streaming** → necesita ancho de banda garantizado
- **Descargas** → puede esperar, no tiene requisito de latencia

**Pregunta de investigación:**  
¿Qué pasa con el VoIP cuando los 32 usuarios bajan archivos pesados al mismo tiempo?  
¿Importa el algoritmo que asigna el canal?

---


# Slide 3 — Red GPON ITU-T G.984

## Estándar implementado: GPON ITU-T G.984 (no EPON, no PON genérico)

```
Central Office
      │
    [OLT]  ← controla toda la red, corre el DBA
      │  20 km · 100 μs de delay
      │
  [Splitter 1:32]  ← pasivo, sin alimentación
      │
      ├── [ONU 0]  ┐
      ├── [ONU 1]  │  32 ONUs
      │    ...     │  cada una con T-CONT 1 + 2 + 4
      └── [ONU 31] ┘
```

## Parámetros físicos (G.984.2 y G.984.3)

| Parámetro | Valor |
|---|---|
| Upstream | **1.24416 Gbps** |
| Downstream | **2.48832 Gbps** |
| Trama GTC | **125 μs** (8.000 tramas/s) |
| Bytes/trama upstream | **19.440 bytes** |
| Alcance | 20 km (Clase B+) |
| Split ratio | 1:32 |
| Delay propagación | 5 μs/km → 100 μs |

---


# Slide 4 — Clases de Tráfico: T-CONTs (ITU-T G.984.3)

> En GPON el tráfico se clasifica en **T-CONTs**, no en eMBB/URLLC/mMTC (esas son categorías 5G).

## T-CONTs implementados: 1, 2 y 4

| T-CONT | Nombre | Asignación | Tráfico simulado | Distribución |
|---|---|---|---|---|
| **T-CONT 1** | Fixed | Pre-reservada siempre | VoIP · 1 Mbps · 160 B | CBR (determinístico) |
| **T-CONT 2** | Assured | Garantía mínima · demand-based | Video · 5 Mbps · 1.000 B | Poisson |
| **T-CONT 4** | Best Effort | Solo lo que sobra | Descargas · 10–100 Mbps · 1.400 B | Pareto α=1.5 |

**T-CONT 1:** la OLT reserva ancho de banda fijo cada trama, sin consultar si la ONU tiene datos (G.984.3 §9.2.1).

**T-CONT 4 — Pareto α=1.5:** tráfico de Internet es self-similar (Leland et al. 1994). Pareto captura las ráfagas de cola pesada que Poisson no modela.

---


# Slide 5 — Mecanismo DBA: SR-DBA Centralizado

## Por qué no IPACT

IPACT es el protocolo de **EPON (IEEE 802.3ah)** — otro estándar. En GPON el mecanismo es **SR-DBA** (Status Reporting DBA, G.984.3 §9.3).

| | IPACT (EPON) | SR-DBA (GPON) — lo implementado |
|---|---|---|
| Mecanismo | Polling individual ONU por ONU | **BWmap broadcast** a todas a la vez |
| Período | Variable, crece con N | **Fijo: 125 μs** siempre |
| Reporte | Mensaje separado por ONU | **DBRu embebido** en el burst |

## Flujo por trama (cada 125 μs)

```
t = 0:       OLT calcula asignaciones → envía BWmap broadcast
t = 100 μs:  32 ONUs reciben BWmap simultáneamente
             Cada ONU transmite según su slot + envía DBRu
t = 200 μs:  OLT recibe datos + DBRu → actualiza tabla
t = 125 μs:  OLT ya calculó el siguiente BWmap (solapado)
```

---


# Slide 6 — Algoritmos Implementados

## BasicDBA — proporcional sin QoS

Reparte proporcionalmente a la demanda de cada ONU, sin diferenciar T-CONT.

```
capacidad efectiva = 19.440 − 32 × 32 (guard) = 18.416 bytes
share[onu] = capacidad × demanda[onu] / demanda_total_red
grant[tcont] = share × cola[tcont] / demanda[onu]
```

**Problema:** T-CONT 4 llena su buffer (2 MB) → T-CONT 1 tiene 160 bytes → proporción ≈ 0.008% → grant = 0 → starvation de VoIP.

## QosDBA — algoritmo propio de prioridades por T-CONT

> G.984.3 define los tipos de T-CONT y SR-DBA. El algoritmo de asignación es propio, inspirado en la jerarquía que implican los T-CONTs.

```
Paso 1 — T-CONT 1 (Fixed): 160 bytes por ONU, sin consultar DBRu
          → 5.120 bytes reservados (26% de la trama)

Paso 2 — T-CONT 2 (Assured): hasta su garantía mínima, demand-based
          → fair_share = remaining / 32

Paso 3 — T-CONT 4 (Best Effort): proporcional al sobrante
          → grant = remaining × demanda[onu] / demanda_total_BE
```

---


# Slide 7 — Simulador de Eventos Discretos Propio

## 100% Python, sin frameworks externos

```
SimEngine (engine.py)
├── Cola de prioridad: min-heap (heapq stdlib)
├── Inserción/extracción: O(log n)
└── Reproducibilidad: campo seq para desempate FIFO

Eventos procesados en simulación completa:
  ~2.8 millones / corrida de 3 segundos simulados
  ~604.000 eventos / segundo de simulación (32 ONUs)
```

## Metodología experimental

| Parámetro | Valor |
|---|---|
| Escenarios | 10 (5 cargas × 2 algoritmos) |
| Cargas T-CONT 4 | 10 · 25 · 50 · 75 · 100 Mbps/ONU |
| Repeticiones | 10 (seeds 42–51) |
| Duración | 10 s simulados (1 s warmup) |
| IC 95% | ȳ ± 1.96 × s / √10 |
| Total corridas | **100** |

---


# Slide 8 — Resultado Clave: Latencia VoIP

## → Insertar figura: `figures/latency_p99_tcont1_vs_load.png`

**Lo que muestra el gráfico:**
- QosDBA (rojo): plano en 164 μs para toda la carga → VoIP siempre protegido
- BasicDBA (azul): estable hasta 75 Mbps, colapso a 26 ms a 100 Mbps
- Línea punteada: budget VoIP de 5 ms

**El salto entre 75 y 100 Mbps en BasicDBA es 61×.**  
No es degradación gradual — es colapso abrupto.

## Números exactos (10 repeticiones, IC95)

| Carga | BasicDBA P99 (μs) | QosDBA P99 (μs) |
|---|---|---|
| 10 Mbps | 476 | **226** |
| 75 Mbps | 476 | **226** |
| 100 Mbps | **26.076** | **226** |

---


# Slide 9 — Comparación Completa a 100 Mbps/ONU

## → Insertar figura: `figures/latency_avg_by_tcont.png`

| T-CONT | Clase | BasicDBA | QosDBA | Factor |
|---|---|---|---|---|
| **T-CONT 1** | VoIP (Fixed) | 25.437 μs | **164 μs** | **155×** |
| **T-CONT 2** | Video (Assured) | 4.411 μs | **401 μs** | **11×** |
| **T-CONT 4** | Datos (BE) | 177.875 μs | 177.875 μs | 1× (igual) |
| T-CONT 4 | Pérdida | 17.84% | 17.84% | 1× (igual) |
| Canal | Utilización | ~100% | ~100% | 1× (igual) |

**T-CONT 4 es igual en ambos:** ambos algoritmos agotan el canal. QosDBA no crea más capacidad — redistribuye prioridades. La diferencia es que la congestión la absorbe T-CONT 4 (best effort) en vez de repartirse entre todos.

---


# Slide 10 — Dashboard de Resultados

## → Insertar figura: `figures/summary_dashboard.png`

**4 subplots en 1 figura:**

- **Arriba izquierda:** Latencia por T-CONT a 100 Mbps — diferencia visual de BasicDBA vs QosDBA
- **Arriba derecha:** P99 VoIP vs carga — el colapso abrupto de BasicDBA
- **Abajo izquierda:** Throughput vs carga — ambos iguales (misma eficiencia)
- **Abajo derecha:** Pérdida por T-CONT — solo T-CONT 4, igual en ambos

---


# Slide 11 — Análisis de Resultados

## ¿Por qué QosDBA mantiene T-CONT 1 constante?

T-CONT 1 recibe su slot **antes** de procesar la demanda de T-CONT 4. Independientemente de cuántos bytes de descargas haya en cola, VoIP ya tiene su ancho de banda garantizado. La latencia es una constante física:
```
164 μs = 100 μs (propagación) + 62.5 μs (espera BWmap) + 1 μs (transmisión)
```

## ¿Por qué BasicDBA colapsa abruptamente?

Con T-CONT 4 al 100 Mbps, cada ONU tiene 2 MB en cola. T-CONT 1 tiene 160 bytes.  
Proporción T-CONT 1 = 160 / 2.000.160 ≈ **0.008%** → grant ≈ 0 → starvation.  
Es un efecto de umbral: pequeñas variaciones de carga producen cambios catastróficos.

## ¿Por qué T-CONT 4 es igual en ambos?

La capacidad del canal es fija. QosDBA no genera más ancho de banda — lo redistribuye. El "precio" de proteger VoIP y Video es que Best Effort sufre más bajo QosDBA. Esto es correcto: T-CONT 4 es best-effort por definición.

---


# Slide 12 — Conclusiones

## 1. QosDBA cumple su objetivo
T-CONT 1 (VoIP) en **164 μs constante** para cualquier carga.  
BasicDBA lo lleva a **25 ms a plena carga** — la llamada se corta.

## 2. El colapso de BasicDBA es abrupto
Entre 75 y 100 Mbps: salto de **61×** en latencia VoIP.  
Sin QoS, la red bajo sobrecarga es impredecible. No se puede planificar capacidad.

## 3. QosDBA no sacrifica eficiencia
Ambos algoritmos alcanzan **~100% de utilización** del canal.  
La QoS no tiene costo en throughput total — solo redistribuye prioridades.

## Implicación práctica
En una red GPON real con tráfico mixto, un algoritmo DBA sin diferenciación de T-CONTs hace inservible el VoIP bajo carga. La jerarquía Fixed → Assured → Best Effort definida por los T-CONTs de GPON no es opcional — es el mecanismo que garantiza convivencia de servicios con requisitos distintos.

---


# Slide 13 — Simplificaciones del Modelo

| Simplificación | Justificación |
|---|---|
| Sin fragmentación GEM | Estándar en simulaciones de DBA a nivel de red |
| Guard time = 32 bytes/ONU | Valor conservador simétrico en ambos algoritmos |
| Todas las ONUs a igual distancia | Sin impacto en comparación de algoritmos |
| Solo upstream | DBA es mecanismo upstream |
| Paquetes de tamaño fijo | Simplificación estándar en literatura de DBA |

**Efecto en la validez:** todas las simplificaciones son simétricas — afectan igual a BasicDBA y QosDBA. La **comparación relativa** entre algoritmos sigue siendo válida.

---


# Slide 14 — Referencias

**Estándares:**
- ITU-T G.984.1 (2008) — Arquitectura GPON
- ITU-T G.984.2 (2003/2006) — Capa física: 1.244 Gbps, longitudes de onda
- ITU-T G.984.3 (2004/2008) — GTC, T-CONTs, BWmap, SR-DBA ← principal

**Papers:**
- Leland et al. (1994). "On the Self-Similar Nature of Ethernet Traffic." IEEE/ACM ToN. → Justifica Pareto para tráfico BE
- Kramer et al. (2002). "IPACT: A Dynamic Protocol for an Ethernet PON." IEEE Comm. Mag. → Define IPACT (EPON, no GPON)
- Chang et al. (2006). "Dynamic Bandwidth Allocation for Differentiated Services in GPON." IEEE Comm. Letters → Base conceptual del QosDBA

**Simulación:**
- Law & Kelton (2000). Simulation Modeling and Analysis. McGraw-Hill. → Warmup, IC95%

---

*OmneTeam — David Retuerto · José Vega · Matías Perelli — TEL-341 UTFSM 2026*
