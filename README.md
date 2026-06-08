# PON DBA Simulation — TEL-341 Simulación de Redes

**Equipo OmneTeam** · David Retuerto · José Vega · Matías Perelli  
Universidad Técnica Federico Santa María (UTFSM) · 2026

---

## ¿Qué es este proyecto?

Simulación en OMNeT++ de una red óptica pasiva (PON) operando como **backhaul 5G**, donde múltiples estaciones base comparten un canal upstream TDM de 1 Gbps. Se comparan dos algoritmos de asignación dinámica de ancho de banda (DBA):

- **IPACT** — estándar IEEE 802.3ah, sin diferenciación de QoS
- **QoS-DBA** — algoritmo propuesto con prioridad estricta para URLLC + WFQ para eMBB/mMTC

**Resultado clave:** IPACT pierde 75–87 % del tráfico URLLC (crítico). QoS-DBA mantiene pérdida URLLC = 0 % en todos los niveles de carga.

---

## Estructura del proyecto

```
pon-dba-sim/
├── src/                        # Código fuente C++17
│   ├── OLT.h / OLT.cc          # Motor DBA: ciclos de polling, grants
│   ├── ONU.h / ONU.cc          # Colas eMBB/URLLC/mMTC, generadores tráfico
│   ├── Splitter.h / Splitter.cc
│   ├── IPACT.h / IPACT.cc      # Algoritmo 1: proporcional sin QoS
│   ├── QoSDBA.h / QoSDBA.cc    # Algoritmo 2: prioridad URLLC + WFQ
│   ├── DBAAlgorithm.h          # Interfaz base (abstracta)
│   ├── PONMessages.msg         # Mensajes OMNeT++: DataPacket, Report, Grant
│   └── PONNetwork.ned          # Topología parametrizable
├── simulations/
│   ├── omnetpp.ini             # Configuración de escenarios
│   ├── run_all.sh              # Script para correr todos los escenarios
│   └── results/                # Archivos .sca y .vec (generados al correr)
├── analysis/
│   ├── analyze.py              # Genera 7 gráficos PNG desde los resultados
│   ├── export_results.sh       # Exporta .sca/.vec a CSV
│   └── figures/                # Gráficos PNG (generados al analizar)
├── Parte 2/                    # Materiales de presentación (Avance Nº 2)
│   ├── informe_avances.tex     # Informe LaTeX
│   ├── informe_avances.pdf     # PDF compilado
│   ├── generar_presentacion.py # Script que genera el PPTX
│   ├── presentacion_avances.pptx
│   ├── guion.md                # Guion oral para la presentación
│   └── figuras/                # Copia de los 7 gráficos para el informe
├── PROYECTO.md                 # Documentación técnica integral del proyecto
├── CLAUDE.md                   # Instrucciones del proyecto para Claude Code
└── README.md                   # Este archivo
```

---

## Requisitos

### Simulación
- **OMNeT++ 6.0.3** instalado en `~/omnetpp-6.0.3/`
- Compilador C++17 (GCC >= 9 o Clang >= 10)

### Análisis
- Python 3.8+
- Paquetes: `pandas`, `matplotlib`, `numpy`, `scipy`

```bash
pip install pandas matplotlib numpy scipy
```

### Informe (PDF)
- `texlive-latex-base`, `texlive-latex-extra`, `texlive-lang-spanish`

```bash
sudo apt-get install -y texlive-latex-base texlive-latex-extra texlive-lang-spanish
```

### Presentación (PPTX)
- `python-pptx`

```bash
pip install python-pptx
```

---

## Cómo ejecutar: paso a paso

### 1. Activar entorno OMNeT++

```bash
source ~/omnetpp-6.0.3/setenv
```

Agrega esto a tu `~/.bashrc` para no repetirlo cada sesión:
```bash
echo 'source ~/omnetpp-6.0.3/setenv' >> ~/.bashrc
```

### 2. Compilar la simulación

```bash
cd ~/pon-dba-sim
opp_makemake -f --deep -O out
make -j$(nproc)
```

Si todo está bien, se genera el ejecutable `pon-dba-sim` en la raíz.

### 3. Ejecutar simulaciones

**Todas las configuraciones de 16 ONUs (recomendado para empezar):**
```bash
cd simulations
bash run_all.sh
```

**O manualmente, una configuración a la vez:**
```bash
# IPACT con 16 ONUs, 3 repeticiones
../pon-dba-sim -u Cmdenv -c IPACT_16ONU -r 0..2

# QoS-DBA con 16 ONUs, 3 repeticiones
../pon-dba-sim -u Cmdenv -c QoSDBA_16ONU -r 0..2

# (Pendiente) 32 ONUs
../pon-dba-sim -u Cmdenv -c IPACT_32ONU -r 0..2
../pon-dba-sim -u Cmdenv -c QoSDBA_32ONU -r 0..2
```

Los resultados se guardan en `simulations/results/` como archivos `.sca` (escalares) y `.vec` (vectores temporales).

### 4. Visualización en GUI (Qtenv)

Para ver la animación en vivo de la red PON:

```bash
cd simulations
../pon-dba-sim -u Qtenv -c IPACT_16ONU -r 0
```

