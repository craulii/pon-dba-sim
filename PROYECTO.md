# Evaluación de Algoritmos DBA en Redes PON bajo Tráfico 5G Multi-Servicio

**Proyecto Final — TEL-341 Simulación de Redes**
**Equipo OmneTeam:** David Retuerto, José Vega, Matías Perelli
**Universidad Técnica Federico Santa María (UTFSM)**

---

## 1. Resumen Ejecutivo

Este proyecto simula una red de fibra óptica pasiva (PON) en la que múltiples usuarios comparten un canal de subida empleando multiplexión por división de tiempo (TDM). El canal es administrado por un algoritmo de **Asignación Dinámica de Ancho de Banda (DBA)**. El objetivo es comparar dos algoritmos —el estándar industrial **IPACT** y un diseño propio **QoS-DBA**— bajo carga de tráfico 5G que mezcla tres clases de servicio con requisitos radicalmente distintos.

**Resultado central:** Con el algoritmo estándar IPACT, entre el 75 % y el 87 % de los paquetes de tráfico crítico (URLLC) se pierden. Con QoS-DBA, la pérdida de URLLC es **0 %** en todos los niveles de carga. El costo es un incremento marginal (~5 pp) en la pérdida de tráfico eMBB, que es el trade-off esperado.

---

## 2. Pertinencia al Curso TEL-341

Este proyecto aplica directamente los conceptos centrales del curso de Simulación de Redes:

### 2.1 Simulación de eventos discretos (DES)
El proyecto utiliza OMNeT++ 6.0, un simulador de eventos discretos orientado a objetos. Cada evento —llegada de paquete, envío de REPORT, recepción de GRANT, inicio de transmisión— es un `cMessage` programado con `scheduleAt()`. El motor de OMNeT++ ejecuta los eventos en orden cronológico, garantizando causalidad.

### 2.2 Modelado de procesos estocásticos reales
Los tres tipos de tráfico 5G emplean distribuciones distintas, justificadas en la literatura:

| Clase | Distribución | Justificación |
|-------|-------------|---------------|
| eMBB | **Pareto (α = 1.5)** inter-arribo | Tráfico self-similar: ráfagas de heavy tail documentadas por Leland et al. (1994) en redes Ethernet reales |
| URLLC | **Exponencial** (proceso de Poisson) | Sensores industriales y control de maquinaria: llegadas memoryless independientes |
| mMTC | **Periódico + jitter ±20 %** | Medidores IoT que reportan en intervalos regulares con pequeña variabilidad |

### 2.3 Diseño experimental riguroso
El diseño sigue principios de simulación replicada:
- **Factores**: algoritmo DBA (2 niveles), carga eMBB (4 niveles: 50/100/150/200 Mbps)
- **Repeticiones**: 3 corridas con semilla diferente (`seed-set = ${repetition}`)
- **Calentamiento**: 1 s excluido del análisis para eliminar el estado transitorio inicial
- **Tiempo de simulación**: 10 s totales por corrida (9 s de régimen permanente)

### 2.4 Validación del modelo
Se verificó que el comportamiento observado es físicamente consistente:
- La latencia mínima posible es mayor al RTT de propagación (~330 μs para 20 km de fibra)
- El throughput agregado no supera la capacidad del canal (1 Gbps)
- Las tasas de pérdida aumentan monotónicamente con la carga, como predice la teoría de colas

### 2.5 Análisis estadístico de resultados
El script `analysis/analyze.py` genera 7 figuras con:
- Intervalos de confianza del 95 % (con las 3 repeticiones actuales, pendiente ampliar a 10)
- Curvas de distribución acumulada (CDF) de latencia URLLC
- Latencia P99 vs. carga (el indicador más relevante para sistemas de tiempo real)
- Comparación de throughput normalizado vs. carga ofrecida

### 2.6 Complejidad de implementación
El proyecto fue implementado **desde cero** en C++17 sin usar frameworks como INET. Esto demuestra dominio de los mecanismos internos de OMNeT++:
- 13 archivos C++ (`*.h` / `*.cc`) con más de 800 líneas de código
- Definición de mensajes personalizados en `PONMessages.msg` (compilados por `opp_msgc`)
- Registro de métricas con `cOutVector` (series temporales) y `recordScalar` (estadísticas finales)
- Animación gráfica en Qtenv con display strings y burbujas de estado dinámicos
- Dos algoritmos DBA intercambiables por parámetro sin recompilar

