---
name: apk-modding
description: >
  Playbook operativo para modificar, parchear y hackear APKs Android desde Linux PC.
  Cubre: decompilación (jadx, apktool, baksmali), parcheo de smali (licencias, premium,
  ads, diálogos de modders), reensamblado, firma (v1/v2/v3), instalación via ADB,
  análisis nativo ARM64 (Ghidra, radare2), instrumentación dinámica (Frida), bypass de
  signature checks, PairipCore, Dex2C, y modding de juegos Unity/IL2CPP.
  Use for authorized testing, research, or modifying your own apps.
---

# APK Modding Playbook

Playbook operativo para modificar APKs Android desde este workspace Linux. Todas las herramientas están instaladas y son nativas de Linux.

## Reglas de oro

0. **Buscar en GitHub primero.** Antes de tocar un byte, buscar `github.com/topics/android-reverse-engineering` y `github.com/search?q=<app>`. Si alguien ya lo parcheo, fork y adapta. No reinventes.

1. **Hackear el original, no el mod.** Si el APK original existe, parchearlo. Los mods añaden protecciones (DEX cifrado, multi-layer signature verification, anti-tamper nativo) órdenes de magnitud más difíciles de bypassar que las licencias simples del original.

2. **Nunca borrar `META-INF/services/`.** Solo borrar firmas: `.SF`, `.RSA`, `.DSA`, `.EC`, `MANIFEST.MF`. Borrar `META-INF/services/` rompe Kotlin `ServiceLoader` → crash `Module with the Main dispatcher is missing`.

3. **Buscar call-sites en TODOS los DEX.** Las inyecciones de modders suelen estar en `classes3.dex` pero las llamadas están en `classes2.dex` (MainActivity). Buscar siempre en todos los DEX.

4. **Solo reensamblar los DEX modificados.** Mantener los demás originales.

5. **Limpiar el dispositivo después del modding.** Proxy, certificados CA, módulos Magisk temporales y Frida Gadget pueden dejar el dispositivo inestable. Usar el skill `android-cleanup` al finalizar.

---

## Herramientas del workspace (todas disponibles)

```
apktool      /usr/bin/apktool          2.7.0    — decompile/recompile APK
baksmali     /usr/bin/baksmali         2.5.2    — DEX → smali
smali        /usr/bin/smali            2.5.2    — smali → DEX
jadx         /usr/local/bin/jadx       1.5.1    — DEX → Java decompiler
apksigner    /usr/bin/apksigner        —        — firma v1/v2/v3/v4
zipalign     /usr/bin/zipalign         —        — alineación de APK
aapt         /usr/bin/aapt             —        — inspección de manifest
aapt2        /usr/bin/aapt2            —        — inspección de recursos
adb          ~/Android/Sdk/platform-tools/adb — conexión a dispositivo
frida        ~/.local/bin/frida        17.15.3  — instrumentación dinámica
frida-ps     ~/.local/bin/frida-ps     —        — listar procesos
objection    ~/.local/bin/objection    1.12.5   — wrapper Frida
r2           /usr/local/bin/r2         6.1.9    — disasm/hex patch nativo
ghidra       /opt/ghidra/              12.x     — análisis nativo ARM64
httptoolkit  /usr/bin/httptoolkit      1.26.1   — interceptación de tráfico
mitmdump     ~/.local/bin/mitmdump     12.2.3   — proxy CLI
python3      /usr/bin/python3          3.13     — scripting
keytool      /usr/bin/keytool          —        — generar keystores
openssl      /usr/bin/openssl          —        — certificados
strings      /usr/bin/strings          —        — extraer strings
readelf      /usr/bin/readelf          —        — símbolos ELF
```

Scripts incluidos en `.opencode/skills/apk-modding/scripts/`:
- `batch-apktool.sh` — flujo completo (decompile, compile, align, sign, install, info)
- `patch_shared_prefs_defaults.py` — cambiar defaults de SharedPreferences
- `neutralize_yhf_dialogs.py` — neutralizar diálogos de modders
- `ziprepack.py` — reempaquetar con compresión correcta
- `strip_sign_and_sign.py` — limpiar firmas, alinear, firmar
- `nightmare.py` — parcheo ARM64 por hex (buscar/reemplazar instrucciones en .so)

---

