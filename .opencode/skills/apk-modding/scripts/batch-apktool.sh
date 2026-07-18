#!/usr/bin/env bash
# batch-apktool.sh — Equivalente Linux de Batch ApkTool (BurSoft) para 4PDA
#
# Replica la funcionalidad de Batch ApkTool en Linux:
#   - Decompilar APK (apktool d)
#   - Recompilar APK (apktool b)
#   - Firmar APK (apksigner v1+v2+v3)
#   - Alinear APK (zipalign -p)
#   - Instalar en dispositivo (adb install)
#
# Uso:
#   ./batch-apktool.sh decompile app.apk [output_dir]
#   ./batch-apktool.sh compile input_dir [output.apk]
#   ./batch-apktool.sh sign app.apk [signed.apk]
#   ./batch-apktool.sh align app.apk [aligned.apk]
#   ./batch-apktool.sh install app.apk
#   ./batch-apktool.sh all app.apk        # decompile + abrir editor
#   ./batch-apktool.sh rebuild input_dir  # compile + align + sign
#
# Requisitos: apktool, baksmali, smali, apksigner, zipalign, aapt, adb (opcional)
# Todos disponibles en este workspace.

set -euo pipefail

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Rutas de herramientas (del workspace)
APKTOOL="${APKTOOL:-/usr/bin/apktool}"
BAKSMALI="${BAKSMALI:-/usr/bin/baksmali}"
SMALI="${SMALI:-/usr/bin/smali}"
APKSIGNER="${APKSIGNER:-/usr/bin/apksigner}"
ZIPALIGN="${ZIPALIGN:-/usr/bin/zipalign}"
AAPT="${AAPT:-/usr/bin/aapt}"
ADB="${ADB:-/home/usuario/Android/Sdk/platform-tools/adb}"

# Keystore de depuración
KS="${KS:-$HOME/.android/debug.keystore}"
KS_PASS="${KS_PASS:-android}"
KS_ALIAS="${KS_ALIAS:-androiddebugkey}"

# API level por defecto
API="${API:-35}"

