---
name: android-reverse-engineering
description: >
  Reverse-engineer Android APKs, XAPK, JAR, and AAR files across Java, Kotlin, and Flutter.
  Static decompilation (jadx, Fernflower/Vineflower, apktool, baksmali), API extraction and
  call-flow documentation, dynamic analysis (Frida, Objection, mitmproxy), SSL pinning bypass
  (OkHttp, Ktor, Cronet, Flutter, WebView), root detection bypass, anti-debugging/anti-tamper
  bypass, cryptoanalysis, deobfuscation (ProGuard/R8/DexGuard/StringFog), native ARM64 analysis
  (Ghidra, radare2), PairipCore/Dex2C detection, Play Integrity/SafetyNet analysis, and OWASP
  MASTG/MASVS compliance testing. Use for authorized security testing (own apps, bug bounty
  with defined scope, or apps with explicit permission from the owner) — not against third-party
  services without authorization.
---

# Android RE Expert

6-phase attack pipeline for pentesting and reverse engineering Android APKs.

## Prerequisites

Requires **Java JDK 17+**, **jadx**, and optionally **Fernflower/Vineflower** + **dex2jar** for better decompilation quality. For the dynamic flow: **Frida**, **mitmproxy/mitmdump**, **Objection**, and a device/emulator with **Magisk** or **KernelSU** if root is needed.

```bash
# Check what you have
jadx --version
java -version
frida --version
mitmdump --version
```