## Flujo operativo estándar

### Fase 1 — Triaje

```bash
# Metadata del APK
aapt dump badging app.apk | head -20

# Si es un bundle .apks / .xapk, extraer base.apk primero
unzip -l app.apk | grep -q "base.apk" && unzip -o app.apk "base.apk" -d extracted/
[ -f extracted/base.apk ] && BASE=extracted/base.apk || BASE=app.apk

# Extraer splits instalados desde dispositivo (si es necesario)
# adb shell pm path com.target.app | cut -d: -f2 | xargs -I{} adb pull {}

# Contar DEX y .so
unzip -l app.apk | grep -c "classes.*\.dex"
unzip -l app.apk | grep -c "\.so$"

# Detección de modders
unzip -p app.apk classes*.dex | strings -a | grep -iE "Liteapks|9mod|ī/íì|īi/ïi|bin/ghost|p000/p001"

# Detección de Flutter
unzip -l app.apk | grep -i "libapp.so\|libflutter.so"

# Detección de Pairip
unzip -p app.apk classes*.dex | strings -a | grep -c "pairip"
unzip -l app.apk | grep -i "pairipcore"

# Detección de Dex2C/VM shell
unzip -l app.apk | grep -i "libstub.so\|protected_by_np\|libcxapkmod"

# Firma actual
apksigner verify --verbose --print-certs app.apk
```

### Fase 2 — Decompilación

```bash
# Java (para lectura)
jadx -d jadx-out/ --no-res app.apk

# Smali (para parcheo) — TODOS los DEX
API=35
for num in "" $(seq 2 20); do
    fname="classes${num}.dex"
    unzip -l app.apk | grep -q "$fname" || continue
    unzip -p app.apk "$fname" > "$fname"
    baksmali d "$fname" -o "dex${num}_out/" --api "$API"
done

# Recursos (si hay que editar manifest/XML)
apktool d app.apk -o apktool-out/
```

### Fase 3 — Análisis y búsqueda de targets

```bash
# SharedPreferences keys (licencia/premium)
rg -n '"premium"|"noads"|"pro"|"isPremium"|"max_' dex*_out/ --glob "**/*.smali"

# Billing / IAP
rg -n 'BillingClient|queryPurchases|getPurchase|startPurchase' dex*_out/

# Cifrado
rg -n 'Cipher;->getInstance|SecretKeySpec|MessageDigest' dex*_out/

# Reflexión
rg -n 'getDeclaredMethod|getDeclaredField|Class.forName|Method;->invoke' dex*_out/

# Root detection
rg -n '"/su"|magisk|busybox|ro.kernel.qemu|isDebuggerConnected' dex*_out/

# Native load
rg -n 'System.loadLibrary|System.load' dex*_out/

# Call-sites de modders (yhf/liteapks)
rg -n "invoke-.*(ī/íì|īi/ïi|p000/p001|p002i/p003i|q6/c|w6/b|d6/a|a/b/pookie)" dex*_out --glob "**/*.smali" \
  | rg -v "^dex\d*_out/(ī|īi|p000|p002i|q6|w6|d6|a)/"
```

### Fase 4 — Parcheo

#### Estrategia A: Cambiar defaults de SharedPreferences

Patrón común:
```java
this.isPremium = prefs.getBoolean("premium", false);
```

En smali, cambiar `const/4 v2, 0x0` → `0x1`:
```smali
const-string v1, "premium"
const/4 v2, 0x0              # ← cambiar a 0x1
invoke-interface {v0, v1, v2}, ...getBoolean...
```

Automatizado:
```bash
python3 .opencode/skills/apk-modding/scripts/patch_shared_prefs_defaults.py \
  --roots dex_out dex2_out --keys premium noads pro --write
```

**Limitación:** Si la app re-sincroniza desde Play Billing o servidor, el valor se sobreescribe. Usar Estrategia C.

#### Estrategia B: Forzar retorno de método

Reemplazar todo el cuerpo del método:
```smali
.method public isPremium()Z
    .registers 1
    const/4 v0, 0x1
    return v0
.end method
```

Inmune a re-sync de SharedPreferences. Si hay múltiples métodos de comprobación (5+), parchear todos.

#### Estrategia C: Hook de getter por nombre de clave