log() { echo -e "${GREEN}[+]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
err() { echo -e "${RED}[✗]${NC} $1" >&2; }
info() { echo -e "${BLUE}[*]${NC} $1"; }

check_tool() {
    if ! command -v "$1" &>/dev/null && [ ! -x "${!2}" ]; then
        err "Herramienta no encontrada: $1 (ruta: ${!2})"
        return 1
    fi
}

ensure_keystore() {
    if [ ! -f "$KS" ]; then
        log "Creando keystore de depuración en $KS"
        mkdir -p "$(dirname "$KS")"
        keytool -genkey -v \
            -keystore "$KS" \
            -storepass "$KS_PASS" \
            -alias "$KS_ALIAS" \
            -keypass "$KS_PASS" \
            -keyalg RSA -keysize 2048 -validity 10000 \
            -dname "CN=Android Debug,O=Android,C=US" 2>/dev/null
    fi
}

# === Comandos ===

cmd_decompile() {
    local apk="$1"
    local out="${2:-${apk%.apk}_out}"

    [ ! -f "$apk" ] && { err "APK no encontrado: $apk"; exit 1; }

    log "Decompilando $apk → $out"
    "$APKTOOL" d -f -o "$out" "$apk"

    # Listar DEX files
    info "Archivos DEX:"
    unzip -l "$apk" | grep -E "classes.*\.dex" | awk '{print "    " $4}'

    # Desensamblar cada DEX con baksmali (además de apktool)
    info "Desensamblando DEX individuales con baksmali..."
    local num
    for num in "" $(seq 2 20); do
        local fname="classes${num}.dex"
        if unzip -l "$apk" | grep -q "$fname"; then
            local dexout="$out/dex${num}_out"
            log "  baksmali $fname → $dexout"
            unzip -p "$apk" "$fname" > "/tmp/$fname"
            "$BAKSMALI" d "/tmp/$fname" -o "$dexout" --api "$API" 2>/dev/null || warn "baksmali falló para $fname"
            rm -f "/tmp/$fname"
        fi
    done

    # Metadata
    info "Metadata del APK:"
    "$AAPT" dump badging "$apk" 2>/dev/null | head -10

    log "Decompilación completa: $out"
    echo ""
    echo "  Edita los archivos smali en $out/dex*_out/"
    echo "  Luego recompila con: $0 rebuild $out"
}

cmd_compile() {
    local indir="$1"
    local out="${2:-${indir%.apk_out}_new.apk}"

    [ ! -d "$indir" ] && { err "Directorio no encontrado: $indir"; exit 1; }

    log "Recompilando $indir → $out"
    "$APKTOOL" b -f -o "$out" "$indir"

    log "APK recompilado: $out"
    warn "Recuerda alinear y firmar antes de instalar:"
    echo "  $0 align $out"
    echo "  $0 sign ${out%.apk}_aligned.apk"
}

cmd_align() {
    local apk="$1"
    local out="${2:-${apk%.apk}_aligned.apk}"

    [ ! -f "$apk" ] && { err "APK no encontrado: $apk"; exit 1; }

    log "Alineando $apk → $out"
    "$ZIPALIGN" -p -f 4 "$apk" "$out"
    log "APK alineado: $out"
}

cmd_sign() {
    local apk="$1"
    local out="${2:-${apk%.apk}_signed.apk}"

    [ ! -f "$apk" ] && { err "APK no encontrado: $apk"; exit 1; }

    ensure_keystore

    log "Firmando $apk → $out"
    "$APKSIGNER" sign \
        --ks "$KS" \
        --ks-pass "pass:$KS_PASS" \
        --ks-key-alias "$KS_ALIAS" \
        --key-pass "pass:$KS_PASS" \
        --v1-signing-enabled true \
        --v2-signing-enabled true \
        --v3-signing-enabled true \
        --out "$out" "$apk"

    log "Verificando firma:"
    "$APKSIGNER" verify --verbose "$out" 2>&1 | head -10

    log "APK firmado: $out"
}

cmd_install() {
    local apk="$1"

    [ ! -f "$apk" ] && { err "APK no encontrado: $apk"; exit 1; }

    if ! command -v "$ADB" &>/dev/null; then
        err "ADB no encontrado: $ADB"
        exit 1
    fi

    log "Desactivando Play Protect temporalmente..."
    "$ADB" shell settings put global package_verifier_enable 0 2>/dev/null || warn "No se pudo desactivar verificador"

    log "Instalando $apk..."
    "$ADB" install -r "$apk"

    log "Reactivando Play Protect..."
    "$ADB" shell settings put global package_verifier_enable 1 2>/dev/null || true

    log "Instalación completa"
}

cmd_rebuild() {
    local indir="$1"
    local tmpapk="/tmp/rebuild_$$.apk"
    local aligned="/tmp/rebuild_aligned_$$.apk"
    local out="${2:-${indir%.apk_out}_signed.apk}"

    cmd_compile "$indir" "$tmpapk"
    cmd_align "$tmpapk" "$aligned"
    cmd_sign "$aligned" "$out"

    rm -f "$tmpapk" "$aligned"
    log "Build completo: $out"
    echo "  Instala con: $0 install $out"
}

cmd_all() {
    local apk="$1"
    local out="${apk%.apk}_out"

    cmd_decompile "$apk" "$out"

    echo ""
    log "Abriendo directorio para edición..."
    echo "  Directorio: $out"
    echo "  Edita los smali y luego ejecuta:"
    echo "    $0 rebuild $out"

    # Abrir en editor si está disponible
    if [ -n "${EDITOR:-}" ]; then
        info "Abriendo con \$EDITOR ($EDITOR)..."
        $EDITOR "$out"
    elif command -v code &>/dev/null; then
        info "Abriendo con VS Code..."
        code "$out"
    else
        warn "No se encontró editor. Edita manualmente: $out"
    fi
}

cmd_info() {
    local apk="$1"
    [ ! -f "$apk" ] && { err "APK no encontrado: $apk"; exit 1; }

    info "=== Metadata ==="
    "$AAPT" dump badging "$apk" 2>/dev/null | head -20

    info "=== DEX files ==="
    unzip -l "$apk" | grep -E "classes.*\.dex"

    info "=== Native libraries ==="
    unzip -l "$apk" | grep -E "\.so$" | head -20

    info "=== Firma ==="
    "$APKSIGNER" verify --verbose --print-certs "$apk" 2>&1 | head -15

    info "=== Detección de modders ==="
    if unzip -p "$apk" classes*.dex 2>/dev/null | strings -a | grep -qiE "Liteapks|9mod|ī/íì|īi/ïi|bin/ghost"; then
        warn "Modder detectado (yhf/liteapks)"
    fi
    if unzip -l "$apk" | grep -qi "libstub.so\|protected_by_np"; then
        warn "Dex2C/VM shell detectado (zhou45) — vía muerta estática"
    fi
    if unzip -p "$apk" classes*.dex 2>/dev/null | strings -a | grep -qi "pairip"; then
        warn "PairipCore detectado"
    fi
    if unzip -l "$apk" | grep -qi "libapp.so\|libflutter.so"; then
        warn "Flutter detectado — usar blutter/reFlutter"
    fi
}

cmd_help() {
    cat << 'EOF'
Batch ApkTool para Linux — Equivalente a BurSoft Batch ApkTool

Comandos:
  decompile <apk> [out]    Decompilar APK (apktool + baksmali por DEX)
  compile <dir> [out]      Recompilar directorio a APK
  align <apk> [out]         Alinear APK (zipalign -p)
  sign <apk> [out]          Firmar APK (apksigner v1+v2+v3)
  install <apk>              Instalar APK via ADB
  rebuild <dir> [out]       compile + align + sign (todo en uno)
  all <apk>                 decompile + abrir editor
  info <apk>                Metadata, DEX, .so, firma, detección de modders

Variables de entorno:
  APKTOOL, BAKSMALI, SMALI, APKSIGNER, ZIPALIGN, AAPT, ADB
  KS (keystore), KS_PASS, KS_ALIAS, API

Ejemplos:
  ./batch-apktool.sh decompile app.apk
  ./batch-apktool.sh rebuild app_out/
  ./batch-apktool.sh install app_out_signed.apk
  ./batch-apktool.sh info app.apk
EOF
}

# === Main ===

case "${1:-help}" in
    decompile|d) shift; cmd_decompile "$@";;
    compile|c) shift; cmd_compile "$@";;
    align|a) shift; cmd_align "$@";;
    sign|s) shift; cmd_sign "$@";;
    install|i) shift; cmd_install "$@";;
    rebuild|r) shift; cmd_rebuild "$@";;
    all) shift; cmd_all "$@";;
    info) shift; cmd_info "$@";;
    help|--help|-h) cmd_help;;
    *) err "Comando desconocido: $1"; cmd_help; exit 1;;
esac