En la GUI verás:
- OLT (azul), splitter (amarillo), ONUs (verde)
- Mensajes moviéndose por la fibra con colores:
  - Verde oval: paquetes eMBB
  - Rojo oval: paquetes URLLC
  - Naranja oval: paquetes mMTC
  - Azul rect: mensajes REPORT
  - Cyan rect: mensajes GRANT/POLL
- Bubble "DROP!" cuando se descarta un paquete

### 5. Exportar resultados a CSV

```bash
cd simulations
bash ../analysis/export_results.sh
```

Requiere que `opp_scavetool` esté en el PATH (incluido con OMNeT++).

### 6. Generar gráficos de análisis

```bash
cd ~/pon-dba-sim
python3 analysis/analyze.py --results-dir simulations/results
```

Genera 7 gráficos PNG en `analysis/figures/`:

| Archivo | Contenido |
|---------|-----------|
| `latency_avg_by_class.png` | Latencia promedio por clase (barras) |
| `latency_p99_urllc_vs_load.png` | P99 URLLC vs. carga (curvas) |
| `throughput_vs_load.png` | Throughput por ONU vs. carga ofrecida |
| `cdf_latency_urllc.png` | CDF de latencia URLLC (escala log) |
| `packet_loss_by_class.png` | Tasa de pérdida por clase (escala log) |
| `latency_timeseries_urllc.png` | Serie temporal de latencia URLLC |
| `summary_dashboard.png` | Dashboard 2x2 para presentación |

### 7. Compilar informe PDF

```bash
cd "Parte 2"
pdflatex -interaction=nonstopmode informe_avances.tex
pdflatex -interaction=nonstopmode informe_avances.tex   # segunda pasada para referencias
```

El PDF resultante es `Parte 2/informe_avances.pdf`.

### 8. Generar presentación PPTX

```bash
cd "Parte 2"
python3 generar_presentacion.py
```

Genera `Parte 2/presentacion_avances.pptx` (13 slides).

---

## Configuraciones de simulación disponibles

Definidas en `simulations/omnetpp.ini`:

| Config | Algoritmo | ONUs | Cargas eMBB | Estado |
|--------|-----------|------|-------------|--------|
| `IPACT_16ONU` | IPACT | 16 | 50/100/150/200 Mbps | Completado |
| `QoSDBA_16ONU` | QoS-DBA | 16 | 50/100/150/200 Mbps | Completado |
| `IPACT_32ONU` | IPACT | 32 | 50/100/150/200 Mbps | Pendiente |
| `QoSDBA_32ONU` | QoS-DBA | 32 | 50/100/150/200 Mbps | Pendiente |
| `QuickTest` | IPACT | 4 | 100 Mbps | Prueba rapida (2s) |
| `QuickTest_QoSDBA` | QoS-DBA | 4 | 100 Mbps | Prueba rapida (2s) |

Para hacer una prueba rapida que corra en ~10 segundos:
```bash
../pon-dba-sim -u Cmdenv -c QuickTest -r 0
```

---

## Parametros clave del modelo

| Parametro | Valor | Descripcion |
|-----------|-------|-------------|
| `numONUs` | 16 (32) | Numero de ONUs/estaciones base |
| `dataRate` | 1 Gbps | Capacidad del canal upstream |
| `pollingCycleTime` | 2 ms | Periodo maximo de un ciclo DBA |
| `maxGrantSize` | 15 000 B | Limite de bytes asignados por ONU por ciclo |
| `urllcDeadline` | 10 ms | Presupuesto de latencia URLLC en backhaul 5G |
| `embbRate` | 50-200 Mbps | Tasa eMBB (variable entre escenarios) |
| `urllcRate` | 5 Mbps | Tasa URLLC fija |
| `mmtcRate` | 0.5 Mbps | Tasa mMTC fija |
| `wfqWeightEMBB` | 0.7 | Peso WFQ para eMBB (solo QoS-DBA) |
| `wfqWeightMMTC` | 0.3 | Peso WFQ para mMTC (solo QoS-DBA) |
| `warmup-period` | 1 s | Periodo de calentamiento excluido del analisis |
| `sim-time-limit` | 10 s | Duracion total de cada corrida |
| `repeat` | 3 | Repeticiones con semillas distintas |

---

## Trabajo pendiente (antes del informe final)

- [ ] Aumentar `repeat` de 3 a 10 en `omnetpp.ini` y re-ejecutar
- [ ] Ejecutar escenarios `IPACT_32ONU` y `QoSDBA_32ONU`
- [ ] Analisis estadistico completo: IC95%, tests Mann-Whitney U
- [ ] Informe final completo estilo IEEE
- [ ] Demo en vivo con Qtenv para presentacion final

---

## Resumen de resultados actuales

Con 16 ONUs y 3 repeticiones:

| Algoritmo | Carga eMBB | Perdida URLLC | Perdida eMBB |
|-----------|-----------|--------------|-------------|
| IPACT     | 50 Mbps   | 75.8 %       | 0.1 %       |
| IPACT     | 200 Mbps  | 87.0 %       | 74.5 %      |
| QoS-DBA   | 50 Mbps   | 0.0 %        | 8.1 %       |
| QoS-DBA   | 200 Mbps  | 0.0 %        | 76.9 %      |

---

## Contacto

Equipo OmneTeam — David Retuerto, Jose Vega, Matias Perelli
TEL-341 Simulacion de Redes, UTFSM 2026