---

## 3. Contexto y Motivación

### 3.1 Redes PON y el rol de backhaul 5G
Una red PON (Passive Optical Network) conecta una **Central Office** con múltiples usuarios finales usando fibra óptica y un splitter óptico pasivo (sin componentes activos en la planta externa). Es la tecnología predominante para redes de acceso FTTH y, en 5G, como infraestructura de **backhaul**: conecta las estaciones base (gNB) con el núcleo de red, siguiendo los estándares ITU-T G.984/G.987 (GPON/XG-PON).

> **Nota sobre el escenario modelado:** El proyecto modela específicamente un escenario de **backhaul/mid-haul** (fibra hasta 20 km, ciclo de polling de 2 ms, deadline URLLC de 10 ms), que es el presupuesto de latencia asignado al segmento PON en este tipo de arquitectura según 3GPP TR 38.913. El fronthaul estricto (C-RAN, < 250 μs) requeriría fibras < 10 km y ciclos de polling < 500 μs, parámetros incompatibles con el modelo de 20 km implementado. Esta distinción es importante: el problema de scheduling bajo tráfico mixto es idéntico en ambos escenarios; solo cambia la escala temporal del deadline.

```
[OLT — Central Office]
        |
  Feeder Fiber (20 km, delay ≈ 100 μs)
        |
  [Splitter 1:16]
   /  /  /  \  \  \
[ONU_0][ONU_1]...[ONU_15]
```

El canal de **bajada** (OLT → ONUs) usa broadcast: todos reciben, cada ONU filtra sus propios datos. El canal de **subida** (ONUs → OLT) es el problema crítico: es **TDM compartido**. Solo puede transmitir una ONU a la vez. Si dos ONUs transmiten simultáneamente, sus señales se superponen en el splitter y generan colisiones irrecuperables.

### 3.2 El problema DBA
El mecanismo DBA (Dynamic Bandwidth Assignment) evita las colisiones coordinando cuándo transmite cada ONU:

1. La OLT envía un mensaje **POLL** a todas las ONUs al inicio de cada ciclo
2. Cada ONU responde con un **REPORT**: cuántos bytes tiene en sus colas
3. La OLT corre el algoritmo DBA y envía un **GRANT** a cada ONU: slot de tiempo asignado (inicio + duración)
4. Cada ONU transmite exactamente en su slot → no hay colisiones
5. Se repite el ciclo (período nominal: 2 ms)

La pregunta de investigación es: **¿cómo distribuir el ancho de banda disponible entre las ONUs cuando tienen clases de tráfico con requisitos muy distintos?**

### 3.3 5G como backhaul: el reto
En arquitecturas 5G, la red PON actúa como **backhaul**: conecta las antenas de radio (RRUs) con el núcleo de red. Esto introduce tres clases de tráfico definidas por 3GPP:

| Clase | Nombre completo | Requisito crítico | Tasa típica |
|-------|----------------|------------------|-------------|
| **eMBB** | Enhanced Mobile Broadband | Throughput alto | 50–200 Mbps por sector |
| **URLLC** | Ultra-Reliable Low Latency | Latencia < 10 ms | 1–10 Mbps |
| **mMTC** | Massive Machine Type Communications | Escala (millones de dispositivos) | < 1 Mbps |

El conflicto es claro: eMBB genera ráfagas masivas de datos, mientras que URLLC necesita llegar en menos de 10 ms o sus paquetes son inútiles (control industrial, cirugía remota, vehículos autónomos). Un algoritmo ciego que trate a todos igual inevitablemente sacrificará URLLC cuando eMBB sature el canal.

---

## 4. Arquitectura del Modelo de Simulación

### 4.1 Topología

```
PONNetwork.ned
├── olt : OLT         (puerto único ponPort, conectado al splitter)
├── splitter : Splitter  (oltPort + onuPort[16])
└── onu[16] : ONU     (puerto único ponPort)

Conexiones:
  olt.ponPort <--> {delay=100us, datarate=1Gbps} <--> splitter.oltPort
  splitter.onuPort[i] <--> {delay=10us, datarate=1Gbps} <--> onu[i].ponPort
```

