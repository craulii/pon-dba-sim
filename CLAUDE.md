# CLAUDE.md — Proyecto PON DBA Simulation en OMNeT++

## Contexto del proyecto

Soy estudiante de Ingeniería Civil Telemática en la UTFSM (Chile). Tengo un proyecto semestral para el ramo **TEL-341 Simulación de Redes** donde debo simular un problema de redes usando OMNeT++.

**Equipo:** OmneTeam (David Retuerto, José Vega, Matías Perelli)

**Tema:** Evaluación de algoritmos de asignación dinámica de ancho de banda (DBA) en redes PON (Passive Optical Network) bajo tráfico 5G multi-servicio.

**Plazo:** 1 semana. Necesito código funcional, compilable y ejecutable.

---

## Qué debe hacer este proyecto

### Resumen en una línea
Simular una red PON (OLT + splitter + N ONUs) donde cada ONU genera tráfico 5G de 3 tipos (eMBB, URLLC, mMTC), comparar 2 algoritmos DBA (IPACT vs QoS-aware), y medir latencia/throughput/jitter/pérdida por clase de servicio.

### Arquitectura de la red

```
[Central Office]
    |
  [OLT] ← Motor DBA (IPACT o QoS-DBA)
    |
  Feeder Fiber (20km, delay = 100μs)
    |
  [Splitter 1:N]
    |--- Distribution Fiber --- [ONU 0] --- [TrafficGen eMBB]
    |--- Distribution Fiber --- [ONU 1] --- [TrafficGen URLLC]
    |--- Distribution Fiber --- [ONU 2] --- [TrafficGen mMTC]
    |--- ...
    |--- Distribution Fiber --- [ONU N-1] --- [TrafficGen mixto]
```

### Mecanismo PON simplificado (TDM upstream)

1. Las ONUs generan tráfico y lo almacenan en buffers internos (3 colas: eMBB, URLLC, mMTC)
2. Cada ONU envía un mensaje REPORT a la OLT indicando cuántos bytes tiene pendientes por cola
3. La OLT ejecuta el algoritmo DBA y envía un mensaje GRANT a cada ONU con su slot de transmisión (inicio + duración)
4. Las ONUs transmiten en su slot asignado (no hay colisiones, es TDM)
5. Se repite el ciclo (polling cycle)

---

## Estructura de archivos esperada

```
pon-dba-sim/
├── src/
│   ├── OLT.ned          # Módulo OLT (compuesto)
│   ├── OLT.h
│   ├── OLT.cc
│   ├── ONU.ned          # Módulo ONU (compuesto)
│   ├── ONU.h
│   ├── ONU.cc
│   ├── Splitter.ned     # Splitter pasivo (solo retransmite)
│   ├── Splitter.h
│   ├── Splitter.cc
│   ├── DBAAlgorithm.h       # Interfaz base para algoritmos DBA
│   ├── IPACT.h               # Algoritmo 1: IPACT
│   ├── IPACT.cc
│   ├── QoSDBA.h              # Algoritmo 2: DBA con prioridad QoS
│   ├── QoSDBA.cc
│   ├── TrafficGenerator.h    # Base class para generadores
│   ├── eMBBTrafficGen.h      # Generador eMBB
│   ├── eMBBTrafficGen.cc
│   ├── URLLCTrafficGen.h     # Generador URLLC
│   ├── URLLCTrafficGen.cc
│   ├── mMTCTrafficGen.h      # Generador mMTC
│   ├── mMTCTrafficGen.cc
│   ├── PONMessages.msg       # Definición de mensajes (REPORT, GRANT, DATA)
│   └── PONNetwork.ned        # Red completa parametrizable
├── simulations/
│   ├── omnetpp.ini            # Configuración de escenarios
│   └── run_all.sh             # Script para correr todos los escenarios
├── analysis/
│   ├── analyze.py             # Script Python para procesar resultados
│   ├── export_results.sh      # Script para exportar .vec/.sca a CSV
│   └── requirements.txt      # pandas, matplotlib, numpy, scipy
├── package.ned                # Package definition
└── README.md
```

---

## Especificaciones técnicas detalladas

### Mensajes (PONMessages.msg)