Interceptar `getBoolean(key, default)` al inicio y retornar `true` si la clave coincide:
```smali
.method public getBoolean(Ljava/lang/String;Z)Z
    .registers 3
    const-string v0, "KEY_IS_PREMIUM"
    invoke-virtual {p1, v0}, Ljava/lang/String;->endsWith(Ljava/lang/String;)Z
    move-result v0
    if-eqz v0, :original
    const/4 v0, 0x1
    return v0
    :original
    # ... cuerpo original
```

Sobrevive re-sync de Play Billing porque intercepta la **lectura**, no el valor almacenado.

#### Estrategia D: Suprimir diálogos de re-login y toasts de auth

```smali
# Suprimir broadcast de re-login
.method ...sendReLoginBroadcast()V
    .registers 0
    return-void
.end method

# Suprimir lanzamiento de ReLoginDialogActivity
.method ...launchReLoginDialog()V
    .registers 0
    return-void
.end method

# Suprimir solo toasts de auth (dejar otros toasts)
if-eqz p1, :show
const-string v0, "uthenticat"
invoke-virtual {p1, v0}, Ljava/lang/String;->contains(Ljava/lang/CharSequence;)Z
move-result v0
if-eqz v0, :show
return-void
:show
# ... código original de toast
```

#### Estrategia E: Parcheo de límites numéricos

```smali
const-string v1, "max_favorites"
const/16 v2, 0x5              # ← cambiar a 0x63 (99) o 0x7FFFFFFF
invoke-interface {v0, v1, v2}, ...getInt...
```

#### Estrategia F: Neutralizar diálogos de modders (yhf/liteapks)

**NO borrar clases de modders** — el launcher Activity tiene referencias DEX directas. Borrar causa `NoClassDefFoundError`.

Automatizado:
```bash
python3 .opencode/skills/apk-modding/scripts/neutralize_yhf_dialogs.py \
  --roots dex_out dex2_out --write
```

Esto neutraliza métodos `public static *(Context)` → `return-void` o `return null`.

**Después, eliminar `invoke-static` calls en Activities a estos métodos.**

### Fase 5 — Reensamblado

```bash
# Solo reensamblar DEX modificados
API=35
for d in dex_out dex2_out; do
    num=$(echo "$d" | sed 's/dex//;s/_out//')
    [ -z "$num" ] && num="" || num="$num"
    smali assemble "$d" --api "$API" -o "classes${num}_new.dex"
done
```

### Fase 6 — Reempaquetado

```bash
# Con script (recomendado)
python3 .opencode/skills/apk-modding/scripts/ziprepack.py \
  --in app.apk --out hacked.apk \
  --replace classes.dex=classes_new.dex classes2.dex=classes2_new.dex

# O con batch-apktool.sh
.opencode/skills/apk-modding/scripts/batch-apktool.sh rebuild apktool-out/
```

**Reglas de compresión (Android 14–16):**
- `.so` → STORE (sin compresión) + página-alineados con `zipalign -p`
- `resources.arsc` → STORE
- `classes*.dex` → STORE (con Python zipfile; con zip/apktool puede DEFLATE)
- Resto → DEFLATE
- Mantener `META-INF/services/`; eliminar solo `.SF/.RSA/.DSA/.EC` y `MANIFEST.MF`

### Fase 7 — Firma e instalación

```bash
# Alinear
zipalign -p -f 4 hacked.apk hacked_aligned.apk

# Firmar (v1+v2+v3)
apksigner sign \
  --ks "$HOME/.android/debug.keystore" --ks-pass pass:android \
  --ks-key-alias androiddebugkey \
  --v1-signing-enabled true --v2-signing-enabled true --v3-signing-enabled true \
  --out hacked_signed.apk hacked_aligned.apk

# Verificar
apksigner verify --verbose --print-certs hacked_signed.apk

# Instalar
adb shell settings put global package_verifier_enable 0
adb install hacked_signed.apk
adb shell settings put global package_verifier_enable 1
```

Automatizado:
```bash
.opencode/skills/apk-modding/scripts/strip_sign_and_sign.py \
  --in hacked.apk --out hacked_signed.apk
adb install hacked_signed.apk
```

---

## Flujo completo en un comando

