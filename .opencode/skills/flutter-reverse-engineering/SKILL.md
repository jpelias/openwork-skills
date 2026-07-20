---
name: flutter-reverse-engineering
description: >
  Comprehensive Flutter/Dart reverse engineering: APK splitting and merging, static analysis
  of libapp.so (Blutter, unflutter, flutterdec, r2flutter), dynamic analysis (Frida Gadget
  embedding, SSL pinning bypass via BoringSSL hooking), Dart VM internals (Object Pool,
  compressed pointers, QK Color objects, AOT snapshot format), traffic interception
  (reFlutter, iptables, socket redirection), and theme/color modification. Covers Android
  ARM64 exclusively. Use for authorized security testing, research, or modifying your own
  apps.
---

# Flutter Reverse Engineering — Complete Guide

Complete methodology for reverse engineering Flutter Android applications. Covers the full lifecycle from APK extraction through static analysis, dynamic instrumentation, SSL pinning bypass, and runtime patching.

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [APK Extraction and Preparation](#2-apk-extraction-and-preparation)
3. [Quick Triage](#3-quick-triage)
4. [Static Analysis — libapp.so](#4-static-analysis--libappso)
5. [Static Analysis — libflutter.so](#5-static-analysis--libflutterso)
6. [Dynamic Analysis — Frida](#6-dynamic-analysis--frida)
    - [6.1. Basic Setup](#basic-setup)
    - [6.2. Dart VM Object Inspection](#dart-vm-object-inspection)
    - [6.3. Reading Dart Strings at Runtime](#reading-dart-strings-at-runtime)
    - [6.4. Hooking Recovered Functions](#hooking-recovered-functions)
    - [6.5. MethodChannel Interception](#methodchannel-interception)
    - [6.6. Blutter + Frida: Flujo de Trabajo Completo](#blutter--frida-flujo-de-trabajo-completo)
7. [SSL Pinning Bypass](#7-ssl-pinning-bypass)
8. [Traffic Interception](#8-traffic-interception)
9. [Dart VM Internals](#9-dart-vm-internals)
10. [Runtime Color/Theme Modification](#10-runtime-colormodification)
11. [Frida Gadget Embedding](#11-frida-gadget-embedding)
12. [Obfuscation Awareness](#12-obfuscation-awareness)
13. [Tool Reference](#13-tool-reference)
14. [Common Pitfalls](#14-common-pitfalls)
15. [References](#15-references)

---

## 1. Architecture Overview

Flutter apps are fundamentally different from native Android/iOS apps. Understanding the architecture is critical before attempting any reverse engineering.

### Flutter Stack

```
┌─────────────────────────────────────────┐
│           Developer's Dart Code          │  ← Your target code
├─────────────────────────────────────────┤
│        Flutter Framework (Dart)          │  ← Widget tree, layouts, HTTP clients
├─────────────────────────────────────────┤
│       Engine (C/C++) — libflutter.so     │  ← Dart VM, BoringSSL, Skia, Impeller
├─────────────────────────────────────────┤
│     AOT Snapshot — libapp.so             │  ← Compiled Dart code + Object Pool
├─────────────────────────────────────────┤
│         Platform (Android/iOS)           │  ← Minimal Java/Kotlin bootstrap
└─────────────────────────────────────────┘
```

### Key Files in APK

| File | Contents | RE Focus |
|------|----------|----------|
| `lib/arm64-v8a/libapp.so` | AOT-compiled Dart snapshot (app code + framework) | Function names, class hierarchies, strings, Object Pool |
| `lib/arm64-v8a/libflutter.so` | Flutter Engine (Dart VM + BoringSSL + Skia) | SSL verification, proxy logic, rendering |
| `assets/flutter_assets/` | Manifests, JSON configs, fonts, `kernel_blob.bin` (debug only) | Secrets, feature flags, theme JSON |
| `classes.dex` | Minimal Java bootstrap (just launches Flutter) | MethodChannel names, platform plugins |

### Why Flutter RE Is Hard

1. **No Java-level hooks work** — all networking (DNS, sockets, TLS) happens inside `libflutter.so`, not in OkHttp/Java layers
2. **BoringSSL uses its own CA store** — importing Burp CA into Android system store changes nothing
3. **Symbols are stripped and mangled** — `JNI_OnLoad` is often the only exported symbol
4. **Dart ignores system proxy settings** — `dart:io` routes directly without consulting Android's global proxy
5. **AOT snapshots use compressed format** — relative pointers, cluster-based serialization, can't patch bytes directly

---

## 2. APK Extraction and Preparation

### Split APK Merging

Flutter apps often ship as split APKs (base + architecture + locale + density). Merge them first.

```bash
# Pull splits from device
adb pull /data/app/es.aemet-*/base.apk                    apk_files/base.apk
adb pull /data/app/es.aemet-*/split_config.arm64_v8a.apk  apk_files/arm64.apk
adb pull /data/app/es.aemet-*/split_config.es.apk         apk_files/es.apk
adb pull /data/app/es.aemet-*/split_config.xxhdpi.apk     apk_files/xxhdpi.apk

# Merge with APKEditor (handles _ prefixed resource names from splits)
java -jar APKEditor.jar m -i apk_files -o merged.apk

# Verify native libs present
unzip -l merged.apk | grep libapp.so
```

**Critical:** Use APKEditor (ARSCLib), NOT apktool — aapt2 rejects `_14.xml` resources inherited from split merges.

### APK Decoding

```bash
# Decode with APKEditor
java -jar APKEditor.jar d -i merged.apk -o decoded_apk

# Extract native libs for analysis
mkdir extracted_libs
unzip -j merged.apk "lib/arm64-v8a/libapp.so" "lib/arm64-v8a/libflutter.so" -d extracted_libs/
```

### Extract flutter_assets

```bash
unzip -j merged.apk "assets/flutter_assets/*" -d flutter_assets/
```

---

## 3. Quick Triage

Run these commands immediately after extraction to understand what you're dealing with.

### Identify Flutter Version

```bash
# Get snapshot hash from libapp.so
python3 get_snapshot_hash.py extracted_libs/libapp.so

# Match hash to Flutter version
curl -s https://raw.githubusercontent.com/Impact-I/reFlutter/refs/heads/main/enginehash.csv | grep <snapshot_hash>
```

### Check for Debug Build

```bash
# kernel_blob.bin presence = debug/non-release build (high-value finding!)
unzip -l merged.apk | grep kernel_blob

# Debug builds have readable Dart source in the snapshot
if [ -f flutter_assets/kernel_blob.bin ]; then
    echo "DEBUG BUILD — full source recovery possible"
fi
```

### Static String Extraction

```bash
# Quick scan for high-value strings
rg -n -a "(https?://|api[_-]?key|token|secret|BEGIN (RSA|EC|PRIVATE)|supabase|stripe|aws)" \
    flutter_assets/ extracted_libs/ -S

# Scan libapp.so specifically
strings extracted_libs/libapp.so | grep -iE "(http|api|key|token|secret|password|auth)"
```

### Java Layer Recon (minimal but useful)

```bash
# Decompile with jadx
jadx -r merged.apk -d jadx_out/

# Find MethodChannel names (Dart ↔ Java communication)
rg -n "MethodChannel|EventChannel|BasicMessageChannel|setMethodCallHandler|invokeMethod" jadx_out/ -S
```

Frida can log channel names at startup:

```javascript
Java.perform(function () {
    var MC = Java.use('io.flutter.plugin.common.MethodChannel');
    MC.$init.overload('io.flutter.plugin.common.BinaryMessenger', 'java.lang.String')
        .implementation = function (messenger, name) {
            console.log('[+] MethodChannel: ' + name);
            return this.$init(messenger, name);
        };
});
```

---

## 4. Static Analysis — libapp.so

### Tool Selection Matrix

| Tool | Approach | Best For | Setup |
|------|----------|----------|-------|
| **Blutter** | Embeds Dart VM, compiles matching SDK | Fastest path to named functions + Frida stubs | High (C++20, cmake, Dart SDK compilation) |
| **unflutter** | Pure parser, no VM needed | Portability, Ghidra/IDA integration, call graphs | Low (Go 1.24+, single binary) |
| **flutterdec** | Rust decompiler → pseudo-Dart | Readable pseudocode, version diffing | Medium (Nix or binary release) |
| **r2flutter** | Radare2 plugin | Binary analysis in r2 ecosystem | Medium (radare2 + make) |
| **disrobe** | Universal RE toolkit | Multi-language projects including Flutter | Low (single binary) |

### 4.1 Blutter — Workflow Paso a Paso

Blutter es la herramienta estándar para RE de Flutter. Embedde la Dart VM, compila el SDK que coincide con la versión de la app, y produce disassembly anotado con nombres de funciones Dart recuperados.

#### Instalación Completa

```bash
# Clonar repositorio
git clone https://github.com/worawit/blutter.git
cd blutter

# Instalar dependencias del sistema (Debian/Ubuntu)
sudo apt install python3-pyelftools python3-requests git cmake ninja-build \
    build-essential pkg-config libicu-dev libcapstone-dev

# En Arch: pacman -S python-pyelftools python-requests cmake ninja capstone
# En macOS: brew install python3 cmake ninja capstone icu4c

# Verificar instalación
python3 blutter.py --help
```

#### Ejecución Básica

```bash
# Opción A: desde APK directamente (Blutter extrae .so automáticamente)
python3 blutter.py /ruta/a/app.apk ./blutter_out/

# Opción B: desde lib/ extraída
mkdir -p ./extracted_libs
unzip -j app.apk "lib/arm64-v8a/libapp.so" "lib/arm64-v8a/libflutter.so" -d ./extracted_libs/
python3 blutter.py ./extracted_libs/ ./blutter_out/
```

**Tiempo de ejecución:** 2-5 minutos en primera ejecución (compila Dart SDK). Ejecuciones posteriores con la misma versión de Flutter son instantáneas.

#### Salida de Blutter — Estructura y Uso

```
blutter_out/
├── asm/                          # Disassembly anotado por función
│   ├── com.example.app.MainActivity@084716.dart
│   ├── weather_api.fetchWeather@123abc.dart
│   ├── login_screen._handleLogin@456def.dart
│   └── ... (una por cada función recuperada)
├── blutter_frida.js              # Template de hooks Frida (requiere edición)
├── pp.txt                        # Object Pool dump completo
├── objs.txt                      # Dump anidado de todos los objetos del Pool
└── symbols.json                  # Mapa de direcciones → nombres (para Ghidra/IDA)
```

#### Interpretar asm/ — Ejemplo Real

Archivo: `asm/com.example.app.LoginScreen@handleLogin.dart`

```
// Function: LoginScreen._handleLogin
// Dart version: 3.4.2
// Architecture: arm64
// Address range: 0x3b24e0 - 0x3b26a0

0x3b24e0:  LDP X29, X30, [SP, #-0x10]!    // Function prologue
0x3b24e4:  ADD X29, SP, #0x0
0x3b24e8:  LDR X0, [PP + 0x2b6f0]         // ← Carga String "email" desde Object Pool
0x3b24ec:  LDR X1, [PP + 0x2b700]         // ← Carga String "password" desde Object Pool
0x3b24f0:  BL  _ZN8dart_api12Dart_NewStringE   // ← Crea Dart String
0x3b24f4:  MOV X19, X0                      // Guarda en registro callee-saved
0x3b24f8:  LDR X20, [PP + 0x1a4c0]        // ← Carga referencia a clase HttpClient
0x3b24fc:  BL  _ZN9flutter13HttpClientNewE   // ← Instancia HttpClient
0x3b2500:  LDR X1, [PP + 0x3c820]          // ← Carga URL "https://api.example.com/login"
0x3b2504:  BL  _ZN9flutter13HttpClientGetE   // ← GET request
0x3b2508:  ...
0x3b26a0:  LDP X29, X30, [SP], #0x10       // Function epilogue
0x3b26a4:  RET
```

**Cómo leer esto:**
- `PP + 0x2b6f0` → offset en el Object Pool. Buscar en `pp.txt` para ver el valor real.
- `0x3b24e0` → offset absoluto dentro de `libapp.so`. Usar en Frida: `libapp.add(0x3b24e0)`
- `BL _ZN8dart_api12Dart_NewStringE` → llamada a Dart API (puedes hookuear por nombre de símbolo si no está stripped)

#### Buscar Funciones Objetivo en asm/

```bash
# Listar todas las funciones
ls blutter_out/asm/ | head -30

# Buscar por palabra clave en nombres de archivo
ls blutter_out/asm/ | grep -iE "login|auth|token|api|http|fetch|upload"

# Buscar dentro del disassembly (strings referenciados)
rg -l "password\|secret\|api_key\|Authorization" blutter_out/asm/

# Buscar funciones que usan HttpClient
rg -l "HttpClient\|http\." blutter_out/asm/

# Ver una función específica
cat "blutter_out/asm/com.example.app.ApiService@makeRequest.dart"
```

#### Interpretar pp.txt — Object Pool Dump

El Object Pool (`pp.txt`) es el recurso más valioso. Contiene todos los strings, colores, constantes y objetos Dart referenciados por el código.

```bash
# Ejemplo de entrada en pp.txt:
# [pp+0x2b6f0] Obj!XK@740301 : "email"
# [pp+0x2b700] Obj!XK@740301 : "password"
# [pp+0x3c820] Obj!XK@740301 : "https://api.example.com/login"
# [pp+0x15d90] Obj!QK@74bd11 : { off_8: double(1), off_10: double(0.15), ... }  ← Color AEMET Blue
```

**Tipos de objetos en pp.txt:**

| Prefijo | Tipo | Descripción |
|---------|------|-------------|
| `Obj!XK` | String | Strings UTF-8 Dart |
| `Obj!QK` | Color | Objetos Color con 4 doubles (ARGB) |
| `Obj!IMM` | Immediate | Valores inmediatos (ints, doubles) |
| `Obj!LIST` | List | Listas Dart |
| `Obj!MAP` | Map | Mapas Dart |
| `Obj!CLOSURE` | Closure | Funciones anónimas |

**Búsquedas útiles en pp.txt:**

```bash
# Encontrar todas las URLs
rg -n "https?://" blutter_out/pp.txt

# Encontrar posibles API keys (strings largos alfanuméricos)
rg -n '"[A-Za-z0-9+/=]{20,}"' blutter_out/pp.txt

# Encontrar colores (objetos QK)
rg -n "Obj!QK" blutter_out/pp.txt | head -20

# Encontrar el color que tiene valores ARGB específicos
python3 -c "
import re
with open('blutter_out/pp.txt') as f:
    for line in f:
        if 'Obj!QK' in line and 'double(' in line:
            # Buscar colores cercanos al azul AEMET (0xff, 0.15, 0.51, 1.0)
            if '0.15' in line and '0.51' in line:
                print(line.strip())
"

# Contar tipos de objetos en el Pool
grep -oP 'Obj!\K\w+' blutter_out/pp.txt | sort | uniq -c | sort -rn
```

#### Usar symbols.json para Importar en Ghidra/IDA

Blutter genera `symbols.json` con todos los símbolos recuperados:

```json
{
  "0x3b24e0": "LoginScreen._handleLogin",
  "0x3b2500": "ApiService.makeRequest",
  "0x45a2c0": "WeatherModel.fromJson",
  ...
}
```

**Importar en Ghidra:**
1. File → Load Language → ARM64
2. Import `libapp.so`
3. Window → Script Manager → Python → `import_symbols.py`:

```python
import json
with open('/path/to/symbols.json') as f:
    symbols = json.load(f)
for addr_str, name in symbols.items():
    addr = int(addr_str, 16)
    createFunction(addr, name)
```

#### Opciones Avanzadas de Blutter

```bash
# Forzar recompilación del binario Blutter (después de git pull)
python3 blutter.py lib/ blutter_out/ --rebuild

# Especificar versión de Dart manualmente (si falla auto-detección)
python3 blutter.py libapp.so blutter_out/ --dart-version 3.4.2_android_arm64

# Modo offline (no descargar SDK de Dart)
python3 blutter.py app.apk blutter_out/ --offline

# Solo generar disassembly, sin análisis de objetos (más rápido)
python3 blutter.py app.apk blutter_out/ --no-analysis
```

#### Troubleshooting de Blutter

| Error | Causa | Solución |
|-------|--------|----------|
| `CMake not found` | cmake no instalado | `sudo apt install cmake ninja-build` |
| `Failed to detect Dart version` | `libflutter.so` ausente o corrupto | Extraer `libflutter.so` del APK manualmente y pasar directorio con ambos .so |
| `Compilation of Dart SDK failed` | Dependencia faltante (libicu-dev, capstone) | Instalar todas las dependencias listadas arriba |
| `blutter_frida.js: HeapAddress uninitialized` | No se llamó `init(context)` | Ver sección 6.5.8 en este documento |
| `asm/ vacío o casi vacío` | Versión de Flutter muy nueva (>3.27) no soportada | Esperar actualización de Blutter o usar `unflutter` como fallback |
| `pp.txt` no contiene strings esperados | La app está ofuscada con `--obfuscate` | Los nombres de funciones/clases estarán ofuscados pero los strings en pp.txt siguen legibles |

#### Integración con Frida (Blutter → Frida Workflow)

Una vez que Blutter termina, el flujo típico es:

```
1. Blutter termina → revisa asm/ → identifica función objetivo → anota su offset (ej: 0x3b24e0)
2. Abre blutter_frida.js → descomenta template → reemplaza direcciones con tus offsets
3. Ejecuta: frida -U -f com.target.app -l blutter_frida.js --no-pause
4. La app se lanza → Frida inyecta → ves los argumentos/retornos en consola
```

Ver sección 6.5 (Blutter + Frida: Flujo de Trabajo Completo) para el código detallado.

### 4.2 unflutter (No VM Required)

```bash
# Build
make build    # produces ./unflutter binary

# Full pipeline
unflutter libapp.so

# Quick scan
unflutter scan libapp.so

# Ghidra decompilation (headless)
unflutter ghidra libapp.so

# IDA decompilation (headless via idalib)
unflutter ida libapp.so

# Metadata only
unflutter meta libapp.so

# With existing disasm
unflutter ghidra libapp.so --from out/target
```

**Key outputs:**
- `functions.jsonl` — function records with names, addresses, sizes, param counts
- `call_edges.jsonl` — BL/BLR call edges with register provenance
- `classes.jsonl` — class layouts with field offsets and instance sizes
- `string_refs.jsonl` — string references from PP loads
- `signal.html` — behavioral signal report (net, URL, base64, cloaking)
- `asm/*.txt` — annotated ARM64 disassembly per function
- `flutter_meta.json` — unified metadata for Ghidra/IDA

**Register mapping (ARM64 Dart):**

| Register | Variable | Purpose |
|----------|----------|---------|
| X15 | `SHADOW_SP` | Dart shadow call stack |
| X21 | `DT` | Dispatch table pointer |
| X22 | `DART_NULL` | Dart null object |
| X26 | `THR` (DartThread*) | Thread pointer, field accesses resolve to struct names |
| X27 | `PP` | Object pool pointer |
| X28 | `HEAP_BASE` | Compressed pointer base |

### 4.3 flutterdec (Pseudo-Dart Output)

```bash
# Install (Nix)
nix profile install github:caverav/flutterdec

# Or download binary
curl -fLO https://github.com/caverav/flutterdec/releases/download/v0.1.0-alpha.2/flutterdec-v0.1.0-alpha.2-Linux-X64.tar.gz

# Inspect
flutterdec info ./sample.apk --json

# Decompile (default: app-unknown scope)
flutterdec decompile ./sample.apk -o ./out

# Decompile everything including framework
flutterdec decompile ./sample.apk -o ./out --function-scope all

# Compare two versions
flutterdec diff --old ./old.apk --new ./new.apk -o ./out-diff --json

# Generate Ghidra/IDA import scripts
flutterdec decompile ./sample.apk -o ./out --emit-ghidra-script --emit-ida-script
```

### 4.4 r2flutter (Radare2)

```bash
# Build and install
make && make user-install

# Print functions
r2flutter -f libapp.so

# Print all strings from Object Pool
r2flutter -z libapp.so

# Decode specific PP slot
r2flutter -O pp+0x15d90 libapp.so

# Full analysis with flags
r2flutter -A libapp.so

# With obfuscation map
r2flutter -m obfuscation_map.json -A libapp.so

# Snapshot header info
r2flutter -HH libapp.so
```

### 4.5 Object Pool Analysis (pp.txt)

The Object Pool (`pp.txt`) is the single most valuable output for finding secrets, endpoints, and constants.

```bash
# Find all QK (Color) objects with double values
grep "Obj!QK" pp.txt

# Find strings that look like URLs or keys
rg -n "(https?://|api[_-]?key|token|secret)" pp.txt

# Find all IMM (Immediate) values that could be ARGB colors
python3 -c "
import re
with open('pp.txt') as f:
    for line in f:
        if 'IMM' in line:
            val = line.split('IMM:')[1].strip()
            if '0xff' in val.lower() and len(val) > 10:
                print(line.strip())
"

# Count object types
grep -oP 'Obj!\K\w+' pp.txt | sort | uniq -c | sort -rn | head -20
```

### 4.6 Searching asm/ for Target Code

```bash
# Find functions referencing specific strings
rg -l "login\|auth\|password\|token" blutter_out/asm/

# Find color-related code
rg -l "Color\|0xff\|TextStyle\|Theme" blutter_out/asm/

# Find network-related functions
rg -l "HttpClient\|WebSocket\|connect\|socket" blutter_out/asm/
```

---

## 5. Static Analysis — libflutter.so

### Symbol Table

```bash
# Check exports (usually only JNI_OnLoad)
nm -D libflutter.so
# or
readelf -Ws libflutter.so | grep -i "FUNC.*GLOBAL"

# Check imports
readelf -Ws libflutter.so | grep UND

# Find snapshot hash offset
readelf -Ws libapp.so | grep _kDartIsolateSnapshotInstructions
```

### String-Based Function Location

The primary technique for finding functions in stripped `libflutter.so`:

```bash
# Find ssl_client/ssl_server strings (BoringSSL error strings retained in stripped builds)
strings -t x libflutter.so | grep "ssl_client"
strings -t x libflutter.so | grep "ssl_server"

# In Ghidra/IDA: search for these strings, follow XREFs
# The function referencing BOTH ssl_client AND ssl_server with 3 parameters
# is ssl_crypto_x509_session_verify_cert_chain
```

### JNI_OnLoad as Anchor

`JNI_OnLoad` is typically the only exported symbol. Use it as an anchor for offset-based hooking:

```
offset = ssl_crypto_x509_session_verify_cert_chain_address - JNI_OnLoad_address
```

Then at runtime:
```javascript
var m = Process.findModuleByName("libflutter.so");
var jniAddr = m.enumerateExports()[0].address;
var sslAddr = ptr(jniAddr).add(offset);  // pre-computed offset
```

---

## 6. Dynamic Analysis — Frida

### Basic Setup

```bash
# Device
adb push frida-server-<version>-android-<arch> /data/local/tmp/frida-server
adb shell "su -c 'chmod 755 /data/local/tmp/frida-server && /data/local/tmp/frida-server &'"

# Spawn app
frida -U -f com.target.app -l script.js --no-pause
```

### Dart VM Object Inspection

The `blutter_frida.js` template provides runtime object inspection. Key concepts:

```javascript
// Heap base register (x28) — used for compressed pointer decompression
function init(context) {
    if (HeapAddress === 0) {
        HeapAddress = context['x28'].shl(32);
    }
}

// Decompress a Dart compressed pointer
function decompressPointer(dptr) {
    return HeapAddress.add(dptr.toInt32());
}

// Read a tagged object value
function getTaggedObjectValue(tptr, depthLeft) {
    if (!isHeapObject(tptr)) {
        // Smi (Small Integer) — tag bit is 0
        return [tptr, Classes[CidSmi], tptr.toInt32() >> 1];
    }
    tptr = decompressPointer(tptr);
    let ptr = tptr.sub(1);  // remove tag
    const cls = Classes[getObjectCid(ptr)];
    const values = getObjectValue(ptr, cls, depthLeft);
    return [tptr, cls, values];
}
```

### Reading Dart Strings at Runtime

```javascript
function getDartString(ptr, cls) {
    const len = ptr.add(cls.lenOffset).readU32() >> 1;  // length stored as Smi
    return ptr.add(cls.dataOffset).readUtf8String(len);
}
```

### Hooking Recovered Functions

From blutter output, use recovered function names:

```javascript
var libapp = Module.findBaseAddress('libapp.so');

// Hook a specific function by offset from blutter asm/ output
Interceptor.attach(libapp.add(0x3b24e0), {
    onEnter: function() {
        init(this.context);
        let objPtr = getArg(this.context, 0);
        const [tptr, cls, values] = getTaggedObjectValue(objPtr);
        console.log(cls.name + '@' + tptr.toString().slice(2) + ' =', JSON.stringify(values));
    }
});
```

### MethodChannel Interception

```javascript
Java.perform(function () {
    // Log all MethodChannel calls
    var MethodChannel = Java.use('io.flutter.plugin.common.MethodChannel');
    MethodChannel.invokeMethod.implementation = function(method, args) {
        console.log('[MethodChannel] ' + this.getName() + '.' + method + '() = ' + args);
        return this.invokeMethod(method, args);
    };
});
```

### Blutter + Frida: Flujo de Trabajo Completo

Esta sección detalla el flujo completo desde que ejecutas Blutter hasta que inyectas el script Frida modificado en el dispositivo.

#### 6.5.1. Ejecutar Blutter

```bash
# Extraer lib/ del APK
unzip app.apk -d tmp_apk

# Blutter necesita libapp.so + libflutter.so
python3 blutter.py tmp_apk/lib/arm64-v8a/ resultados/
```

**Salida esperada:**

```
resultados/
├── asm/              # Ensamblador anotado por función
│   ├── com.example.app.MainActivity@084716.dart
│   ├── weather_api.fetchWeather@123abc.dart
│   └── login_screen._handleLogin@456def.dart
├── blutter_frida.js  # Script Frida generado
├── pp.txt            # Object Pool dump
└── objs.txt          # Dump completo de objetos
```

#### 6.5.2. Encontrar funciones objetivo en asm/

```bash
# Buscar funciones por nombre
ls resultados/asm/ | grep -iE "login|api|http|fetch|token"

# Buscar funciones que referencian strings específicos
rg -l "password\|secret\|api_key" resultados/asm/

# Ver una función específica
cat resultados/asm/com.example.app.LoginScreen@handleLogin.dart
```

Ejemplo de contenido de `asm/`:

```
// Function: LoginScreen._handleLogin
// Address: 0x3b24e0
// Dart version: 3.4.2
0x3b24e0: ldr x0, [pp+0x2b6f0]    // Load String "email"
0x3b24e4: ldr x1, [pp+0x2b700]    // Load String "password"
0x3b24e8: blr x21                  // Call HTTP method
...
```

El número `0x3b24e0` es el **offset dentro de libapp.so** que usarás en Frida.

#### 6.5.3. Modificar blutter_frida.js

El archivo `blutter_frida.js` generado contiene todas las definiciones de clases Dart con sus offsets, más un template de hook que debes completar:

```javascript
// En blutter_frida.js, busca la función onLibappLoaded()
// y reemplaza el contenido con tus hooks:

function onLibappLoaded() {
    // --- HOOK 1: Interceptar login ---
    const login_addr = 0x3b24e0;  // Offset de handleLogin desde asm/
    Interceptor.attach(libapp.add(login_addr), {
        onEnter: function () {
            init(this.context);
            // Los argumentos de funciones Dart se leen con getArg()
            let emailPtr = getArg(this.context, 0);
            let passPtr  = getArg(this.context, 1);

            const [eTptr, eCls, email] = getTaggedObjectValue(emailPtr);
            const [pTptr, pCls, pass]  = getTaggedObjectValue(passPtr);

            console.log(`[LOGIN] email=${email} password=${pass}`);
        }
    });

    // --- HOOK 2: Ver respuesta HTTP ---
    const http_resp = 0x3b2a00;  // Offset de una función que procesa respuesta HTTP
    Interceptor.attach(libapp.add(http_resp), {
        onEnter: function () {
            init(this.context);
            let respPtr = getArg(this.context, 0);
            const [tptr, cls, values] = getTaggedObjectValue(respPtr);
            console.log('[HTTP Response]', JSON.stringify(values, null, 2));
        }
    });
}
```

> **Registros de argumentos en ARM64 Dart:**
> - `getArg(context, 0)` → primer argumento (X0)
> - `getArg(context, 1)` → segundo argumento (X1)
> - ... hasta `getArg(context, 7)` → octavo argumento (X7)
> - Más de 8 args se pasan por pila (stack)

#### 6.5.4. Leer Strings, Mapas y Listas en onLeave

Para leer el **valor de retorno** de una función, necesitas llamar a `init()` también en `onLeave`:

```javascript
Interceptor.attach(libapp.add(fn_addr), {
    onEnter: function () {
        init(this.context);  // ← OBLIGATORIO para inicializar HeapAddress
    },
    onLeave: function (retval) {
        init(this.context);  // ← TAMBIÉN necesario en onLeave
        const [tptr, cls, values] = getTaggedObjectValue(retval);
        console.log(`[RETURN] ${cls.name} =`, JSON.stringify(values, null, 2));

        // MODIFICAR el valor de retorno:
        // Si es un String, se puede sobrescribir:
        // Nota: los strings Dart son inmutables, hay que reemplazar el puntero
        // La forma más fácil es crear un string en heap manualmente
        // Para tipos básicos (int, bool) se puede usar retval.replace()
    }
});
```

> **Error común:** `"Uninitialized HeapAddress"` en onLeave ocurre cuando no llamaste `init(this.context)`. El `this.context` en `onLeave` contiene los registros igual que en `onEnter`.

#### 6.5.5. Modificar objetos Dart en runtime

Para modificar objetos Dart (cambiar valores de campos) directamente en memoria:

```javascript
Interceptor.attach(libapp.add(0x3b24e0), {
    onEnter: function () {
        init(this.context);

        // Obtener puntero al objeto (argumento 0)
        let objPtr = getArg(this.context, 0);
        const [tptr, cls, values] = getTaggedObjectValue(objPtr);

        // El tagged pointer descomprimido apunta al objeto en heap
        let heapPtr = tptr.sub(1);  // remove tag bit

        // Cambiar permisos a RWX
        Memory.protect(heapPtr, cls.size, 'rwx');

        // Modificar campo en offset específico
        // Los offsets de campos se ven en objs.txt o pp.txt
        heapPtr.add(0x10).writeDouble(0.0);   // cambiar double
        heapPtr.add(0x18).writeS32(0);         // cambiar Smi (int pequeño)

        // Restaurar permisos
        Memory.protect(heapPtr, cls.size, 'r-x');

        console.log(`[MODIFIED] ${cls.name} field at offset 0x10`);
    }
});
```

#### 6.5.6. Ejemplo completo: interceptar llamadas HTTP

```javascript
var libapp = null;

function onLibappLoaded() {
    console.log('[+] libapp loaded at: ' + libapp);

    // Hook: función HTTP request (buscar en asm/ por "http|fetch|api")
    const httpFn = 0x45a2c0;  // ← REEMPLAZAR con offset real de asm/
    Interceptor.attach(libapp.add(httpFn), {
        onEnter: function () {
            init(this.context);
            try {
                let urlPtr = getArg(this.context, 0);
                let bodyPtr = getArg(this.context, 1);

                const [_, urlCls, url] = getTaggedObjectValue(urlPtr);
                const [__, bodyCls, body] = getTaggedObjectValue(bodyPtr);

                if (urlCls && urlCls.id === CidString) {
                    console.log('[HTTP] URL: ' + url);
                    console.log('[HTTP] Body: ' + JSON.stringify(body));
                }

                // Registrar timestamp
                this.startTime = Date.now();

            } catch(e) {
                    console.log('[HTTP Error] ' + e);
            }
        },
        onLeave: function (retval) {
            if (this.startTime) {
                console.log('[HTTP] Duration: ' + (Date.now() - this.startTime) + 'ms');
            }
            try {
                init(this.context);
                const [_, cls, val] = getTaggedObjectValue(retval);
                console.log('[HTTP] Response: ' + JSON.stringify(val));
            } catch(e) {}
        }
    });
}

function tryLoadLibapp() {
    try { libapp = Module.findBaseAddress('libapp.so'); } catch(e) {}
    if (libapp === null) {
        try { libapp = Process.findModuleByName('libapp.so'); if (libapp) libapp = libapp.base; } catch(e) {}
    }
    if (libapp === null) setTimeout(tryLoadLibapp, 500);
    else onLibappLoaded();
}
tryLoadLibapp();
```

#### 6.5.7. Ejemplo: listar clases disponibles en blutter_frida.js

El `blutter_frida.js` generado contiene un objeto `Classes` con todas las clases de Dart identificadas. Puedes inspeccionarlas:

```javascript
// Imprimir todas las clases encontradas por Blutter
function listClasses() {
    for (let cid in Classes) {
        let cls = Classes[cid];
        if (cls && cls.name) {
            console.log(`CID ${cid}: ${cls.name} (size: ${cls.size}, fields: ${cls.fbitmap.toString(16)})`);
        }
    }
}

// Llamar después de onLibappLoaded
// listClasses();
```

#### 6.5.8. Problemas comunes con blutter_frida.js

| Problema | Causa | Solución |
|----------|-------|----------|
| `Module.findBaseAddress is not a function` | Frida versión antigua | Usar `Process.findModuleByName('libapp.so').base` |
| `Uninitialized HeapAddress` | No se llamó `init(context)` en `onEnter` o `onLeave` | Llamar `init(this.context)` al inicio de cada callback |
| `TypeError: not a function` en `decompressPointer` | HeapAddress no inicializado o contexto incorrecto | Asegurar que `init()` se ejecute antes de cualquier `getTaggedObjectValue()` |
| `Cannot read properties of null` | La dirección hookeada no es una función Dart válida | Verificar el offset en asm/ — debe ser una entrada de función |
| `undefined` en nombres de clase | La clase no está en el mapa `Classes` | Revisar `objs.txt` para el CID, puede ser una clase nueva no mapeada |
| `frida: process crashed` después de escribir | Se violó W^X — memoria dejada como `rw-` | Restaurar siempre a `r-x` después de escribir |
| Blutter no reconoce `libflutter.so` | Versión de Flutter no soportada | Esperar actualización de Blutter o usar `--dart-version` manual |

#### 6.5.9. Usar Blutter con APK directamente (sin extraer)

Blutter soporta entrada directa como APK:

```bash
python3 blutter.py app.apk resultados/
```

Internamente extrae `lib/arm64-v8a/libapp.so` y `lib/arm64-v8a/libflutter.so` automáticamente.

Para especificar una versión de Dart sin `libflutter.so`:

```bash
python3 blutter.py libapp.so resultados/ --dart-version 3.4.2_android_arm64
```

#### 6.5.10. Forzar recompilación del binario Blutter

```bash
python3 blutter.py extracted_libs/ resultados/ --rebuild
```

Útil cuando actualizas Blutter con `git pull` y necesitas reconstruir el ejecutable para la versión de Dart de tu app.

---

## 7. SSL Pinning Bypass

Flutter's SSL verification lives in BoringSSL inside `libflutter.so`, NOT in Java/Kotlin layers. The target function is `ssl_crypto_x509_session_verify_cert_chain` in `ssl_x509.cc`.

### Method A: reFlutter — Workflow Completo

reFlutter es la forma más fácil de bypassear SSL pinning en Flutter. Parchea el engine a nivel binario recompilando `libflutter. 
#### Instalación

```bash
# Instalar reFlutter
pip3 install reflutter==0.8.6

# Verificar
reflutter --help
```

#### Pre-requisito: Obtener Snapshot Hash

reFlutter necesita coincidir la versión exacta de Flutter de la app. Obtén el snapshot hash primero:

```bash
# Extraer libapp.python3 -c "
import sys
with open('libapp.so', 'rb') as f:
    data = f.read()
    # Buscar snapshot hash (primeros 32 bytes después del header ELF)
    # El hash aparece como string legible tipo "a1b2c3d4..."
    import re
    matches = re.findall(b'[a-f0-9]{32}', data)
    if matches:
        print('Snapshot hash:', matches[0].decode())
"

# O usar Blutter (que lo detecta automáticamente)
python3 blutter.py libapp.so /tmp/blutter_out/
# La primera línea de salida muestra: "Flutter version: X.Y.Z, snapshot: <hash>"
```

#### Ejecución Paso a Paso

```bash
# 1. Asegúrate de que el APK NO esté dividido (merge splits primero si es necesario)
#    Ver: Sección 2 (APK Extraction and Preparation)

# 2. Ejecutar reFlutter
reflutter merged.apk

# El script te pedirá:
# - "Enter proxy IP:" → pon la IP de tu Burp/mitmproxy (ej: 192.168.1.50)
#   (si no quieres proxy, pon 0.0.0.0)
# - "Enter proxy port:" → pon el puerto (ej: 8080)
#
# Tiempo: 5-15 minutos (clona y recompila Flutter Engine)

# 3. Resultado: release.RE.apk en el mismo directorio
ls -lh release.RE.apk

# 4. Firmar con uber-apk-signer
java -jar uber-apk-signer.jar --allowResign -a release.RE.apk

# 5. Instalar
adb install -r release.RE.signed.apk
```

#### Qué Hace reFlutter Internamente

```
1. Descomprime el APK
2. Lee lib/arm64-v8a/libflutter.3. Clona el repositorio flutter/engine commit que coincide con esa versión
4. Parchea ssl_x509.cc:
   - Función: ssl_crypto_x509_session_verify_cert_chain()
   - Cambio: force return 1 (siempre confía en el cert)
5. Opcionalmente parchea socket.cc:
   - Hardcodea la IP del proxy en Dart's socket layer
   - Esto hace que Dart use el proxy aunque ignore las settings del sistema
6. Recompila libflutter.7. Reemplaza lib/arm64-v8a/libflutter.8. Reempaqueta el APK
```

#### Verificar que el Parche Funcionó

```bash
# 1. Lanzar app con Frida para ver logs
frida -U -f com.target.app -l check_reflutter.js

# check_reflutter.js:
Java.perform(function() {
    console.log("[+] App launched");
    // Si ves tráfico en Burp → reFlutter funcionó
    // Si ves "Certificate pinning failed" → no funcionó
});

# 2. Verificar en Burp:
# Proxy → HTTP History → ¿Aparecen requests HTTPS de la app?

# 3. Verificar que libflutter.adb shell "strings /data/app/com.target.app/lib/arm64/libflutter.so | grep -i 'return 1'"
# Debería aparecer el string del parche
```

#### Builds Pre-parcheados (Ahorra Tiempo)

El mantenedor de reFlutter sube builds pre-parcheados para hashes comunes:

```bash
# Visitar: https://github.com/Impact-I/reFlutter/releases
# Buscar tu snapshot hash en la lista
# Si existe: descargar libflutter.zip → reemplazar en tu APK manualmente
```

#### Troubleshooting de reFlutter

| Error | Causa | Solución |
|-------|--------|----------|
| `Failed to find snapshot hash` | libapp.so corrupto o no es Flutter | Verificar con `file libapp.so` |
| `git clone flutter/engine failed` | Sin internet o rate limit de GitHub | Usar `--offline` si ya clonaste antes, o hacer `git config --global url."https://github.com/".insteadOf git@github.com:` |
| `CMake error` / `Ninja not found` | Faltan dependencias de compilación | `sudo apt install cmake ninja-build clang` |
| `release.RE.apk` no se instala (`INSTALL_FAILED_VERIFICATION`) | Firma inválida | Usar `uber-apk-signer` o `apksigner` explícitamente |
| App crashea al lanzar (SIGSEGV) | reFlutter compiló `libflutter.so` incompatible | Usar Method B (PyGhidra) o Method D (offset-based) en su lugar |
| Tráfico no aparece en Burp tras parchear | Proxy IP mal configurada o Dart no usa socket parcheado | Verificar IP/port; usar `iptables` (Sección 8, Opción 2) como respaldo |

#### Alternativa: Parchear libflutter.so Manualmente (Sin reFlutter)

Si reFlutter falla, puedes parchear `ssl_x509.cc` a mano:

```bash
# 1. Clonar flutter/engine (la versión que usa la app)
git clone https://github.com/flutter/engine.git flutter_engine
cd flutter_engine
git checkout <commit_hash_de_la_version>

# 2. Parchear ssl_x509.cc
sed -i 's/return 0;/return 1;/g' src/third_party/boringssl/src/ssl/ssl_x509.cc
# O parchear la función ssl_crypto_x509_session_verify_cert_chain específicamente

# 3. Compilar (sigue las instrucciones de flutter/engine para build on-device)
# Esto es COMPLEJO y requiere GN + Ninja + depot_tools
# Solo recomendado si reFlutter falla consistentemente
```

**Recomendación:** Si reFlutter falla, usa **Method D** (offset-based hook con Frida) en su lugar. Es mucho más rápido.

### Method B: PyGhidra Auto-Generation (Recommended)

```bash
pip install pyghidra
# Requires Ghidra installed

# Auto-generate Frida + Renef scripts
python3 flutter_ssl_pinning.py extracted_libs/libflutter.so

# Run generated script
frida -U -f com.target.app -l flutter_ssl_pinning.js
```

**How it works:**
1. PyGhidra scans `libflutter.so` for `"ssl_client"` string
2. Follows XREFs to find the 3-parameter function (ssl_crypto_x509_session_verify_cert_chain)
3. Bakes the RVA into generated Frida/Renef scripts

### Method C: Manual Pattern Scan (Frida)

Find the function first using Ghidra (search `"ssl_client"` string → XREFs → 3-param function → capture first bytes), then:

```javascript
// x86-64 pattern (SensePost/2025)
var sig = "55 41 57 41 56 41 55 41 54 53 48 83 EC 38 C6 02";

// ARM64 pattern (varies per Flutter version — derive from Ghidra)
// var sig = "F? 5? 0? A9 F? ?? 03 A9 ?? ?? ?? ??";

var flutter = Process.getModuleByName("libflutter.so");
Memory.scan(flutter.base, flutter.size, sig, {
    onMatch: function (addr) {
        console.log("[+] ssl_verify found at: " + addr);
        Interceptor.attach(addr, {
            onLeave: function (retval) {
                retval.replace(0x1);  // force true
            }
        });
    },
    onComplete: function () { console.log("scan done"); }
});
```

### Method D: Offset-Based Hook (Most Portable)

```javascript
// Pre-computed offset from Ghidra analysis
// offset = ssl_crypto_x509_session_verify_cert_chain - JNI_OnLoad

function disablePinning() {
    var m = Process.findModuleByName("libflutter.so");
    var jniAddr = m.enumerateExports()[0].address;  // JNI_OnLoad
    var offset = ptr('0x0027b624');  // pre-computed per app version
    var sslAddr = jniAddr.add(offset);

    console.log("[+] libflutter.so at: " + m.base);
    console.log("[+] SSL verify at: " + sslAddr);

    Interceptor.attach(sslAddr, {
        onEnter: function(args) { console.log("[+] SSL validation disabled"); },
        onLeave: function(retval) {
            console.log("[+] retval: " + retval + " -> 0x1");
            retval.replace(0x1);
        }
    });
}
setTimeout(disablePinning, 1000);
```

### Method E: Patching ssl_verify_peer_cert (NVISO Approach)

Hook at an earlier point in the call chain — `ssl_verify_peer_cert` in `handshake.cc`:

```javascript
// Hook ssl_verify_peer_cert and replace with return 0
// This disables BOTH default SSL validation AND custom_verify_callback

function hook_ssl_verify_peer_cert(address) {
    Interceptor.replace(address, new NativeCallback(function(pathPtr, flags) {
        console.log("[+] Certificate validation disabled");
        return 0;  // ssl_verify_ok
    }, 'int', ['pointer', 'int']));
}

// Find via pattern scan (ARM64 pattern from NVISO)
var sig = "?? ?? ?? ?? ?? ?? ?? ?? ?? ?? ?? ?? F? 4? 0? A9";
// ... or use memory patterns from NVISO repo
```

### Four-Tier BoringSSL Resolution (apkre)

When symbols are stripped, use this priority:

| Tier | Technique | When |
|------|-----------|------|
| 1 | Exported symbol lookup | Debug builds, custom-compiled apps |
| 2 | ARM64 ADRP+ADD cross-reference from error strings | Release builds (most common) |
| 3 | Prologue pattern scan (`STP X29, X30` + `CBZ X0`) | When Tier 2 is noisy |
| 4 | reFlutter binary patching | When all runtime approaches fail |

---

## 8. Traffic Interception

### Why Standard Proxy Doesn't Work

- Dart's HTTP client routes directly, ignoring Android system proxy
- BoringSSL uses its own CA store inside `libflutter.so`
- No CONNECT request is sent to the proxy

### Option 1: Android Studio Emulator Proxy

```
Settings → Proxy → Manual proxy configuration
Host: 127.0.0.1, Port: 8080
```

This forces ALL traffic through the proxy at the hardware/simulation level. Works for emulator only.

### Option 2: iptables + adb reverse (Physical Device)

```bash
# Root required
adb shell su -c "iptables -t nat -A OUTPUT -p tcp -d <target_host> --dport 443 -j DNAT --to-destination 127.0.0.1:8080"
adb reverse tcp:8080 tcp:8080

# Start Burp as invisible proxy
# Proxy → Options → Support invisible proxying = True
```

### Option 3: Frida Socket Redirect (Fluttida / Flutter-Proxy-Unlocker)

```bash
# Configure proxy IP in script
# Edit FlutterProxy.js: BURP_PROXY_IP = "192.168.x.x"; BURP_PROXY_PORT = 8080;

frida -Uf com.target.app -l FlutterProxy.js
```

### Option 4: reFlutter Hardcoded Proxy

reFlutter can hardcode proxy into `socket.cc` during rebuild. Configure via IP prompt during `reflutter` execution.

### Option 5: Android Global Proxy (Flutter 3.24.0+)

```bash
# Starting from Flutter 3.24.0, hardcoded proxy removed
# Configure directly on device:
adb shell "settings put global http_proxy <proxy_ip:port>"
```

### Option 6: DNS Spoofing + Evil AP

Set up a rogue Wi-Fi access point pointing target hostnames to your Burp instance. Combined with Burp invisible proxy mode.

### Complete Workflow

```
1. Bypass SSL pinning (Method A-E from Section 7)
2. Route traffic to proxy (Option 1-6 above)
3. Install Burp CA in system store (for non-Flutter traffic)
4. Start Burp with invisible proxy mode
5. Launch app → traffic appears in HTTP History
```

---

## 9. Dart VM Internals

Understanding the Dart VM is essential for advanced patching (colors, theme objects, runtime modification).

### Object Model

```
Tagged Pointer (compressed):
  Bit 0 = 1 → Heap Object (pointer to object - 1)
  Bit 0 = 0 → Smi (Small Integer, value >> 1)

Object Header (first 8 bytes):
  Bits 0-11:  tag bits
  Bits 12-31: Class ID (CID)
  Bits 32+:   other metadata
```

### Key CIDs (Class IDs)

| CID | Name | Notes |
|-----|------|-------|
| 45 | Object | Base class |
| 57 | Closure | Function closures |
| 60 | _Smi | Small integers (tagged) |
| 61 | int | Heap-allocated integers |
| 62 | double | 64-bit IEEE 754 |
| 63 | bool | Single byte |
| 86 | Map | Linked hash map |
| 88 | Set | Linked hash set |
| 90 | List | Fixed-length array |
| 92 | GrowableList | Dynamic array |
| 94 | String | UTF-8 strings |
| 95 | TwoByteString | UTF-16 strings |
| 171 | Null | Dart null value |

### QK (Color) Objects

Colors in Flutter are `Color` objects with CID typically in the QK range. Each has 4 `double` fields representing ARGB components (0.0-1.0):

```
[pp+0x15d90] Obj!QK@74bd11 : {
  off_8:  double(1),           // Alpha
  off_10: double(0.15294117647058825),  // Red (= 0x27/0xFF)
  off_18: double(0.5098039215686274),   // Green (= 0x82/0xFF)
  off_20: double(1),           // Blue
  off_28_Obj!XK@760c01         // Type arguments (Color class)
}
```

**To patch a color at runtime:**
```javascript
// Write new double values to the QK object
var colorBase = libapp.add(0x15d90);  // pp+ offset
colorBase.add(0x08).writeDouble(1.0);    // Alpha
colorBase.add(0x10).writeDouble(0.1);    // Red (dark)
colorBase.add(0x18).writeDouble(0.1);    // Green (dark)
colorBase.add(0x20).writeDouble(0.1);    // Blue (dark)
```

**Important:** Only QK objects with `double()` values respond to `writeDouble`. Objects with `int(0x0)` are ambiguous (Smi vs double(0.0)) and often not referenced by UI code.

### Compressed Pointers

Dart uses compressed 32-bit pointers stored in the heap. Decompression requires the heap base from register X28:

```javascript
var HeapAddress = context['x28'].shl(32);

function decompressPointer(dptr) {
    return HeapAddress.add(dptr.toInt32());
}
```

### Memory Protection

When patching heap objects:
- Original permissions: `r-x` (read + execute)
- Change to `rwx` to write
- **Restore to `r-x`** after writing (do NOT leave as `rw-`)
- Protect the **object base address**, not `object + 0x10` (avoid crossing page boundaries)

### Object Pool (pp) Structure

The Object Pool is a flat array of tagged values referenced by `pp+<offset>`:

```
pp+0x15d90  → QK Color (AEMET Blue)
pp+0x16ec8  → QK Color (DarkBlue)
pp+0x16c00  → QK Color (White)
pp+0x2b6f0  → QK Color (LightGray)
pp+0x2b928  → QK Color (Light Blue — ONLY ONE referenced in UI code!)
```

**Critical lesson:** Out of 473 QK objects in the pool, only 1 (`0x2b928`) is directly referenced in UI code (asm/ files). Most UI colors are inlined as ARM64 immediates or embedded in TextStyle/ThemeData constructors — not standalone pool entries.

---

## 10. Runtime Color/Theme Modification

### Working Pipeline (Proven)

```
APKEditor m → merge splits
APKEditor d → decode
AndroidManifest → extractNativeLibs="true"
Add to lib/arm64-v8a/:
  libfrida-gadget.so        (Frida Gadget binary)
  libfrida-gadget.config.so (JSON: {"interaction":{"type":"script","path":"libfrida-gadget.script.so"}})
  libfrida-gadget.script.so (JS script with color patches)
Smali: System.loadLibrary("frida-gadget") in MainActivity.onCreate
APKEditor b → rebuild
apksigner sign → adb install
```

### Frida Script for Color Patching

```javascript
var libapp = null;
var libappBase = null;

function patchColors() {
    // QK objects with double() values — verified in pp.txt
    var patches = [
        { offset: 0x15d90, name: "Primary BG",      alpha: 0.10, r: 0.10, g: 0.10, b: 0.10 },
        { offset: 0x16ec8, name: "Secondary Blue",   alpha: 0.10, r: 0.10, g: 0.10, b: 0.10 },
        { offset: 0x16c00, name: "Card Surface",     alpha: 0.18, r: 0.18, g: 0.18, b: 0.18 },
        { offset: 0x2b6f0, name: "Light Surface",    alpha: 0.18, r: 0.18, g: 0.18, b: 0.18 },
        { offset: 0x307a0, name: "Light BG",         alpha: 0.18, r: 0.18, g: 0.18, b: 0.18 },
        { offset: 0x5cb80, name: "Material Blue",    alpha: 0.10, r: 0.10, g: 0.10, b: 0.10 },
    ];

    patches.forEach(function(p) {
        try {
            var base = libappBase.add(p.offset);
            // Change memory protection to writable
            Memory.protect(base, 0x20, 'rwx');
            base.add(0x08).writeDouble(p.alpha);
            base.add(0x10).writeDouble(p.r);
            base.add(0x18).writeDouble(p.g);
            base.add(0x20).writeDouble(p.b);
            // Restore to r-x
            Memory.protect(base, 0x20, 'r-x');
            console.log('[+] Patched: ' + p.name);
        } catch(e) {
            console.log('[-] Failed: ' + p.name + ' — ' + e);
        }
    });
}

function tryLoad() {
    try { libapp = Process.findModuleByName('libapp.so'); } catch(e) {}
    if (libapp === null) setTimeout(tryLoad, 500);
    else setTimeout(function() {
        libappBase = libapp.base;
        patchColors();
    }, 3000);  // 3s delay for Dart_Initialize to complete
}
tryLoad();
```

### Why Remaining Colors Are Hard

- Most UI colors are **inlined as ARM64 immediates** in instruction operands
- Or embedded in `TextStyle`/`ThemeData` constructor calls
- Or computed at runtime from theme inheritance chains
- Only 1 of 1372 `pp+` references in actual UI code points to a QK object

**Next steps for full dark mode:**
1. Hook Skia/Impeller drawing functions to capture colors at render time
2. Search `IMM` entries in pp.txt for ARGB hex values
3. Hook `android_dlopen_ext` for reliable timing (replace 3s setTimeout)

---

## 11. Frida Gadget Embedding

For persistent instrumentation without `frida-server`:

### File Structure in APK

```
lib/arm64-v8a/
├── libapp.so
├── libflutter.so
├── libfrida-gadget.so          ← Frida Gadget binary
├── libfrida-gadget.config.so   ← JSON config (MUST end in .so)
└── libfrida-gadget.script.so   ← JavaScript script (MUST end in .so)
```

### Config File

```json
{
  "interaction": {
    "type": "script",
    "path": "libfrida-gadget.script.so"
  }
}
```

### Critical: File Naming Convention

Android's native library extractor only copies files ending in `.so` from `lib/<abi>/`. The Gadget binary looks for its config by replacing the `.so` extension in its own filename:

| File | Name |
|------|------|
| Gadget binary | `libfrida-gadget.so` |
| Config | `libfrida-gadget.config.so` |
| Script | `libfrida-gadget.script.so` |

**Do NOT use** names like `.config` or `.js` — Android won't extract them.

### Smali Injection

Edit `smali/classes6/es/aemet/MainActivity.smali`:

```smali
.method protected onCreate(Landroid/os/Bundle;)V
    .locals 3
    const-string v0, "frida-gadget"
    invoke-static {v0}, Ljava/lang/System;->loadLibrary(Ljava/lang/String;)V
    # ... rest of original onCreate ...
```

### Manifest Change

```xml
android:extractNativeLibs="true"
```

---

## 12. Obfuscation Awareness

Flutter obfuscation (`--obfuscate --split-debug-info`) only:
- Renames symbols (function/class names become random strings)
- Stores symbol map externally for developer use (`flutter symbolize`)

It does **NOT**:
- Encrypt `flutter_assets`
- Prevent native disassembly of `libapp.so`
- Stop runtime hooks
- Hide string constants in Object Pool

### Recovering Obfuscated Names

1. **Obfuscation map** — if developers leak `--split-debug-info` output or obfuscation-map JSON
2. **DWARF symbols** — if debug info was not stripped
3. **reFlutter dump** — runtime class/function dump
4. **unflutter** — recovers names from snapshot metadata regardless of obfuscation

### CI/CD Artifact Search

```bash
# Check for leaked debug symbols
find . -name "*.symbols" -o -name "SYMBOLS" -o -name "obfuscation-map*.json"
find . -name "app.*.dwarf" -o -name "split-debug-info"
```

---

## 13. Tool Reference

### Installation Quick Reference

| Tool | Install | Command |
|------|---------|---------|
| Blutter | `git clone` + cmake build | `python3 blutter.py <lib_dir|apk> <out_dir> [--rebuild] [--no-analysis] [--dart-version X.Y.Z_android_arm64]` |
| unflutter | `go install` or `make build` | `unflutter <libapp.so>` |
| flutterdec | Nix, binary, or cargo | `flutterdec decompile <apk> -o <out>` |
| r2flutter | `make && make user-install` | `r2flutter -f <libapp.so>` |
| reFlutter | `pip3 install reflutter` | `reflutter <apk>` |
| disrobe | Binary or cargo | `disrobe flutter decompile <libapp.so> --out <out>` |
| apkre | `pip install apkre[all]` | `apkre analyze --package <pkg>` |
| PyGhidra | `pip install pyghidra` | `python3 flutter_ssl_pinning.py <libflutter.so>` |

### External Tools

| Tool | Purpose | Install |
|------|---------|---------|
| APKEditor | Merge/split/rebuild APKs | GitHub release JAR |
| Ghidra | Disassembly + decompilation | `brew install ghidra` |
| IDA Pro | Disassembly + Hex-Rays | Commercial |
| Radare2 | Binary analysis | `brew install radare2` |
| Frida | Dynamic instrumentation | `pip install frida-tools` |
| mitmproxy | HTTP/HTTPS proxy | `brew install mitmproxy` |
| Burp Suite | HTTP/HTTPS proxy | PortSwigger |
| jadx | DEX decompilation | `brew install jadx` |
| apktool | APK decode/rebuild | `brew install apktool` |

---

## 14. Common Pitfalls

| Mistake | Why It Fails | Fix |
|---------|-------------|-----|
| Patch AOT snapshot bytes directly | Compressed format with relative pointers — corrupts object graph | Use runtime instrumentation (Frida Gadget) |
| Use `apktool b` on merged splits | aapt2 rejects `_` prefixed resource names | Use `APKEditor b` instead |
| Place Frida script at `/data/local/tmp/` | SELinux `untrusted_app` can't read `shell_data_file` | Embed script inside APK as `.script.so` |
| Hook `Dart_Initialize` | Symbol not exported in `libflutter.so` | Use `setTimeout(3000)` or hook `android_dlopen_ext` |
| Use `settings put global http_proxy` | Dart ignores Android system proxy | Use iptables, Frida socket redirect, or emulator proxy |
| Patch QK objects with `int(0x0)` values | May be Smi(0) not double(0.0); may not be referenced by UI | Only patch QKs with confirmed `double()` values from pp.txt |
| Leave memory as `rw-` after patching | Violates Android W^X policy → crash | Restore to `r-x` after writing |
| Protect `object + 0x10` instead of base | May cross page boundary | Protect the object base address |

---

## 15. References

### Essential Reading

- **HackTricks Flutter** — https://hacktricks.wiki/en/mobile-pentesting/android-app-pentesting/flutter.html
- **SensePost Blog** — "Going Full Hardcore Mode with Frida" (2025) — https://sensepost.com/blog/2025/intercepting-https-communication-in-flutter-going-full-hardcore-mode-with-frida/
- **NVISO Labs** — "Intercept Flutter traffic on iOS and Android" (2022) — https://blog.nviso.eu/2022/08/18/intercept-flutter-traffic-on-ios-and-android-http-https-dio-pinning/
- **Intuity** — "Bypassing Certificate Pinning on Flutter-based Android Apps" (2024) — https://www.intuity.it/en/2024/05/07/bypassing-certificate-pinning-on-flutter-based-android-apps-a-new-guide-2/
- **Guardsquare** — "Obstacles in Dart Decompilation" — https://www.guardsquare.com/blog/obstacles-in-dart-decompilation-and-the-impact-on-flutter-app-security

### Tool Repositories

- **Blutter** — https://github.com/worawit/blutter
- **unflutter** — https://github.com/zboralski/unflutter
- **flutterdec** — https://github.com/caverav/flutterdec
- **reFlutter** — https://github.com/Impact-I/reFlutter
- **r2flutter** — https://github.com/trufae/r2flutter
- **disrobe** — https://github.com/1-3-7/disrobe
- **universal-flutter-ssl-pinning** — https://github.com/vichhka-git/universal-flutter-ssl-pinning
- **Fluttida** — https://github.com/XDcobra/Fluttida
- **Flutter-Proxy-Unlocker** — https://github.com/arthghori/Flutter-Proxy-Unlocker
- **disable-flutter-tls-verification** — https://github.com/NVISOsecurity/disable-flutter-tls-verification
- **apkre** — https://github.com/schwarztim/apkre

### Educational Resources

- **Flutter-Reverse-Engineering-Labs** — https://github.com/brnpl/Flutter-Reverse-Engineering-Labs (9 progressive challenges)
- **flutter-re-demo** — https://github.com/Guardsquare/flutter-re-demo (Guardsquare research scripts)
- **androidReverse** — https://github.com/UltraSina/androidReverse (on-device RE suite)

### Dart VM Internals

- **mrale.ph** (Vyacheslav Egorov) — Dart VM engineer blog: pointer tagging, Object Pool, AOT optimization
- **flutter/engine** source — `runtime/` for Dart_Initialize, snapshot memory layout
- **dart-lang/sdk Wiki** — Heap snapshot serialization format

### BoringSSL Source

- **ssl_x509.cc** — https://github.com/google/boringssl/blob/main/ssl/ssl_x509.cc (target: `ssl_crypto_x509_session_verify_cert_chain`)

---

## 16. Caso de Estudio Completo: App Bancaria Flutter (SSL Pinning + Dark Mode)

Este caso demuestra el flujo completo de RE en una app Flutter de banca (ficticia: "BancoEjemplo"). La app tiene SSL pinning y solo modo claro. El objetivo es: (1) interceptar tráfico, (2) forzar modo oscuro.

### 16.1. Extracción del APK

```bash
# La app tiene splits (ARM64 + x86_64 + locales)
adb shell pm list packages | grep bancoejemplo
# com.bancoejemplo.app

# Extraer splits
mkdir -p /tmp/banco_apk
adb pull /data/app/~~randomstring==/com.bancoejemplo.app-XYZ==/base.apk /tmp/banco_apk/
adb pull /data/app/~~randomstring==/com.bancoejemplo.app-XYZ==/split_config.arm64_v8a.apk /tmp/banco_apk/
adb pull /data/app/~~randomstring==/com.bancoejemplo.app-XYZ==/split_config.es.apk /tmp/banco_apk/
adb pull /data/app/~~randomstring==/com.bancoejemplo.app-XYZ==/split_config.xxhdpi.apk /tmp/banco_apk/

# Merge con APKEditor
java -jar APKEditor.jar m -i /tmp/banco_apk -o /tmp/banco_merged.apk

# Verificar que libapp.so está presente
unzip -l /tmp/banco_merged.apk | grep libapp.so
```

### 16.2. Triaje Rápido

```bash
# Identificar versión de Flutter
python3 get_snapshot_hash.py /tmp/banco_merged.apk
# Output: Snapshot hash: a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4
# Buscar en tabla de reFlutter:
curl -s https://raw.githubusercontent.com/Impact-I/reFlutter/main/enginehash.csv | grep a1b2c3d4
# Output: a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4,3.24.5,...

# Verificar si es debug build
unzip -l /tmp/banco_merged.apk | grep kernel_blob
# (No output = release build, continúar)

# Extracción rápida de strings
mkdir -p /tmp/banco_libs
unzip -j /tmp/banco_merged.apk "lib/arm64-v8a/libapp.so" "lib/arm64-v8a/libflutter.so" -d /tmp/banco_libs/

strings /tmp/banco_libs/libapp.so | grep -iE "https?://|api|token|secret|password" | head -20
# Posibles hallazgos:
#   https://api.bancoejemplo.com/v1/login
#   https://api.bancoejemplo.com/v1/accounts
#   Authorization: Bearer
#   supabase_key_android
```

### 16.3. Análisis Estático con Blutter

```bash
# Ejecutar Blutter
python3 blutter.py /tmp/banco_merged.apk /tmp/banco_blutter_out/

# Explorar funciones
ls /tmp/banco_blutter_out/asm/ | grep -iE "login|auth|account|transfer"

# Ejemplo de salida:
# com.bancoejemplo.auth.LoginScreen@handleLogin.dart
# com.bancoejemplo.api.ApiService@makeRequest.dart
# com.bancoejemplo.home.HomeScreen@build.dart

# Inspeccionar función de login
cat "/tmp/banco_blutter_out/asm/com.bancoejemplo.auth.LoginScreen@handleLogin.dart"

# Buscar referencias a URLs en el Object Pool
grep -n "api.bancoejemplo.com" /tmp/banco_blutter_out/pp.txt
# Output:
# [pp+0x3c820] Obj!XK@740301 : "https://api.bancoejemplo.com/v1/login"
# [pp+0x3c840] Obj!XK@740301 : "https://api.bancoejemplo.com/v1/accounts"

# Buscar colores (para Dark Mode)
grep "Obj!QK" /tmp/banco_blutter_out/pp.txt | head -10
# Output (ejemplo):
# [pp+0x15d90] Obj!QK@74bd11 : { off_8: double(1), off_10: double(1), ... }  ← Blanco (0xffffffff)
# [pp+0x16ec8] Obj!QK@74bd11 : { off_8: double(1), off_10: double(0), ... }  ← Azul primario
```

### 16.4. Bypass de SSL Pinning con reFlutter

```bash
# Instalar reFlutter (si no está)
pip3 install reflutter==0.8.6

# Parchear APK
reflutter /tmp/banco_merged.apk
# Prompts:
#   Enter proxy IP: 192.168.1.100   (IP de tu Burp/mitmproxy)
#   Enter proxy port: 8080

# Resultado: release.RE.apk en /tmp/

# Firmar
java -jar uber-apk-signer.jar --allowResign -a /tmp/release.RE.apk

# Instalar
adb install -r /tmp/release.RE.signed.apk
```

### 16.5. Intercepción de Tráfico

```bash
# Configurar Burp Suite:
# 1. Proxy → Options → Add → Port 8080, Bind to address: All interfaces
# 2. Proxy → Options → Request handling → Support invisible proxying: CHECKED

# Lanzar app con Frida para ver logs
frida -U -f com.bancoejemplo.app -l check_traffic.js

# check_traffic.js:
Java.perform(function() {
    console.log("[+] App launched with reFlutter patch");
});

# Verificar en Burp:
# Proxy → HTTP History → ¿Aparecen requests a api.bancoejemplo.com?
```

### 16.6. Análisis Dinámico con Frida (+ Blutter)

```bash
# Usar blutter_frida.js generado por Blutter
cp /tmp/banco_blutter_out/blutter_frida.js /tmp/banco_hook.js

# Editar /tmp/banco_hook.js y añadir hooks:
```

```javascript
// /tmp/banco_hook.js (añadir al final):
function onLibappLoaded() {
    console.log('[+] libapp loaded, hooking functions...');

    // Hook: Login function (offset desde asm/)
    const login_fn = 0x3b24e0;  // ← Reemplazar con offset real
    Interceptor.attach(libapp.add(login_fn), {
        onEnter: function() {
            init(this.context);
            let userPtr = getArg(this.context, 0);
            let passPtr = getArg(this.context, 1);
            const [_, __, user] = getTaggedObjectValue(userPtr);
            const [___, ____, pass] = getTaggedObjectValue(passPtr);
            console.log(`[LOGIN] user=${user} pass=${pass}`);
        }
    });

    // Hook: API requests
    const api_fn = 0x45a2c0;  // ← Offset de ApiService.makeRequest
    Interceptor.attach(libapp.add(api_fn), {
        onEnter: function() {
            init(this.context);
            let urlPtr = getArg(this.context, 0);
            const [_, __, url] = getTaggedObjectValue(urlPtr);
            console.log(`[API] URL: ${url}`);
            this.url = url;
        },
        onLeave: function(retval) {
            init(this.context);
            const [_, cls, val] = getTaggedObjectValue(retval);
            console.log(`[API] Response: ${JSON.stringify(val).substring(0, 200)}...`);
        }
    });
}

function tryLoadLibapp() {
    try { libapp = Module.findBaseAddress('libapp.so'); } catch(e) {}
    if (libapp === null) setTimeout(tryLoadLibapp, 500);
    else onLibappLoaded();
}
tryLoadLibapp();
```

```bash
# Ejecutar
frida -U -f com.bancoejemplo.app -l /tmp/banco_hook.js --no-pause

# La app se lanza → hacer login → ver credenciales en consola de Frida
```

### 16.7. Parcheo de Colores (Dark Mode) con Frida Gadget

```bash
# Decodificar APK parcheado (release.RE.signed.apk)
java -jar APKEditor.jar d -i /tmp/release.RE.signed.apk -o /tmp/banco_decoded

# Verificar que extractNativeLibs="true" en AndroidManifest.xml
grep extractNativeLibs /tmp/banco_decoded/AndroidManifest.xml
# Si no está: añadir android:extractNativeLibs="true" al <application>

# Añadir Frida Gadget
cp /home/usuario/.local/share/frida/android/arm64/frida-gadget.so \
   /tmp/banco_decoded/lib/arm64-v8a/libfrida-gadget.so
cp .opencode/skills/flutter-reverse-engineering/frida_gadget_config.json \
   /tmp/banco_decoded/lib/arm64-v8a/libfrida-gadget.config.so

# Crear script de parcheo de colores (libfrida-gadget.script.so)
cat > /tmp/dark_mode_patch.js << 'EOF'
var libappBase = null;

function patchDarkMode() {
    // Offsets desde pp.txt (ejemplo, usar los reales de tu app)
    var darkPatches = [
        { offset: 0x15d90, name: "Background",    a:1.0, r:0.12, g:0.12, b:0.12 },
        { offset: 0x16ec8, name: "Primary Blue",  a:1.0, r:0.20, g:0.20, b:0.22 },
        { offset: 0x16c00, name: "Card Surface",  a:1.0, r:0.18, g:0.18, b:0.18 },
    ];
    darkPatches.forEach(function(p) {
        try {
            var base = libappBase.add(p.offset);
            Memory.protect(base, 0x20, 'rwx');
            base.add(0x08).writeDouble(p.a);
            base.add(0x10).writeDouble(p.r);
            base.add(0x18).writeDouble(p.g);
            base.add(0x20).writeDouble(p.b);
            Memory.protect(base, 0x20, 'r-x');
            console.log('[+] Patched: ' + p.name);
        } catch(e) { console.log('[-] Failed: ' + p.name); }
    });
}

function tryLoad() {
    var m = Process.findModuleByName('libapp.so');
    if (m === null) setTimeout(tryLoad, 500);
    else {
        libappBase = m.base;
        setTimeout(patchDarkMode, 3000);  // Esperar a Dart_Initialize
    }
}
tryLoad();
EOF

# Empaquetar script como .so (Android solo extrae .so)
cp /tmp/dark_mode_patch.js /tmp/banco_decoded/lib/arm64-v8a/libfrida-gadget.script.so

# Inyectar System.loadLibrary en smali
# Editar smali/classesX/com/bancoejemplo/MainActivity.smali:
```

```smali
# En onCreate():
.method protected onCreate(Landroid/os/Bundle;)V
    .locals 3
    const-string v0, "frida-gadget"
    invoke-static {v0}, Ljava/lang/System;->loadLibrary(Ljava/lang/String;)V
    # ... resto del código original ...
```

```bash
# Reconstruir APK
java -jar APKEditor.jar b -i /tmp/banco_decoded -o /tmp/banco_dark.apk

# Firmar
java -jar uber-apk-signer.jar --allowResign -a /tmp/banco_dark.apk

# Instalar y probar
adb install -r /tmp/banco_dark.signed.apk
adb shell am force-stop com.bancoejemplo.app
adb shell monkey -p com.bancoejemplo.app -c android.intent.category.LAUNCHER 1
# La app se lanza → Frida Gadget se inyecta automáticamente → colores cambiados a dark
```

### 16.8. Resultados Esperados

```
✓ Tráfico HTTPS visible en Burp Suite (reFlutter bypass)
✓ Credenciales de login capturadas en consola Frida
✓ Respuestas de API visibles en consola Frida
✓ App se ve en modo oscuro (colores parcheados)
```

### 16.9. Troubleshooting del Caso

| Problema | Causa | Solución |
|----------|--------|-----------|
| reFlutter tarda >30 min | Compilación de Flutter Engine | Usar builds pre-parcheados de GitHub releases |
| Frida no encuentra funciones | Offsets incorrectos | Verificar en `asm/` que el offset es de una función (no datos) |
| Colores no cambian | Offsets de pp.txt incorrectos o colores inlined | Buscar en `asm/` por inmediatos ARM64 (`0x3fXXXXXX` = floats) |
| App crashea con Frida Gadget | Conflicto con `extractNativeLibs` | Asegurar `extractNativeLibs="true"` en Manifest |
| Burp no ve tráfico | Proxy IP incorrecta o Dart no usa socket parcheado | Verificar IP; usar `iptables` (Sección 8) como respaldo |

---

## Skills relacionados

- **`android-reverse-engineering`** — RE general de APKs Android (Java, Kotlin, nativo, SSL pinning, root bypass, Frida, MASTG). Contiene un resumen de triaje Flutter que remite a este skill para análisis profundo.
- **`apk-modding`** — Playbook operativo para modificar, parchear y hackear APKs (smali patching, signature killers, PairipCore bypass, Frida Gadget). Usar cuando el objetivo sea modificar el comportamiento de la app Flutter.
- **`ghidra-pyghidra`** — Ghidra + pyghidra para análisis binario. Usar para análisis estático profundo de `libapp.so` y `libflutter.so` cuando blutter no sea suficiente.
- **`httptoolkit-android`** — HTTP Toolkit en Android. Usar para captura de tráfico cuando reFlutter no sea viable o se necesite un enfoque alternativo.
- **`android-cleanup`** — Limpieza post-pentesting. Usar después de sesiones de dynamic analysis con Frida o reFlutter.
- **handshake.cc** — https://github.com/google/boringssl/blob/main/ssl/handshake.cc (target: `ssl_verify_peer_cert`)