```
// OMNeT++ message definitions
packet DataPacket {
    int sourceONU;
    int trafficClass;      // 0=eMBB, 1=URLLC, 2=mMTC
    simtime_t creationTime; // para calcular latencia
    simtime_t deadline;     // solo URLLC, -1 para otros
    int dataSize @unit(byte);
}

message ReportMessage {
    int sourceONU;
    int queueSize_eMBB @unit(byte);
    int queueSize_URLLC @unit(byte);
    int queueSize_mMTC @unit(byte);
}

message GrantMessage {
    int destONU;
    simtime_t startTime;
    int grantSize_eMBB @unit(byte);
    int grantSize_URLLC @unit(byte);
    int grantSize_mMTC @unit(byte);
}
```

### Parámetros de los generadores de tráfico

| Parámetro | eMBB | URLLC | mMTC |
|-----------|------|-------|------|
| Distribución inter-arrival | Pareto (self-similar) | Poisson (exponencial) | Periódico + jitter |
| Tamaño paquete | 1000-1500 bytes | 32-256 bytes | 20-200 bytes |
| Tasa media | Configurable (50-200 Mbps) | Configurable (1-10 Mbps) | Configurable (0.1-1 Mbps) |
| Deadline | No (-1) | 250 μs | No (-1) |

### Algoritmo 1: IPACT (Interleaved Polling with Adaptive Cycle Time)
- La OLT encuesta (poll) cada ONU secuencialmente
- Cada ONU reporta sus bytes pendientes (total, sin diferenciar clase)
- La OLT asigna un grant proporcional al reporte, con un máximo por ONU (max grant)
- No hay diferenciación de QoS — todos los paquetes se tratan igual
- Referencia: paper de Kramer & Mukherjee (2002)

### Algoritmo 2: QoS-DBA (Priority-based with WFQ)
- La OLT recibe reportes con detalle por clase (3 valores)
- Paso 1: asignar bandwidth a TODAS las colas URLLC primero (prioridad estricta)
- Paso 2: repartir el bandwidth restante entre eMBB y mMTC usando Weighted Fair Queuing (pesos configurables, ej: eMBB=70%, mMTC=30%)
- Cada ONU recibe un grant detallado por clase

### Parámetros de red (configurables en omnetpp.ini)

```ini
# Topología
**.numONUs = 16                    # Número de ONUs (variar: 16, 32)
**.fiberLength = 20km              # Largo fibra alimentadora
**.splitterRatio = 16              # Ratio del splitter

# Canal
**.dataRate = 1Gbps                # Velocidad upstream (simplificado)
**.propagationDelay = 5us/km       # Delay de propagación en fibra

# DBA
**.dbaAlgorithm = "IPACT"          # o "QoSDBA"
**.maxGrantSize = 64000B           # Grant máximo por ONU por ciclo
**.pollingCycleTime = 2ms          # Tiempo máximo de ciclo de polling
**.guardTime = 1us                 # Tiempo de guarda entre slots

# Buffers ONU
**.bufferSize_eMBB = 1MB
**.bufferSize_URLLC = 100KB
**.bufferSize_mMTC = 500KB

# Tráfico (ajustar para variar carga)
**.embbRate = 100Mbps
**.urllcRate = 5Mbps
**.mmtcRate = 0.5Mbps

# Simulación
sim-time-limit = 10s
warmup-period = 1s
repeat = 10
seed-set = ${repetition}
```

### Métricas a registrar (usando cOutVector y recordScalar)

Por cada ONU y por cada clase de servicio:
- **Latencia upstream**: `simTime() - packet->getCreationTime()`
- **Throughput**: bytes transmitidos exitosamente / tiempo de simulación
- **Jitter**: variación de latencia entre paquetes consecutivos
- **Tasa de pérdida**: paquetes perdidos (buffer overflow + deadline expired) / paquetes generados
- **Utilización del canal**: tiempo que el canal está ocupado / tiempo total

### Escenarios a simular (como Config sections en omnetpp.ini)

```ini
[Config IPACT_16ONU]
**.dbaAlgorithm = "IPACT"
**.numONUs = 16
**.embbRate = ${load=50, 100, 150, 200}Mbps  # Variar carga

[Config QoSDBA_16ONU]
**.dbaAlgorithm = "QoSDBA"
**.numONUs = 16
**.embbRate = ${load=50, 100, 150, 200}Mbps

[Config IPACT_32ONU]
**.dbaAlgorithm = "IPACT"
**.numONUs = 32
**.embbRate = ${load=50, 100, 150, 200}Mbps

[Config QoSDBA_32ONU]
**.dbaAlgorithm = "QoSDBA"
**.numONUs = 32
**.embbRate = ${load=50, 100, 150, 200}Mbps
```

