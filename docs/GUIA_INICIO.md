# Guía de inicio — para alguien que no sabe nada de este proyecto

## OmneTeam · TEL-341 Simulación de Redes · UTFSM 2026

Este documento es el punto de entrada. Si nunca has visto este repo, empieza
aquí; el resto de `docs/` profundiza en cada tema.

---

## 1. La historia del proyecto en 3 frases

1. **Fase 1**: la idea original era simular GPON en **OMNeT++**, pero el
   simulador mezclaba conceptos de EPON (IPACT) y categorías 5G
   (eMBB/URLLC/mMTC) que no son de GPON. La profesora lo rechazó.
2. **Fase 2**: se reescribió **desde cero en Python puro** (sin OMNeT++, sin
   SimPy — motor de eventos propio), modelando GPON real (ITU-T G.984), 32
   ONUs, con dos algoritmos DBA centralizados (BasicDBA y QoSDBA). **Esta
   fase está entregada y no se toca.**
3. **Fase 3** (estado actual, completa, **única fase activa en la raíz del
   repo**): la profesora pivotó el enfoque a **XG-PON1 (ITU-T G.987)**, 8
   ONUs idénticas, con un **SLA de latencia explícito** (T-CONT1/VoIP ≤ 2
   ms) como problema central, comparando **3 algoritmos**: IPACT (polling,
   de EPON, usado aquí solo como comparación declarada), GIANT (nativo
   GPON/XG-PON) y QoSDBA (la referencia de Fase 2, reescalada).

El repo fue reorganizado para que la raíz contenga solo Fase 3: Fase 1 y
Fase 2 viven intactas (código sin modificar, solo movido) en `legacy/fase1/`
y `legacy/fase2/`. Los módulos del motor que Fase 3 reutiliza sin cambios
(`simulator/engine.py`, `onu.py`, `tcont.py`, `traffic.py`, `olt.py`,
`dba_qos.py`, `metrics/collector.py`) se quedaron en la raíz porque están
compartidos — no se duplicaron en `legacy/`.

## 2. ¿Qué problema resuelve el simulador?

En una red óptica pasiva (PON), **muchas ONUs comparten una sola fibra
upstream** hacia la OLT — solo puede transmitir una a la vez (TDMA). El
problema de ingeniería es: **¿cómo decide la OLT cuándo y cuánto puede
transmitir cada ONU?** Esa decisión se llama **DBA (Dynamic Bandwidth
Allocation)**, y de ella depende si el tráfico sensible a latencia (VoIP)
cumple su SLA cuando la red está congestionada.

El simulador existe para responder esa pregunta **sin necesitar hardware
real ni un simulador de redes de terceros**: se programa el comportamiento
exacto de la OLT, las ONUs y el canal óptico, se generan paquetes con las
distribuciones estadísticas correctas, y se mide qué pasa.

## 3. ¿Qué es "un simulador de eventos discretos" (DES)?

No es una animación ni un bucle que avanza en pasos de tiempo fijos. Es un
programa que mantiene una **lista de "cosas que van a pasar en el futuro"**
(eventos, cada uno con un timestamp), ordenada por tiempo. El reloj de la
simulación **salta directamente al próximo evento** — no hay nada que
calcular en los intervalos vacíos. Cada evento, al procesarse, puede
generar nuevos eventos futuros.

Ejemplo: una ONU genera un paquete de voz → ese mismo evento programa
"el próximo paquete de voz" dentro de 20 ms. La OLT nunca "espera" de forma
activa: simplemente no hay ningún evento programado para ese hueco de
tiempo, así que el motor salta limpio al siguiente.

Implementación real en este repo: `simulator/engine.py`, ~80 líneas, usa un
min-heap (`heapq`) de Python. Sin frameworks de simulación.

## 4. Pseudocódigo del funcionamiento completo

