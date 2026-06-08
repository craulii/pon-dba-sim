#!/bin/bash
# Exportar resultados .sca y .vec a CSV para análisis Python
set -e

RESULTS_DIR="../simulations/results"
OUT_DIR="."

if [ ! -d "$RESULTS_DIR" ]; then
    echo "ERROR: No se encontró el directorio $RESULTS_DIR"
    exit 1
fi

cd "$RESULTS_DIR"

echo "Exportando scalars (.sca) ..."
for f in *.sca; do
    [ -f "$f" ] || continue
    opp_scavetool export -o "${f%.sca}.csv" -F CSV-S "$f"
    echo "  -> ${f%.sca}.csv"
done

echo "Exportando vectores (.vec) ..."
for f in *.vec; do
    [ -f "$f" ] || continue
    opp_scavetool export -o "${f%.vec}_vec.csv" -F CSV-R "$f"
    echo "  -> ${f%.vec}_vec.csv"
done

echo ""
echo "Exportación completada."
