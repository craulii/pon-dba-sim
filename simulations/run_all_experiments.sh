#!/bin/bash
# Ejecuta todos los escenarios con 10 repeticiones y 5 niveles de carga (25-200 Mbps).
# Total: 4 configs × 5 cargas × 10 reps = 200 corridas.
# Uso: bash run_all_experiments.sh

set -e
cd "$(dirname "$0")"
mkdir -p results

echo "=== Inicio: $(date) ==="
echo "Corridas totales: 200 (4 configs × 5 cargas × 10 reps)"
echo ""

for config in IPACT_16ONU QoSDBA_16ONU IPACT_32ONU QoSDBA_32ONU; do
    echo "--- Corriendo $config (reps 0-9) ---"
    ../pon-dba-sim -u Cmdenv -c "$config" -r 0..49 \
        --result-dir=results 2>&1 | tail -3
    echo "$config completado: $(date)"
    echo ""
done

echo "=== Todas las corridas completadas ==="
echo "Fin: $(date)"