```
simular(config, algoritmo, seed):
    random.seed(seed)
    motor = SimEngine()                       # heap vacío, reloj=0
    metrics = MetricsCollector(warmup, sla_bounds)
    onus = [ONU(i, motor, config, metrics) for i in 0..N-1]
    # cada ONU, al construirse, agenda su 1er paquete por T-CONT en
    # t = offset_i + intervalo_segun_distribucion()

    si algoritmo == "ipact":
        olt = OLTPolling(motor, N, IpactDBA(), config, metrics)
        motor.schedule(0, OLT_SEND_GATE, {onu: 0})        # arranca en ONU 0
    sino:
        dba = GiantDBA() o QoSDBA()
        olt = OLT(motor, N, dba, config, metrics)
        motor.schedule(0, OLT_GENERATE_BWMAP)

    motor.run(hasta=duracion)                  # LOOP PRINCIPAL
    retornar metrics.summary(duracion)

motor.run(hasta):
    mientras heap no vacío y heap[0].tiempo <= hasta:
        evt = heap.pop_min()                   # menor (tiempo, seq)
        motor.now = evt.tiempo                 # el reloj SALTA al próximo evento
        tabla_handlers[evt.tipo](evt)          # puede agendar nuevos eventos
    retornar n_eventos_procesados

# --- generación de tráfico (self-scheduling, una distribución por T-CONT) ---
ONU.on_generate_traffic(evt):
    pkt = Paquete(tamaño=gen.next_pkt_size(), t_creacion=motor.now)
    tcont.buffer.enqueue(pkt)                  # si no cabe -> drop (pérdida)
    motor.schedule(gen.next_interval(), ONU_GENERATE_TRAFFIC, mismo evt.data)
    # T-CONT1 (VoIP):        intervalo fijo (CBR, determinístico)
    # T-CONT2 (Video):       intervalo ~ Exponencial (proceso de Poisson)
    # T-CONT4 (Best effort): intervalo ~ Pareto(alpha=1.5), cola pesada

# --- camino centralizado (broadcast, SR-DBA): GIANT / QoSDBA ---
OLT.on_generate_bwmap(evt):                    # cada 125us exactos
    bwmap = dba.allocate(ultimos_reportes, capacidad_trama, N, config)
    para cada (onu, asignacion) en bwmap:
        motor.schedule(prop_delay, ONU_RECEIVE_BWMAP, {onu, asignacion})
    motor.schedule(125us, OLT_GENERATE_BWMAP)  # se reagenda a 125us de distancia

ONU.on_receive_bwmap(evt):
    para cada (tcont, bytes_otorgados) en evt.asignacion:
        pkts = tcont.dequeue(bytes_otorgados)
        para cada pkt: motor.schedule_at(now + tx_acumulado + prop_delay, OLT_RECEIVE_DATA, pkt)
    motor.schedule(prop_delay, OLT_RECEIVE_REPORT, estado_colas)   # DBRu embebido

# --- camino polling (round-robin): IPACT ---
OLTPolling.on_send_gate(evt):                  # le toca a 1 ONU a la vez
    reporte = ultimo_reporte[onu_actual]       # puede tener ~1 ciclo de antigüedad
    asignacion = IpactDBA.allocate_onu(reporte, B_max)   # "limited service"
    motor.schedule(prop_delay, ONU_RECEIVE_GATE, {onu_actual, asignacion})
    motor.schedule(tiempo_grant + guard_time, OLT_POLL_NEXT)  # no espera respuesta
OLTPolling.on_poll_next(evt):
    onu_actual = (onu_actual + 1) mod N
    motor.schedule(0, OLT_SEND_GATE, {onu_actual})         # dispara el siguiente poll
```

La diferencia clave entre los dos caminos: **GIANT/QoSDBA** reparten cada
**trama fija de 125 μs** entre las 8 ONUs a la vez (broadcast); **IPACT**
le da turno a **una ONU a la vez**, y el ciclo completo (volver a la ONU 0)
dura lo que dure servir a las 8 — variable, entre 8 μs (colas vacías) y
1008 μs (saturación).

## 5. Las 3 distribuciones de tráfico (por qué cada una)

| T-CONT | Tráfico real que representa | Distribución | Por qué esa distribución |
|---|---|---|---|
| T-CONT1 | VoIP (G.711) | **Determinística (CBR)** | La voz codificada genera paquetes a intervalo fijo — no hay variabilidad que modelar |
| T-CONT2 | Video streaming | **Poisson** (interarribo exponencial) | Modelo clásico de tráfico "garantizado" con tasa media estable pero llegada aleatoria |
| T-CONT4 | Datos best-effort (web, P2P, descargas) | **Pareto α=1.5** (cola pesada) | Captura las ráfagas y self-similarity típicas de tráfico de datos real (a diferencia de Poisson, que subestima las ráfagas) |

