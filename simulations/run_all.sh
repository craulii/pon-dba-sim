#!/bin/bash
# Ejecutar todos los escenarios en modo batch (Cmdenv)
set -e

BINARY=../pon-dba-sim
INI=omnetpp.ini

if [ ! -f "$BINARY" ]; then
    echo "ERROR: No se encontró el binario $BINARY"
    echo "Compilar primero con: source ~/omnetpp-6.0.3/setenv && opp_makemake -f --deep -O out && make -j\$(nproc)"
    exit 1
fi

mkdir -p results

CONFIGS=(IPACT_16ONU QoSDBA_16ONU IPACT_32ONU QoSDBA_32ONU)

for cfg in "${CONFIGS[@]}"; do
    echo "============================================"
    echo "Ejecutando: $cfg"
    echo "============================================"
    $BINARY -u Cmdenv -c "$cfg" -f "$INI" 2>&1 | tee "results/${cfg}.log"
    echo "Completado: $cfg"
done

echo ""
echo "Todos los escenarios completados. Resultados en simulations/results/"