---

## Script de análisis (analysis/analyze.py)

El script debe:
1. Leer los archivos .sca y .vec generados por OMNeT++ (usar `omnetpp.scavetool export` para convertir a CSV, o parsear directamente)
2. Generar los siguientes gráficos con Matplotlib:
   - **Latencia promedio por clase de servicio** (barras agrupadas, IPACT vs QoS-DBA)
   - **Latencia P99 URLLC vs carga** (curvas, con línea horizontal en 250μs como referencia)
   - **Throughput agregado vs carga** (curvas por algoritmo)
   - **CDF de latencia URLLC** (comparando IPACT vs QoS-DBA bajo carga alta)
   - **Tasa de pérdida por clase** (barras agrupadas)
3. Incluir intervalos de confianza del 95% (10 repeticiones)
4. Guardar los gráficos como PNG de alta resolución (300 DPI)

### Script export_results.sh

```bash
#!/bin/bash
# Exportar todos los resultados a CSV para análisis en Python
cd ../simulations/results
for f in *.sca; do
    opp_scavetool export -o "${f%.sca}.csv" -F CSV-S "$f"
done
for f in *.vec; do
    opp_scavetool export -o "${f%.vec}_vec.csv" -F CSV-R "$f"
done
echo "Exportación completada."
```

### Especificación detallada de gráficos (analyze.py)

El script debe generar exactamente estos 7 gráficos, guardados en `analysis/figures/`:

#### Gráfico 1: `latency_avg_by_class.png`
- Tipo: barras agrupadas (grouped bar chart)
- Eje X: clase de servicio (eMBB, URLLC, mMTC)
- Eje Y: latencia promedio upstream (μs)
- Grupos: IPACT vs QoS-DBA
- Barras de error: intervalo de confianza 95%
- Carga fija: la más alta (200 Mbps eMBB)
- Colores: azul para IPACT, rojo para QoS-DBA

#### Gráfico 2: `latency_p99_urllc_vs_load.png`
- Tipo: curvas (line plot)
- Eje X: carga eMBB (50, 100, 150, 200 Mbps)
- Eje Y: latencia P99 de URLLC (μs)
- Dos curvas: IPACT y QoS-DBA
- Línea horizontal punteada roja en 250 μs (deadline URLLC)
- Banda sombreada: intervalo de confianza 95%
- **Este es el gráfico más importante del proyecto**

#### Gráfico 3: `throughput_vs_load.png`
- Tipo: curvas
- Eje X: carga ofrecida (normalizada, 0.3 a 0.9)
- Eje Y: throughput agregado (Mbps)
- Dos curvas por algoritmo
- Línea diagonal punteada gris = throughput ideal (carga = throughput)

#### Gráfico 4: `cdf_latency_urllc.png`
- Tipo: CDF (Cumulative Distribution Function)
- Eje X: latencia URLLC (μs)
- Eje Y: probabilidad acumulada (0 a 1)
- Dos curvas: IPACT vs QoS-DBA
- Solo bajo carga alta (200 Mbps eMBB)
- Línea vertical en 250 μs (deadline)
- Escala X logarítmica si es necesario

#### Gráfico 5: `packet_loss_by_class.png`
- Tipo: barras agrupadas
- Eje X: clase de servicio
- Eje Y: tasa de pérdida (%)
- IPACT vs QoS-DBA
- Escala Y logarítmica (para ver diferencias en URLLC donde objetivo es <10⁻⁵)

#### Gráfico 6: `latency_timeseries_urllc.png`
- Tipo: scatter/line plot
- Eje X: tiempo de simulación (s)
- Eje Y: latencia por paquete URLLC (μs)
- Dos subplots: IPACT arriba, QoS-DBA abajo
- Línea horizontal en 250 μs
- Solo una corrida representativa (para mostrar comportamiento temporal)

#### Gráfico 7: `summary_dashboard.png`
- Tipo: figura compuesta (2x2 subplots)
- Subplot 1: latencia promedio por clase (barras)
- Subplot 2: P99 URLLC vs carga (curvas)
- Subplot 3: throughput vs carga (curvas)
- Subplot 4: pérdida por clase (barras)
- Título general: "Comparación IPACT vs QoS-DBA — Red PON con tráfico 5G"
- **Este gráfico es para la presentación final (1 slide)**

