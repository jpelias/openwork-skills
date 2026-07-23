---
name: android-reverse-engineering
description: >
  Reverse-engineer Android APKs, AAB/App Bundles, XAPK, JAR, and AAR files across Java, Kotlin,
  Flutter, React Native/Hermes, and Unity/IL2CPP. Static decompilation (jadx, Fernflower/Vineflower,
  apktool, baksmali, Il2CppDumper, hermes-dec), API extraction and call-flow documentation,
  gRPC/Protobuf black-box decoding, dynamic analysis (Frida, Objection, mitmproxy), SSL pinning
  bypass (OkHttp, Ktor, Cronet, Flutter, WebView), root detection bypass, anti-debugging/anti-tamper
  bypass, Frida detection/evasion, deep link/App Link hijacking, AIDL/Binder exploitation,
  ContentProvider path traversal, cryptoanalysis, deobfuscation (ProGuard/R8/DexGuard/StringFog),
  native ARM64 analysis (Ghidra, radare2), PairipCore/Dex2C detection, Play Integrity/SafetyNet
  analysis, and OWASP MASTG/MASVS compliance testing. Use for authorized security testing (own
  apps, bug bounty with defined scope, or apps with explicit permission from the owner) — not
  against third-party services without authorization.
---

# Android RE Expert

## ⛔ REGLA ABSOLUTA: Nunca crear APIs ni registrarse en servicios cloud

El agente tiene **PROHIBIDO TERMINANTEMENTE**:

1. Crear API keys de Google (Maps, Places, Firebase, etc.)
2. Navegar a `console.cloud.google.com`, `console.firebase.google.com`, o similares
3. Registrarse, crear cuentas, o habilitar APIs en cualquier plataforma cloud
4. Usar el navegador para formularios de consolas de administracion (Google Cloud, AWS, Azure, Mapbox...)
5. Intentar resolver CAPTCHAs o formularios web complejos

**Motivo:** El agente no puede completar formularios Angular/React, no tiene metodo de pago, el usuario no lo quiere, y es una perdida de tiempo.

**Alternativa correcta:** Si una app necesita API key de Google Maps y la firma original esta disponible, usar la APK sin modificar + Frida para parchear el resto en runtime. Si no hay firma original, buscar keys unrestricted en APKs ya moddeadas (resources.arsc). Consultar `.opencode/skills/apk-modding/google-apis.md` para el flujo completo.

---

6-phase attack pipeline for pentesting and reverse engineering Android APKs.

## Prerequisites

Requires **Java JDK 17+**, **jadx 1.5.1+**, and optionally **Fernflower/Vineflower** + **dex2jar** for better decompilation quality. For the dynamic flow: **Frida 17.15.3+**, **mitmproxy/mitmdump 12.x+**, **Objection 1.12.5+**, and a device/emulator with **Magisk**, **KernelSU**, or **KernelSU-Next** if root is needed.

```bash
# Check what you have
jadx --version
java -version
frida --version
mitmdump --version
apktool --version
```

If something is missing, install with the system package manager (apt, brew, pipx, etc.) or consult the official documentation for each tool.

### Environment Setup (from zero)

```bash
# Debian/Ubuntu base
sudo apt install -y openjdk-17-jdk aapt apksigner zipalign adb fastboot \
  python3-pip radare2 binutils-aarch64-linux-gnu

# Python tooling (isolated)
pipx install frida-tools objection mitmproxy

# jadx
wget -q https://github.com/skylot/jadx/releases/download/v1.5.1/jadx-1.5.1.zip
unzip -q jadx-1.5.1.zip -d ~/tools/jadx && export PATH=$PATH:~/tools/jadx/bin

# apktool
wget -q https://raw.githubusercontent.com/iBotPeaches/Apktool/master/scripts/linux/apktool -O ~/tools/apktool
chmod +x ~/tools/apktool

# bundletool (para .aab)
wget -q https://github.com/google/bundletool/releases/download/1.17.2/bundletool-all-1.17.2.jar -O ~/tools/bundletool.jar

# Il2CppDumper (para Unity)
git clone https://github.com/Perfare/Il2CppDumper ~/tools/Il2CppDumper

# Device: frida-server (arm64 físico, x86_64 emulador)
frida --version  # la versión del server DEBE coincidir exactamente
adb push frida-server-17.x-android-arm64 /data/local/tmp/fs
adb shell "chmod 755 /data/local/tmp/fs"
adb shell "su -c /data/local/tmp/fs &"   # o sin su si frida-gadget
```

## ⚠️ GOLDEN RULE — SIEMPRE, SIN EXCEPCION

**Antes de tocar un solo byte, buscar en GitHub.** `github.com/topics/android-reverse-engineering`, `github.com/search?q=<app>`. Si alguien ya lo analizo, fork y adapta. No reinventes la rueda. Nunca.

## Analysis Profiles — elegir antes de empezar

El mismo APK exige flujos distintos según el objetivo. Declarar el perfil al inicio de la sesión:

| Perfil | Objetivo | Fases prioritarias | Output |
|---|---|---|---|
| **Pentest** | Encontrar vulnerabilidades explotables (MASVS) | TRIAGE → JAVA → IPC → HOOK | Informe con findings clasificados |
| **Modding** | Modificar comportamiento persistentemente | TRIAGE → SMALI → REBUILD | APK parcheado y firmado → skill `apk-modding` |
| **Malware** | Entender capacidades e IoCs | TRIAGE → NATIVE → HOOK (aislado) | IoCs, C2, descripción de payload |
| **API mapping** | Documentar endpoints para cliente propio | TRIAGE → JAVA → captura tráfico | Lista de endpoints + auth + payloads |

**Regla:** si el objetivo es "modificar la app", delegar la fase de parcheo al skill `apk-modding`. Si es "entenderla", quedarse aquí.

### Quick Start — primera sesión (si eres nuevo en Android RE)

Si nunca has hecho RE de Android, NO empieces con una app de producción. Empieza con una app vulnerable intencionalmente:

```bash
# 1. Descarga DIVA (Diverse Insecure Vulnerable App)
wget https://github.com/payatu/diva-android/raw/master/app-debug.apk -O diva.apk

# 2. Instala en dispositivo/emulador
adb install diva.apk

# 3. Triaje rápido
jadx -d diva-out/ diva.apk
aapt dump badging diva.apk | grep -E "package:|launchable|permission"
```

**Flujo mínimo de 15 minutos para familiarizarte con el pipeline:**
1. Abre `diva-out/sources/` en jadx-gui → busca `Log.e` y `SharedPreferences` → las vulnerabilidades son deliberadas y visibles.
2. Lanza mitmproxy: `mitmdump -p 8080 -w diva.flows` → explora la app → revisa qué endpoints llama.
3. Conecta Frida: `frida -U -f jakhar.aseem.diva` → prueba `android sslpinning disable` con Objection.
4. Abre el APK con `apktool d diva.apk` → busca `android:debuggable` en el manifest → entiende la estructura de un APK desempaquetado.