```bash
.opencode/skills/apk-modding/scripts/batch-apktool.sh all app.apk
# decompile + abrir editor
# editar smali...
.opencode/skills/apk-modding/scripts/batch-apktool.sh rebuild app_out/
.opencode/skills/apk-modding/scripts/batch-apktool.sh install app_out_signed.apk
```

---

## Detección de modders (2025–2026)

### Perfiles

| Modder | Firma | ¿Parcheable estático? |
|---|---|---|
| **yhf / liteapks** | `ī/íì/`, `īi/ïi/` | ⚠️ Parcial (Java sí, nativo no) |
| **yhf (2025+)** | `p000/p001/`, `p002i/p003i/` | ⚠️ Parcial (renombrado) |
| **黯笙** | `bin.mt.signature.KillerApplication` | ✅ Sí (Java puro) |
| **Kunkka** | `LSPAppComponentFactoryStub` + `assets/lspatch/config.json` | ✅ Sí (via LSPosed) |
| **zhou45** | `libstub.so` + `assets/protected_by_np` | ❌ No (Dex2C VM shell) |
| **辰夕** | `libcxapkmod.so` + `assets/cxapkDex/*.Epic` | ❌ No (VM nativa) |
| **幻幻喵** | `libmiaomiaohuan.so` + prefijo `miaomiaohuan0` | ❌ No |

### Árbol de decisión

```
¿Tiene libstub.so + assets/classes0.jar?
  → SÍ: Dead end estático. Hackear el APK original.
  → NO: ¿Tiene ī/íì + métodos nativos (up.process, bi.b)?
         → SÍ: Intentar neutralizar <clinit> que llaman EntryPoint.stub
         → Si se cuelga: Dead end parcial.
         → Si funciona: ✅
  → NO: ¿Tiene solo ī/íì con métodos Java (iaw.w, iab.b)?
         → SÍ: Neutralizar normalmente ✅
  → NO: ¿No tiene ī/íì ni libstub?
         → SÍ: Es el original o un mod limpio. Aplicar Estrategias A-F ✅
```

---

## Bypass de signature checks

### Java-level (parche smali)

Buscar `getPackageInfo(GET_SIGNATURES)` y neutralizar la comparación.

### Native-level (parche .so con Ghidra/radare2)

```bash
# Extraer .so
unzip -p app.apk lib/arm64-v8a/libnative.so > libnative.so

# Buscar strings de verificación
strings libnative.so | grep -iE "sign|cert|integrity|verify|package"

# Abrir en radare2
r2 -A libnative.so
# > afl~JNI
# > s sym.JNI_OnLoad
# > pdf

# Ghidra: trace abort() → XREFs → encontrar condición → patch
```

### Runtime (Frida, sin parchear APK)

```javascript
// Spoof signature hash at runtime without modifying the APK
Java.perform(function() {
    var ActivityThread = Java.use("android.app.ActivityThread");
    var PackageManager = Java.use("android.content.pm.PackageManager");
    var Signature = Java.use("android.content.pm.Signature");

    // Replace the system PackageManager with a dynamic proxy
    var currentApplication = ActivityThread.currentApplication();
    var packageManager = currentApplication.getPackageManager();

    var proxy = Java.registerClass({
        name: "com.example.SignatureSpoof",
        implements: [PackageManager],
        methods: {
            getPackageInfo: function(packageName, flags) {
                var pi = packageManager.getPackageInfo(packageName, flags);
                if ((flags & PackageManager.GET_SIGNATURES.value) !== 0 && pi.signatures.value) {
                    var spoof = Signature.$new("3082..."); // base64 DER of original cert
                    pi.signatures.value = Java.array("android.content.pm.Signature", [spoof]);
                }
                return pi;
            }
        }
    });

    // Note: full implementation requires proxying all PackageManager methods.
    // Use only for research on apps you own.
});
```

For a complete runtime signature spoof, use existing modules like **LSPosed CorePatch** or **Xposed Signature Spoofing** modules, which handle all PackageManager methods correctly.

---

## PairipCore bypass

### Detección
```bash
unzip -p app.apk classes*.dex | strings -a | grep -c "pairip"
unzip -l app.apk | grep -i "pairipcore"
```

### Bypass mínimo (solo smali)

Si la app solo tiene Pairip para verificación de licencia (sin dependencias del vault):
1. Neutralizar `SignatureCheck.verifyIntegrity(Context)V` → `return-void`
2. Neutralizar `StartupLauncher.launch()V` → `return-void`