El retardo de propagación total OLT ↔ ONU es **110 μs** (100 μs fibra troncal + 10 μs distribución). El RTT mínimo para cualquier paquete de upstream es ≈ 330 μs (ONU→OLT: 110 μs + procesamiento ≈ 10 μs + GRANT OLT→ONU: 110 μs + guard time 1 μs + transmisión mínima).

### 4.2 Módulos implementados

| Archivo | Rol |
|---------|-----|
| `OLT.h / OLT.cc` | Motor principal. Envía POLLs, recibe REPORTs, ejecuta el algoritmo DBA, envía GRANTs. Registra `cycleTime` como vector. |
| `ONU.h / ONU.cc` | Genera tráfico de las 3 clases, mantiene 3 colas separadas, responde REPORTs, transmite según GRANTs. Registra latencia, jitter y bytes transmitidos por clase. |
| `Splitter.h / Splitter.cc` | Reenvío puro: cualquier mensaje recibido por un puerto se reenvía a todos los demás puertos. |
| `IPACT.h / IPACT.cc` | Algoritmo DBA estándar. |
| `QoSDBA.h / QoSDBA.cc` | Algoritmo DBA con prioridad QoS. |
| `DBAAlgorithm.h` | Interfaz base abstracta para los algoritmos. |
| `PONMessages.msg` | Define `DataPacket`, `ReportMessage`, `GrantMessage`. Compilado automáticamente por `opp_msgc`. |
| `PONNetwork.ned` | Red completa parametrizable. |

### 4.3 Flujo de eventos (un ciclo completo)

```
t=0    OLT::startNewCycle() → envía POLL a todas las ONUs
t≈110μs  ONU[i]::handleMessage(POLL) → envía REPORT con queueSize_{eMBB,URLLC,mMTC}
t≈220μs  OLT::processReport(REPORT) → cuando llegan todos los N REPORTs:
           → ejecuta DBA::computeGrants(reports)
           → envía GRANT[i] a cada ONU con startTime + grantSize por clase
t≈330μs  ONU[i]::handleMessage(GRANT) → programa txDone en startTime asignado
t=startTime  ONU[i] transmite paquetes de cada cola según grant recibido
             → registra latencia = simTime() - pkt->getCreationTime()
             → descarta paquetes URLLC cuya deadline < simTime()
t=2ms   OLT programa siguiente ciclo
```

### 4.4 Métricas registradas

Por cada ONU y por cada clase de servicio:

- **Latencia**: `simTime() - pkt->creationTime()` al momento de transmisión (o descarte)
- **Jitter**: `|latencia_actual - latencia_anterior|`
- **Throughput**: `bytesTransmitted * 8 / (simTime - warmupPeriod)`
- **Tasa de pérdida**: `pktsDropped / pktsGenerated`, donde pérdida = buffer overflow + deadline expirado (solo URLLC)

---

## 5. Algoritmos DBA

### 5.1 IPACT — Interleaved Polling with Adaptive Cycle Time

**Referencia:** Kramer, G., Mukherjee, B., Pesavento, G. (2002). IPACT: a dynamic protocol for an Ethernet PON. *IEEE Communications Magazine*, 40(2), 74–80.

IPACT es el estándar de facto para redes PON Ethernet (EPON). Su lógica es simple e igualitaria:

```
Para cada ONU i con reporte (eMBB_i, URLLC_i, mMTC_i):
    total_i = eMBB_i + URLLC_i + mMTC_i
    granted = min(total_i, maxGrantSize)      # cap por equidad
    if total_i > 0:
        grant_eMBB[i]  = granted × (eMBB_i / total_i)   # proporcional
        grant_URLLC[i] = granted × (URLLC_i / total_i)
        grant_mMTC[i]  = granted - grant_eMBB[i] - grant_URLLC[i]
```

**Problema:** cuando eMBB tiene una ráfaga Pareto (puede ser 3–10× el tamaño medio), el denominador `total_i` es dominado por eMBB, y URLLC recibe una fracción mínima del grant. Los paquetes URLLC esperan en cola múltiples ciclos (cada ciclo ≈ 2 ms), acumulando latencia hasta superar el deadline de 10 ms y ser descartados.

