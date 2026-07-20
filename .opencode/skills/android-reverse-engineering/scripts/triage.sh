#!/usr/bin/env bash
# scripts/triage.sh — One-shot triage de APK Android
set -e

APK="${1}"
PKG="${2:-$1}"   # Si el segundo arg es un package name, extrae desde device

if [[ ! -f "$APK" && "$1" =~ ^[a-z] ]]; then
    # Es un nombre de paquete → extraer APK del dispositivo
    echo "[TRIAGE] Encontrando APK en dispositivo para: $1"
    paths=$(adb shell pm path "$1" 2>/dev/null | cut -d: -f2)
    if [[ -z "$paths" ]]; then echo "ERROR: package no encontrado"; exit 1; fi
    mkdir -p "./splits-$1"
    echo "$paths" | while read p; do adb pull "$p" "./splits-$1/" 2>/dev/null; done
    APK=$(find "./splits-$1" -name "*.apk" | sort | head -1)
    echo "[TRIAGE] APK base: $APK"
fi

if [[ ! -f "$APK" ]]; then echo "Uso: $0 <app.apk|com.package.name>"; exit 1; fi

echo "========================================"
echo "=== TRIAGE: $(basename "$APK") ==="
echo "========================================"

# 1. Manifest básico
echo ""
echo "--- 1. MANIFEST ---"
aapt dump badging "$APK" 2>/dev/null | head -15

# 2. Permissions críticas
echo ""
echo "--- 2. PERMISSIONS CRÍTICAS ---"
aapt dump permissions "$APK" 2>/dev/null | grep -iE "SMS|CAMERA|RECORD|LOCATION|PRIVILEGED|DEBUG|INSTALL|ACCESSIBILITY|OVERLAY|BACKGROUND|MANAGE"

# 3. Componentes exportados
echo ""
echo "--- 3. EXPORTED COMPONENTS ---"
aapt dump xmltree "$APK" AndroidManifest.xml 2>/dev/null | grep -E 'exported.*"true"' -A2 -B2 | head -30

# 4. Network framework
echo ""
echo "--- 4. NETWORK FRAMEWORK ---"
echo -n "OkHttp: "; unzip -l "$APK" 2>/dev/null | grep -ci okhttp || echo "no"
echo -n "Ktor:   "; unzip -l "$APK" 2>/dev/null | grep -ci ktor || echo "no"
echo -n "Cronet: "; unzip -l "$APK" 2>/dev/null | grep -ci cronet || echo "no"
echo -n "gRPC:   "; unzip -p "$APK" classes*.dex 2>/dev/null | strings | grep -ci "grpc" || echo "no"
echo -n "Flutter: "; unzip -l "$APK" 2>/dev/null | grep -ci "libflutter.so" || echo "no"
echo -n "ReactNative: "; unzip -l "$APK" 2>/dev/null | grep -ciE "libhermes.so|libreactnative" || echo "no"
echo -n "RN (bundle): "; unzip -l "$APK" 2>/dev/null | grep -ci "index.android.bundle" || echo "no"
echo -n "Unity IL2CPP: "; unzip -l "$APK" 2>/dev/null | grep -ci "libil2cpp.so" || echo "no"
echo -n "Cordova/Ionic: "; unzip -l "$APK" 2>/dev/null | grep -ciE "www|capebuffer" || echo "no"

# 5. Network Security Config
echo ""
echo "--- 5. NSC (Network Security Config) ---"
if aapt dump xmltree "$APK" res/xml/network_security_config.xml 2>/dev/null; then
    echo "NSC declarado ✅"
else
    echo "NSC NO declarado ❌"
fi

# 6. Deep links
echo ""
echo "--- 6. DEEP LINKS / SCHEMES ---"
aapt dump xmltree "$APK" AndroidManifest.xml 2>/dev/null | grep -iE 'scheme=|host=|action.*VIEW' | head -20

# 7. Native libraries
echo ""
echo "--- 7. NATIVE LIBRARIES ---"
unzip -l "$APK" 2>/dev/null | grep "lib/arm64-v8a/" | awk '{print $NF}' | head -15

# 8. Secrets hardcoded (búsqueda rápida)
echo ""
echo "--- 8. HARDCODED SECRETS (strings DEX) ---"
unzip -p "$APK" classes.dex 2>/dev/null | strings -n 20 | grep -iE "api_key|apikey|secret|password|token|access_key|client_id|client_secret|bearer" | head -15

# 9. Multi-dex
echo ""
echo "--- 9. DEX FILES ---"
unzip -l "$APK" 2>/dev/null | grep "classes.*\.dex"

echo ""
echo "========================================"
echo "[TRIAGE] Completo → próximo paso: jadx -d out/ $APK"