**NO neutralizar `VMRunner.invoke` ni `VMRunner.setContext`** — toda la app depende de ellos para desencriptar strings.

### Bypass completo (vault strings comprometidos)

Si el APK ya está moddeado y los vault strings están vacíos:
1. Reemplazar clase `Application` en AndroidManifest (remover wrapper Pairip)
2. Patch `VMRunner.invoke` → return null
3. Patch protobuf field lookup para nombres vacíos
4. Crear `SafeExceptionHandler` para capturar NPE en background threads
5. Envolver crypto init en try-catch
6. Stub `FlutterSecureStorage` → `success(null)`

---

## Frida Gadget embedding (APK redistribuible sin root)

Para apps con `libstub.so` (Dex2C) donde el smali no es parcheable:

1. Descargar `frida-gadget` para arm64
2. Colocar en `lib/arm64-v8a/libfrida-gadget.so`
3. Config en `assets/frida-gadget.config` (modo listen)
4. Inyectar `System.loadLibrary("frida-gadget")` en `<clinit>()` de la Application
5. Conectar: `frida -H 127.0.0.1:27042 -p <pid> -l hook.js`

**Lecciones aprendidas (Frida 17.15.3):**
- ✅ Gadget .so en `lib/arm64-v8a/` + config en `assets/`
- ❌ `"type": "script"` con archivo externo → ignorado en Frida 17.x
- Priorizar encontrar un mod sin `libstub.so` (parcheable en smali)

---

## Unity / IL2CPP modding (juegos)

```bash
# Detectar IL2CPP
unzip -l app.apk | grep -i "libil2cpp.so\|global-metadata.dat"

# Dump de IL2CPP
# Usar Il2CppDumper (Linux): extrae libil2cpp.so + global-metadata.dat
# Genera dump.cs con todas las clases/métodos

# Hook con Frida
# Usar frida-il2cpp-bridge para hook dinámico de métodos IL2CPP
```

---

## Android 16+ Developer Verifier bypass

`com.google.android.verifier` bloquea instalación de APKs con certificados no registrados en Android 16+ (BR/ID/SG/TH).

Bypass (DEX patching del verifier app):
1. `onVerificationRequired` → llamar `reportVerificationBypassed(1)`
2. Platform policy flag (45681539) → retornar `Long(0)` = NONE
3. Forced backport flag (45749715) → retornar `Boolean.TRUE`

Requiere instalar el verifier parcheado como system app (Magisk module o ADB con root).

---

## Morphe patcher (alternativa programática)

Para mantener patches entre versiones, usar Morphe patcher con fingerprints:

```kotlin
val enablePremiumPatch = bytecodePatch(
    name = "Enable Premium",
) {
    compatibleWith(Compatibility("BlockerHero", "com.blockerhero", listOf(AppTarget("1.5.0"))))
    execute {
        PrefsGetBooleanFingerprint.method.addInstructionsWithLabels(0, """
            const-string v0, "com.blockerhero.KEY_IS_PREMIUM"
            invoke-virtual {p1, v0}, Ljava/lang/String;->endsWith(Ljava/lang/String;)Z
            move-result v0
            if-eqz v0, :original
            const/4 v0, 0x1
            return v0
        """, ExternalLabel("original", method.getInstruction(0)))
    }
}
```

Repos:
- `MorpheApp/morphe-manager` (★6399) — engine
- `rushiranpise/morphe-patches` (★173) — 50+ patches
- `arandomhooman/hoomans-morphe-patches` (★92) — patches adicionales

---

## Plantilla de case study

```markdown
# Case: [App] [Versión]

## Metadata
- App: com.example.app
- Versión: 1.2.3
- Fuente: APKMirror / adb pull
- Objetivo: desbloquear premium / eliminar ads / quitar diálogo modder

## Inspección
- DEX: N | Native: Sí/No | Modder: yhf/ninguno
- Protección: SharedPreferences / Play Billing / native check

## Análisis
- Claves SP: premium, noads, max_favorites
- Métodos: isPremium()Z, checkLicense()V
- DEX inyección: classes3.dex | Call-sites: classes2.dex

## Parches
| Archivo | Método | Cambio | Estrategia |
|---|---|---|---|
| classes2.dex | isPremium()Z | return true | B |

## Resultado
- ✅ Premium desbloqueado / ❌ Re-sync de Billing revierte (usar C)

## Lección
[Una frase]
```