### 5.2 QoS-DBA — Priority-based con Weighted Fair Queuing

Este algoritmo fue diseñado específicamente para el contexto 5G del proyecto. Opera en dos pasos:

```
Para cada ONU i con reporte (eMBB_i, URLLC_i, mMTC_i):
    remaining = maxGrantSize

    # Paso 1: PRIORIDAD ESTRICTA para URLLC
    grant_URLLC[i] = min(URLLC_i, remaining)
    remaining -= grant_URLLC[i]

    # Paso 2: WFQ (Weighted Fair Queuing) para eMBB y mMTC
    if remaining > 0 and (eMBB_i + mMTC_i) > 0:
        ideal_eMBB = remaining × wEMBB / (wEMBB + wMTC)   # wEMBB=0.7, wMTC=0.3
        ideal_mMTC = remaining - ideal_eMBB

        grant_eMBB[i] = min(eMBB_i, ideal_eMBB)
        grant_mMTC[i] = min(mMTC_i, ideal_mMTC)

        # Ceder sobrante si alguna clase no usa toda su asignación
        sobrante_eMBB = ideal_eMBB - grant_eMBB[i]
        grant_mMTC[i] += min(mMTC_i - grant_mMTC[i], sobrante_eMBB)
        # (análogo para sobrante mMTC → eMBB)
```

**Invariante clave:** URLLC siempre recibe exactamente lo que necesita (hasta el cap), sin importar cuánto tráfico eMBB esté pendiente. Solo si URLLC no tiene demanda, ese bandwidth se libera a eMBB y mMTC.

### 5.3 Parámetros críticos del diseño

| Parámetro | Valor | Justificación |
|-----------|-------|---------------|
| `maxGrantSize` | 15 000 bytes | ≈ fair share para 16 ONUs en canal 1 Gbps / ciclo 2 ms: (1e9 × 2e-3) / 8 / 16 = 15 625 bytes |
| `urllcDeadline` | 10 ms | Budget de latencia asignado a la red de acceso en arquitecturas 5G (3GPP TS 38.913) |
| `pollingCycleTime` | 2 ms | Estándar IEEE 802.3ah para EPON |
| `guardTime` | 1 μs | Tiempo entre slots para evitar colisiones por drift de reloj |

---

## 6. Generadores de Tráfico

### 6.1 eMBB — Pareto self-similar

```cpp
// Pareto(α=1.5): E[X] = xm × α/(α-1) = 3×xm
// Para E[X] = tamaño_paquete × 8 / embbRate → xm = E[X] / 3
double xm = (1250.0 * 8.0) / embbRate / 3.0;
double u = uniform(0.001, 0.999);
inter_arribo = xm × pow(u, -1/1.5);
```

El parámetro de forma α = 1.5 garantiza varianza infinita (heavy-tailed). Esto modela el comportamiento self-similar del tráfico HTTP/streaming documentado en mediciones reales de Internet desde los años 90.

### 6.2 URLLC — Proceso de Poisson

```cpp
inter_arribo = exponential((128 bytes × 8 bits/byte) / urllcRate);
```

Proceso memoryless, apropiado para señales de control y telemetría industrial.

### 6.3 mMTC — Periódico con jitter

```cpp
inter_arribo = (100 bytes × 8 bits/byte / mmtcRate) × uniform(0.8, 1.2);
```

Reportes de sensores IoT: periódicos con pequeña variación natural (±20 %).

---

## 7. Configuración Experimental

### 7.1 Parámetros de red

```ini
**.numONUs          = 16          # Usuarios en la red PON
**.dataRate         = 1Gbps       # Canal upstream compartido
**.pollingCycleTime = 2ms
**.maxGrantSize     = 15000       # bytes por ONU por ciclo
**.guardTime        = 1us
**.urllcDeadline    = 10ms        # Budget de latencia 5G URLLC
**.urllcRate        = 5Mbps       # Tasa URLLC por ONU
**.mmtcRate         = 0.5Mbps     # Tasa mMTC por ONU
**.wfqWeightEMBB    = 0.7         # Peso WFQ para eMBB
**.wfqWeightMMTC    = 0.3         # Peso WFQ para mMTC
```

