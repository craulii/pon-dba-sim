# Informe de Estado — Simulador GPON DBA
**TEL-341 Simulación de Redes — OmneTeam**
**Fecha:** 13 de mayo de 2026

---

## Estado general: COMPLETO ✓

Todo el proyecto está terminado y funcionando. A continuación el detalle por componente.

---

## 1. Código fuente

| Módulo | Archivo | Líneas | Estado |
|--------|---------|--------|--------|
| Motor DES | `simulator/engine.py` | 75 | ✓ Funcional |
| OLT | `simulator/olt.py` | 99 | ✓ Funcional |
| ONU | `simulator/onu.py` | 160 | ✓ Funcional |
| T-CONT (buffer) | `simulator/tcont.py` | 102 | ✓ Funcional |
| Generadores tráfico | `simulator/traffic.py` | 65 | ✓ CBR, Poisson, Pareto |
| DBA básico | `simulator/dba_basic.py` | 61 | ✓ Proporcional |
| DBA QoS | `simulator/dba_qos.py` | 85 | ✓ 3 pasos prioritarios |
| Métricas | `metrics/collector.py` | 122 | ✓ Funcional |
| CLI | `main.py` | 212 | ✓ Funcional |
| Experimentos | `run_experiments.py` | 132 | ✓ Funcional |
| Análisis y gráficos | `analysis/analyze.py` | 419 | ✓ 7 gráficos |
| **Total** | | **~1,540 líneas** | |

---

## 2. Experimentos ejecutados

- **Escenarios:** 10 (5 cargas × 2 algoritmos)
- **Repeticiones:** 10 por escenario con seeds distintos (42–51)
- **Total corridas:** 100
- **Resultados:** `results/all_results.csv` — 30 filas (10 escenarios × 3 T-CONTs)
- **Cargas T-CONT 4 probadas:** 10, 25, 50, 75, 100 Mbps/ONU

---

## 3. Resultados clave

### Comparación a carga máxima (100 Mbps/ONU)

| Métrica | BasicDBA | QosDBA | Diferencia |
|---------|----------|--------|------------|
| **T-CONT 1 latencia media** | 25,437 μs | **164 μs** | **155x mejor** |
| **T-CONT 1 P99** | 26,076 μs | **226 μs** | **115x mejor** |
| **T-CONT 1 pérdida** | 0% | 0% | Igual |
| T-CONT 2 latencia media | 4,411 μs | **401 μs** | **11x mejor** |
| T-CONT 2 P99 | 12,790 μs | **546 μs** | **23x mejor** |
| T-CONT 4 latencia media | 177,875 μs | 177,875 μs | Igual (ambos saturan) |
| T-CONT 4 pérdida | 17.8% | 17.8% | Igual |
| Utilización canal | ~100% | ~100% | Igual (sin desperdicio) |

### Conclusión técnica
QosDBA garantiza latencia constante para T-CONT 1 (VoIP) en **164 ± 0 μs** independiente de la carga. BasicDBA colapsa VoIP a 25ms bajo sobrecarga — inaceptable para telefonía (budget ITU-T G.114: ≤ 150ms extremo a extremo).

---

## 4. Gráficos generados

Todos en `figures/`:

| Archivo | Contenido | Estado |
|---------|-----------|--------|
| `latency_avg_by_tcont.png` | 2 paneles: latencia T-CONT 1&2 / T-CONT 4 | ✓ |
| `latency_p99_tcont1_vs_load.png` | P99 VoIP vs carga, línea budget 5ms | ✓ |
| `loss_rate_by_tcont.png` | Pérdida por T-CONT, escala log | ✓ |
| `throughput_vs_load.png` | Throughput por T-CONT + agregado vs carga | ✓ |
| `cdf_latency_tcont4.png` | CDF T-CONT 1 VoIP — diferencia 155x visible | ✓ |
| `channel_utilization.png` | Utilización canal upstream vs carga | ✓ |
| `summary_dashboard.png` | Dashboard 2×2 para presentación | ✓ |

---

## 5. Documentación

- `DOCUMENTACION_TECNICA.md` — **1,034 líneas** con:
  - Base teórica GPON ITU-T G.984.1/2/3
  - Arquitectura completa del simulador
  - Justificación de cada distribución estadística (CBR, Poisson, Pareto)
  - Fórmulas matemáticas de cada métrica
  - Ambos algoritmos DBA explicados paso a paso
  - Simplificaciones y limitaciones reconocidas
  - 12+ referencias bibliográficas

---

## 6. Cómo ejecutar

```bash
cd ~/USM/Simula/pon-dba-sim/gpon-sim

# Una corrida individual
python3 main.py --algorithm qos --load 100 --seed 42 --verbose

# Todos los experimentos (ya ejecutado, ~15 min)
python3 run_experiments.py

# Regenerar los 7 gráficos
python3 analysis/analyze.py
```

---

## 7. Pendiente

Nada crítico. Opcional antes de la presentación:
- Imprimir el `summary_dashboard.png` para tener en físico
- Preparar guión explicando los resultados de la tabla 3
