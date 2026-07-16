---
name: flutter-reverse-engineering
description: Comprehensive Flutter/Dart reverse engineering: APK splitting and merging, static analysis of libapp.so (Blutter, unflutter, flutterdec, r2flutter), dynamic analysis (Frida Gadget embedding, SSL pinning bypass via BoringSSL hooking), Dart VM internals (Object Pool, compressed pointers, QK Color objects, AOT snapshot format), traffic interception (reFlutter, iptables, socket redirection), and theme/color modification. Covers Android ARM64 exclusively. Use for authorized security testing, research, or modifying your own apps.
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

### 4.1 Blutter (The Standard)

```bash
# Install dependencies (Debian/Ubuntu)
apt install python3-pyelftools python3-requests git cmake ninja-build \
    build-essential pkg-config libicu-dev libcapstone-dev

# Run
python3 blutter.py extracted_libs/ blutter_out/

# Key outputs:
# asm/*.dart        — annotated ARM64 disassembly with Dart names
# pp.txt            — Object Pool dump (strings, colors, constants)
# objs.txt          — complete nested dump of Object Pool objects
# blutter_frida.js  — starter Frida hook template
```

**Important:** Blutter auto-detects Dart version and compiles matching SDK if needed. Use `--offline` to prevent automatic checkout.

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

### Method A: reFlutter (Easiest — Binary Patching)

```bash
pip3 install reflutter==0.8.6

# Patch APK (Android)
reflutter merged.apk
# Enter Burp proxy IP when prompted
# Result: release.RE.apk

# Sign and install
java -jar uber-apk-signer.jar --allowResign -a release.RE.apk
adb install -r release.RE.apk
```

**What reFlutter does internally:**
1. Clones exact Flutter Engine + Dart SDK for the app's version
2. Patches `ssl_x509.cc` to force `return 1` in `ssl_crypto_x509_session_verify_cert_chain`
3. Optionally patches `socket.cc` to hardcode proxy IP
4. Recompiles `libflutter.so` and repackages APK

**Pre-patched builds:** Check https://github.com/Impact-I/reFlutter/releases for your snapshot hash.

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
- **handshake.cc** — https://github.com/google/boringssl/blob/main/ssl/handshake.cc (target: `ssl_verify_peer_cert`)
