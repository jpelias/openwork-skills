# Android RE & Security Toolbox — Curaduría de recursos públicos

> **Alcance:** Herramientas y recursos públicos para investigación de seguridad, auditoría de aplicaciones propias y pruebas autorizadas. Todo uso fuera de ese alcance es responsabilidad exclusiva del usuario.
>
> **Fecha de compilación:** 2026-07-18. Conteos de estrellas son aproximados y cambian con el tiempo.

---

## 0. Índice

1. [Estática — Decompiladores y desensambladores](#1-estática--decompiladores-y-desensambladores)
2. [Smali / DEX / Bytecode](#2-smali--dex--bytecode)
3. [Dinámica — Frida, Objection, instrumentación](#3-dinámica--frida-objection-instrumentación)
4. [Nativo ARM64 — Ghidra, radare2, binutils](#4-nativo-arm64--ghidra-radare2-binutils)
5. [Flutter / Dart](#5-flutter--dart)
6. [Kotlin específico](#6-kotlin-específico)
7. [Red y tráfico — Proxy, TLS, SSL pinning](#7-red-y-tráfico--proxy-tls-ssl-pinning)
8. [Desofuscación y análisis de strings](#8-desofuscación-y-análisis-de-strings)
9. [Anti-tamper y bypass de protecciones (autorizado)](#9-anti-tamper-y-bypass-de-protecciones-autorizado)
10. [Criptografía y almacenamiento de claves](#10-criptografía-y-almacenamiento-de-claves)
11. [Empaquetado, firma y bundles](#11-empaquetado-firma-y-bundles)
12. [Detección de root / SafetyNet / Play Integrity](#12-detección-de-root--safetynet--play-integrity)
13. [Automatización y pipelines](#13-automatización-y-pipelines)
14. [Recursos formativos — MSTG, MASVS, CTFs](#14-recursos-formativos--mstg-masvs-ctfs)
15. [Awesome lists y comunidades](#15-awesome-lists-y-comunidades)
16. [Comandos rápidos de referencia](#16-comandos-rápidos-de-referencia)

---

## 1. Estática — Decompiladores y desensambladores

| Herramienta | Repo / URL | Lenguaje | Uso principal |
|---|---|---|---|
| **jadx** | `skylot/jadx` | Java | Decompilador DEX→Java más usado. CLI + GUI. Soporta plugins. |
| **jadx-gui** | (incluido en jadx) | — | GUI con árbol de clases, búsqueda, resaltado. |
| **Vineflower** | `Vineflower/vineflower` | Java | Fork moderno de jadx con mejor rendimiento y UI. |
| **apktool** | `iBotPeaches/Apktool` | Java | Decodifica/reconstruye recursos + smali. Esencial para manifest y XML. |
| **baksmali / smali** | `google/smali` | Java | Disassemble/assemble DEX con control fino. |
| **dexlib2** | (incluido en apktool) | Java | Librería para leer/escribir DEX programáticamente. |
| **aapt / aapt2** | Android SDK | C++ | Inspección de manifest, badging, recursos. |
| **androguard** | `androguard/androguard` | Python | Análisis estático de APK: permisos, clases, strings, firma. v4.x. |
| **APKInspector** | `hussien89mm/APKInspector` | Python | GUI para explorar estructura de APK. |
| **apkleaks** | `dxa9098/apkleaks` | Go | Escaneo de URIs, keys y secretos en APK. |
| **MobSF** | `MobSF/Mobile-Security-Framework-MobSF` | Python | Framework completo: estática + dinámica + API. Web UI. |
| **Quark Engine** | `quark-engine/quark-engine` | Python | Análisis de malware Android con reglas. |
| **DroidDetective** | `dxa9098/DroidDetective` | Python | Análisis rápido de APK para detectar comportamientos. |

### Comandos clave

```bash
# Decompilación completa
jadx -d jadx-out/ --no-res app.apk
jadx -d jadx-out/ --show-bad-code app.apk   # incluir código decompilado con errores

# Solo recursos
apktool d app.apk -o apktool-out/

# Badging y permisos
aapt dump badging app.apk
aapt2 dump packagename app.apk

# Inspección de DEX con androguard
androguard analyze app.apk
```

---

## 2. Smali / DEX / Bytecode

| Herramienta | Repo | Uso |
|---|---|---|
| **smali** | `google/smali` | Ensamblar smali → DEX |
| **baksmali** | `google/smali` | Desensamblar DEX → smali |
| **dexdump** | Android SDK | Volcado de DEX con encabezados |
| **dex2jar** | `pxb1988/dex2jar` | DEX → JAR (para JD-GUI u otros) |
| **enjarify** | `google/enjarify` | DEX → JAR, mejor que dex2jar en casos complejos |
| **simplify** | `celzero/reftool` | Simplificación de bytecode (deobfuscation) |
| **dex-oracle** | `CalebFenton/dex-oracle` | Optimización de bytecode por interpretación parcial |
| **deguard** | `pxb1988/deguard` | Recuperación de nombres de clases ofuscadas con ProGuard |

### Patrones de búsqueda en smali

```bash
# SharedPreferences keys
rg -n '"premium"|"noads"|"pro"|"max_' dex*_out/ --glob "**/*.smali"

# Billing / IAP
rg -n 'BillingClient|startPurchase|queryPurchases|getPurchase' dex*_out/

# Cifrado
rg -n 'Cipher;->getInstance|SecretKeySpec|MessageDigest' dex*_out/

# Reflexión
rg -n 'java/lang/reflect/Method|getDeclaredMethod|invoke(' dex*_out/
```

---

## 3. Dinámica — Frida, Objection, instrumentación

| Herramienta | Repo | Uso |
|---|---|---|
| **Frida** | `frida/frida` | Instrumentación dinámica multiplataforma. Core en C, bindings JS/Python. |
| **frida-tools** | `frida/frida-tools` | CLI: frida, frida-trace, frida-ps, frida-kill |
| **Objection** | `sensepost/objection` | Wrapper de Frida para exploración runtime sin escribir scripts. |
| **Frida CodeShare** | `frida/frida-codeshare` | Repositorio de scripts compartidos. |
| **frida-gadget** | (incluido en frida) | Para embeber Frida en APK redistribuible (sin root). |
| **House** | `nccgroup/house` | GUI web para Frida. |
| **Brida** | `federicodotta/Brida` | Bridge Frida ↔ Burp Suite. |
| **r2frida** | `frida/r2frida` | Integración radare2 + Frida. |
| **Dexcalibur** | `FrenchYeti/dexcalibur` | Instrumentación automática de DEX con Frida. |

### Scripts Frida de referencia (públicos)

```bash
# Listar procesos
frida-ps -U

# Attach a app corriendo
frida -U -f com.example.app -l hook.js --no-pause

# Trace de llamadas a métodos
frida-trace -U -f com.example.app -j '*!*onCreate*'
```

**Patrones de hook comunes (laboratorio autorizado):**

```javascript
// Hook genérico de método
Java.perform(function() {
    var cls = Java.use("com.example.License");
    cls.isPremium.implementation = function() {
        console.log("[+] isPremium called, returning true");
        return true;
    };
});

// Hook de SharedPreferences.getBoolean
Java.perform(function() {
    var SP = Java.use("android.content.SharedPreferences");
    // Nota: SharedPreferences es interfaz; hook en la implementación real
});
```

---

## 4. Nativo ARM64 — Ghidra, radare2, binutils

| Herramienta | Repo / URL | Uso |
|---|---|---|
| **Ghidra** | `NationalSecurityAgency/ghidra` | Decompilación + análisis ARM64. Headless + GUI. |
| **radare2** | `radareorg/radare2` | Disasm, hex patch, scripting. CLI. |
| **rizin** | `rizinorg/rizin` | Fork de radare2 con licencia LGPL. |
| **Cutter** | `rizinorg/cutter` | GUI para rizin/radare2. |
| **IDA Free** | `hex-rays.com` | Versión gratuita de IDA Pro (ARM64 limitado). |
| **binutils** | GNU | readelf, objdump, strings, nm, addr2line. |
| **pyelftools** | `eliben/pyelftools` | Análisis ELF en Python. |
| **capstone** | `aquynh/capstone` | Disassembler framework (C/Python). |
| **keystone** | `keystone-engine/keystone` | Assembler framework (para patching). |
| **unicorn** | `unicorn-engine/unicorn` | Emulador de CPU para análisis dinámico de .so. |
| **angr** | `angr/angr` | Análisis simbólico y ejecución simbólica. |
| **r2frida** | `frida/r2frida` | radare2 + Frida combinados. |

### Flujo de análisis nativo

```bash
# Extraer .so
unzip -p app.apk lib/arm64-v8a/libnative.so > libnative.so

# Símbolos y strings
readelf -Ws libnative.so > symbols.txt
strings -a libnative.so > strings.txt
rabin2 -zz libnative.so > r2_strings.txt

# Abrir en radare2
r2 -A libnative.so
# > afl              # listar funciones
# > s sym.JNI_OnLoad  # saltar a JNI_OnLoad
# > pdf              # desensamblar función
# > iz~sign          # buscar strings con "sign"

# Ghidra headless
/opt/ghidra/support/analyzeHeadless /tmp ghidra_proj -import libnative.so -postScript DecompileAll.java
```

### Referencia rápida ARM64

| Instrucción | Hex (LE) | Efecto |
|---|---|---|
| `ret` | `c0 03 5f d6` | Retornar |
| `nop` | `1f 20 03 d5` | No operación |
| `mov w0, #1` | `20 00 80 52` | Retornar true/1 |
| `mov x0, xzr` | `e0 03 1f aa` | Retornar 0/null |
| `mov x0, x1` | `e0 03 01 aa` | Retornar jclass |

---

## 5. Flutter / Dart

Flutter compila Dart a AOT snapshot en `libapp.so` + `libflutter.so`. El análisis estático es limitado; la mayoría del trabajo es dinámico o de ingeniería de snapshots.

| Herramienta | Repo | Uso |
|---|---|---|
| **reFlutter** | `nicolo-ribaudo/reflutter` | Parchea Flutter engine para inspección de tráfico y snapshots. |
| **blutter** | `nicolo-ribaudo/blutter` | Análisis de Dart AOT snapshots. Extrae clases y métodos. |
| **Doldrums** | `nicolo-ribaudo/doldrums` | Parser de Dart AOT snapshots. |
| **dart_snapshot_parser** | `nicolo-ribaudo/dart_snapshot_parser` | Parser de snapshots de Dart. |
| **flutter-spy** | `nicolo-ribaudo/flutter-spy` | Inspección de APKs Flutter. |
| **frida-dart** | scripts de la comunidad | Hooks de Frida para Dart runtime. |
| **rebuild** | `nicolo-ribaudo/rebuild` | Reconstrucción de estructura de Dart AOT. |

### Estrategia Flutter (alto nivel)

```bash
# 1. Detectar Flutter
unzip -l app.apk | grep -i "libapp.so\|libflutter.so"

# 2. Extraer version de Flutter
strings libflutter.so | grep -oP 'flutter_engine_version=\K.*'
strings libflutter.so | grep -oP 'dart_sdk_version=\K.*'

# 3. reFlutter para parchear engine (laboratorio)
pip install reflutter
reflutter app.apk

# 4. blutter para análisis de snapshot
python3 blutter.py path/to/libapp.so output_dir/

# 5. Frida para hook dinámico
# Buscar offsets de métodos Dart en el snapshot y hook con Interceptor.attach
```

**Limitaciones conocidas:**
- Los nombres de métodos Dart no están en strings; se reconstruyen desde el snapshot.
- El pinning en Flutter usa `BoringSSL` compilado dentro de `libflutter.so`, no el del sistema.
- reFlutter parchea el engine para deshabilitar pinning, pero requiere reempaquetar y firmar.

---

## 6. Kotlin específico

Kotlin compila a DEX estándar, pero introduce patrones que requieren interpretación:

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

### Herramientas para Kotlin

| Herramienta | Repo | Uso |
|---|---|---|
| **kotlinp** | `bashor/kotlinp` | Decompilador de Kotlin metadata. |
| **kotlinx.metadata** | `Kotlin/kotlinx-metadata-jvm` | Lectura de metadata de Kotlin en JVM. |
| **detekt** | `detekt/detekt` | Análisis estático de código Kotlin (útil para apps propias). |

### Búsqueda de corrutinas en smali

```bash
# Suspended functions
rg -n 'invokeSuspend|Continuation|kotlin/coroutines' dex*_out/

# State machine labels
rg -n 'goto/|packed-switch|sparse-switch' dex*_out/ --glob "**/*Continuation*"
```

---

## 7. Red y tráfico — Proxy, TLS, SSL pinning

> **Solo para auditorías autorizadas.** El bypass de pinning en apps ajenas sin permiso es ilegal.

### Herramientas de proxy

| Herramienta | Repo / URL | Uso |
|---|---|---|
| **mitmproxy** | `mitmproxy/mitmproxy` | Proxy HTTP/HTTPS con scripting Python. |
| **mitmdump** | (incluido) | CLI para automatización. |
| **HTTP Toolkit** | `httptoolkit/httptoolkit` | Proxy con UI; modo Android via VPN + cert Magisk. |
| **Burp Suite Community** | `portswigger.net` | Proxy estándar de la industria. |
| **Charles Proxy** | `charlesproxy.com` | Alternativa comercial con trial. |
| **PCAPdroid** | `emanuele-f/PCAPdroid` | Captura de tráfico en dispositivo sin root. |

### SSL Pinning bypass (laboratorio autorizado)

| Técnica | Herramienta | Requisitos | Notas |
|---|---|---|---|
| **Frida scripts** | `httptoolkit/frida-android-unpinning` | Root + Frida | Universal para OkHttp/TrustManager. |
| **Objection** | `objection -g com.app explore -s "android sslpinning disable"` | Root + Frida | Comando único. |
| **LSPosed + TrustMeAlready** | `ViRb3/TrustMeAlready` | Root + LSPosed | Module Xposed para bypass global. |
| **reFlutter** | `nicolo-ribaudo/reflutter` | Sin root (reempaqueta) | Solo apps Flutter. |
| **Network Security Config** | XML en APK | Sin root (reempaqueta) | Solo si la app respeta NSC (Android 7+). |
| **apk-mitm** | `shroudedcode/apk-mitm` | Sin root (reempaqueta) | Añade NSC + deshabilita pinning en smali. |
| **HTTP Toolkit** | VPN + cert Magisk | Root | Inyección de CA via tmpfs. |

### Scripts de unpinning de referencia

```bash
# Repositorio de scripts Frida para unpinning
git clone https://github.com/httptoolkit/frida-android-unpinning.git

# Ejecutar
frida -U -f com.example.app -l frida-android-unpinning/universal-android-ssl-pinning-bypass-with-frida.js --no-pause

# Objection
objection -g com.example.app explore
# > android sslpinning disable
```

### Network Security Config (reempaquetado)

```xml
<!-- res/xml/network_security_config.xml -->
<network-security-config>
  <base-config cleartextTrafficPermitted="true">
    <trust-anchors>
      <certificates src="system"/>
      <certificates src="user"/>
    </trust-anchors>
  </base-config>
</network-security-config>
```

```xml
<!-- AndroidManifest.xml: <application> -->
android:networkSecurityConfig="@xml/network_security_config"
```

**Limitaciones del NSC:**
- No funciona si la app usa pinning propio (OkHttp CertificatePinner, Cronet, boringssl).
- No funciona si la app usa mTLS con certificados embebidos.
- No funciona en Flutter (usa su propio stack TLS).

---

## 8. Desofuscación y análisis de strings

| Herramienta | Repo | Uso |
|---|---|---|
| **simplify** | `celzero/reftool` | Simplificación de bytecode via interpretación parcial. |
| **deguard** | `pxb1988/deguard` | Recuperación de nombres ProGuard con heurísticas. |
| **StringFogDecoder** | varios scripts de la comunidad | Decodificación de StringFog (XOR/Base64). |
| **DexGuard analyzer** | scripts personalizados | Análisis de flujos de decrypt de strings. |
| **JADX search** | (incluido) | Búsqueda con regex en código decompilado. |
| **ripgrep** | `BurntSushi/ripgrep` | Búsqueda rápida en smali/Java decompilado. |
| **strings** + **rabin2** | binutils / radare2 | Extracción de strings en DEX y .so. |

### Patrones de ofuscación comunes

| Ofuscador | Patrón | Detección |
|---|---|---|
| **ProGuard / R8** | nombres de 1-2 letras (a, b, o0O0) | `rg -c '\b[a-z]\b' jadx-out/` |
| **StringFog** | strings codificadas, decrypt en clinit | `rg -n 'StringFog|encrypt\|decrypt' jadx-out/` |
| **DexGuard** | strings en assets, reflexión masiva, encrypt de clases | `rg -n 'DexGuard|com.secure' jadx-out/` |
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

---

## 9. Anti-tamper y bypass de protecciones (autorizado)

> Solo para auditorías con alcance firmado. Bypass de protecciones en apps ajenas sin permiso es ilegal.

### Tipos de protecciones y enfoques

| Protección | Detección | Enfoque de análisis (autorizado) |
|---|---|---|
| **Signature check (Java)** | `getPackageInfo(GET_SIGNATURES)` | Hook PMS con Frida o parche smali. |
| **Signature check (native)** | `JNI_OnLoad` → abort | Análisis Ghidra: trace abort() XREFs. |
| **DEX integrity hash** | hash de classes.dex en .so | Patch del memcmp o actualización del hash esperado. |
| **Root detection** | `su`, `Magisk`, `busybox`, `/system` writable | Hook de File.exists, Runtime.exec. |
| **Emulator detection** | `Build.FINGERPRINT`, `ro.kernel.qemu` | Hook de Build y SystemProperties. |
| **Frida detection** | puertos abiertos, `/data/local/tmp/frida` | Renombrar frida-server, usar gadget. |
| **Debug detection** | `android.os.Debug.isDebuggerConnected` | Hook del método. |
| **SafetyNet** | Google Play Services API | Análisis de respuesta (laboratorio). |
| **Play Integrity** | Google Play Services API | Análisis de tokens (laboratorio). |
| **App Attest / DeviceCheck** | iOS equivalente | N/A en Android. |

### Herramientas de bypass (laboratorio)

| Herramienta | Repo | Uso |
|---|---|---|
| **Magisk** | `topjohnwu/Magisk` | Root moderno con Zygisk. |
| **Zygisk** | (incluido en Magisk) | Hook a nivel Zygote. |
| **LSPosed** | `LSPosed/LSPosed` | Framework Xposed moderno (Zygisk). |
| **Shamiko** | `LSPosed/LSPosed.github.io` | Ocultar root de apps. |
| **HideMyApplist** | `Dr-TSNG/HideMyApplist` | Ocultar lista de apps instaladas. |
| **Frida codeShare** | `frida/frida-codeshare` | Scripts de bypass de root/emulator detection. |
| **r0capture** | `r0ysue/r0capture` | Captura de tráfico a nivel SSL con Frida. |

---

## 10. Criptografía y almacenamiento de claves

### Análisis de uso criptográfico

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

### Herramientas

| Herramienta | Repo | Uso |
|---|---|---|
| **apkleaks** | `dxa9098/apkleaks` | Detección de API keys, tokens, URIs. |
| **truffleHog** | `trufflesecurity/trufflehog` | Detección de secretos en repos y binarios. |
| **mobi-core** | `hakanonymos/mobi-core` | Análisis de almacenamiento de apps. |
| **KeyStore Explorer** | `kaikramer/keystore-explorer` | GUI para inspeccionar keystores. |

### Almacenamiento común

| Mecanismo | Dónde buscar | Notas |
|---|---|---|
| **SharedPreferences** | `/data/data/<pkg>/shared_prefs/` | XML en claro por defecto. |
| **SQLite** | `/data/data/<pkg>/databases/` | `sqlite3 db.sqlite .dump` |
| **EncryptedSharedPreferences** | Jetpack Security | Clave en Keystore + AES-256-GCM. |
| **Realm** | `/data/data/<pkg>/files/` | Formato binario propio. |
| **Room** | SQLite subyacente | Igual que SQLite. |
| **Flutter SecureStorage** | `FlutterSecureStorage` | Usa EncryptedSharedPreferences en Android. |
| **Keystore** | Hardware-backed | No extraíble; hook de `getKey` para interceptar. |

---

## 11. Empaquetado, firma y bundles

| Herramienta | Repo / Fuente | Uso |
|---|---|---|
| **apksigner** | Android SDK build-tools | Firma v1/v2/v3/v4. |
| **zipalign** | Android SDK build-tools | Alineación de ZIP para mmap. |
| **bundletool** | `google/bundletool` | Manipulación de AAB/APKS. |
| **apktool** | `iBotPeaches/Apktool` | Reconstrucción de APK con recursos. |
| **aapt2** | Android SDK | Compilación de recursos. |
| **uber-apk-signer** | `patrickfav/uber-apk-signer` | Wrapper de firma con keystore automático. |
| **apksigner** | SDK | Firma oficial. |

### Firma y verificación

```bash
# Verificar firmas
apksigner verify --verbose --print-certs app.apk

# Firmar (v1+v2+v3)
apksigner sign \
  --ks "$HOME/.android/debug.keystore" --ks-pass pass:android \
  --ks-key-alias androiddebugkey \
  --v1-signing-enabled true --v2-signing-enabled true --v3-signing-enabled true \
  --out signed.apk aligned.apk

# Alinear (antes de firmar)
zipalign -p -f 4 input.apk aligned.apk
```

### Bundles (AAB)

```bash
# Generar APKS desde AAB
java -jar bundletool.jar build-apks \
  --bundle app.aab \
  --output app.apks \
  --ks "$HOME/.android/debug.keystore" \
  --ks-pass pass:android \
  --ks-key-alias androiddebugkey

# Extraer universal APK
java -jar bundletool.jar extract-apks \
  --apks app.apks \
  --output-dir extracted/

# Instalar splits
java -jar bundletool.jar install-apks --apks app.apks
```

### Reglas de compresión (Android 14–16)

| Archivo | Compresión | Razón |
|---|---|---|
| `*.so` | STORE | `dlopen` falla con .so comprimido. |
| `resources.arsc` | STORE | Android 11+ requiere sin compresión. |
| `classes*.dex` | STORE (con Python zipfile) | Python zipfile corrompe con DEFLATED. |
| Resto | DEFLATE | Tamaño reducido. |

---

## 12. Detección de root / SafetyNet / Play Integrity

### Detección de root (qué buscar en smali)

```bash
# Búsqueda de paths de root
rg -n '"/su"\|"/system/xbin/su"\|"/sbin/su"\|magisk"\|busybox' dex*_out/

# Build props
rg -n 'Build.FINGERPRINT\|Build.MODEL\|Build.MANUFACTURER\|ro.kernel.qemu' dex*_out/

# Magisk específico
rg -n 'magisk\|zygisk\|riru' dex*_out/
```

### SafetyNet / Play Integrity

| API | Versión | Estado |
|---|---|---|
| **SafetyNet Attestation** | Deprecated | Reemplazada por Play Integrity. |
| **Play Integrity API** | 2023+ | Reemplaza SafetyNet. Tokens firmados por Google. |
| **Classic SafetyNet** | Legacy | Aún presente en apps antiguas. |

**Notas:**
- Play Integrity devuelve tokens JWT firmados por Google; verificar server-side.
- Bypass de Play Integrity en producción viola ToS de Google Play.
- En laboratorio: análisis de respuestas con Frida hook de `IntegrityTokenResponse`.

---

## 13. Automatización y pipelines

| Herramienta | Repo | Uso |
|---|---|---|
| **MobSF** | `MobSF/Mobile-Security-Framework-MobSF` | Pipeline completo estática + dinámica. |
| **QARK** | `appknox/qark` | Análisis estático automatizado. |
| **MARA** | `xtiankisutsa/MARA-framework` | Framework de análisis de malware. |
| **APKLab** | `APKLab/APKLab` | Extensión VS Code para análisis de APK. |
| **jadx-ai** | varios | Plugins de IA para jadx. |
| **Paresh-Maheshwari/morphe-ai** | `Paresh-Maheshwari/morphe-ai` | Pipeline multi-agente con IA para análisis y patching. |

### Pipeline de análisis (esquema)

```
APK
 ├─ aapt dump badging → metadata
 ├─ jadx -d out/ → Java decompilado
 ├─ apktool d → recursos + smali
 ├─ baksmali d classes*.dex → smali por DEX
 ├─ androguard analyze → permisos, firma, strings
 ├─ apkleaks → secretos
 ├─ strings lib/*.so → strings nativos
 ├─ readelf -Ws lib/*.so → símbolos
 ├─ Ghidra headless → decompilación nativa
 └─ Frida (dinámico) → hooks, trace, dump
```

---

## 14. Recursos formativos — MSTG, MASVS, CTFs

### Documentación oficial

| Recurso | URL | Descripción |
|---|---|---|
| **OWASP MSTG** | `OWASP/owasp-mstg` | Mobile Security Testing Guide. |
| **OWASP MASVS** | `OWASP/owasp-masvs` | Mobile Application Security Verification Standard. |
| **OWASP Mobile Top 10** | `OWASP/owasp-mstg` | Riesgos top de mobile. |
| **Android Security** | `source.android.com/security` | Docs oficiales de Android. |

### Apps vulnerables intencionalmente (para práctica legal)

| App | Repo | Nivel |
|---|---|---|
| **OWASP UnCrackable Apps** | `OWASP/owasp-mstg` (Crackmes) | L1 (Java), L2 (native), L3 (native+obfuscation), L4 (Flutter), L5 (Kotlin) |
| **DVIA-v2** | `prateek147/DVIA-v2` | Damn Vulnerable iOS App (referencia). |
| **InsecureBankv2** | `dineshshetty/Android-InsecureBankv2` | App bancaria vulnerable. |
| **Sieve** | `OWASP/owasp-mstg` | App de ejemplo para análisis. |
| **DIVA-Android** | `exploit-db/DIVA` | Diverse Insecure Vulnerable App. |
| **MSTG Crackmes** | `OWASP/owasp-mstg` | Conjunto de crackmes por nivel. |

### Certificaciones

| Cert | Org | Enfoque |
|---|---|---|
| **OSMR** | OffSec | Mobile testing (Android + iOS). |
| **eMAPT** | eLearnSecurity | Mobile App Penetration Testing. |
| **GMOB** | GIAC | Mobile Device Security Analyst. |
| **GREM** | GIAC | Reverse Engineering Malware. |

---

## 15. Awesome lists y comunidades

| Lista | Repo | Contenido |
|---|---|---|
| **awesome-android-security** | `ashishb/awesome-android-security` | Curaduría general. |
| **awesome-frida** | `dweinstein/awesome-frida` | Scripts y recursos Frida. |
| **awesome-reverse-engineering** | `mytechnotalent/awesome-reverse-engineering` | RE general. |
| **awesome-mobile-security** | `viaasys/awesome-mobile-security` | Seguridad móvil. |
| **AndroidReverse** | `ZJ595/AndroidReverse` | Curso de RE Android (chino). |
| **r2frida** | `frida/r2frida` | Integración r2 + Frida. |
| **Frida CodeShare** | `frida/frida-codeshare` | Scripts compartidos. |

### Comunidades

- **r/ReverseEngineering** (Reddit)
- **r/netsecstudents** (Reddit)
- **Frida Slack** (`frida.io`)
- **OWASP Mobile Slack**
- **XDA Developers** (foros de modding legal)

---

## 16. Comandos rápidos de referencia

### Inspección inicial

```bash
# Metadata
aapt dump badging app.apk
unzip -l app.apk | grep -c "classes.*\.dex"
unzip -l app.apk | grep -c "\.so$"

# Detección de modders
unzip -p app.apk classes*.dex | strings -a | grep -iE "Liteapks|9mod|ī/íì|īi/ïi|bin/ghost"

# Detección de Flutter
unzip -l app.apk | grep -i "libapp.so\|libflutter.so"

# Detección de Pairip
unzip -p app.apk classes*.dex | strings -a | grep -c "pairip"
unzip -l app.apk | grep -i "pairipcore"
```

### Descompilación completa

```bash
# Java
jadx -d jadx-out/ --no-res app.apk

# Smali (todos los DEX)
API=35
for num in "" $(seq 2 20); do
    fname="classes${num}.dex"
    unzip -l app.apk | grep -q "$fname" || continue
    unzip -p app.apk "$fname" > "$fname"
    baksmali d "$fname" -o "dex${num}_out/" --api "$API"
done

# Recursos
apktool d app.apk -o apktool-out/
```

### Búsqueda de patrones

```bash
# Licencia/premium
rg -n '"premium"|"noads"|"pro"|"isPremium"|"max_' dex*_out/ --glob "**/*.smali"

# Billing
rg -n 'BillingClient|queryPurchases|getPurchase|startPurchase' dex*_out/

# Cifrado
rg -n 'Cipher;->getInstance|SecretKeySpec|MessageDigest|KeyGenerator' dex*_out/

# Reflexión
rg -n 'getDeclaredMethod|getDeclaredField|Class.forName|Method;->invoke' dex*_out/

# Root detection
rg -n '"/su"|magisk|busybox|ro.kernel.qemu|isDebuggerConnected' dex*_out/

# Native load
rg -n 'System.loadLibrary|System.load' dex*_out/
```

### Reempaquetado y firma

```bash
# Reensamblar DEX modificado
smali assemble dex2_out/ --api 35 -o classes2_new.dex

# Reempaquetar (ver scripts/ziprepack.py)
python3 scripts/ziprepack.py --in app.apk --out hacked.apk \
  --replace classes2.dex=classes2_new.dex

# Alinear
zipalign -p -f 4 hacked.apk hacked_aligned.apk

# Firmar
apksigner sign \
  --ks "$HOME/.android/debug.keystore" --ks-pass pass:android \
  --ks-key-alias androiddebugkey \
  --v1-signing-enabled true --v2-signing-enabled true --v3-signing-enabled true \
  --out hacked_signed.apk hacked_aligned.apk

# Verificar
apksigner verify --verbose --print-certs hacked_signed.apk

# Instalar (desactivar Play Protect temporalmente)
adb shell settings put global package_verifier_enable 0
adb install hacked_signed.apk
adb shell settings put global package_verifier_enable 1
```

### Análisis nativo

```bash
# Extraer .so
unzip -p app.apk lib/arm64-v8a/libnative.so > libnative.so

# Strings y símbolos
strings -a libnative.so | grep -iE 'sign|cert|integrity|verify|package'
readelf -Ws libnative.so | grep -i 'JNI\|verify\|check'

# radare2
r2 -A libnative.so
# > afl~JNI
# > s sym.JNI_OnLoad
# > pdf

# Ghidra headless
/opt/ghidra/support/analyzeHeadless /tmp proj -import libnative.so \
  -postScript DecompileAll.java -scriptPath /opt/ghidra/Ghidra/Features/Decompiler/
```

### Frida (dinámica)

```bash
# Listar procesos
frida-ps -U

# Spawn con script
frida -U -f com.example.app -l hook.js --no-pause

# Trace de métodos
frida-trace -U -f com.example.app -j '*!*onCreate*'

# Objection
objection -g com.example.app explore
# > android sslpinning disable
# > android root disable
# > android hooking list activities
# > android hooking search classes License
```

---

## Apéndice: Mapa de herramientas por escenario

| Escenario | Estática | Dinámica | Nativo |
|---|---|---|---|
| App Java simple | jadx, baksmali | Frida | — |
| App Kotlin | jadx, baksmali | Frida | — |
| App Flutter | blutter, reFlutter | Frida + reFlutter | Ghidra (libapp.so) |
| App con .so | jadx, readelf | Frida + r2frida | Ghidra, r2 |
| App con Pairip | jadx (vault strings) | Frida (VMRunner.invoke) | Ghidra (libpairipcore.so) |
| App con Dex2C | — (DEX vacío) | Frida (hook nativo) | Ghidra (libstub.so) |
| App con SSL pinning | apk-mitm | Frida unpinning | — |
| App con root detection | rg patterns | Frida hook | — |
| App con Play Integrity | — | Frida hook (laboratorio) | — |

---

*Documento generado para investigación de seguridad autorizada. El uso de estas herramientas fuera de un alcance firmado es responsabilidad exclusiva del usuario.*
