#!/usr/bin/env bash
# scripts/extract_splits.sh — Extrae base + splits de un paquete instalado
set -e

PKG="${1}"

if [[ -z "$PKG" ]]; then
    echo "Uso: $0 <com.package.name>"
    exit 1
fi

OUTDIR="./splits-$PKG"
mkdir -p "$OUTDIR"

echo "[SPLIT] Buscando splits para $PKG..."
paths=$(adb shell pm path "$PKG" 2>/dev/null | cut -d: -f2)

if [[ -z "$paths" ]]; then
    echo "ERROR: Package '$PKG' no encontrado en el dispositivo"
    exit 1
fi

echo "$paths" | while read p; do
    filename=$(basename "$p")
    echo "[SPLIT] Pulling $filename..."
    adb pull "$p" "$OUTDIR/$filename" 2>/dev/null || echo "[WARN] Falló pull de $p"
done

echo ""
echo "[SPLIT] Extraídos en: $OUTDIR/"
ls -la "$OUTDIR/"
