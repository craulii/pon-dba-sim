# Legacy — Fases 1 y 2 (archivadas)

Generaciones anteriores del proyecto, archivadas para no generar confusión
con el código activo de Fase 3 en la raíz del repo. Ver
[`docs/GUIA_INICIO.md`](../docs/GUIA_INICIO.md) en la raíz para el contexto completo.

## `fase1/`

Propuesta original: simular GPON en **OMNeT++**. Rechazada por la profesora
(mezclaba IPACT de EPON y categorías 5G que no son de GPON). Solo quedan el
PDF y el PPTX de esa entrega — sin código, se descartó por completo.

## `fase2/`

El simulador GPON ITU-T G.984 completo (32 ONUs, BasicDBA vs QoSDBA).
**Ya entregado, no se modifica.** Sigue siendo ejecutable tal cual:

```bash
python3 legacy/fase2/main.py --algorithm qos --load 100 --num-onus 32 --seed 6767 --verbose
python3 legacy/fase2/run_experiments.py
python3 legacy/fase2/analysis/analyze.py
python3 legacy/fase2/run.py          # menú interactivo
```

Documentación completa en `fase2/docs/`. Resultados en `fase2/results/`,
gráficos en `fase2/figures/`, entrega académica en `fase2/Parte_2/`.

Nota: los módulos del motor que Fase 3 reutiliza sin cambios
(`simulator/engine.py`, `onu.py`, `tcont.py`, `traffic.py`, `olt.py`,
`dba_qos.py`, `metrics/collector.py`) **no están aquí** — siguen en la raíz
del repo porque están compartidos entre ambas fases. Solo `dba_basic.py`
(exclusivo de Fase 2) vive dentro de `fase2/`.
