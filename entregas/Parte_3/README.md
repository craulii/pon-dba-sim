# Parte 3 — Fase 3: XG-PON, IPACT vs GIANT vs QoSDBA (SLA-driven)
## OmneTeam · TEL-341 · UTFSM 2026

Pivote pedido por la profesora tras la reunión del 9/6/2026: XG-PON1 (ITU-T
G.987), 8 ONUs idénticas, comparación de 3 algoritmos DBA (IPACT, GIANT,
QoSDBA) bajo una tabla de SLA por T-CONT (T-CONT1 ≤ 2 ms como meta
principal). Es **aditivo** a la Fase 2 (`entregas/Parte_2/`), que no se
modifica.

## Documentación

- [`docs/PARA_LA_PROFE_FASE3.md`](../../docs/PARA_LA_PROFE_FASE3.md) —
  resumen ejecutivo: qué cambió y por qué, parámetros XG-PON, T-CONTs
  reescalados, tabla SLA, los 3 algoritmos, y la tabla de resultados clave.
- [`docs/DOCUMENTACION_TECNICA_FASE3.md`](../../docs/DOCUMENTACION_TECNICA_FASE3.md) —
  referencia técnica completa: estándar G.987, arquitectura, motor DES,
  pseudocódigo de IPACT/GIANT/QoSDBA, métricas SLA, configuración,
  simplificaciones y referencias bibliográficas.
- [`docs/COMO_FUNCIONA_FASE3.md`](../../docs/COMO_FUNCIONA_FASE3.md) —
  explicación accesible, sin jerga, paso a paso (motor de eventos, modelo de
  canal/uplink, generadores de tráfico, los 3 algoritmos).
- [`docs/PLAN_FASE3.md`](../../docs/PLAN_FASE3.md) — diseño original y
  derivaciones acordadas con el equipo.

## Figuras (`figures/xgpon/`)

| Archivo | Contenido |
|---|---|
| `sla_compliance_by_tcont.png` | Cumplimiento de SLA por T-CONT @ 800 Mbps/ONU (headline) |
| `max_delay_tcont1_vs_load.png` | Delay máximo de T-CONT1 vs carga, con línea SLA de 2 ms |
| `cycle_time_distribution.png` | Distribución del ciclo de polling IPACT vs trama fija 125 μs |
| `throughput_vs_load_xgpon.png` | Throughput agregado vs carga, con referencia de capacidad |
| `sla_compliance_vs_load.png` | Cumplimiento SLA de T-CONT1 vs carga |
| `summary_dashboard_xgpon.png` | Dashboard 2×2 con los 4 gráficos clave |

## Resultados (`results/`)

- `xgpon_results.csv` — 9 escenarios (3 algoritmos × 3 cargas T-CONT4) × 3
  T-CONT, con media + IC95% sobre 10 repeticiones: latencia
  media/P95/P99/máx, jitter, throughput, loss rate, `sla_compliance_pct`.
- `xgpon_cycle_times.csv` — muestras de duración de ciclo (solo escenarios
  IPACT), usadas en `cycle_time_distribution.png`.

---

*OmneTeam — David Retuerto · José Vega · Matías Perelli — TEL-341 UTFSM 2026*