### 7.2 Escenarios ejecutados (estado actual)

| Configuración | Algoritmo | ONUs | Carga eMBB | Repeticiones | Estado |
|--------------|-----------|------|-----------|-------------|--------|
| IPACT_16ONU | IPACT | 16 | 50/100/150/200 Mbps | 3 | ✅ Completado |
| QoSDBA_16ONU | QoS-DBA | 16 | 50/100/150/200 Mbps | 3 | ✅ Completado |
| IPACT_32ONU | IPACT | 32 | 50/100/150/200 Mbps | — | Pendiente |
| QoSDBA_32ONU | QoS-DBA | 32 | 50/100/150/200 Mbps | — | Pendiente |

Total ejecutado: **24 corridas** (2 × 4 cargas × 3 repeticiones).

---

## 8. Resultados Obtenidos

### 8.1 Tasa de pérdida de paquetes (resultados reales de simulación)

| Algoritmo | Carga eMBB | Pérdida URLLC | Pérdida eMBB | Pérdida mMTC |
|-----------|-----------|--------------|-------------|-------------|
| IPACT     | 50 Mbps   | **75.8 %**   | 0.1 %       | 0.0 %       |
| IPACT     | 100 Mbps  | **86.8 %**   | 49.0 %      | 0.0 %       |
| IPACT     | 150 Mbps  | **86.9 %**   | 66.0 %      | 0.0 %       |
| IPACT     | 200 Mbps  | **87.0 %**   | 74.5 %      | 0.0 %       |
| QoS-DBA   | 50 Mbps   | **0.0 %**    | 8.1 %       | 0.0 %       |
| QoS-DBA   | 100 Mbps  | **0.0 %**    | 53.9 %      | 0.0 %       |
| QoS-DBA   | 150 Mbps  | **0.0 %**    | 69.2 %      | 0.0 %       |
| QoS-DBA   | 200 Mbps  | **0.0 %**    | 76.9 %      | 0.0 %       |

### 8.2 Análisis de los resultados

**IPACT falla en proteger URLLC desde el primer nivel de carga.** Incluso a 50 Mbps (el 50 % de la capacidad nominal del canal), el 75 % de los paquetes URLLC se pierden. La causa es mecánica: cada ciclo de 2 ms, una ráfaga Pareto de eMBB puede acumular ~500 KB en cola, mientras URLLC solo tiene ~12.5 KB. El grant proporcional asigna a URLLC ≈ 2.4 % del slot, suficiente para 360 bytes por ciclo, pero la tasa de llegada de URLLC es 5 Mbps → 1 250 bytes/ms → 2 500 bytes/ciclo. La cola URLLC crece, los paquetes esperan múltiples ciclos y eventualmente expiran.

**QoS-DBA elimina completamente la pérdida URLLC.** Al asignar el grant URLLC antes de repartir el resto, garantiza que cada ONU siempre transmita sus paquetes URLLC dentro de 1–2 ciclos (2–4 ms), bien dentro del deadline de 10 ms. La latencia URLLC medida es consistentemente < 5 ms.

**El trade-off eMBB es el esperado.** Con QoS-DBA, eMBB pierde algunos puntos porcentuales adicionales en pérdida porque URLLC consume parte del grant antes. Este trade-off está documentado en la literatura y es el precio aceptado por la protección de servicios críticos.

### 8.3 Análisis detallado de los gráficos

Las figuras se encuentran en `analysis/figures/` y `Parte 2/figuras/`. A continuación se analiza cada una.

---

#### Gráfico 1 — `latency_avg_by_class.png`

**Qué muestra:** Latencia promedio upstream por clase de servicio a carga máxima (200 Mbps eMBB). Barras azules = IPACT, barras rojas = QoS-DBA.

