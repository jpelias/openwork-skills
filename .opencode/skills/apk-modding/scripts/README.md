# Scripts de automatización — apk-modding

Scripts Python para automatizar tareas comunes de modding de APKs. Todos trabajan sobre salidas de `baksmali` (directorios `dexN_out/`) y generan backups automáticos.

## Requisitos

- Python 3.8+
- `baksmali` / `smali` (para desensamblar/reensamblar DEX)
- `ripgrep` (`rg`) recomendado para búsquedas rápidas

## Scripts

### patch_shared_prefs_defaults.py

Cambia valores por defecto `false` → `true` en llamadas a `SharedPreferences.getBoolean()` para claves específicas (premium, noads, pro, etc.).

```bash
# Modo dry-run (solo informa)
python3 patch_shared_prefs_defaults.py --roots dex_out dex2_out --keys premium noads pro

# Aplicar cambios
python3 patch_shared_prefs_defaults.py --roots dex_out dex2_out --keys premium noads pro --write
```

**Estrategia:** A (cambiar defaults). Ver SKILL.md para limitaciones (re-sync de Billing).

### neutralize_yhf_dialogs.py

Neutraliza métodos estáticos `public static *(Context)` inyectados por modders (yhf/liteapks y variantes) sin borrar clases.

```bash
# Modo dry-run
python3 neutralize_yhf_dialogs.py --roots dex_out dex2_out

# Aplicar cambios
python3 neutralize_yhf_dialogs.py --roots dex_out dex2_out --write
```

**Estrategia:** Reemplaza el cuerpo del método con `return-void` (void) o `return null` (object). Crea backup `.orig`.

### ziprepack.py

Reempaqueta un APK con reglas de compresión correctas y reemplazos opcionales de DEX.

```bash
# Reempaquetar con DEX reemplazados
python3 ziprepack.py --in app.apk --out hacked.apk \
  --replace classes2.dex=classes2_new.dex classes8.dex=classes8_new.dex
```

**Reglas:**
- STORE (sin compresión): `*.dex`, `resources.arsc`, `lib/**/*.so`
- DEFLATE: resto de archivos
- Elimina solo firmas en `META-INF/` (`.SF`, `.RSA`, `.DSA`, `.EC`, `MANIFEST.MF`)
- Preserva `META-INF/services/`

### strip_sign_and_sign.py

Limpia firmas antiguas, alinea con `zipalign` y firma con keystore de depuración.

```bash
# Firmar APK
python3 strip_sign_and_sign.py --in hacked.apk --out hacked_signed.apk

# Con keystore personalizado
python3 strip_sign_and_sign.py --in hacked.apk --out hacked_signed.apk \
  --ks /path/to/keystore.jks --ks-pass changeit --alias mykey
```

Genera keystore de depuración en `~/.android/debug.keystore` si no existe.

### batch-apktool.sh

Equivalente Linux de Batch ApkTool (BurSoft) para 4PDA. Replica toda la funcionalidad en un solo script bash.

```bash
# Decompilar (apktool + baksmali por DEX)
./batch-apktool.sh decompile app.apk

# Recompilar + alinear + firmar (todo en uno)
./batch-apktool.sh rebuild app_out/

# Instalar via ADB
./batch-apktool.sh install app_out_signed.apk

# Metadata + detección de modders
./batch-apktool.sh info app.apk

# Decompilar + abrir editor
./batch-apktool.sh all app.apk
```

**Comandos disponibles:** decompile, compile, align, sign, install, rebuild, all, info

## Flujo completo

```bash
# 1. Descompilar todos los DEX
API=35
for num in "" $(seq 2 20); do
    fname="classes${num}.dex"
    unzip -l app.apk | grep -q "$fname" || continue
    unzip -p app.apk "$fname" > "$fname"
    baksmali d "$fname" -o "dex${num}_out/" --api "$API"
done

# 2. Parchear defaults de SharedPreferences
python3 scripts/patch_shared_prefs_defaults.py \
  --roots dex_out dex2_out --keys premium noads pro --write

# 3. Neutralizar diálogos de modder
python3 scripts/neutralize_yhf_dialogs.py \
  --roots dex_out dex2_out --write

# 4. Reensamblar DEX modificados
for d in dex_out dex2_out; do
    num=$(echo "$d" | sed 's/dex//;s/_out//')
    [ -z "$num" ] && num="" || num="$num"
    smali assemble "$d" --api "$API" -o "classes${num}_new.dex"
done

# 5. Reempaquetar
python3 scripts/ziprepack.py --in app.apk --out hacked.apk \
  --replace classes.dex=classes_new.dex classes2.dex=classes2_new.dex

# 6. Alinear y firmar
python3 scripts/strip_sign_and_sign.py --in hacked.apk --out hacked_signed.apk

# 7. Instalar
adb shell settings put global package_verifier_enable 0
adb install hacked_signed.apk
adb shell settings put global package_verifier_enable 1
```

## Notas

- Todos los scripts excluyen directorios de framework (`android/`, `androidx/`, `com/google/`, `dalvik/`, `java/`, `kotlin/`, `kotlinx/`, `io/flutter/`).
- Los backups se crean con extensión `.orig` o `.bak`.
- El modo dry-run (sin `--write`) es seguro y no modifica archivos.