---

## Troubleshooting

| Síntoma | Causa probable | Solución |
|---|---|---|
| `INSTALL_FAILED_UPDATE_INCOMPATIBLE` | Certificado de firma diferente al original | Desinstalar app original antes de instalar el mod |
| `INSTALL_FAILED_INVALID_APK` | Compresión incorrecta o APK no alineado | Verificar `zipalign -p 4` y reglas de compresión |
| `NoClassDefFoundError` al iniciar | Se borró `META-INF/services/` o una clase de modder | Restaurar `META-INF/services/`; no borrar clases de modders |
| App crashea tras parche smali | Registros insuficientes o tipo de retorno incorrecto | Ajustar `.registers` y verificar tipos de retorno |
| `libfrida-gadget.so` no carga | Arquitectura incorrecta o config ausente | Usar arm64, colocar config en `assets/frida-gadget.config` |
| Play Integrity revierte el mod | Verificación server-side del token | No se puede parchear; ocultar root o modificar backend propio |
| Tráfico no se intercepta | QUIC/HTTP3 o SSL pinning nativo | Usar HTTP Toolkit o hooks específicos de BoringSSL |
| Diálogo de modder persiste | Call-sites no eliminados en todas las Activities | Buscar `invoke-static` a métodos de modder en todos los DEX |

---

## Referencias

- **Cases:** `cases/` (GPS Emulator, CamScanner, YouTube Morphe, AdGuard, GPS Data, Liteapks Store)
- **Google APIs:** `google-apis.md` (reemplazo de API keys, AOSP testkey)
- **Toolbox completo:** `reports/android-re-toolbox.md` (80+ herramientas, 16 categorías)
- **Foros rusos:** 4PDA (`4pda.to`) — MT Manager, NP Manager, Batch ApkTool, Lucky Patcher
- **Lista maestra:** `jbro129/android-modding` (★739, 821 líneas, 50+ herramientas categorizadas)

### Skills relacionados

> **Workflow recomendado:** usar `android-reverse-engineering` para triaje, análisis de protecciones y extracción de API endpoints; luego `apk-modding` para implementar parches persistentes.

- **`frida-expert`** — Cookbook completo de Frida para Android: SSL pinning (14 librerias), root bypass (5 vectores), crypto intercept, native connect hook. Usar para bypass en runtime antes o en lugar de parcheo smali.
- **`android-reverse-engineering`** — RE general de APKs (Java, Kotlin, nativo, SSL pinning, root bypass, Frida, MASTG). Usar para análisis e investigación antes de modding.
- **`flutter-reverse-engineering`** — RE profundo de Flutter/Dart (libapp.so, Dart VM internals, blutter, reFlutter, BoringSSL hooking). Usar cuando el APK sea Flutter.
- **`ghidra-pyghidra`** — Ghidra + pyghidra como herramienta (análisis headless, scripting Python, decompilación automatizada). Usar para análisis nativo ARM64 profundo.
- **`httptoolkit-android`** — HTTP Toolkit en Android (mecanismo de interceptación, troubleshooting). Usar para captura de tráfico.
- **`android-cleanup`** — Limpieza de dispositivo Android post-pentesting (proxy, iptables, CA certs, Frida Gadget, Magisk modules). Usar después de sesiones de modding/dynamic analysis.

---

## Changelog

- 2026-07-19 (v5): Actualización 2026: regla de oro de cleanup, herramientas con versiones (HTTP Toolkit, mitmdump), manejo de bundles .apks/.xapk en triaje, bypass runtime de signature checks expandido, sección de troubleshooting, referencias cruzadas reforzadas a `android-reverse-engineering`.
- 2026-07-18 (v4): Reescrito como playbook operativo para el agente. Enfoque en herramientas Linux PC del workspace. Eliminadas herramientas on-device secundarias. Flujo estándar de 7 fases. Estrategias A-F. Detección de modders 2025-2026. Bypass de signature checks (Java, nativo, runtime). PairipCore. Frida Gadget. Unity/IL2CPP. Android 16+ verifier. Morphe patcher. Scripts de automatización.