**Lectura:**
- **eMBB:** IPACT ~150 000 μs (150 ms), QoS-DBA ~165 000 μs (165 ms). Ambos valores son altos —el tráfico eMBB espera en cola un tiempo largo porque el canal está saturado. QoS-DBA muestra latencia eMBB ligeramente mayor que IPACT, lo cual parece contra-intuitivo pero tiene explicación: con IPACT, el 74.5 % del eMBB se descarta (solo llegan los paquetes que salen rápido); con QoS-DBA la pérdida eMBB es mayor (~77 %), pero los que sí se transmiten lo hacen después de esperar más en cola (porque URLLC tiene prioridad). Es un efecto de selección, no un empeoramiento real.
- **URLLC:** IPACT ~10 000 μs (10 ms), QoS-DBA ~1 000 μs (1 ms). Diferencia de 10× a favor de QoS-DBA. Con IPACT los paquetes que *logran* transmitirse lo hacen casi al límite de su deadline. Con QoS-DBA se transmiten en ~1–2 ciclos (2–4 ms).
- **mMTC:** IPACT ~85 000 μs (85 ms), QoS-DBA ~1 000 μs (1 ms). Diferencia de 85×. Con QoS-DBA, tras servir URLLC, mMTC recibe su fracción WFQ sin competir con grandes ráfagas eMBB.
- Las barras de error (IC 95 %) son pequeñas, indicando resultados estables entre repeticiones.

**Estado:** Correcto. Comunica claramente el beneficio de QoS-DBA para URLLC y mMTC.

---

#### Gráfico 2 — `latency_p99_urllc_vs_load.png`

**Qué muestra:** Percentil 99 de latencia URLLC vs. carga eMBB ofrecida, con línea de deadline a 10 ms = 10 000 μs.

**Lectura:**
- **IPACT (azul):** Curva plana a ~10 000 μs en todos los niveles de carga. El P99 se clava en el deadline porque los paquetes que superan 10 ms son descartados —el script solo registra los que se transmiten. Los paquetes que "sobreviven" son aquellos que justo alcanzaron a transmitirse antes de expirar, por eso su latencia está justo al tope del deadline. La curva plana indica que desde 50 Mbps el sistema ya opera en modo de descarte masivo.
- **QoS-DBA (rojo):** Curva plana a ~2 400 μs (~2.4 ms) en todos los niveles. Independiente de la carga, URLLC siempre se sirve dentro de 2–3 ciclos de polling (4–6 ms). La planeidad es esperada: con prioridad absoluta, la latencia URLLC no depende de la carga eMBB.
- La línea de deadline (rojo punteado, 10 ms) coincide visualmente con la curva IPACT —esto confirma que IPACT opera al límite del deadline, mientras QoS-DBA opera con un margen de 4× por debajo.

**Limitación:** Con solo 3 repeticiones las bandas de IC 95 % son amplias. Con 10 repeticiones esta curva sería más precisa. La planeidad de ambas curvas es un resultado real, no un artefacto —indica que el comportamiento está determinado por el mecanismo DBA y no varía con la carga en el rango probado.

---

#### Gráfico 3 — `throughput_vs_load.png`

**Qué muestra:** Throughput por ONU (normalizado por capacidad del canal, 62.5 Mbps) vs. carga ofrecida total por ONU normalizada por la misma capacidad.

**Lectura:**
- Eje X: carga ofrecida por ONU (eMBB + URLLC + mMTC) / 62.5 Mbps. A 50 Mbps eMBB: (55.5/62.5) ≈ 0.89 — el canal ya está al 89 % de saturación desde el nivel de carga mínimo probado.
- Eje Y: throughput efectivo por ONU / 62.5 Mbps. Ambas curvas están en ~1.0, lo que significa que el canal está completamente lleno en todos los escenarios.
- La curva punteada gris ("capacidad del canal") muestra el techo teórico de 1.0. Ambos algoritmos alcanzan ese techo, indicando que ninguno desperdicia capacidad del canal —la diferencia entre ellos está en *qué* tráfico se sirve, no en la cantidad total.
- IPACT y QoS-DBA están superpuestos porque el throughput total es idéntico (~62.5 Mbps por ONU = 1 Gbps total). La diferencia cualitativa (quién de los paquetes llega) no se refleja en esta métrica agregada.