If something is missing, install with the system package manager (apt, brew, pipx, etc.) or consult the official documentation for each tool.

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
```

**Strategy by result:**
```
OkHttp present      → CertificatePinner.check() + TrustManagerImpl
Ktor Client         → Only TrustManagerImpl (doesn't use OkHttp)
Cronet present      → Native BoringSSL (SSL_CTX_set_custom_verify)
gRPC detected       → Binary traffic (Protobuf), mitmdump captures but can't read
Flutter             → reFlutter / kill_flutter / iptables transparent
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
Ionic/Cordova? → DNAT + mitmdump (system proxy does NOT work)
NDK?     → Layer 5 (curl_easy_setopt or BoringSSL)
None? → search for custom TrustManager in jadx → specific hook
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

## Frida Cookbook

```javascript
// === SSL/TLS ===
var TMI=Java.use('com.android.org.conscrypt.TrustManagerImpl')
TMI.verifyChain.overloads.forEach(o=>o.implementation=function(){return arguments[0]})
TMI.checkTrustedRecursive.overloads.forEach(o=>o.implementation=function(){return Java.use('java.util.ArrayList').$new()})

Java.use('okhttp3.CertificatePinner').check.overloads.forEach(o=>o.implementation=function(){})
Java.use('android.webkit.WebViewClient').onReceivedSslError.overload('android.webkit.WebView','android.webkit.SslErrorHandler','android.net.http.SslError').implementation=function(v,h,e){h.proceed()}
Java.use('javax.net.ssl.HostnameVerifier').verify.implementation=function(){return true}

// === Root (7 techniques) ===
// File.exists → filter su/magisk/frida/xposed
// Runtime.exec("su") → Fake Process (exitValue=0, empty streams)
// UnixFileSystem.checkAccess → native layer
// PackageManager.getPackageInfo → NameNotFoundException
// SystemProperties.get → ro.debuggable=0, ro.secure=1
// Build.TAGS → "release-keys"
// Debug.isDebuggerConnected → false

// === Crypto ===
var C=Java.use('javax.crypto.Cipher')
C.getInstance.overload('java.lang.String').implementation=function(a){return C.getInstance(a)}
C.doFinal.overload('[B').implementation=function(d){return C.doFinal.call(this,d)} // + log
var M=Java.use('javax.crypto.Mac')
M.getInstance.overload('java.lang.String').implementation=function(a){return M.getInstance(a)}

// === Network ===
var R=Java.use('okhttp3.Request')
R.url.implementation=function(){return R.url.call(this)} // + log

// === Anti-Debug ===
Java.use('android.os.Debug').isDebuggerConnected.implementation=function(){return false}
// Native: Interceptor.attach(Module.findExportByName(null,'ptrace'),{onLeave:r=>r.replace(0)})

// === Cronet/BoringSSL (Google apps, TikTok) ===
// Find the module and hook SSL_CTX_set_custom_verify
var mods = ['libcronet.so', 'libsscronet.so', 'libboringssl.so', 'libssl.so'];
mods.forEach(function(m) {
    var mod = Process.findModuleByName(m);
    if (mod) {
        var fn = Module.findExportByName(mod.name, 'SSL_CTX_set_custom_verify');
        if (fn) {
            Interceptor.attach(fn, {
                onEnter: function(args) {
                    args[2] = null; // NULL callback = no custom verification
                }
            });
        }
        var fn2 = Module.findExportByName(mod.name, 'SSL_set_custom_verify');
        if (fn2) {
            Interceptor.attach(fn2, {
                onEnter: function(args) {
                    args[2] = null;
                }
            });
        }
    }
});
// Fallback: search for export in any module
var fn3 = Module.findExportByName(null, 'SSL_CTX_set_custom_verify');
if (fn3) Interceptor.attach(fn3, { onEnter: function(args) { args[2] = null; } });

// === Advanced (underground) Techniques ===
// Native C-level bypass: hook open/access/fopen/stat/lstat → filter root paths
// Native string scan bypass: hook strstr/memmem → filter "frida","magisk","su" in /proc/self/maps
// Frida CModule API: hooks in native C (faster and stealthier than JS)
// DexClassLoader.loadClass → intercept classes loaded at runtime
// Process.killProcess/System.exit/Runtime.exit → prevent app suicide
// FLAG_SECURE bypass Smali: replace 0x2000→0x0 in Window.addFlags/setFlags
// Flutter dynamic offset: ADRP+ADD walkback from string anchors (ssl_client/ssl_server)
// Cronet/BoringSSL (Google apps, TikTok): hook SSL_CTX_set_custom_verify → callback returns 0
// Facebook Proxygen: hook native proxygen::SSLVerification::verifyWithMetrics
// Dex dumping cross-sandbox: read /proc/<pid>/mem from Redroid host
```

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
/home/usuario/.local/share/pipx/venvs/mitmproxy/bin/python3 << 'PYEOF'
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
| **gRPC** | `google.internal.service.v1.Endpoint/Method` | Binary proto, unreadable without .proto | ❌ Protobuf |

**For gRPC:** Traffic is captured in mitmproxy but the body is binary (Protobuf). Without the original `.proto` file you cannot deserialize it. Search for proto hints in the DEX strings.

## Frida Gotchas

- `setTimeout` only inside `Java.perform()`
- `tail -f /dev/zero | frida ...` to keep alive
- Same client/server version
- NEVER `return undefined` → `return ArrayList.$new()` or `return arguments[0]`
- `arm64` for physical, `x86` for google_apis emulator
- **Multiple Frida sessions:** If you run `frida -U <PID>` multiple times, Frida processes accumulate. Kill them with `kill $(pgrep -f "frida.*<PID>")` before re-attaching.

## Modern Root Hiding

```bash
# 2025-2026 stack for STRONG integrity:
KernelSU-Next / Magisk Alpha + Zygisk Next + Shamiko + TrickyStore + PlayIntegrityFork + HMA-OSS

# Magisk DenyList (the simplest):
# Settings → Zygisk ON → Configure DenyList → check app → reboot
```

## Learning References

- **☆ [Maddie Stone's Android RE 101](https://www.ragingrock.com/AndroidAppRE/)** — Full course with exercises (jadx, Ghidra, practice APKs)
- **☆ [Blue Fox: Arm Assembly Internals & RE](https://www.amazon.com/dp/1119745306)** — Maria Markstedter (Azeria Labs). 450p. Armv8-A in depth: ELF, AArch64/AArch32 registers, exception levels, addressing modes, static/dynamic analysis, arm64 malware. **The ARM RE bible.**
- **☆ [Awesome Android RE](https://github.com/user1342/Awesome-Android-Reverse-Engineering)** — Curated list of tools, training and resources (2446⭐, updated)
- **☆ Mobile App RE (Abhinav Mishra, 2022)** — Extracted in `docs/mobile-re-book/`: fundamentals, tools, Android RE (JADX/smali/obfuscation), automation with MobSF

## Tools

| Phase | Primary | Alternatives |
|---|---|---|
| Triage | jadx, apktool, aapt | unzip, strings |
| Java | jadx-gui, grep | MobSF, AndroGuard |
| Dynamic | Frida, Objection | Medusa, Auto-Frida |
| Network | mitmdump, tcpdump | Burp, HTTP Toolkit, Wireshark |
| Native | Ghidra, radare2 | IDA Pro, Il2CppDumper |
| Flutter | reFlutter, iptables | kill_flutter (dynamic offset) |
| Root | Magisk, KernelSU | TrickyStore, Shamiko |
| Stealth | fridare, phantom-frida | renef (memfd, no ptrace) |

## Top 14 Errors

| Error | Fix |
|---|---|
| Cert DER 812 bytes | Regenerate WITHOUT -text |
| verifyChain args mismatch | Hook ALL overloads |
| Frida dies alone | `tail -f /dev/zero \| frida ...` |
| WebView won't load with proxy | No proxy; Magisk DenyList |
| setTimeout not function | Inside Java.perform() |
| JNI crash SIGABRT | return ArrayList, not undefined |
| Read-only filesystem | `mount -o rw,remount magisk` |
| Frida version mismatch | Same client/server version |
| Proxy breaks miniapps | tcpdump without proxy |
| STRONG_INTEGRITY fail | TrickyStore + keybox |
| Multiple Frida sessions | `kill $(pgrep -f 'frida.*<PID>')` before re-attaching |
| Ionic/WebView app not capturing with proxy | Use iptables DNAT, not system proxy |
| Chrome Custom Tab rejects cert | Doesn't use Java TrustManager. Disable DNAT, authenticate, re-enable |
| Ionic WebView crashes with Frida spawn | Use `attach` instead of `-f` spawn |
| mitmdump dies when closing shell | Use `setsid` + `&` or `tail -f /dev/zero \| frida` |

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

## Anti-Debugging and Anti-Tampering (beyond root)

| Technique | Detection | Bypass |
|---|---|---|
| `Debug.isDebuggerConnected()` | Direct Java | Hook → `false` |
| Timing checks (`nanoTime()` between instructions) | Detects breakpoints | Hook clock or skip block |
| `ptrace(PTRACE_TRACEME)` in JNI_OnLoad | Native, blocks attach | Hook `ptrace` before it runs |
| APK signature verified at runtime | Detects recompilation | Hook hash comparator → `true` |
| `/proc/self/maps` searching for "frida","xposed","magisk" | String matching in memory | Native hook `strstr`/`memmem` |

## Xposed / LSPosed as a Frida Alternative

- Frida is dynamic (PC + USB/network); Xposed/LSPosed is persistent (the hook survives reboots without a PC connected).
- Useful when: the bypass must survive reboots, or Frida is detected and you need a smaller footprint (doesn't inject an external process, loads via Zygote).
- Basic structure: `IXposedHookLoadPackage` + `findAndHookMethod` on the target package, packaged as an APK and installed via LSPosed Manager.
- Limitation: requires Zygisk/LSPosed (root); Frida can run without root with `frida-gadget` embedded in the APK.

## Kotlin: Decompilation Particularities

- `@Metadata` annotation — jadx uses it to reconstruct Kotlin-like syntax. If removed/obfuscated, it shows plain Java with synthetic getters/setters.
- `Companion object` → inner static class (`Foo$Companion`) — look for constants and "static" methods there.
- Coroutines (`suspend fun`) → `Continuation` parameter + state machine (`when(label)`) — hard to read; use the original method signature as a guide.
- Null-safety (`?.`, `!!`) → `Intrinsics.checkNotNull()` — visual noise, ignore.

## Manifest and Permission Analysis

```bash
aapt dump badging app.apk       # package, version, permissions, SDK, exported activities
aapt dump permissions app.apk   # only declared permissions
```
- Permissions to check first: `READ_SMS`, `RECEIVE_SMS` (OTP interception), `SYSTEM_ALERT_WINDOW` (overlay), `REQUEST_INSTALL_PACKAGES`, `BIND_ACCESSIBILITY_SERVICE`.
- `android:allowBackup="true"` → `adb backup` extracts data without root (tokens, SQLite DBs).
- `android:debuggable="true"` (rare in production) → `jdb`/`gdb` without root or Frida.

## MobSF (Mobile Security Framework)

```bash
docker run -it --rm -p 8000:8000 opensecurity/mobile-security-framework-mobsf:latest
# Upload APK at localhost:8000 → report: permissions, hardcoded secrets, CVEs, exported components
```
- Automatic triage in 2-5 min. Useful before manual analysis.

## Native Libraries: Quick Identification

```bash
nm -D lib.so 2>/dev/null | grep -i "JNI_OnLoad\|Java_"
strings lib.so | grep -iE "boringssl|openssl|curl|cronet|flutter"
file lib.so
```
- Common fingerprints: `libflutter.so` (Flutter), `libcronet.so`/`libsscronet.so` (Cronet/QUIC), `libssl.so`/`libcrypto.so` (vendored OpenSSL/BoringSSL).

## Expected Output

At the end of an RE session, you must produce:

1. **Decompiled code** in the output directory (`sources/`).
2. **Architecture summary**: package structure, pattern (MVP/MVVM/Clean), Application class, exported components.
3. **API documentation**: all discovered endpoints with method, path, parameters, auth headers, and the call chain from where they are invoked.
4. **Call flow map**: key UI-to-network routes, especially login, registration, and critical functions (payments, sensitive data).
5. If dynamic analysis applies: **classified capture file** (`.flows`) + notes on which pinning/root-detection layers were bypassed and how.

## Environment

- **Device:** Android 10+, ARM64, Magisk
- **ADB:** `/home/usuario/Android/Sdk/platform-tools/adb`
- **CA:** `~/.mitmproxy/mitmproxy-ca-cert.pem`

---

## Flutter / Dart Reverse Engineering

> **Skill dedicado:** `.opencode/skills/flutter-reverse-engineering/SKILL.md` (1285 líneas)
>
> Flutter merece un skill propio porque: `libapp.so` (AOT snapshot), Dart VM internals (Object Pool, compressed pointers, QK Color objects), blutter, reFlutter, BoringSSL hooking — son temas que requieren tratamiento profundo.
>
> **Usar el skill dedicado para:** análisis completo de snapshots, Dart VM internals, modificación de temas/colores, Frida Gadget embedding en Flutter.
>
> **Resumen rápido aquí para triaje:**

### Detección

```bash
unzip -l app.apk | grep -i "libapp.so\|libflutter.so"
# libapp.so  → lógica Dart compilada (AOT snapshot)
# libflutter.so → Flutter engine (incluye BoringSSL para TLS)
```

### Versión de Flutter

```bash
strings libflutter.so | grep -oP 'flutter_engine_version=\K.*'
strings libflutter.so | grep -oP 'dart_sdk_version=\K.*'
```

### SSL Pinning en Flutter

Flutter usa **BoringSSL compilado dentro de `libflutter.so`**, no el del sistema. El pinning no se puede bypass con NSC ni con hooks de Java TrustManager.

**Opciones:**
1. **reFlutter** — parchea el engine para deshabilitar pinning (reempaqueta el APK).
2. **Hook nativo** — buscar `ssl_verify_cert_chain` o `SSL_CTX_set_verify` en `libflutter.so` y hookear con Frida. Ver script `scripts/flutter_ssl_bypass.js`.
3. **iptables transparent** — redirigir tráfico a mitmproxy en modo transparente.

**Para análisis profundo de Flutter, cargar el skill `flutter-reverse-engineering`.**

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
rg -n 'PlayIntegrityApi\|IntegrityTokenRequest\|IntegrityTokenResponse' dex*_out/
```

**Tipos de verificación:**
- **App Integrity**: ¿La app está modificada? (hash del certificado de firma)
- **Device Integrity**: ¿El dispositivo es genuine? (MEETS_DEVICE_INTEGRITY, MEETS_STRONG_INTEGRITY)
- **Account Details**: ¿La cuenta de Google está vinculada? (appLicense)

**Análisis en laboratorio (autorizado):**
- Hook `IntegrityTokenResponse` con Frida para inspeccionar tokens.
- Análisis de respuesta server-side (el token está firmado por Google, no se puede falsificar).
- Bypass de Play Integrity en producción viola ToS de Google Play.

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
            return null; // o lanzar IOException
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

### Bypass de anti-Frida

```javascript
// anti_frida_bypass.js
// Hook strstr para filtrar "frida", "gum", "agent" en /proc/self/maps
Interceptor.attach(Module.findExportByName("libc.so", "strstr"), {
    onEnter: function(args) {
        var needle = args[1].readCString();
        if (needle && (needle.indexOf("frida") >= 0 || needle.indexOf("gum") >= 0 ||
            needle.indexOf("agent") >= 0 || needle.indexOf("gadget") >= 0)) {
            this.should_replace = true;
        }
    },
    onLeave: function(retval) {
        if (this.should_replace) {
            retval.replace(0); // retornar NULL = no encontrado
        }
    }
});

// Hook fopen para /proc/self/maps
Interceptor.attach(Module.findExportByName("libc.so", "fopen"), {
    onEnter: function(args) {
        var path = args[0].readCString();
        if (path && path.indexOf("/proc/self/maps") >= 0) {
            this.should_redirect = true;
        }
    },
    onLeave: function(retval) {
        if (this.should_redirect) {
            // Retornar un FILE* a un archivo limpio sin frida
            // o retornar NULL
        }
    }
});
```

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

> **Skill dedicado:** `.opencode/skills/ghidra-pyghidra/SKILL.md` (434 líneas)
>
> Ghidra + pyghidra como herramienta general de análisis binario. Cubre: instalación, análisis headless, scripting Python con API de Ghidra, decompilación automatizada, apertura de proyectos.
>
> **Usar el skill dedicado para:** scripting pyghidra, análisis headless automatizado, API de Ghidra en Python.
>
> **Workflow específico para Android ARM64 aquí:**

### Workflow de análisis nativo

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

Plugin que identifica constantes criptográficas y algoritmos en código binario:
- AES S-box (0x63, 0x7C, 0x77...)
- CRC32 table
- MD5 init values
- SHA-256 constants

**Para scripting avanzado con pyghidra, cargar el skill `ghidra-pyghidra`.**

---

## Frida Advanced Techniques

### CModule (hooks nativos en C)

CModule permite escribir hooks en C nativo, más rápido y stealthy que JS:

```javascript
var cm = new CModule(`
#include <gum/guminterceptor.h>

void on_enter(GumInvocationContext *ic) {
    // Hook nativo en C
    gpointer *arg0 = gum_invocation_context_get_nth_argument(ic, 0);
    // ...
}

void on_leave(GumInvocationContext *ic) {
    // ...
}
`);

Interceptor.attach(target_addr, {
    onEnter: cm.on_enter,
    onLeave: cm.on_leave
});
```

### Memory scanning

```javascript
// Buscar strings en memoria
Memory.scanSync(ptr("0x40000000"), 0x10000000, "48 65 6c 6c 6f")  // "Hello" en hex

// Buscar patrón de bytes
Memory.scanSync(baseAddr, size, "48 8b ?? ?? 48 85")  // ?? = wildcard

// Dump de región de memoria
var data = Memory.readByteArray(ptr("0x12345678"), 256);
console.log(hexdump(data, {ansi: true}));
```

### DexClassLoader hook

```javascript
// Intercepta clases cargadas dinámicamente
Java.perform(function() {
    var DexClassLoader = Java.use("dalvik.system.DexClassLoader");
    DexClassLoader.$init.implementation = function(dexPath, optDir, libPath, parent) {
        console.log("[DEX-LOAD] Loading: " + dexPath);
        return this.$init(dexPath, optDir, libPath, parent);
    };

    // Hook loadClass para ver qué clases se cargan
    DexClassLoader.loadClass.implementation = function(name) {
        console.log("[DEX-CLASS] " + name);
        return this.loadClass(name);
    };
});
```

### Anti-suicide hooks

```javascript
// Prevenir que la app se cierre al detectar instrumentación
Java.perform(function() {
    var System = Java.use("java.lang.System");
    System.exit.implementation = function(code) {
        console.log("[BLOCKED] System.exit(" + code + ")");
        // No llamar al original = prevenir exit
    };

    var Runtime = Java.use("java.lang.Runtime");
    Runtime.exit.implementation = function(code) {
        console.log("[BLOCKED] Runtime.exit(" + code + ")");
    };

    var Process = Java.use("android.os.Process");
    Process.killProcess.implementation = function(pid) {
        console.log("[BLOCKED] killProcess(" + pid + ")");
    };
});
```

---

## Toolbox Reference

Referencia completa de herramientas en `reports/android-re-toolbox.md` (16 secciones):
- Estática, Smali/DEX, Dinámica, Nativo ARM64, Flutter/Dart, Kotlin, Red/SSL, Desofuscación, Anti-tamper, Criptografía, Empaquetado, Root/Integrity, Automatización, MSTG/MASVS, Awesome lists, Comandos rápidos.

---

## Skills relacionados

- **`apk-modding`** — Playbook operativo para modificar, parchear y hackear APKs (smali patching, signature killers, PairipCore bypass, Frida Gadget, Unity/IL2CPP). Usar cuando el objetivo sea modificar el comportamiento de la app, no solo analizarla.
- **`flutter-reverse-engineering`** — RE profundo de Flutter/Dart (libapp.so, Dart VM internals, blutter, reFlutter, BoringSSL hooking, theme/color modification). Usar cuando el APK sea Flutter y se necesite análisis profundo más allá del triaje.
- **`ghidra-pyghidra`** — Ghidra + pyghidra como herramienta (análisis headless, scripting Python con API de Ghidra, decompilación automatizada). Usar para scripting pyghidra y análisis headless automatizado.
- **`httptoolkit-android`** — HTTP Toolkit en Android (mecanismo de interceptación VPN + Magisk tmpfs cert, troubleshooting, root vs non-root). Usar para captura de tráfico cuando Frida no sea necesario.
- **`android-cleanup`** — Limpieza de dispositivo Android post-pentesting (proxy global, iptables NAT, bind mounts, CA certificates, Frida Gadget, Magisk bypass modules, SELinux). Usar después de sesiones de dynamic analysis.

---

## Changelog

- 2026-07-18 (v2): Ampliación con Flutter/Dart RE (referencia cruzada a skill dedicado), Kotlin deep dive, desofuscación, criptoanálisis, PairipCore/Dex2C, Play Integrity/SafetyNet, anti-debugging extendido, OWASP MASTG/MASVS, MobSF automation, Ghidra ARM64 workflow (referencia cruzada a skill dedicado + pyghidra), Frida advanced (CModule, memory scan, DexClassLoader, anti-suicide), toolbox reference, referencias cruzadas a skills relacionados.