## 6. Los 3 algoritmos DBA comparados (Fase 3)

| Algoritmo | Mecanismo | Archivo |
|---|---|---|
| **IPACT** | Polling round-robin secuencial, ciclo de duración variable, grant = min(demanda, B_max) | `simulator/dba_ipact.py` + `simulator/olt_ipact.py` |
| **GIANT** | GPA (T1 fijo + T2 asegurado con contador SImax) + SPA (T4 round-robin con contador SImin) | `simulator/dba_giant.py` |
| **QoSDBA** | Prioridad estricta T1 > T2 > T4, sin contadores de servicio | `simulator/dba_qos.py` (sin cambios desde Fase 2) |

## 7. Resultado central (lo que hay que poder explicar)

A carga alta (800 Mbps/ONU, sobrecarga ~257%): **GIANT y QoSDBA cumplen
100% el SLA de T-CONT1** (≤2ms) porque reservan ancho de banda de voz
**incondicionalmente** en cada trama de 125 μs, sin mirar la demanda
reportada. **IPACT cae a 88.4%** porque asigna T1 según el último reporte
recibido (~1 ciclo de antigüedad) y, bajo saturación, ese ciclo se estanca
en 1008 μs — el delay máximo de voz llega a 2109 μs, superando el límite de
2 ms. Es exactamente el contraste que pidió la profesora: reserva
garantizada (SR-DBA/GIANT) vs. polling demand-based puro (IPACT).

## 8. Gráficos — cuáles mostrar en la presentación

Generados por `analysis/analyze.py` en `figures/` (6 PNG):

1. **`sla_compliance_by_tcont.png`** — slide principal: barras de % SLA por
   T-CONT, los 3 algoritmos, a carga 800 Mbps/ONU.
2. **`max_delay_tcont1_vs_load.png`** — segundo slide imprescindible:
   delay máximo de T-CONT1 vs carga, con la línea de SLA (2 ms) cruzada por
   IPACT. Es la evidencia más clara del hallazgo.
3. `cycle_time_distribution.png` — opcional, para explicar el *por qué*
   (el ciclo de IPACT se satura en 1008 μs).
4. `throughput_vs_load.png` — opcional, hallazgo secundario de
   eficiencia (QoSDBA se estanca en ~73% de capacidad).
5. `sla_compliance_vs_load.png` — redundante con 1+2, omitir si falta tiempo.
6. `summary_dashboard.png` — dashboard 2×2 con todo junto, útil como
   slide de respaldo/apéndice si preguntan detalle.

## 9. Cómo correr todo (resumen rápido)

```bash
# Una corrida individual de Fase 3
python3 main.py --algorithm giant --load 800 --verbose

# Los 9 escenarios completos (3 algoritmos x 3 cargas x 10 repeticiones)
python3 run_experiments.py

# Regenerar los 6 gráficos
python3 analysis/analyze.py
```

## 10. Dónde seguir leyendo

| Si quieres... | Lee... |
|---|---|
| Explicación accesible paso a paso (sin jerga) | `docs/COMO_FUNCIONA_FASE3.md` |
| Resumen ejecutivo + tabla de resultados | `docs/PARA_LA_PROFE_FASE3.md` |
| Referencia técnica completa (estándares, pseudocódigo, resultados) | `docs/DOCUMENTACION_TECNICA_FASE3.md` |
| El plan de diseño original y sus derivaciones | `docs/PLAN_FASE3.md` |
| Cómo se construyó (checkpoint histórico) | `docs/ESTADO_FASE3.md` |
| Convenciones de código para trabajo nuevo | `CLAUDE.md` (sección "Convenciones de código") |
| Fase 1 (OMNeT++, rechazada) y Fase 2 (GPON G.984, 32 ONUs) | `legacy/fase1/`, `legacy/fase2/` (ver `legacy/fase2/docs/`) |

---

*OmneTeam — David Retuerto · José Vega · Matías Perelli — TEL-341 UTFSM 2026*