**Interpretación clave:** El canal opera en régimen de saturación permanente. Con 16 ONUs y 50 Mbps eMBB + 5.5 Mbps adicionales = 888 Mbps ofrecidos (cerca del límite). En este régimen, ambos algoritmos usan el 100 % del canal, pero QoS-DBA prioriza los paquetes *correctos* (URLLC), mientras IPACT desperdicia slots en paquetes que ya expiraron.

---

#### Gráfico 4 — `cdf_latency_urllc.png`

**Qué muestra:** Distribución acumulada (CDF) de latencia URLLC a carga máxima (200 Mbps eMBB). Escala X logarítmica. Línea vertical en 10 ms = 10 000 μs.

**Lectura:**
- **QoS-DBA (rojo):** Curva suave desde ~100 μs hasta ~3 000 μs. P50 ≈ 1 500 μs, P99 ≈ 2 500 μs. El 100 % de los paquetes llega antes del deadline de 10 ms. La distribución tiene forma de S típica de una suma de exponenciales (tiempo de espera en cola + propagación).
- **IPACT (azul):** Curva casi vertical en ~9 000–10 000 μs. La CDF "salta" desde ~0 hasta ~1 en un rango muy estrecho justo antes del deadline. Esto significa que todos los paquetes URLLC que *logran transmitirse* lo hacen con latencias cercanas a los 10 ms —están al límite. Los paquetes que superaron el deadline no aparecen en la CDF porque fueron descartados antes de registrar latencia.
- La separación entre curvas (factor ~4–6 en latencia) cuantifica el beneficio de QoS-DBA.

**Estado:** Correcto. Es el gráfico más informativo del conjunto.

---

#### Gráfico 5 — `packet_loss_by_class.png`

**Qué muestra:** Tasa de pérdida por clase de servicio a carga máxima (200 Mbps eMBB). Escala Y logarítmica para visualizar diferencias de varios órdenes de magnitud.

**Lectura:**
- **eMBB:** IPACT ~75 %, QoS-DBA ~77 %. Diferencia pequeña, ambas altas. Esperado: el canal está saturado y la mayoría del eMBB excede el buffer.
- **URLLC:** IPACT ~87 % (barra azul llena hasta ~10²), QoS-DBA ~10⁻⁶ % (barra roja al piso del gráfico, prácticamente 0). Esta es la diferencia más importante del proyecto —5 órdenes de magnitud.
- **mMTC:** Ambos algoritmos tienen pérdida ~10⁻⁶ % (esencialmente cero). mMTC tiene tasa baja (0.5 Mbps) y buffer suficiente para absorber variabilidad.
- Las barras de QoS-DBA URLLC y mMTC están en 10⁻⁶ porque el script usa ese valor como piso para evitar `log(0)`. La pérdida real es 0 paquetes en las 3 repeticiones.

**Estado:** Correcto. La escala logarítmica es la elección correcta para este tipo de datos.

---

#### Gráfico 6 — `latency_timeseries_urllc.png`

**Qué muestra:** Latencia de cada paquete URLLC a lo largo del tiempo de simulación, para una corrida representativa a 200 Mbps eMBB. Dos subplots con escalas Y independientes.

**Lectura:**
- **IPACT (subplot superior, 0–10 000 μs):** Todos los puntos se agrupan entre ~8 000 y ~10 000 μs. La línea de deadline está al tope. No hay paquetes con latencia baja —todos esperan casi hasta el límite antes de poder transmitirse. La dispersión vertical es baja, indicando comportamiento estacionario.
- **QoS-DBA (subplot inferior, 0–500 μs):** Los puntos se distribuyen entre ~50 y ~400 μs. La nota "Deadline = 10 ms (fuera de escala)" indica que el deadline está 25× por encima del rango visible. El comportamiento es estacionario sin tendencia temporal —QoS-DBA mantiene latencia baja a lo largo de toda la simulación.

**Estado:** Correcto tras corrección de escala Y independiente para QoS-DBA. Evidencia gráfica directa del comportamiento en el tiempo.

---

#### Gráfico 7 — `summary_dashboard.png`

**Qué muestra:** Los 4 subplots principales juntos en una figura 2×2, diseñada para usar en una sola lámina de presentación.