### Estilo visual de los gráficos
- Usar `plt.style.use('seaborn-v0_8-whitegrid')` como base
- Fuente: `plt.rcParams['font.family'] = 'serif'` (estilo paper IEEE)
- Tamaño fuente ejes: 12pt, título: 14pt
- Colores consistentes: IPACT = `#1f77b4` (azul), QoS-DBA = `#d62728` (rojo)
- Colores por clase: eMBB = `#2ca02c` (verde), URLLC = `#d62728` (rojo), mMTC = `#ff7f0e` (naranja)
- Leyenda siempre visible, fuera del área de datos si es posible
- Grid suave con alpha=0.3
- Guardar con `dpi=300, bbox_inches='tight'`
- Cada gráfico debe tener título, labels de ejes con unidades, y leyenda

---

## Visualización gráfica en OMNeT++ (GUI Qtenv)

### Display strings en archivos NED

Cada módulo debe tener un `@display` string para que se vea correctamente en la GUI animada (Qtenv). Esto es OBLIGATORIO para la demo en la presentación.

#### PONNetwork.ned (red completa)
```ned
network PONNetwork {
    parameters:
        int numONUs = default(16);
        @display("bgb=900,500");  // tamaño del canvas
    submodules:
        olt: OLT {
            @display("p=100,250;i=device/server2;is=l");  // izquierda, ícono grande
        }
        splitter: Splitter {
            @display("p=350,250;i=device/opticalswitch;is=n");
        }
        onu[numONUs]: ONU {
            @display("p=600,50+400*index/numONUs;i=device/modem;is=s");  // distribuidas verticalmente
        }
    connections:
        olt.ponPort <--> {delay=100us; datarate=1Gbps;} <--> splitter.oltPort;
        for i=0..numONUs-1 {
            splitter.onuPort[i] <--> {delay=10us; datarate=1Gbps;} <--> onu[i].ponPort;
        }
}
```

### Iconos a usar (built-in de OMNeT++)
- OLT: `i=device/server2` (servidor grande) — color azul
- Splitter: `i=device/opticalswitch` — color amarillo
- ONU: `i=device/modem` — color verde
- También se puede usar `i=abstract/router` o `i=device/terminal`
- Tamaños: `is=l` (large), `is=n` (normal), `is=s` (small), `is=vs` (very small)

### Colores de mensajes en movimiento
Los mensajes deben tener colores distintos para que se diferencien visualmente en la animación:

En los archivos .cc, al crear mensajes:
```cpp
// En DataPacket - color según clase de servicio
DataPacket *pkt = new DataPacket("eMBB-data");
pkt->setDisplayString("b=10,10,oval,green");   // eMBB = verde

DataPacket *pkt = new DataPacket("URLLC-data");
pkt->setDisplayString("b=10,10,oval,red");     // URLLC = rojo

DataPacket *pkt = new DataPacket("mMTC-data");
pkt->setDisplayString("b=10,10,oval,orange");  // mMTC = naranja

// ReportMessage
ReportMessage *report = new ReportMessage("REPORT");
report->setDisplayString("b=8,8,rect,blue");   // Azul

// GrantMessage
GrantMessage *grant = new GrantMessage("GRANT");
grant->setDisplayString("b=8,8,rect,cyan");    // Cyan
```

### Textos dinámicos en módulos (bubble y display string updates)

En los módulos, actualizar el display string en runtime para mostrar estado:

```cpp
// En OLT::handleMessage() — mostrar algoritmo activo
getDisplayString().setTagArg("t", 0, (std::string("DBA: ") + dbaAlgorithm).c_str());

// En ONU::handleMessage() — mostrar ocupación del buffer
char buf[64];
sprintf(buf, "Q: %d/%d/%d B", queueSize_eMBB, queueSize_URLLC, queueSize_mMTC);
getDisplayString().setTagArg("t", 0, buf);

// Mostrar bubble cuando se descarta un paquete
if (packetDropped) {
    bubble("Packet dropped!");
    getDisplayString().setTagArg("i2", 0, "status/excl");  // ícono de warning
}

// Mostrar bubble cuando URLLC cumple deadline
if (urllcDeadlineMet) {
    bubble("URLLC OK");
}
```

### Animación del canal
Para que se vean los paquetes moviéndose por la fibra (no solo aparecer), los canales deben tener delay configurado:
```ned
// Esto ya está en las connections, pero verificar que el delay sea visible
// Un delay de 100us es muy corto para ver la animación. En el omnetpp.ini se puede
// escalar el tiempo de animación:
// **.animation-speed = 0.5
```