Cuando DIVA te resulte trivial, escala a **InsecureBankv2** (`dineshshetty/Android-InsecureBankv2`) y luego a **OWASP UnCrackable L1** (Maddie Stone's RE 101).

**Principio fundamental:** el 80% de las apps reales usan los mismos patrones que estas apps de entrenamiento (OkHttp + Retrofit + SharedPreferences + WebView). Domina primero los fundamentos en terreno conocido.

## Attack Pipeline

```
TRIAGE  → jadx + apktool + unzip + aapt
JAVA    → CertificatePinner, TrustManager, crypto, auth, OkHttp
SMALI   → debug flags, root bypass, NSC mod
REBUILD → apktool b → zipalign → apksigner → adb install
HOOK    → Frida Java + Native (.so)
NATIVE  → Ghidra/IDA/radare2 → pattern scan → memory patch
```

## ⚠️ HOW TO CAPTURE TRAFFIC — READ FIRST ⚠️

**NEVER USE `settings put global http_proxy`. NEVER USE iptables DNAT. DON'T WASTE TIME WITH FIREFOX, VIVALDI, OR MANUAL CERTIFICATES. NONE OF THAT WORKS.**

> **Nota:** La prohibición de iptables DNAT aplica a **redirigir tráfico a un proxy** (raw TLS no es interpretable por mitmdump regular). Sí se puede usar iptables para **bloquear o filtrar tráfico específico** (ej: bloquear UDP 443 para forzar HTTP/2).

### Decision tree

```
Do you have HTTP Toolkit? → YES → USE IT (Click "Android device via ADB")
                           → NO  → Does the app have SSL pinning?
                                    → YES → Use Frida native-connect-hook.js
                                    → NO  → Use Frida native-connect-hook.js too
```

**Always use `native-connect-hook.js` from HTTP Toolkit.** It's a VPN without an app — hooks `connect()` from libc and redirects ALL sockets to the proxy. Works with any app, with or without SSL pinning, with or without a browser.

### Step by step (without HTTP Toolkit Desktop)

```bash
# 1. Clone
git clone https://github.com/httptoolkit/frida-interception-and-unpinning.git
cd frida-interception-and-unpinning

# 2. Edit config.js: set your CA (mitmproxy) and PROXY_HOST=127.0.0.1, PROXY_PORT=8080

# 3. PC: mitmdump + adb reverse
adb reverse tcp:8080 tcp:8080
mitmdump --mode regular -p 8080 -w captura.flows

# 4. Device: Frida with the app
frida -U \
  -l config.js \
  -l native-connect-hook.js \
  -l android/android-system-certificate-injection.js \
  -l android/android-certificate-unpinning.js \
  -f com.target.app
```

**What each script does:**
| Script | Purpose |
|---|---|
| `native-connect-hook.js` | **VPN without an app.** Hooks `connect()` from libc. All TCP sockets go to the proxy. |
| `android-system-certificate-injection.js` | Injects CA into Android's TrustStore |
| `android-certificate-unpinning.js` | Disables Certificate Transparency, OkHttp pinning, TrustManager |
| `native-tls-hook.js` | (Optional) If the app uses native BoringSSL/Cronet |

**If the app does NOT have SSL pinning** (e.g. Cordova/Ionic apps, WebView apps): you can try just `native-connect-hook.js` + `system-certificate-injection.js`. The other scripts don't hurt if they're extra.

**If the app DOES have SSL pinning**: use all 4 scripts.

### ❌ THINGS THAT DON'T WORK (don't waste time)

| What NOT to do | Why it doesn't work |
|---|---|
| `settings put global http_proxy 127.0.0.1:8080` | Most apps ignore the system proxy. Browsers too. |
| iptables DNAT to PC + mitmdump regular | mitmdump regular expects HTTP/CONNECT, not raw TLS |
| iptables REDIRECT + mitmdump transparent on PC | The original destination is lost in forwarding |
| Manually install certificate in Firefox/Vivaldi | Browsers ignore the system CA or have CT |
| Use `--ignore-certificate-errors` in Chrome | Doesn't work on Android, flags ignored |
| Change the default browser | No browser trusts self-signed CAs without native bypass |

### ✅ What DOES work

| Method | When to use |
|---|---|
| **HTTP Toolkit Desktop App** | Whenever you can. Click → done. |
| **Frida native-connect-hook.js** | If you don't have HTTP Toolkit or it doesn't work |
| **mitmdump --mode transparent on device** | If you have Python on the device and root |

### Edge cases: QUIC/HTTP3 and mTLS

**QUIC/HTTP3:** Some apps (Google apps, TikTok, Discord) use QUIC over UDP. `native-connect-hook.js` hooks TCP `connect()`, so QUIC traffic may bypass the proxy. Options:
1. Force the app to downgrade to HTTP/2 by blocking UDP 443 outbound (requires root/iptables).
2. Use HTTP Toolkit, which handles QUIC interception transparently.
3. Hook the Cronet/QUIC layer and disable QUIC via `CronetEngine.Builder.enableQuic(false)` if the app exposes a Java API.

**mTLS (Client Certificates):** If the server demands a client certificate, mitmproxy cannot complete the TLS handshake. You must:
1. Extract the client cert + private key from the APK (search for `.p12`, `.pfx`, `KeyStore`, `PrivateKey`, `X509KeyManager`).
2. Configure mitmproxy with the client cert: `mitmdump --client-cert cert.pem --client-key key.pem`.
3. Or hook `X509KeyManager.chooseClientAlias` / `getPrivateKey` / `getCertificateChain` to return the app's client cert.

## Android RE Fundamentals

### APK and Entry Points
- **APK = ZIP**: AndroidManifest.xml, classes.dex (Dalvik bytecode), lib/ (native .so), assets/, META-INF/
- **XAPK / bundles**: some distributors use `.xapk` wrappers (APKPure) or `.apks` (SAI). They are ZIPs containing `base.apk` + `split_config.*.apk`. When decompiling, if jadx produces very few Java files, it's because it only processed the wrapper — extract the real `base.apk` and re-decompile on top of it.
- **Split APKs**: Modern apps can have a base APK + splits by architecture, language, density:
  ```bash
  adb shell pm path com.app
  # → package:/data/app/com.app-xxx==/base.apk
  # → package:/data/app/com.app-xxx==/split_config.arm64_v8a.apk
  # → package:/data/app/com.app-xxx==/split_config.es.apk
  ```
  - Native libraries (.so) may ONLY be in the architecture split, not in base.apk
  - **Always extract all splits** for complete analysis
  - Google apps (Tasks, Photos, etc.) usually have native Cronet in `split_config.arm64_v8a.apk`
- **Entry points** (where to start analysis):
  - `Launcher Activity`: MAIN + LAUNCHER intents in the manifest
  - `Services`: executables without UI, started with `startService` → `onStart`
  - `Broadcast Receivers`: listeners for system broadcasts, registered in manifest or with `registerReceiver()`
  - `Application subclass`: instantiated before any other class; `attachBaseContext` is called before `onCreate`
  - **Exported components** (`android:exported="true"` or intent-filters): accessible from other processes
- **DEX → Smali → Java**: Java/Kotlin → compiled to DEX bytecode → disassembled to Smali (readable format) → decompiled to Java with jadx. If jadx fails, read Smali with the [instruction set](https://source.android.com/docs/core/runtime/instruction-formats).

### AAB / App Bundle (.aab)

Since 2021, Play Store requires `.aab` for new apps. You CANNOT decompile an `.aab` directly with good results — convert it first:

```bash
# Convert .aab → universal APK (single APK with all resources)
java -jar bundletool.jar build-apks \
  --bundle=app.aab \
  --output=app.apks \
  --mode=universal \
  --ks=debug.keystore --ks-pass=pass:android   # requiere firma

unzip -p app.apks universal.apk > universal.apk
jadx -d out/ universal.apk
```

**Diferencias clave vs APK:**
- `resources.arsc` está en formato protobuf compilado — `aapt` clásico falla, usar `aapt2`
- Sin firma v1: el `.aab` nunca se instala tal cual, Play lo transforma en splits firmados
- **Dynamic feature modules**: código en módulos `feature_*.dex` descargados on-demand — el análisis del `base` NO los incluye. Listar módulos: `unzip -l app.aab | grep -E "^[^/]+/dex/"`
- Si solo tienes el dispositivo: `adb shell pm path com.app` te da los splits YA instalados (incluye dynamic features descargados)

### Extracción de APKs desde el dispositivo

```bash
# Todas las rutas (base + splits)
adb shell pm path com.target.app

# Pull de cada una
adb shell pm path com.target.app | cut -d: -f2 | while read p; do
  adb pull "$p" ./splits/
done

# Script listo: scripts/extract_splits.sh <package>
```

### JNI: Java ↔ Native Bridge
- **Dynamic Linking**: the native function is named `Java_<package>_<Class>_<method>`. The JNI system resolves it automatically.
- **Static Linking**: `RegisterNatives` is used in `JNI_OnLoad`. More common in malware/obfuscation because it hides names.
- `System.loadLibrary("foo")` → loads `libfoo.so` and executes `JNI_OnLoad` if it exists.
- **Tip**: search for `System.loadLibrary` or `System.load` in jadx → leads you to the .so and its `JNI_OnLoad`.

### Obfuscation Indicators
| Indicator | Solution |
|---|---|
| No readable strings | Find the method that receives strings as an argument → trace back to the deobfuscator |
| Scrambled strings (all go through the same function) | That function is the deobfuscator → transliterate to Python |
| `DexClassLoader` + file in assets/ | Loads additional code. Follow from where the file is read |
| No `Java_` or `RegisterNatives` in the .so | Start at `JNI_OnLoad`, find routine that loads additional code |
| APK with multiple classes.dex or .so in non-standard paths | Malware hiding payload |

### ARM Assembly (Armv8-A / AArch64)

**Architecture:**
- **Armv8 Profiles**: A (Android/smartphones), R (modems/SSD/real-time), M (microcontrollers). Android uses A-profile.
- **Micro-architecture vs Architecture**: micro = how the chip is built (caches, pipeline). Architecture = which instructions it supports. Same architecture (Armv8-A), different micro-architectures (Cortex-A72, A78, etc.).
- **AArch64**: 64-bit, 31 registers X0-X30 (64b), W0-W30 (32b subset). XZR/WZR = zero register. X30 = LR (link register). SP is not a GPR.
- **AArch32**: 32-bit, 16 registers R0-R15. R13=SP, R14=LR, R15=PC.
- **Exception Levels**: EL0 (user apps), EL1 (kernel), EL2 (hypervisor), EL3 (secure monitor). In normal Android, you only see EL0. Root/kernel = EL1.

**Key instructions:**
- `LDR X0, [X1]` — loads 64b from the address in X1 into X0
- `STR X0, [X1]` — stores X0 at the address in X1
- **Addressing modes**: `[X1, #8]` (immediate offset), `[X1, X2]` (register), `[X1, X2, LSL #3]` (scaled register), `[X1, #8]!` (pre-index with writeback)
- `STP/LDP` — store/load pair (efficient push/pop of 2 registers)
- **Conditionals (AArch64)**: only B.cond (b.eq, b.ne, etc.), CSEL (select), CSET, CINC. There is no conditional execution on every instruction like in AArch32.
- **Branch**: `B label`, `BL func` (link, saves return in X30), `RET X30` (return)
- **Stack**: grows downward. `STP X29, X30, [SP, #-16]!` = prologue. `LDP X29, X30, [SP], #16` = epilogue.

## Architecture Mapping and Call Flows

1. Read `AndroidManifest.xml`: launcher Activity, components, permissions, `Application` class.
2. Identify pattern: MVP (`Presenter`), MVVM (`ViewModel`/`LiveData`), Clean Architecture (`domain`/`data`/`presentation`).
3. Trace from the entry point: `onCreate()` → listener → ViewModel/Presenter → Repository → API interface → actual HTTP call.
4. **With Dagger/Hilt**: search for classes annotated with `@Module`/`@Provides`/`@Binds` to know which implementation is injected. The `@Inject` interface in a ViewModel constructor leads you to the module that provides it. jadx preserves Dagger annotations even with ProGuard obfuscation.
5. With obfuscated code: use Retrofit annotations (`@GET`, `@POST`, `@Header`) and URL literals as anchors (they are never obfuscated).

```bash
# Quick Dagger/Hilt module search
grep -r "@Module\|@Provides\|@Binds\|@Inject\|HiltAndroidApp" sources/ | head -20
```

## Decompilers: jadx vs Fernflower/Vineflower

| Situation | Engine |
|---|---|
| First pass on any APK | `jadx` (fast, handles resources) |
| JAR/AAR library analysis | `fernflower` (better Java output) |
| jadx gives warnings/broken code | `both` (compare and pick the best per class) |
| Complex lambdas/generics/streams | `fernflower` |

```bash
# jadx (always the first option)
jadx -d output/ app.apk

# Fernflower + dex2jar (alternative when jadx fails)
d2j-dex2jar app.apk -o app.jar
java -jar fernflower.jar app.jar output/
```

**XAPK / bundles auto-detection**: if passing the APK through jadx yields very few `.java` files, check if it's a wrapper:
```bash
unzip -l app.xapk  # or app.apks
# If it contains base.apk + split_config.*.apk, it's a wrapper
unzip app.xapk "*.apk"
jadx -d output/ base.apk  # re-decompile the real one
```

## Quick Triage: Detect Network Framework

Before choosing the bypass strategy, identify which network stack the app uses:

```bash
# 1. Search for OkHttp
unzip -l app.apk 2>/dev/null | grep -i "okhttp" | head -3
# → okhttp3/internal/publicsuffix/  → uses OkHttp

# 2. Search for Ktor Client
unzip -l app.apk 2>/dev/null | grep -i "ktor" | head -3
# → META-INF/kotlinx_coroutines_reactive.version  → uses Ktor

# 3. Search for Cronet (native) — check split APKs
aapt dump badging app.apk 2>/dev/null | grep "split"
# If it has split_config.arm64_v8a.apk:
unzip -l split_config.arm64_v8a.apk 2>/dev/null | grep -i "cronet\|cronet"
# → libcronet.so or libsscronet.so  → uses native Cronet

# 4. Search for Flutter
unzip -l app.apk 2>/dev/null | grep -i "libflutter.so" | head -1
# → libflutter.so  → Flutter

# 5. Search for gRPC (in classes.dex)
unzip -p app.apk classes*.dex 2>/dev/null | strings | grep -i "grpc\|GRPC"
# → gRPC frame header malformed  → uses gRPC (common in Google apps)

# 6. Search for Network Security Config
unzip -p app.apk AndroidManifest.xml 2>/dev/null | strings | grep "networkSecurityConfig"
# → networkSecurityConfig=@0x...  → has declarative NSC
aapt dump xmltree app.apk res/xml/network_security_config.xml 2>/dev/null
# → Check trust-anchors and domain-config

# 7. Search for hybrid app (Cordova/Ionic/React Native)
unzip -l app.apk 2>/dev/null | grep -ciE "assets/www|cordova|ionic|capacitor"
# → If >0, it's a hybrid app. Check config.xml:
unzip -p app.apk res/xml/config.xml 2>/dev/null | grep -i "hostname\|IonicWebView"
# → If it has hostname preference, it uses Ionic WebView with local server

# 8. Search for React Native / Hermes
unzip -l app.apk 2>/dev/null | grep -iE "index.android.bundle|libhermes.so|libreactnativejni.so" | head -3
# → libhermes.so  → RN con Hermes bytecode (ver sección React Native)

# 9. Search for Unity / IL2CPP
unzip -l app.apk 2>/dev/null | grep -iE "libil2cpp.so|libunity.so|global-metadata.dat" | head -3
# → libil2cpp.so  → Unity IL2CPP (ver sección Unity/IL2CPP)
# → libmono.so    → Unity Mono (más viejo, DLLs .NET en assets/bin/Data/Managed/)

# 10. One-shot: scripts/triage.sh app.apk  (ejecuta todos los checks)
```

**Strategy by result:**
```
OkHttp present      → CertificatePinner.check() + TrustManagerImpl
Ktor Client         → Only TrustManagerImpl (doesn't use OkHttp)
Cronet present      → Native BoringSSL (SSL_CTX_set_custom_verify)
gRPC detected       → Binary traffic (Protobuf) → sección "gRPC and Protobuf Analysis"
Flutter             → reFlutter / kill_flutter / iptables transparent
React Native        → sección "React Native / Hermes" (bridge hook, Hermes bytecode)
Unity/IL2CPP        → sección "Unity / IL2CPP" (Il2CppDumper, NO leer smali — la lógica está en nativo)
Declarative NSC     → Check if it trusts user certificates
```

## SSL Pinning Bypass (6 layers + tree)

| Layer | Technique | When |
|---|---|---|
| 1. TrustManager | `verifyChain()` + `checkTrustedRecursive()` → bypass | Android 7+, all native apps |
| 2. OkHttp | `CertificatePinner.check()` → no-op | Apps with OkHttp |
| 3. WebView | `onReceivedSslError` → `handler.proceed()` | React Native, miniapps |
| 4. Network Sec Config | Modify manifest or hook `isCleartextTrafficPermitted` | Android 7+ declarative pinning |
| 5. Native BoringSSL | `SSL_CTX_set_verify(0)` + `SSL_set_custom_verify(NULL)` | Flutter, NDK, Cronet |
| **6. Cronet/gRPC** | `SSL_CTX_set_custom_verify` callback → NULL | Google apps (Tasks, Gemini, Photos), Cronet-based |

**Quick tree:**
```
Flutter? → reFlutter / memory scan / iptables
OkHttp?  → Layer 1 + Layer 2
Ktor Client? → Layer 1 (uses Android's TrustManagerImpl, doesn't go through OkHttp)
Cronet/gRPC? → Layer 6 (Native BoringSSL, SSL_CTX_set_custom_verify)
WebView? → + Layer 3
Ionic/Cordova? → native-connect-hook.js (system proxy does NOT work)
NDK?     → Layer 5 (curl_easy_setopt or BoringSSL)
None? → search for custom TrustManager in jadx → specific hook
```

### Client Certificate Pinning Bypass

Some apps pin a specific client certificate for mutual TLS (mTLS). If you need to replay requests from another context:

```javascript
// Hook X509KeyManager to return the app's client certificate
Java.perform(function() {
    var X509KeyManager = Java.use("javax.net.ssl.X509KeyManager");
    X509KeyManager.chooseClientAlias.implementation = function(keyTypes, issuers, socket) {
        console.log("[mTLS] chooseClientAlias called");
        return this.chooseClientAlias(keyTypes, issuers, socket);
    };
    X509KeyManager.getPrivateKey.implementation = function(alias) {
        console.log("[mTLS] getPrivateKey for alias: " + alias);
        return this.getPrivateKey(alias); // dump or reuse
    };
    X509KeyManager.getCertificateChain.implementation = function(alias) {
        var chain = this.getCertificateChain(alias);
        console.log("[mTLS] Certificate chain length: " + chain.length);
        return chain;
    };
});
```

To extract the client cert statically, search for:
```bash
rg -n 'KeyStore|PrivateKey|X509KeyManager|KeyManagerFactory' jadx-out/
unzip -l app.apk | grep -iE '\.p12|\.pfx|\.pem|\.bks'
```

### Cert Injection (THE CRITICAL ONE — 825 bytes or nothing)
```bash
# NEVER -text. MUST yield 825 bytes.
HASH=$(openssl x509 -inform PEM -subject_hash_old -in cert.pem | head -1)
openssl x509 -inform PEM -in cert.pem -outform DER -out $HASH.0
adb shell su -c "mount -o rw,remount magisk /system/etc/security/cacerts"
adb push $HASH.0 /sdcard/ && adb shell su -c "cp /sdcard/$HASH.0 /system/etc/security/cacerts/$HASH.0"
adb shell su -c "chmod 644 /system/etc/security/cacerts/$HASH.0; mount -o ro,remount magisk /system/etc/security/cacerts"
```

## Frida Quick Reference

> **Skill completo:** `frida-expert` — cookbook con scripts verificados: SSL pinning (14 librerías), root bypass (5 vectores), anti-Frida, crypto intercept, OkHttp3 interceptor, native connect hook, Flutter BoringSSL, CModule, memory scanning.

### Técnicas principales (tabla resumen)

| Técnica | Bypass | Skill reference |
|---|---|---|
| SSL pinning (OkHttp) | `CertificatePinner.check` → no-op | `frida-expert` § SSL |
| SSL pinning (TrustManager) | `verifyChain` + `checkTrustedRecursive` → bypass | `frida-expert` § SSL |
| SSL pinning (Cronet/BoringSSL) | `SSL_CTX_set_custom_verify` → NULL callback | `frida-expert` § SSL |
| Root detection | File.exists, Runtime.exec, SystemProperties, Build.TAGS, Debug | `frida-expert` § Root |
| Crypto intercept | Cipher.doFinal, Mac.doFinal, MessageDigest | `frida-expert` § Crypto |
| Anti-Frida | strstr/fopen/memmem hooks, CModule | `frida-expert` § Anti-Frida |
| Anti-suicide | System.exit, Runtime.exit, Process.killProcess → block | `frida-expert` § Anti-suicide |
| CModule | Hooks nativos en C (más rápido que JS) | `frida-expert` § CModule |
| Memory scanning | Memory.scanSync, pattern matching | `frida-expert` § Memory |
| DexClassLoader | Interceptar clases cargadas dinámicamente | `frida-expert` § Advanced |

### Gotchas importantes

- `setTimeout` solo dentro de `Java.perform()`
- `tail -f /dev/zero | frida ...` para mantener vivo
- Siempre misma versión client/server
- NUNCA `return undefined` → `return ArrayList.$new()` o `return arguments[0]`
- `arm64` para físico, `x86` para emulador google_apis
- **Sesiones múltiples:** Kill con `kill $(pgrep -f "frida.*<PID>")` antes de re-attach

## Objection (top 8 commands)

```bash
objection -g com.app explore
android sslpinning disable   # 5 automatic layers
android root disable          # 7 checks
android hooking list/watch classes
android intent launch_activity
android keystore list
android clipboard monitor
android heap search instances <class>
```

## Ionic/Cordova Apps — only native-connect-hook works

Ionic/Cordova apps with `IonicWebViewEngine` ignore any system proxy. **DO NOT use iptables or `settings put global http_proxy`.** Use `native-connect-hook.js` (see "HOW TO CAPTURE TRAFFIC" section above). It is the only method that forces connections to the proxy without depending on system network configuration.

**⚠️ For federated login via Chrome Custom Tab (OIDC/SAML):** Chrome rejects mitmproxy certificates. With `native-connect-hook.js` and `android-certificate-unpinning.js`, Chrome's CT is bypassed as well. If you use HTTP Toolkit, it handles this automatically.

## Discovered API Analysis

Once traffic is captured, classify endpoints by type:

```bash
# Extract all unique URLs from the mitmproxy capture file
python3 << 'PYEOF'
from mitmproxy import io
from urllib.parse import urlparse
flows = []
with open("captura.flows", "rb") as f:
    for flow in io.FlowReader(f).stream():
        flows.append(flow)
endpoints = set()
for flow in flows:
    if not hasattr(flow, 'request') or not flow.request: continue
    u = flow.request.pretty_url
    p = urlparse(u)
    if any(x in p.netloc for x in ['api.', 'rest', 'service', 'v1', 'v2']):
        fn = u.split('?')[0][:100]
        endpoints.add(fn)
for e in sorted(endpoints): print(e)
PYEOF
```

**Three typical API patterns in Android apps:**

| Pattern | Characteristic | Example | Readable |
|---|---|---|---|
| **Legacy REST** | `?function=getX&format=json` | `/1-4/?function=getData&format=json` | ✅ JSON |
| **Modern REST** | `/v1/app/categories` | `/v1/app/content/page/1` | ✅ JSON |
| **gRPC** | `package.Service/Method` | Binary proto → decodificable black-box (ver sección gRPC) | ⚠️ Protobuf |

**For gRPC:** el body es binario (Protobuf) PERO se puede decodificar sin el `.proto` original usando las técnicas de la sección **"gRPC and Protobuf Analysis"** más abajo: extracción de esquema desde las clases generadas, protoscope black-box, y hook del serializador con Frida.

## Frida Gotchas

- `setTimeout` only inside `Java.perform()`
- `tail -f /dev/zero | frida ...` to keep alive
- Same client/server version
- NEVER `return undefined` → `return ArrayList.$new()` or `return arguments[0]`
- `arm64` for physical, `x86` for google_apis emulator
- **Multiple Frida sessions:** If you run `frida -U <PID>` multiple times, Frida processes accumulate. Kill them with `kill $(pgrep -f "frida.*<PID>")` before re-attaching.

## Frida Detection and Evasion

Las apps modernas detectan Frida por múltiples vectores. Si `frida -f` no arranca o aborta tras 1-2 segundos → probablemente hay detección.

### Detección conocida

| Método de detección | Patrón observado |
|---|---|
| Puerto D-Bus/TCP | `/proc/net/tcp`, puertos 27042-27046 por defecto |
| `ptrace` contra sí mismo | Otra app/threads hace `ptrace(TRACEME)` → falla si Frida ya está attached |
| `/proc/self/maps` | Strings "frida", "gum", "agent", "gadget" en memory map |
| `/proc/self/smaps` | Más detallado que maps, busca nombres de bibliotecas |
| `stat()` de artefactos Frida | `/data/local/tmp/frida-server`, `/data/local/tmp/re.frida.server` |
| `readlink()` de /proc/self/exe o fd | Revela nombre del proceso Frida |
| `find /data/local/tmp` | App escanea directorios temporales |
| Tamaño de pila (stack canaries) | Frida modifica el tamaño del stack → detectable |
| Tiempo de respuesta de JNI | El hook introduce latencia → detectable por timers |

### Estrategia de evasión sistemática

**Orden recomendado:**

```bash
# 1. Cambiar nombre de frida-server y ruta
cp frida-server-17.x-android-arm64 /data/local/tmp/.sys-tool-1
#  2. Puerto no estándar:
/data/local/tmp/.sys-tool-1 -P 31337
# PC:
frida -U -p <PID> --listen 0.0.0.0:31337

# 3. Si sigue detectando: evitar /proc/self/maps completamente
# scripts/frida_stealth.js (hook de open/fopen/strstr/strstr/memmem)
```

**Script base de evasión (JavaScript → referencia, mejor usar `frida-expert`):**

```javascript
// Hook estratégico: nativo (libc) antes de que JNI se inicialice
Interceptor.attach(Module.findExportByName("libc.so", "strstr"), {
    onEnter: function(args) {
        var needle = args[1].readCString();
        if (needle && /frida|gum|agent|gadget/i.test(needle)) {
            this.hide = true;
        }
    },
    onLeave: function(retval) {
        if (this.hide) retval.replace(0); // NULL = no encontrado
    }
});

Interceptor.attach(Module.findExportByName("libc.so", "fopen"), {
    onEnter: function(args) {
        var path = args[0].readCString();
        if (path && /maps|status|smaps|\/proc\/self/.test(path)) {
            this.block = true;
        }
    },
    onLeave: function(retval) {
        if (this.block) {
            // Retorna NULL (archivo inaccesible) → la app interpreta "no se pudo abrir"
            retval.replace(ptr(0));
        }
    }
});

// Hook ptrace PTRACE_TRACEME → retornar 0 (éxito, aunque haya debugger)
Interceptor.attach(Module.findExportByName(null, "ptrace"), {
    onEnter: function(args) {
        if (args[0].toInt32() === 0) this.is_traceme = true;
    },
    onLeave: function(retval) {
        if (this.is_traceme) retval.replace(0);
    }
});
```

**Alternativas si Frida es detectada de forma agresiva (orden de preferencia):**

1. **Renombrar + puerto aleatorio** + script de evasión básico
2. **Frida-Gadget** embebido en APK (sin frida-server en el dispositivo)
3. **LSPosed** (persistente, ningún proceso externo)
4. **Emulación Android limpia** (sin root visible, sin Magisk)

**Detalle de cada alternativa:**

1. **Renombrar + puerto aleatorio + stealth.js**: funciona en ~60% de apps con detección básica. Si la app usa `/proc/self/maps` o `strstr`, el script de evasión lo bloquea.
2. **Frida-Gadget**: embebes `libfrida-gadget.so` en el APK y configuras `libfrida-gadget.config.so` para modo `listen`. No hay proceso `frida-server` visible, no hay puerto D-Bus. La app carga a Frida como una librería más. Ideal cuando el detector busca procesos externos.
3. **LSPosed**: un módulo Xposed no necesita PC conectado ni proceso externo. El hook se ejecuta dentro del propio proceso de la app vía Zygote. Requiere root pero es el más persistente. Limitación: solo Java (no nativo directo).
4. **Emulación con AVD escribible**: crea un emulador con `--writable-system` y elimina toda traza de root (sin Magisk, sin su, sin busybox). Usa `adb root` del emulador en lugar de Magisk, que es invisible para las apps. Ventaja: snapshot para restaurar estado limpio en segundos.
   ```bash
   # Crear AVD con system escribible (API 33+)
   avdmanager create avd -n re_lab -k "system-images;android-33;google_apis;x86_64" --force
   # Arrancar con writable system + adb root
   emulator -avd re_lab -writable-system -no-snapshot &
   adb root && adb remount
   # Push frida-server a /system/xbin (no a /data/local/tmp)
   adb push frida-server-17.x-android-x86_64 /system/xbin/.netd
   adb shell chmod 755 /system/xbin/.netd
   /system/xbin/.netd -l 0.0.0.0:31337 &
   ```
5. **DBI alternativo (QBDI/Triton)** — si Frida es totalmente bloqueada y necesitas tracing nativo: QBDI ( Quarkslab) para DBI a nivel de instrucción ARM64, o Triton (concolic execution). Más complejo pero indetectable por fingerprints de Frida. Requiere compilación cruzada desde PC.

**Tests de validación:** después de aplicar evasión, ejecutar:
```bash
# Si arranca sin crash y funciona 60+ segundos, bypass exitoso
frida -U -f com.target.app -l stealth.js --runtime=v8 -e "console.log('ALIVE')"
```

## Modern Root Hiding

```bash
# 2025-2026 stack for STRONG integrity:
KernelSU-Next / Magisk Alpha + Zygisk Next + Shamiko + TrickyStore + PlayIntegrityFork + HMA-OSS

# Magisk DenyList (the simplest):
# Settings → Zygisk ON → Configure DenyList → check app → reboot
```

### Recommended setup for STRONG_INTEGRITY (authorized testing only)

1. **Root solution**: KernelSU-Next or Magisk Alpha with Zygisk Next.
2. **Hide root from target app**:
   - Magisk: Settings → Zygisk ON → Configure DenyList → check target app → reboot.
   - KernelSU-Next: use `SUSFS` or `SUSu` modules for app-specific hiding.
3. **Hide modules**: Install **Shamiko** (white-list mode) so Zygisk is not exposed to the target app.
4. **Spoof device attestation**: Install **TrickyStore** + a valid **keybox.xml** to pass MEETS_STRONG_INTEGRITY on supported devices.
5. **Play Integrity bypass**: Use **PlayIntegrityFork** (PIF) or **TrickyStore** to return genuine-looking attestation responses.
6. **Hide apps**: Use **HMA-OSS** (Hide My Applist) to hide root/magisk apps from the target app's package enumeration.

### Quick checks

```bash
# Verify Play Integrity verdict locally (if the app exposes it)
adb shell dumpsys activity provider com.google.android.gms.chimera.container.GmsModuleProvider | grep -i integrity

# Check which apps are in Magisk DenyList
adb shell su -c "cat /data/adb/magisk.db" | strings | grep -i denylist
```

**Warning:** Bypassing Play Integrity on apps you do not own may violate the Google Play Terms of Service and local laws. Only use these techniques on your own apps or with explicit authorization.

## Learning References

- **☆ [Maddie Stone's Android RE 101](https://www.ragingrock.com/AndroidAppRE/)** — Full course with exercises (jadx, Ghidra, practice APKs)
- **☆ [Blue Fox: Arm Assembly Internals & RE](https://www.amazon.com/dp/1119745306)** — Maria Markstedter (Azeria Labs). 450p. Armv8-A in depth: ELF, AArch64/AArch32 registers, exception levels, addressing modes, static/dynamic analysis, arm64 malware. **The ARM RE bible.**
- **☆ [Awesome Android RE](https://github.com/user1342/Awesome-Android-Reverse-Engineering)** — Curated list of tools, training and resources (2446⭐, updated)
- **☆ Mobile App RE (Abhinav Mishra, 2022)** — Extracted in `docs/mobile-re-book/`: fundamentals, tools, Android RE (JADX/smali/obfuscation), automation with MobSF

## Tools

| Phase | Primary | Alternatives |
|---|---|---|
| Triage | jadx 1.5.1, apktool 2.7.0, aapt | unzip, strings, aapt2 |
| Java | jadx-gui, grep, Vineflower | MobSF, AndroGuard |
| Dynamic | Frida 17.15.3, Objection 1.12.5 | Medusa, Auto-Frida |
| Network | HTTP Toolkit, mitmdump 12.x, tcpdump | Burp, Wireshark |
| Native | Ghidra 12.x, radare2 6.1.9 | IDA Pro, Il2CppDumper |
| Flutter | reFlutter, iptables | kill_flutter (dynamic offset) |
| Root | Magisk, KernelSU, KernelSU-Next | TrickyStore, Shamiko, HMA-OSS |
| Stealth | fridare, phantom-frida | renef (memfd, no ptrace) |

## Top 20 Errors

| Error | Fix |
|---|---|
| Cert DER 812 bytes | Regenerate WITHOUT -text |
| verifyChain args mismatch | Hook ALL overloads |
| Frida dies alone | `tail -f /dev/zero \| frida ...` |
| Frida detected/killed by app | See "Frida Detection and Evasion" section; rename server + random port |
| AAB extracts to very few files | `.aab` is not installable — requires `bundletool build-apks --mode=universal` |
| WebView won't load with proxy | No proxy; Magisk DenyList |
| setTimeout not function | Inside Java.perform() |
| JNI crash SIGABRT | return ArrayList, not undefined |
| Read-only filesystem | `mount -o rw,remount magisk` |
| Frida version mismatch | Same client/server version |
| Proxy breaks miniapps | tcpdump without proxy |
| STRONG_INTEGRITY fail | TrickyStore + valid keybox + hide root |
| Multiple Frida sessions | `kill $(pgrep -f 'frida.*<PID>')` before re-attaching |
| Ionic/WebView app not capturing with proxy | Use native-connect-hook.js, not system proxy |
| Chrome Custom Tab rejects cert | Use native-connect-hook.js + cert unpinning |
| Ionic WebView crashes with Frida spawn | Use `attach` instead of `-f` spawn |
| mitmdump dies when closing shell | Use `setsid` + `&` or `tail -f /dev/zero \| frida` |
| Split APK missing native libs | Extract all splits (`adb shell pm path com.app`) |
| Play Integrity token rejected | Cannot forge; hide root or control server |
| Android 16 verifier blocks install | Patch verifier or use ADB with package_verifier_enable=0 |

## APK Signing (v1/v2/v3/v4)

| Scheme | Introduced in | Covers | Known weakness |
|---|---|---|---|
| v1 (JAR signing) | Android 1.0 | Only JAR entries, not the full ZIP | Vulnerable to Janus, Master Key |
| v2 (APK Signature Scheme) | Android 7.0 | Entire APK as a binary block | Requires re-signing after any modification |
| v3 | Android 9.0 | Same as v2 + key rotation | — |
| v4 | Android 11 | Incremental signing (for streaming install) | Requires a separate `.idsig` file |

- After modifying smali/resources and running `apktool b`, the APK loses the original signature. You must re-sign with `apksigner sign --ks debug.keystore app.apk` before installing.
- `apksigner verify --print-certs app.apk` shows which schemes an APK uses and the certificate hash.

## ProGuard / R8 / DexGuard — Obfuscation Levels

| Tool | What it does | How it shows in jadx |
|---|---|---|
| **ProGuard/R8** (standard, free) | Renames classes/methods/fields to `a`, `b`, `c...`; removes dead code | Single-letter names, flat package structure |
| **DexGuard** (commercial) | Adds string encryption, class encryption, control-flow flattening, anti-tamper | jadx fails on entire classes or strings appear as bytes |
| **Manual/reflection obfuscation** | Replaces direct calls with `Class.forName()` + reflection | No direct references, only loose strings resolved at runtime |

- `mapping.txt` (if found in the APK/assets) reverses ProGuard renaming — always search for it before decompiling manually.
- For encrypted strings: identify the method that takes a single `String`/`byte[]` and is called most frequently — that is usually the decrypter. Invoke it with Frida without reimplementing the algorithm.

## Anti-Debugging and Anti-Tampering

> **Contenido completo en sección "Anti-Debugging and Anti-Tampering (Extended)"** más abajo. Aquí el resumen rápido:

| Technique | Detection | Bypass |
|---|---|---|
| `Debug.isDebuggerConnected()` | Direct Java | Hook → `false` |
| Timing checks (`nanoTime()` between instructions) | Detects breakpoints | Hook clock or skip block |
| `ptrace(PTRACE_TRACEME)` in JNI_OnLoad | Native, blocks attach | Hook `ptrace` before it runs |
| APK signature verified at runtime | Detects recompilation | Hook hash comparator → `true` |
| `/proc/self/maps` searching for "frida","xposed","magisk" | String matching in memory | Native hook `strstr`/`memmem` |

**Para técnicas extendidas, Frida scripts y bypass detallado, ver sección "Anti-Debugging and Anti-Tampering (Extended)".**

## Xposed / LSPosed as a Frida Alternative

- Frida is dynamic (PC + USB/network); Xposed/LSPosed is persistent (the hook survives reboots without a PC connected).
- Useful when: the bypass must survive reboots, or Frida is detected and you need a smaller footprint (doesn't inject an external process, loads via Zygote).
- Basic structure: `IXposedHookLoadPackage` + `findAndHookMethod` on the target package, packaged as an APK and installed via LSPosed Manager.
- Limitation: requires Zygisk/LSPosed (root); Frida can run without root with `frida-gadget` embedded in the APK.

## Kotlin: Decompilation

> **Contenido completo en sección "Kotlin: Decompilation Particularities (Deep Dive)"** más abajo. Aquí el resumen rápido:

- `@Metadata` annotation — jadx usa esto para reconstruir sintaxis Kotlin. Si se elimina/ofusca, se ve como Java plano con getters/setters sintéticos.
- `Companion object` → clase interna estática (`Foo$Companion`) — buscar constantes y métodos "static" ahí.
- Coroutines (`suspend fun`) → parámetro `Continuation` + state machine (`when(label)`).
- Null-safety (`?.`, `!!`) → `Intrinsics.checkNotNull()` — ruido visual, ignorar.

**Para tabla completa de patrones, estructura smali de corrutinas y Metadata, ver sección "Kotlin: Decompilation Particularities (Deep Dive)".**

## Manifest and Permission Analysis

```bash
aapt dump badging app.apk       # package, version, permissions, SDK, exported activities
aapt dump permissions app.apk   # only declared permissions
```
- Permissions to check first: `READ_SMS`, `RECEIVE_SMS` (OTP interception), `SYSTEM_ALERT_WINDOW` (overlay), `REQUEST_INSTALL_PACKAGES`, `BIND_ACCESSIBILITY_SERVICE`.
- `android:allowBackup="true"` → `adb backup` extracts data without root (tokens, SQLite DBs, tokens SQLite, shared_prefs).
- `android:debuggable="true"` (rare in production) → `jdb`/`gdb` without root or Frida.

### Deep Link and App Link Exploitation

Deep links (`scheme://host/path`) y App Links (`http(s)://domain/path` con verificación) son un vector de ataque subestimado en apps Android.

**Enumerar declaradas:**

```bash
aapt dump xmltree app.apk AndroidManifest.xml | grep -B5 'android:scheme\|action.*VIEW\|category.*BROWSABLE'
# O más detallado:
jadx -d out/ app.apk && grep -rn 'android.intent.action.VIEW' out/resources/AndroidManifest.xml -A3 | grep 'scheme\|host\|pathPrefix'
```

**Vectores de ataque:**

| Vector | Descripción | Prueba |
|---|---|---|
| **Scheme hijacking** | Cualquier app maliciosa registra el mismo custom scheme (`myapp://callback`) y el OS lo abre en su lugar | `adb shell am start -d "myapp://login?token=XYZ"` |
| **App Links sin verificar** | `autoVerify="true"` pero `assetlinks.json` 404 o mal firmado → fallback a scheme (hijackable) | `curl https://domain/.well-known/assetlinks.json` |
| **Inyección en Intent** | `Intent.parseUri()` sin sanitización → path traversal, content:// injection | Fuzz con `"myapp://open?data=file:///..%2f..%2fdata%2fdata%2fcom.target%2fshared_prefs%2fprefs.xml"` |
| **WebView injection** | Deep link que alimenta WebView sin validar URL → Open Redirect/XSS | `"myapp://web?url=javascript:alert(1)"` |

### AIDL / Binder Exploitation

Los servicios exported sin permisos son callable desde cualquier app. Actúan como una RPC sin autenticación de caller.

**Enumerar:**

```bash
aapt dump xmltree app.apk AndroidManifest.xml | grep -E 'service.*exported.*"true"' -A3
# Verificar si tiene android:permission definido
```

**Generar cliente AIDL atacante (autorizado):**
1. Extraer el `.aidl` del APK (buscar `I*Service` implementando `IInterface`)
2. Compilar stub AIDL en un proyecto Android separado
3. `asBinder().transact(CODE, data, reply, 0)` con parcelables malformados

**Fuzzing vía adb:**
```bash
adb shell service call <service_name> <txn_code> i32 <arg>
# Saltos de control si el IBinder no valida `data.enforceInterface()`
```

### ContentProvider and DocumentProvider Path Traversal

```bash
# Providers exported sin permisos
aapt dump xmltree app.apk AndroidManifest.xml | grep -B2 'provider.*exported.*"true"'
# Path traversal via content://
adb shell content query --uri "content://com.target.files/docs/..%2f..%2f..%2fdata%2fdata%2fcom.target%2fdatabases%2f"
```

**DocumentProvider** (SAF): si `documentId` construye path sin validar `..`:
```bash
# Probar traversal en DocumentsContract
adb shell content call --uri content://com.target.documents --method openDocument \
  --arg 'primary:../../shared_prefs/target.xml'
```

## Native Libraries: Quick Identification

```bash
nm -D lib.so 2>/dev/null | grep -i "JNI_OnLoad\|Java_"
strings lib.so | grep -iE "boringssl|openssl|curl|cronet|flutter"
file lib.so
```
- Common fingerprints: `libflutter.so` (Flutter), `libcronet.so`/`libsscronet.so` (Cronet/QUIC), `libssl.so`/`libcrypto.so` (vendored OpenSSL/BoringSSL).

## Expected Output

At the end of an RE session, you must produce structured deliverables. The format depends on the **Analysis Profile** chosen at the start.

### General Deliverables

1. **Decompiled code** in the output directory (`sources/`).
2. **Architecture summary**: package structure, pattern (MVP/MVVM/Clean), Application class, exported components.
3. **API documentation**: all discovered endpoints with method, path, parameters, auth headers, and the call chain from where they are invoked.
4. **Call flow map**: key UI-to-network routes, especially login, registration, and critical functions (payments, sensitive data).
5. If dynamic analysis applies: **classified capture file** (`.flows`) + notes on which pinning/root-detection layers were bypassed and how.

### Report Template (for Pentest/MASVS Profile)

Copy and fill this template when producing a final report. Filling it demonstrates thoroughness and produces transferable, high-value output.

**Copiar plantilla desde:** `templates/MASVS-report-template.md`

#### Executive Summary
- **Target**: `com.example.app` v3.4.1 (SHA-256: `...`)
- **Scope**: Static analysis (jadx), Dynamic analysis (Frida + mitmproxy), Network intercept
- **Device**: Android 14, Magisk Alpha, KernelSU-Next
- **Summary**: N findings of which X critical, Y high. Primary categories: [MASVS-STORAGE, MASVS-NETWORK, MASVS-PLATFORM].

#### Findings Table

| ID | MASVS Category | Description | CVSS | Severity | PoC | Remediation |
|---|---|---|---|---|---|---|
| MASVS-001 | MASVS-NETWORK | OkHttp CertificatePinner pinning can be disabled at runtime via Frida (Layer 2 bypass) | 5.3 | Medium | `frida -U -f com.app -l ssl_pinning_bypass.js` | Pin on TrustManager level AND implement cert chain validation |
| MASVS-002 | MASVS-PLATFORM | Deep link `myapp://auth` exported with no validation → token hijacking | 7.5 | High | `adb shell am start -d "myapp://auth?token=XYZ"` | Add referrer validation; require user intent |
| ... | ... | ... | ... | ... | ... | ... |

#### Technical Annex
- **Network endpoints** (all captured, classified by protocol: REST/gRPC/WebSocket)
- **Call chains** (login → Activity → ViewModel → Repository → OkHttp → endpoint)
- **Frida scripts used** (with versions: Frida 17.x, mitmproxy 12.x)
- **Native analysis** (if applicable: .so functions mapped, patches applied)
- **Anti-debug/root bypass summary** (layers bypassed: which method, which script)

#### Evidence Annex
- Screenshots of decompiled classes (jadx)
- `.flows` capture files with path to critical flows
- JSON/Protobuf decoded samples (if gRPC)
- `mitmdump` command history used for capture

## Environment

- **Device:** Android 10+, ARM64, Magisk
- **ADB:** `adb` (en PATH del sistema)
- **CA:** `~/.mitmproxy/mitmproxy-ca-cert.pem`

---

## Flutter / Dart Reverse Engineering

> **Skill completo:** `flutter-reverse-engineering` — RE profundo de Flutter/Dart: libapp.so (AOT snapshot), Dart VM internals (Object Pool, compressed pointers, QK Color objects), Blutter, unflutter, flutterdec, reFlutter, Frida Gadget embedding, theme/color modification.

### Detección rápida (triage)

```bash
unzip -l app.apk | grep -i "libapp.so\|libflutter.so"
# libapp.so  → lógica Dart compilada (AOT snapshot)
# libflutter.so → Flutter engine (incluye BoringSSL para TLS)
```

### SSL Pinning en Flutter

BoringSSL está compilado dentro de `libflutter.so` — no se puede bypass con NSC ni hooks Java TrustManager.

**Opciones (ver skill dedicado para detalles):**
1. **reFlutter** — parchea el engine, reempaqueta el APK
2. **Hook nativo** — `ssl_verify_cert_chain` / `SSL_CTX_set_verify` en `libflutter.so`
3. **iptables transparent** — redirigir a mitmproxy en modo transparente

**Para análisis profundo (libapp.so, Blutter, Dart VM, Frida Gadget), cargar el skill `flutter-reverse-engineering`.**

---

## gRPC and Protobuf Analysis

gRPC es dominante en Google apps, fintech, Discord y backends modernos. El tráfico se captura en mitmproxy (HTTP/2) pero el body es Protobuf binario. **SÍ se puede analizar sin el `.proto` original.**

### Anatomía de un frame gRPC

```
[1 byte: compressed flag (00)] [4 bytes: big-endian message length] [N bytes: protobuf message]
```

El path HTTP/2 revela servicio y método: `/com.example.UserService/GetUser`.

### 1. Extraer el esquema desde el DEX (la mejor opción)

Las clases Java/Kotlin generadas por protoc están EN el APK y revelan campos, tipos y nombres:

```bash
# Clases generadas por protoc (sobreviven a ProGuard: los nombres de campo están en literales)
rg -n "extends .*GeneratedMessageLite|extends .*AbstractMessage" jadx-out/ -l | head -30

# Builders → cada campo tiene setXxx()/getXxx()
rg -n "newBuilder\(\)|getDefaultInstance\(\)" jadx-out/ | head -20

# Los FieldDescriptors serializan nombres de campo como strings → buscar en clases del servicio
rg -n '"[a-z_]+", *[0-9]+, *[A-Z]' jadx-out/ --glob "**/grpc/**" | head
```

Reconstruir el `.proto` a mano desde los getters/setters: `getUserId()` → `string user_id = N;` donde N es el field number (visible en el parser o en `internal_field_data`).

### 2. Black-box decode con protoscope

Sin esquema, Protobuf sigue siendo auto-descriptivo (field numbers + wire types):

```bash
# Extraer body de un flow de mitmproxy (saltando los 5 bytes de header gRPC)
tail -c +6 request_body.bin | protoscope
# → 1: {"user@example.com"}  2: 0x1a2b3c

# O en Python puro (script listo: scripts/extract_proto.py)
python3 scripts/extract_proto.py request_body.bin
```

Wire types: `0=varint, 1=64-bit, 2=length-delimited (string/bytes/embedded), 5=32-bit`. Con field number + tipo + valores de ejemplo, el esquema se deduce.

### 3. Hook del serializador con Frida (el más fiable)

Los mensajes pasan por `toByteArray()` al enviar y `parseFrom()` al recibir — hook universal:

```javascript
// scripts/frida_grpc_hook.js — dump de mensajes protobuf con su clase
Java.perform(function() {
    // Lite runtime (Android usa casi siempre protobuf-javalite)
    var candidates = [
        "com.google.protobuf.GeneratedMessageLite",
        "com.google.protobuf.AbstractMessageLite"
    ];
    candidates.forEach(function(cls) {
        try {
            var MsgLite = Java.use(cls);
            MsgLite.toByteArray.implementation = function() {
                var bytes = this.toByteArray();
                console.log("[Proto→] " + this.getClass().getName() +
                            " (" + bytes.length + "B): " + bytesToHex(bytes));
                return bytes;
            };
        } catch(e) {}
    });

    // Interceptar el método gRPC stub directamente (nombres sobreviven en grpc.MethodDescriptor)
    try {
        var MethodDescriptor = Java.use("io.grpc.MethodDescriptor");
        MethodDescriptor.getFullMethodName.implementation; // exists check
        Java.choose("io.grpc.MethodDescriptor", {
            onMatch: function(inst) {
                console.log("[gRPC] Method: " + inst.getFullMethodName());
            }, onComplete: function() {}
        });
    } catch(e) {}

    function bytesToHex(b) {
        var h = [];
        for (var i = 0; i < b.length; i++) h.push(("0" + (b[i] & 0xFF).toString(16)).slice(-2));
        return h.join("");
    }
});
```

### 4. Replay con grpcurl

```bash
# Con esquema reconstruido:
grpcurl -import-path . -proto user.proto -d '{"user_id":"123"}' \
  -H "authorization: Bearer $TOKEN" api.target.com:443 com.example.UserService/GetUser

# Sin TLS propio: usar el cert del dispositivo capturado o -insecure en lab
```

**Nota TLS:** gRPC sobre Android suele ir dentro de Cronet/OkHttp → los bypass de SSL de la capa correspondiente aplican igual.

---

## Unity / IL2CPP Analysis

El 60%+ de juegos Android compila C# a nativo con IL2CPP. **El smali es solo el launcher — TODA la lógica está en `libil2cpp.so`.** No pierdas tiempo en jadx más allá del manifest.

### Detección y extracción

```bash
unzip -l app.apk | grep -iE "libil2cpp.so|global-metadata.dat"
# Extraer (ojo: pueden estar en split_config.arm64_v8a.apk):
unzip -p app.apk lib/arm64-v8a/libil2cpp.so > libil2cpp.so
unzip -p app.apk assets/bin/Data/Managed/Metadata/global-metadata.dat > global-metadata.dat
```

**Verificar metadata no cifrada:** los primeros 4 bytes deben ser `AF 1B B1 FA` (magic `0xFAB11BAF`). Si no lo son → metadata cifrada, buscar la rutina de descifrado en el `.so` (hook `il2cpp_init` o memscan en runtime, ver abajo).

### Il2CppDumper — el pipeline completo

```bash
cd ~/tools/Il2CppDumper
dotnet run libil2cpp.so global-metadata.dat ./out/

# Output:
#   dump.cs        → todas las clases, campos, métodos con RVA
#   script.json    → offsets para Ghidra/IDA
#   il2cpp.h       → headers C++
```

`dump.cs` ejemplo:
```csharp
// RVA: 0x1A2B3C0 Offset: 0x1A2B3C0
public bool get_IsPremium() { }
// RVA: 0x2C4D5E0 Offset: 0x2C4D5E0
public void AddCoins(int amount) { }
```

### Importar a Ghidra con símbolos

1. Importar `libil2cpp.so` (AARCH64:LE:64:v8A), NO auto-analyze todavía
2. `Window → Script Manager → ghidra_with_struct.py` (viene con Il2CppDumper)
3. Seleccionar `script.json` → funciones renombradas con firmas reales
4. Auto-analyze después de renombrar

### Parcheo típico (autorizado)

`get_IsPremium()` → retornar true:

```
# ARM64: MOV W0, #1 ; RET
bytes: 20 00 80 52 C0 03 5F D6
```

```bash
# Script listo: scripts/il2cpp_patch.py libil2cpp.so 0x1A2B3C0
python3 scripts/il2cpp_patch.py libil2cpp.so 0x1A2B3C0 --ret1
# Verificar:
aarch64-linux-gnu-objdump -d --start-address=0x1A2B3C0 --stop-address=0x1A2B3C8 libil2cpp.so
```

**Ojo:** en el `.so` el file offset ≠ RVA si hay segmentos con align distinto. Il2CppDumper reporta ambos; usar "Offset" para parchear el fichero.

### Frida en IL2CPP

```javascript
// Hook directo por RVA (de dump.cs) — no hace falta resolver nombres
var base = Process.findModuleByName("libil2cpp.so").base;
Interceptor.attach(base.add(0x1A2B3C0), {   // get_IsPremium
    onLeave: function(retval) { retval.replace(1); }
});
Interceptor.attach(base.add(0x2C4D5E0), {   // AddCoins
    onEnter: function(args) {
        console.log("AddCoins(" + args[1].toInt32() + ")");
        args[1] = ptr(999999);  // argumentos: X0=this, X1=amount
    }
});
```

**Metadata cifrada en runtime:** si `global-metadata.dat` está cifrada, IL2CPP la descifra en memoria antes de `il2cpp_init`. Dumpear desde el proceso:

```bash
frida -U -f com.game -e '
Process.enumerateRanges({protection:"rw-",coalesce:true}).forEach(function(r){
    try {
        var magic = Memory.readU32(r.base);
        if (magic === 0xFAB11BAF) console.log("metadata @ " + r.base + " size " + r.size);
    } catch(e){}
});' 
# luego Memory.readByteArray → write a disco via send()/recv
```

**Mono (Unity antiguo):** si hay `libmono.so`, las DLLs .NET están en `assets/bin/Data/Managed/*.dll` — decompilar directamente con ILSpy/dnSpy. Mucho más fácil que IL2CPP.

**Para modding profundo de juegos (bypass de protecciones Unity, Cheat Engine, speedhack), el skill `apk-modding` cubre Unity/IL2CPP operativo.**

---

## React Native / Hermes Analysis

Apps bancarias, retail y delivery usan RN cada vez más. La lógica de negocio está en JS, no en DEX.

### Detección

```bash
unzip -l app.apk | grep -iE "index.android.bundle|libhermes.so|libreactnativejni.so"
```

### Caso 1: Bundle JS plano (debug o sin Hermes)

`assets/index.android.bundle` es JavaScript legible (minificado). Beautificar y auditar directamente:

```bash
npx js-beautify index.android.bundle > bundle.js
rg -n "fetch\(|axios|api_key|secret" bundle.js
```

### Caso 2: Hermes bytecode (producción)

Magic bytes del bundle: `c6 1f bc 03 c1 03 19 1f` (versionado — el descompilador debe coincidir con la versión de Hermes).

```bash
# Identificar versión
strings libhermes.so | grep -i "hermes" | head

# Desensamblar (hbc -> pseudo-asm)
hbcdump index.android.bundle > bundle.hbc.asm

# Decompilar a pseudo-JS
# hermes-dec (https://github.com/P1sec/hermes-dec)
python3 hbc_decompiler.py index.android.bundle bundle_decompiled.js
```

**Si la versión de Hermes no está soportada:** parchear el bundle es frágil. Alternativa dinámica: hook del bridge.

### Hook del bridge JS↔Java con Frida

Los módulos nativos expuestos a JS (`@ReactMethod`) son el attack surface real:

```javascript
Java.perform(function() {
    // Toda llamada JS→Java pasa por aquí
    var JavaMethodWrapper = Java.use("com.facebook.react.bridge.JavaMethodWrapper");
    JavaMethodWrapper.invoke.implementation = function(jsInstance, args) {
        console.log("[RN→Java] " + this.getMethod().getName());
        return this.invoke(jsInstance, args);
    };

    // Promesas JS (auth, pagos)
    var Promise = Java.use("com.facebook.react.bridge.PromiseImpl");
    Promise.resolve.implementation = function(value) {
        console.log("[RN Promise.resolve] " + value);
        return this.resolve(value);
    };
});
```

### SSL pinning en RN

La capa de red es **OkHttp nativa** (la misma que una app nativa) → aplicar los bypass estándar de las capas 1-2. El JS hereda el trust store configurado en nativo. Si usa `react-native-ssl-pinning` (fetch con `sslPinning` option), la verificación extra está en Java → buscar la clase del módulo y no-op.

### Parchear el bundle

Rebuild estático viable: `apktool b` incluye el bundle modificado si es JS plano. Con Hermes, hay que recompilar el bundle con `hermesc` de la MISMA versión — normalmente no merece la pena frente a Frida/bridge hooking.

---

## Kotlin: Decompilation Particularities (Deep Dive)

Kotlin compila a DEX estándar, pero introduce patrones que requieren interpretación específica:

### Patrones de ofuscación y compilación

| Patrón | Cómo se ve en smali | Notas |
|---|---|---|
| **lateinit** | campo sin inicializador, getter sintético | Verificar `isInitialized` antes de uso |
| **Corrutinas** | `kotlin.coroutines` + `Continuation` | State machine en smali; buscar `invokeSuspend` |
| **Companion object** | clase interna estática `$Companion` | Métodos estáticos en la clase inner |
| **Extension functions** | métodos estáticos con receptor como primer parámetro | `Lcom/example/ExtKt;->foo(LReceiver;)V` |
| **Data class** | getters/setters + `component1`, `copy`, `toString`, `hashCode`, `equals` | Generados automáticamente |
| **Sealed class** | jerarquía con subclases anidadas | Pattern matching via `instance-of` |
| **Inline functions** | cuerpo copiado en el call site | No aparece como método independiente |
| **Reified generics** | métodos sintéticos con sufijo `$default` | Reflexión bajo el capó |
| **Delegated properties** | `getValue`/`setValue` en un delegate | Buscar `kotlin.properties.ReadWriteProperty` |

### Corrutinas en smali

Las corrutinas (`suspend fun`) se compilan a state machines. El método recibe un `Continuation` y usa `when(label)` para gestionar estados:

```bash
# Buscar suspended functions
rg -n 'invokeSuspend|Continuation|kotlin/coroutines' dex*_out/

# State machine labels
rg -n 'goto/|packed-switch|sparse-switch' dex*_out/ --glob "**/*Continuation*"
```

**Estructura típica de una corrutina en smali:**
```smali
.method public static synthetic foo$suspendImpl(LContinuation;)Ljava/lang/Object;
    .registers 4
    instance-of v0, p1, Lcom/example/Foo$foo$1;  # ¿es reanudación?
    if-eqz v0, :new_call
    # ... reanudación: restaurar estado del Continuation
    goto :switch
:new_call:
    # ... primera llamada: inicializar
:switch:
    packed-switch v_label, :pswitch_data
    :pswitch_0  # estado 0: antes del primer suspend
    # ...
    :pswitch_1  # estado 1: después del primer suspend
    # ...
:pswitch_data:
    .packed-switch 0x0
        :pswitch_0
        :pswitch_1
    .end packed-switch
.end method
```

### Metadata de Kotlin

- `@Metadata` annotation — jadx la usa para reconstruir sintaxis tipo Kotlin. Si se elimina/ofusca, muestra Java plano con getters/setters sintéticos.
- `kotlinx-metadata-jvm` (`Kotlin/kotlinx-metadata-jvm`) — librería para leer metadata de Kotlin en JVM programáticamente.

---

## Deobfuscation Techniques

### Identificación del ofuscador

| Ofuscador | Patrón | Detección |
|---|---|---|
| **ProGuard / R8** | nombres de 1-2 letras (a, b, o0O0) | `rg -c '\b[a-z]\b' jadx-out/` |
| **StringFog** | strings codificadas, decrypt en clinit | `rg -n 'StringFog\|encrypt\|decrypt' jadx-out/` |
| **DexGuard** | strings en assets, reflexión masiva, encrypt de clases | `rg -n 'DexGuard\|com.secure' jadx-out/` |
| **Allatori** | nombres con Unicode, strings en resources | `rg -n '\\u00' jadx-out/` |
| **DashO** | ofuscación de control flow | Análisis de CFG en smali |
| **Stringer** | strings en nativo | `strings lib*.so \| grep -i decrypt` |

### Estrategia de desofuscación

1. **Identificar el ofuscador**: buscar marcas en manifest, strings, imports.
2. **Localizar decrypt de strings**: buscar `clinit`, `decrypt(`, `decode(`, `xor`.
3. **Renombrar clases con significado**: partir de entrypoints (Activity, Application) y propagar.
4. **Reconstruir CFG**: usar simplify o dex-oracle para simplificar saltos.
5. **Extraer strings dinámicamente**: Frida hook de `String.<init>` o `decrypt`.
6. **Mapear reflexión**: hook `Class.forName`, `getDeclaredMethod`, `invoke`.

### Desofuscación dinámica con Frida

```javascript
// Hook String constructor para capturar strings desencriptados en runtime
Java.perform(function() {
    var String = Java.use("java.lang.String");
    String.$init.overload("[B", "java.lang.String").implementation = function(bytes, charset) {
        var result = this.$init(bytes, charset);
        var str = this.toString();
        if (str.length > 5 && str.length < 200) {
            // Filtrar strings interesantes
            if (/api|http|key|token|secret|password|url/i.test(str)) {
                console.log("[String] " + str);
            }
        }
        return result;
    };
});

// Hook reflexión para mapear llamadas dinámicas
Java.perform(function() {
    var Class = Java.use("java.lang.Class");
    Class.forName.implementation = function(name) {
        console.log("[forName] " + name);
        return this.forName(name);
    };

    var Method = Java.use("java.lang.reflect.Method");
    Method.invoke.overload("java.lang.Object", "[Ljava.lang.Object;").implementation = function(obj, args) {
        console.log("[invoke] " + this.getName());
        return this.invoke(obj, args);
    };
});
```

### mapping.txt (ProGuard)

Si se encuentra `mapping.txt` en el APK/assets, revierte el renombrado de ProGuard automáticamente. Siempre buscarlo antes de decompilar manualmente:

```bash
find . -name "mapping.txt" 2>/dev/null
unzip -l app.apk | grep -i mapping
```

---

## Cryptoanalysis

### Detección de uso criptográfico

```bash
# Buscar uso de cifrado
rg -n 'Cipher;->getInstance|SecretKeySpec|KeyGenerator|MessageDigest' dex*_out/

# Algoritmos débiles
rg -n '"AES/ECB|"DES|"MD5|"SHA1"' dex*_out/

# Hardcoded keys
rg -n 'SecretKeySpec\([^)]+"\)' jadx-out/
rg -n 'byte\[\].*=.*0x[0-9a-f]{2}' jadx-out/ | head -50

# Keystore
rg -n 'AndroidKeyStore|KeyStore.getInstance' dex*_out/
```

### Hook de cifrado con Frida

```javascript
// hook_crypto.js - Intercepta operaciones de cifrado/descifrado
Java.perform(function() {
    var Cipher = Java.use("javax.crypto.Cipher");

    Cipher.doFinal.overload("[B").implementation = function(input) {
        var mode = this.getAlgorithm();
        var op = this.getOpmode ? this.getOpmode() : "?";
        console.log("[Cipher] Algorithm: " + mode + " Op: " + op);
        console.log("[Cipher] Input (" + input.length + "): " + bytesToHex(input));

        var result = this.doFinal(input);
        console.log("[Cipher] Output (" + result.length + "): " + bytesToHex(result));
        return result;
    };

    // Hook Mac (HMAC)
    var Mac = Java.use("javax.crypto.Mac");
    Mac.doFinal.overload("[B").implementation = function(input) {
        console.log("[HMAC] Algorithm: " + this.getAlgorithm());
        console.log("[HMAC] Input: " + bytesToHex(input));
        var result = this.doFinal(input);
        console.log("[HMAC] Output: " + bytesToHex(result));
        return result;
    };

    // Hook MessageDigest (hash)
    var MD = Java.use("java.security.MessageDigest");
    MD.digest.overload("[B").implementation = function(input) {
        console.log("[Hash] Algorithm: " + this.getAlgorithm());
        console.log("[Hash] Input: " + bytesToHex(input));
        var result = this.digest(input);
        console.log("[Hash] Output: " + bytesToHex(result));
        return result;
    };

    function bytesToHex(bytes) {
        var hex = [];
        for (var i = 0; i < bytes.length; i++) {
            hex.push(("0" + (bytes[i] & 0xFF).toString(16)).slice(-2));
        }
        return hex.join("");
    }
});
```

### Almacenamiento de claves

| Mecanismo | Dónde buscar | Notas |
|---|---|---|
| **SharedPreferences** | `/data/data/<pkg>/shared_prefs/` | XML en claro por defecto. |
| **SQLite** | `/data/data/<pkg>/databases/` | `sqlite3 db.sqlite .dump` |
| **EncryptedSharedPreferences** | Jetpack Security | Clave en Keystore + AES-256-GCM. |
| **Realm** | `/data/data/<pkg>/files/` | Formato binario propio. |
| **Room** | SQLite subyacente | Igual que SQLite. |
| **Flutter SecureStorage** | `FlutterSecureStorage` | Usa EncryptedSharedPreferences en Android. |
| **Keystore** | Hardware-backed | No extraíble; hook de `getKey` para interceptar. |

### Detección de claves hardcoded

```bash
# Buscar patrones de clave en código decompilado
rg -n 'SecretKeySpec\(' jadx-out/
rg -n 'byte\[\].*=.*\{.*0x[0-9a-f]{2}.*\}' jadx-out/
rg -n 'AES\.ECB|DES\.|RC4|Blowfish' jadx-out/

# Buscar en strings nativos
strings lib/*.so | grep -iE 'key|secret|password|token|api_key'
```

---

## PairipCore and Dex2C Analysis

### PairipCore

PairipCore (`libpairipcore.so`) es una librería de verificación de licencia de Google Play que encripta strings de la app en un vault y valida la firma del APK contra Play Store.

**Detección:**
```bash
unzip -p app.apk classes*.dex | strings -a | grep -c "pairip"
unzip -l app.apk | grep -i "pairipcore"
```

**Cómo funciona:**
```
Application.attachBaseContext()
  → VMRunner.setContext(Context)        # Native VM init
  → SignatureCheck.verifyIntegrity(Context)  # APK signature check
  → VMRunner.invoke(id, args)          # Encrypted string decryption
      → libpairipcore.so               # Native VM execution
```

`VMRunner.invoke(String, Object[])` es la API central — se llama desde cientos de sitios para desencriptar strings en runtime.

**Análisis RE (autorizado):**
- Hook `VMRunner.invoke` con Frida para capturar strings desencriptados.
- NO neutralizar `VMRunner.invoke` ni `VMRunner.setContext` — la app depende de ellos.
- Si solo hay verificación de licencia: neutralizar `SignatureCheck.verifyIntegrity` → `return-void`.

### Dex2C / VM Shells

Algunos modders y protectores comerciales traducen DEX bytecode a código nativo ARM64 dentro de un `.so`. La lógica original corre dentro de una VM nativa — **invisible al análisis estático de smali**.

**Detección:**
```bash
# Marcadores Dex2C/VM shell
unzip -p app.apk classes*.dex | strings -a | grep -iE "YJ-Dex2C|yjaq\.xyz|libstub|libcxapkmod|protected_by_np"

# DEX vacío o mínimo
unzip -l app.apk | grep "classes.*\.dex"
# Si classes.dex es muy pequeño y hay libstub.so → Dex2C

# Verificar DEX cifrado
unzip -l app.apk | grep "classes0.jar\|classes\.jar"
```

**Marcadores de modders con VM shell:**

| Modder | Firma | Archivos clave | ¿Parcheable estático? |
|---|---|---|---|
| **zhou45** | `libstub.so` + `assets/protected_by_np` | `assets/classes0.jar` | ❌ No |
| **辰夕** | `libcxapkmod.so` + `assets/cxapkDex/*.Epic` | VM nativa | ❌ No |
| **幻幻喵** | `libmiaomiaohuan.so` + prefijo `miaomiaohuan0` | Hook nativo | ❌ No |

**Enfoque de análisis (autorizado):**
- Análisis dinámico con Frida (hook de la VM o de funciones específicas).
- Análisis del `.so` con Ghidra/radare2 para entender la VM.
- En casos extremos, emulación con unicorn para ejecutar la VM offline.

---

## Play Integrity and SafetyNet Analysis

### SafetyNet Attestation (Legacy)

```bash
# Buscar uso de SafetyNet en código
rg -n 'SafetyNetApi\|attest\|com.google.android.gms.safetynet' dex*_out/
```

**API flow:**
```
SafetyNet.getClient(context).attest(nonce, API_KEY)
  → Google Play Services
  → Response: JWS (JSON Web Signature) con:
    - ctsProfileMatch: true/false (Certified Trusted Services)
    - basicIntegrity: true/false
    - evaluationType: "BASIC" | "HARDWARE_BACKED"
```

### Play Integrity API (2023+)

Reemplaza SafetyNet. Devuelve tokens JWT firmados por Google.

```bash
# Buscar uso de Play Integrity
rg -n 'PlayIntegrityApi\|IntegrityTokenRequest\|IntegrityTokenResponse\|IntegrityManager' dex*_out/
```

**Tipos de verificación (2026):**
- **App Integrity**: ¿La app está modificada? (hash del certificado de firma)
- **Device Integrity**: ¿El dispositivo es genuine? (MEETS_DEVICE_INTEGRITY, MEETS_STRONG_INTEGRITY, MEETS_VIRTUAL_INTEGRITY)
- **Account Details**: ¿La cuenta de Google está vinculada? (appLicense)

**Análisis en laboratorio (autorizado):**
- Hook `IntegrityTokenResponse` con Frida para inspeccionar tokens.
- Análisis de respuesta server-side (el token está firmado por Google, no se puede falsificar).
- Bypass de Play Integrity en producción viola ToS de Google Play.

### Play Integrity API 2026 — Current State

As of 2026, Play Integrity API responses are cryptographically signed by Google and cannot be forged client-side. The only reliable ways to influence the verdict are:

1. **Hide root/modifications** so the device passes `MEETS_DEVICE_INTEGRITY` / `MEETS_STRONG_INTEGRITY`.
2. **Use a valid keybox** with TrickyStore to pass hardware-backed attestation on devices that support it.
3. **Server-side manipulation** (if you control the backend): accept weaker verdicts or skip attestation.

**What does NOT work:**
- Patching Google Play Services to return fake verdicts (signature verification fails server-side).
- Replaying old tokens (nonces and timestamps are validated).
- Static modification of the APK's Play Integrity call site (the token is still signed by Google).

**Client-side inspection with Frida:**
```javascript
Java.perform(function() {
    var IntegrityTokenResponse = Java.use("com.google.android.gms.tasks.zzw");
    // Class name may vary; search for IntegrityTokenResponse in jadx
    Java.choose("com.google.android.play.core.integrity.IntegrityTokenResponse", {
        onMatch: function(instance) {
            console.log("[PI] Token: " + instance.token().value);
        },
        onComplete: function() {}
    });
});
```

### Root Detection Bypass (Frida)

```javascript
// root_bypass.js - Bypass de detección de root
Java.perform(function() {
    // Bypass RootBeer library
    try {
        var RootBeer = Java.use("com.scottyab.rootbeer.RootBeer");
        RootBeer.isRooted.implementation = function() {
            console.log("[RootBeer] isRooted() bypassed");
            return false;
        };
    } catch(e) {}

    // Bypass generic file-based root checks
    var File = Java.use("java.io.File");
    var originalExists = File.exists;
    File.exists.implementation = function() {
        var path = this.getAbsolutePath();
        var rootPaths = ["/system/app/Superuser.apk", "/system/xbin/su",
                         "/sbin/su", "/system/bin/su", "/data/local/bin/su",
                         "/data/local/tmp/frida-server", "/sbin/.magisk"];
        if (rootPaths.indexOf(path) >= 0) {
            console.log("[Root] Blocked check for: " + path);
            return false;
        }
        return originalExists.call(this);
    };

    // Bypass Runtime.exec("su")
    var Runtime = Java.use("java.lang.Runtime");
    Runtime.exec.overload("java.lang.String").implementation = function(cmd) {
        if (cmd.indexOf("su") >= 0) {
            console.log("[Root] Blocked exec: " + cmd);
            throw Java.use("java.io.IOException").$new("Command not found");
        }
        return this.exec(cmd);
    };

    // Bypass Build.TAGS check
    var Build = Java.use("android.os.Build");
    Build.TAGS.value = "release-keys";

    // Bypass Debug.isDebuggerConnected
    var Debug = Java.use("android.os.Debug");
    Debug.isDebuggerConnected.implementation = function() {
        return false;
    };
});
```

---

## Anti-Debugging and Anti-Tampering (Extended)

### Técnicas anti-debug nativas

| Técnica | Detección | Bypass |
|---|---|---|
| `ptrace(PTRACE_TRACEME)` en JNI_OnLoad | Native, bloquea attach | Hook `ptrace` antes de que ejecute |
| `/proc/self/status` TracerPid != 0 | Native, lee /proc | Hook `open`/`fopen` para filtrar `/proc/self/status` |
| `/proc/self/maps` buscando "frida","xposed","magisk" | String matching en memoria | Hook `strstr`/`memmem` nativo |
| Timing checks (`nanoTime()` entre instrucciones) | Detecta breakpoints | Hook clock o skip block |
| APK signature verified at runtime | Detecta recompilación | Hook hash comparator → `true` |
| DEX integrity hash en .so | Hash de classes.dex en nativo | Patch del memcmp o actualizar hash |

**Scripts de bypass:** Ver sección "Frida Detection and Evasion" más arriba (strstr, fopen, ptrace hooks).

---

## OWASP MASTG / MASVS Reference

### OWASP MASTG (Mobile Application Security Testing Guide)

Guía completa para pentesting de apps móviles (Android + iOS).

**Estructura:**
- **MASTG-TEST-XXXX**: Tests específicos por categoría
- **MASVS-XXXX**: Requisitos de verificación (L1, L2)

### Categorías MASVS

| Categoría | ID | Descripción |
|---|---|---|
| **Storage** | MASVS-STORAGE | Almacenamiento seguro de datos |
| **Crypto** | MASVS-CRYPTO | Uso correcto de criptografía |
| **Auth** | MASVS-AUTH | Autenticación y gestión de sesiones |
| **Network** | MASVS-NETWORK | Comunicación de red segura |
| **Platform** | MASVS-PLATFORM | Interacción con la plataforma |
| **Code** | MASVS-CODE | Protección del código (anti-tamper) |
| **Resilience** | MASVS-RESILIENCE | Resistencia a ingeniería inversa |

### Niveles MASVS

| Nivel | Descripción | Requisitos |
|---|---|---|
| **L1** | Verificación básica | Tests estáticos + dinámicos estándar |
| **L2** | Verificación avanzada | Defensa en profundidad, anti-tamper |
| **R** | Resilience | Anti-RE, anti-tamper, anti-debug |

### Apps vulnerables intencionalmente (práctica legal)

| App | Repo | Nivel |
|---|---|---|
| **OWASP UnCrackable Apps** | `OWASP/owasp-mstg` (Crackmes) | L1 (Java), L2 (native), L3 (native+obfuscation), L4 (Flutter), L5 (Kotlin) |
| **DVIA-v2** | `prateek147/DVIA-v2` | iOS |
| **InsecureBankv2** | `dineshshetty/Android-InsecureBankv2` | App bancaria vulnerable |
| **Sieve** | `OWASP/owasp-mstg` | App de ejemplo |
| **DIVA-Android** | `exploit-db/DIVA` | Diverse Insecure Vulnerable App |

---

## MobSF (Mobile Security Framework) — Automated Analysis

```bash
# Desplegar MobSF via Docker
docker run -it --rm -p 8000:8000 opensecurity/mobile-security-framework-mobsf:latest

# Upload APK via REST API
curl -F "file=@target_app.apk" http://localhost:8000/api/v1/upload \
  -H "Authorization: <API_KEY>"

# Trigger scan
curl -X POST http://localhost:8000/api/v1/scan \
  -H "Authorization: <API_KEY>" \
  -d "scan_type=apk&file_name=target_app.apk&hash=<FILE_HASH>"

# Retrieve JSON report
curl -X POST http://localhost:8000/api/v1/report_json \
  -H "Authorization: <API_KEY>" \
  -d "hash=<FILE_HASH>" -o report.json

# PDF report
curl -X POST http://localhost:8000/api/v1/download_pdf \
  -H "Authorization: <API_KEY>" \
  -d "hash=<FILE_HASH>" -o report.pdf
```

**Cobertura de MobSF:**
- **Manifest**: exported components, debuggable, allowBackup, networkSecurityConfig
- **Code**: hardcoded secrets, insecure SharedPreferences, weak crypto
- **Network**: missing pinning, custom TrustManagers, cleartext traffic
- **Binary**: ProGuard/R8, native lib vulnerabilities (checksec)

**Limitaciones:**
- MobSF analiza Java/Kotlin pero tiene cobertura limitada de nativo (.so).
- Falsos positivos en patrones como `password` en nombres de variables.
- Precisión baja contra apps ofuscadas (DexGuard, custom packers).

---

## Ghidra for ARM64 Native Analysis

> **Skill completo:** `ghidra-pyghidra` — análisis headless, scripting Python con API de Ghidra, decompilación automatizada, gestión de proyectos.

### Workflow Android ARM64

```bash
# 1. Extraer .so
unzip -p app.apk lib/arm64-v8a/libnative.so > libnative.so

# 2. Símbolos y strings
readelf -Ws libnative.so > symbols.txt
strings -a libnative.so > strings.txt
rabin2 -zz libnative.so > r2_strings.txt

# 3. Ghidra headless
/opt/ghidra/support/analyzeHeadless /tmp ghidra_proj -import libnative.so \
  -postScript DecompileAll.java -scriptPath /opt/ghidra/Ghidra/Features/Decompiler/

# 4. pyghidra para scripting Python nativo
python3 -c "
import pyghidra
with pyghidra.open_program('libnative.so') as prog:
    fm = prog.getFunctionManager()
    for func in fm.getFunctions(True):
        print(f'{func.getName()} @ {func.getEntryPoint()}')
"
```

### Ghidra GUI — Trazado de abort()

```
1. File → Import → libnative.so (AARCH64:LE:64:v8A, auto-analyze)
2. Symbol Tree → search "abort" → References → Show References To
3. Buscar funciones que llaman abort() condicionalmente:
   if (!check()) { abort(); }
   if (memcmp(h1, h2, 32)) { abort(); }
4. Decompiler (F4) → trazar hacia atrás desde la condición
5. Search → Program Text → SHA, digest, checksum, memcmp, classes.dex
6. Patch Instruction:
   CBNZ X0, fail  →  NOP
   B fail         →  NOP
   BL check       →  MOV W0, #1
7. File → Export Program → patched.so
```

### Atajos de Ghidra

```
G         - Go to address
Ctrl+E    - Search for strings
X         - Show cross-references
Ctrl+Shift+F - Search memory for byte patterns
L         - Rename label/function
;         - Add comment
T         - Retype variable
Ctrl+L    - Retype return value
```

### FindCrypt (Ghidra Plugin)

Identifica constantes criptográficas: AES S-box, CRC32 table, MD5 init values, SHA-256 constants.

**Para scripting avanzado con pyghidra, cargar el skill `ghidra-pyghidra`.**

---

## Frida Advanced Techniques

> **Skill completo:** `frida-expert` — CModule (hooks nativos en C), Memory scanning, DexClassLoader hook, Anti-suicide hooks, y más. Ver secciones correspondientes en el skill dedicado.

---

## Toolbox Reference

Herramientas por fase (ver también las tablas en Prerequisites y Learning References):

| Fase | Principal | Alternativas |
|---|---|---|
| Triage | jadx 1.5.1, apktool 2.7.0, aapt | unzip, strings, aapt2 |
| Java | jadx-gui, grep, Vineflower | MobSF, AndroGuard |
| Dynamic | Frida 17.15.3, Objection 1.12.5 | Medusa, Auto-Frida |
| Network | HTTP Toolkit, mitmdump 12.x, tcpdump | Burp, Wireshark |
| Native | Ghidra 12.x, radare2 6.1.9 | IDA Pro, Il2CppDumper |
| Flutter | reFlutter, iptables | kill_flutter (dynamic offset) |
| Root | Magisk, KernelSU, KernelSU-Next | TrickyStore, Shamiko, HMA-OSS |
| Stealth | fridare, phantom-frida | renef (memfd, no ptrace) |

---

## Skills relacionados

> **Workflow recomendado:** usar `android-reverse-engineering` para triaje y análisis, luego `apk-modding` para implementar parches persistentes en smali/nativo.

- **`android-pentesting-checklist`** — Checklist estructurado estatico + dinamico + tecnicas avanzadas (AIDL/Binder, App Links, dual-signing, LSPosed, Unity RCE).
- **`android-ctf-writeups`** — 13 tecnicas practicas de CTFs reales (NativeFunction, stub .so, strcmp hook, WebView XSS, crypto detection).
- **`hacktricks-reference`** — Indice ligero de enlaces externos (HackTricks Wiki, bi0s, Flutter RE, laboratorios, cursos).
- **`frida-expert`** — Cookbook completo de Frida para Android: SSL pinning (14 librerias), root bypass (5 vectores), anti-Frida, crypto intercept, OkHttp3 interceptor, native connect hook, Flutter BoringSSL, CModule, memory scanning. Usar como referencia principal para instrumentacion dinamica.
- **`apk-modding`** — Playbook operativo para modificar, parchear y hackear APKs (smali patching, signature killers, PairipCore bypass, Frida Gadget, Unity/IL2CPP). Usar cuando el objetivo sea modificar el comportamiento de la app, no solo analizarla.
- **`flutter-reverse-engineering`** — RE profundo de Flutter/Dart (libapp.so, Dart VM internals, blutter, reFlutter, BoringSSL hooking, theme/color modification). Usar cuando el APK sea Flutter y se necesite análisis profundo más allá del triaje.
- **`ghidra-pyghidra`** — Ghidra + pyghidra como herramienta (análisis headless, scripting Python con API de Ghidra, decompilación automatizada). Usar para scripting pyghidra y análisis headless automatizado.
- **`httptoolkit-android`** — HTTP Toolkit en Android (mecanismo de interceptación VPN + Magisk tmpfs cert, troubleshooting, root vs non-root). Usar para captura de tráfico cuando Frida no sea necesario.
- **`android-cleanup`** — Limpieza de dispositivo Android post-pentesting (proxy global, iptables NAT, bind mounts, CA certificates, Frida Gadget, Magisk bypass modules, SELinux). Usar después de sesiones de dynamic analysis.

---

## Changelog

- **2026-07-21 (v5 — Restructuring as Router)**:
  - **Delegación a skills especializados**: Frida Cookbook (~120 líneas de snippets), Flutter summary (~35 líneas), Ghidra workflow (~75 líneas), Frida Advanced Techniques (~80 líneas) reemplazados por tablas resumen + links a `frida-expert`, `flutter-reverse-engineering`, `ghidra-pyghidra`.
  - **Duplicados eliminados**: Kotlin brief (6 líneas) y Anti-Debugging brief (10 líneas) reemplazados por cross-refs a sus respectivas secciones deep dive. Scripts anti-Frida duplicados (Anti-Debugging Extended) eliminados.
  - **Bugs corregidos**: `fopen` hook anti-Frida implementado (estaba solo comentarios). Referencia muerta a `reports/android-re-toolbox.md` reemplazada por tabla inline. Paths hardcodeados `/home/usuario/` corregidos a genéricos.
  - **Contradicciones resueltas**: iptables DNAT prohibido VS usado para QUIC (nota aclaratoria añadida). `Runtime.exec` unificado a `throw IOException`.
  - **Reducción total**: 2065 → 1847 líneas (-10.6%).
  - **Frameworks modernos**: gRPC/Protobuf análisis completo (extracción de .proto desde DEX, decode black-box con protoscope/script, hook Frida, grpcurl replay), Unity/IL2CPP (pipeline Il2CppDumper + Ghidra, patch ARM64, metadata cifrada), React Native/Hermes (detección, descompilación hbc, bridge hook).
  - **Attack surface extension**: Deep Links/App Links hijacking, AIDL/Binder exploitation, ContentProvider/DocumentProvider path traversal.
  - **AAB/App Bundle**: conversión a APK universal, módulos dinámicos, bundletool.
  - **Frida detection/evasion**: árbol de decisión por 9 métodos de detección, estrategia de evasión escalonada (renombrar → port random → maps evasion → gadget → LSPosed).
  - **Analysis Profiles**: pentest / modding / malware / api-mapping.
  - **Report Template**: plantilla MASVS con tabla de findings, anexos técnicos y de evidencia.
  - **Scripts/ operativos**: `triage.sh` (one-shot APK framework detection), `extract_splits.sh` (pull de dispositivo), `extract_proto.py` (decode protobuf black-box), `il2cpp_patch.py` (patch .so por RVA).
  - **Setup environment**: instalación completa de tools cero desde Debian/Ubuntu.
  - **Top 18 → Top 20 Errors**: añadidos "AAB decompila a vacío" y "Anti-Frida crash".
  - **Correcciones**: bloque de código huérfano eliminado, backticks balanceados en tablas.
- 2026-07-19 (v3): Actualizacion 2026: prerrequisitos con versiones de herramientas, captura de trafico QUIC/HTTP3 y mTLS, bypass de client certificate pinning, root hiding moderno (KernelSU-Next, Zygisk Next, TrickyStore, PIF), estado actual de Play Integrity API 2026, cookbook Frida mejorado con bypass de root, tabla de herramientas actualizada, Top 18 errores, referencias cruzadas a `apk-modding`, `frida-expert` y `hacktricks-reference`.
- 2026-07-18 (v2): Ampliación con Flutter/Dart RE (referencia cruzada a skill dedicado), Kotlin deep dive, desofuscación, criptoanálisis, PairipCore/Dex2C, Play Integrity/SafetyNet, anti-debugging extendido, OWASP MASTG/MASVS, MobSF automation, Ghidra ARM64 workflow (referencia cruzada a skill dedicado + pyghidra), Frida advanced (CModule, memory scan, DexClassLoader, anti-suicide), toolbox reference, referencias cruzadas a skills relacionados.