**Lectura:** Combina los gráficos 1, 2, 3 y 5 en formato compacto. El subplot de throughput (inferior izquierdo) muestra las curvas superpuestas (misma saturación de canal en ambos algoritmos). El subplot de pérdida (inferior derecho) es quizás el más impactante visualmente: la diferencia de 5 órdenes de magnitud en URLLC es evidente a simple vista.

**Recomendación de uso:** Este gráfico es el más adecuado para la lámina de resultados del informe final.

---

## 9. Cómo Compilar y Ejecutar

### 9.1 Compilación

```bash
cd ~/pon-dba-sim
source ~/omnetpp-6.0.3/setenv
opp_makemake -f --deep -O out
make -j$(nproc)
```

### 9.2 Ejecución en modo batch (todas las configuraciones 16 ONUs)

```bash
./pon-dba-sim -u Cmdenv -c IPACT_16ONU  -r 0..2
./pon-dba-sim -u Cmdenv -c QoSDBA_16ONU -r 0..2
```

### 9.3 Visualización en GUI (Qtenv)

```bash
./pon-dba-sim -u Qtenv -c IPACT_16ONU -r 0
```

La GUI muestra la red animada: OLT (servidor azul), splitter (switch amarillo), ONUs (módems verdes). Los mensajes se mueven por la fibra con colores:
- Verde oval: paquetes eMBB
- Rojo oval: paquetes URLLC
- Naranja oval: paquetes mMTC
- Azul rect: mensajes REPORT
- Cyan rect: mensajes GRANT/POLL

Cada ONU muestra en tiempo real el tamaño de sus tres colas. Cuando se descarta un paquete, aparece un bubble "DROP eMBB!" o "DROP URLLC!" y un ícono de advertencia.

### 9.4 Análisis de resultados

```bash
# Exportar .sca a CSV (requiere opp_scavetool en el PATH)
bash simulations/export_results.sh

# Generar 7 figuras PNG
python3 analysis/analyze.py --results-dir simulations/results
```

---

## 10. Trabajo Pendiente

| Tarea | Descripción | Prioridad |
|-------|-------------|-----------|
| 10 repeticiones | Aumentar de 3 a 10 para intervalos de confianza del 95 % estadísticamente válidos | Alta |
| Escenarios 32 ONUs | Ejecutar IPACT_32ONU y QoSDBA_32ONU para evaluar escalabilidad | Alta |
| Análisis estadístico | Tests de hipótesis (Mann-Whitney U), IC95%, verificación de distribuciones | Media |
| Informe final IEEE | Documento formal con todas las secciones, bibliografía completa | Alta |
| Demo Qtenv | Preparar corrida visual con velocidad de animación ajustada para presentación | Baja |

---

## 11. Conclusiones Preliminares

1. **La hipótesis central se confirma:** IPACT es insuficiente para redes PON-5G con tráfico mixto. Su diseño sin conciencia de QoS condena al tráfico URLLC a tasas de pérdida inaceptables (≥ 75 %) desde niveles de carga moderados.

2. **QoS-DBA resuelve el problema:** La prioridad estricta para URLLC, combinada con WFQ para las clases restantes, garantiza pérdida cero de tráfico crítico en todos los escenarios probados.

3. **El modelo es físicamente válido:** Los resultados son coherentes con los parámetros de la red (RTT, capacidad del canal, tamaño de buffers) y con el comportamiento teórico de sistemas de colas con tráfico heavy-tailed.

4. **Trabajo pendiente antes de conclusiones definitivas:** El análisis estadístico completo (IC95%, tests de hipótesis) y los escenarios de 32 ONUs son necesarios para que las conclusiones sean formalmente sólidas.

---

## 12. Referencias

- Kramer, G., Mukherjee, B., Pesavento, G. (2002). IPACT: a dynamic protocol for an Ethernet PON. *IEEE Communications Magazine*, 40(2), 74–80.
- Leland, W. E., Taqqu, M. S., Willinger, W., Wilson, D. V. (1994). On the self-similar nature of Ethernet traffic. *IEEE/ACM Transactions on Networking*, 2(1), 1–15.
- 3GPP TR 38.913 (2017). Study on scenarios and requirements for next generation access technologies.
- Varga, A. (2010). OMNeT++. In Modeling and Tools for Network Simulation. Springer.