### Configuración de Qtenv en omnetpp.ini
```ini
[General]
# Configuración visual para la GUI
qtenv-default-config = IPACT_16ONU
qtenv-default-run = 0

# Velocidad de animación (ajustar para demo)
**.animation-speed = 1
**.animation-msgnames = true
**.animation-methodcalls = false
```

---

## Instrucciones para Claude Code

### Prioridades (en orden)
1. **Que compile**: código C++ correcto para OMNeT++ 6.x, archivos NED válidos, mensajes .msg correctos
2. **Que corra**: que la simulación se ejecute sin errores de runtime
3. **Que se vea**: display strings en NED, colores de mensajes, textos de estado dinámicos, bubbles — la GUI Qtenv debe mostrar una red PON animada y visualmente clara
4. **Que mida**: que registre las métricas correctamente en archivos .vec/.sca
5. **Que compare**: que los 2 algoritmos DBA sean intercambiables por configuración
6. **Que grafique**: que `analyze.py` genere los 7 gráficos PNG especificados con estilo IEEE paper

### Cosas importantes de OMNeT++ que debes saber
- Los módulos heredan de `cSimpleModule` (módulos simples) o son `module` en NED (compuestos)
- Los mensajes se definen en archivos `.msg` y OMNeT++ genera automáticamente las clases C++ con `opp_msgc`
- `handleMessage(cMessage *msg)` es el método principal que procesa eventos
- `scheduleAt(simtime_t, cMessage*)` programa un evento futuro (self-message)
- `send(cMessage*, const char* gateName)` envía un mensaje por un gate
- `cOutVector` registra series temporales, `recordScalar()` registra valores finales
- `par("nombreParam")` lee parámetros del .ned/.ini
- Los gates se conectan en el .ned con `<-->` (bidireccional) o `-->` (unidireccional)
- Los canales tienen `delay` y `datarate` como propiedades
- `simTime()` retorna el tiempo actual de simulación
- Para vectores de módulos en NED: `onu[numONUs]: ONU;`

### Estilo de código
- C++ moderno (C++17)
- Comentarios en español
- Nombres de variables/funciones en inglés (convención OMNeT++)
- Cada clase en su propio .h/.cc
- Usar `EV <<` para logging (no cout/printf)

### NO hacer
- No usar INET Framework (solo OMNeT++ base) — todo custom
- No modelar la capa física óptica (potencia, BER, etc.)
- No implementar downstream (solo upstream es relevante para DBA)
- No usar features de OMNeT++ 5.x deprecated en 6.x

---

## Resultado esperado

Al terminar, debo poder:
1. Abrir el proyecto en el IDE de OMNeT++
2. Compilar sin errores con `opp_makemake -f --deep -O out && make -j$(nproc)`
3. Correr cada Config section en modo terminal (`-u Cmdenv`)
4. **Ver la animación en GUI** (`-u Qtenv`): OLT, splitter y ONUs con íconos, mensajes de colores moviéndose (verde=eMBB, rojo=URLLC, naranja=mMTC, azul=REPORT, cyan=GRANT), textos de estado en cada módulo, y bubbles cuando se descartan paquetes
5. Obtener archivos .vec/.sca con resultados en `simulations/results/`
6. Correr `analysis/export_results.sh` para convertir a CSV
7. Correr `analysis/analyze.py` y obtener **7 gráficos PNG** en `analysis/figures/` listos para el informe y la presentación

### Para la presentación necesito mostrar:
- **Demo en vivo**: correr la simulación en Qtenv mostrando la animación de la red PON con mensajes de colores
- **Gráfico dashboard** (summary_dashboard.png): 1 slide con 4 subplots comparando IPACT vs QoS-DBA
- **Gráfico P99 URLLC vs carga**: el resultado clave que muestra que QoS-DBA protege el tráfico URLLC

### Entorno de desarrollo
- OMNeT++ 6.0.3 instalado en: `~/omnetpp-6.0.3/`
- Proyecto en: `~/pon-dba-sim/`
- Para compilar: `source ~/omnetpp-6.0.3/setenv && opp_makemake -f --deep -O out && make -j$(nproc)`
- Para correr GUI: `./pon-dba-sim -u Qtenv`
- Para correr batch: `./pon-dba-sim -u Cmdenv -c IPACT_16ONU -r 0..9`

**Este es un proyecto universitario real con nota. La calidad del código, la visualización gráfica y la rigurosidad de la simulación importan.**