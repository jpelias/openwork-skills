---
name: apk-modding
description: >
  Operational playbook for modifying, patching, and hacking Android APKs from a Linux PC.
  Covers: decompilation (jadx, apktool, baksmali), smali patching (licenses, premium,
  ads, modder dialogs), reassembly, signing (v1/v2/v3), installation via ADB,
  native ARM64 analysis (Ghidra, radare2), dynamic instrumentation (Frida), bypass of
  signature checks, PairipCore, Dex2C, and Unity/IL2CPP game modding.
  Use for authorized testing, research, or modifying your own apps.
---

# APK Modding Playbook

Operational playbook for modifying Android APKs from this Linux workspace. All tools are installed and are native Linux tools.

## ⚠️ GOLDEN RULE — ALWAYS, NO EXCEPTIONS

**Before touching a single byte, search GitHub.** `github.com/topics/android-reverse-engineering`, `github.com/search?q=<app>`. If someone already patched it, fork and adapt. Don't reinvent the wheel. Ever.

## Golden rules

1. **Hack the original, not the mod.** If the original APK exists, patch it. Mods add protections (encrypted DEX, multi-layer signature verification, native anti-tamper) orders of magnitude harder to bypass than simple original licenses.

2. **Never delete `META-INF/services/`.** Only delete signatures: `.SF`, `.RSA`, `.DSA`, `.EC`, `MANIFEST.MF`. Deleting `META-INF/services/` breaks Kotlin `ServiceLoader` → crash `Module with the Main dispatcher is missing`.

3. **Search call-sites in ALL DEX files.** Modder injections are usually in `classes3.dex` but calls are in `classes2.dex` (MainActivity). Always search across all DEX files.

4. **Only reassemble modified DEX files.** Keep the rest as originals.

5. **Clean up the device after modding.** Proxy, CA certificates, temporary Magisk modules, and Frida Gadget can leave the device unstable. Use the `android-cleanup` skill when finished.

---

## Workspace tools (all available)

```
apktool      /usr/bin/apktool          2.7.0    — decompile/recompile APK
baksmali     /usr/bin/baksmali         2.5.2    — DEX → smali
smali        /usr/bin/smali            2.5.2    — smali → DEX
jadx         /usr/local/bin/jadx       1.5.1    — DEX → Java decompiler
apksigner    /usr/bin/apksigner        —        — v1/v2/v3/v4 signing
zipalign     /usr/bin/zipalign         —        — APK alignment
aapt         /usr/bin/aapt             —        — manifest inspection
aapt2        /usr/bin/aapt2            —        — resource inspection
adb          ~/Android/Sdk/platform-tools/adb — device connection
frida        ~/.local/bin/frida        17.15.3  — dynamic instrumentation
frida-ps     ~/.local/bin/frida-ps     —        — list processes
objection    ~/.local/bin/objection    1.12.5   — Frida wrapper
r2           /usr/local/bin/r2         6.1.9    — native disasm/hex patch
ghidra       /opt/ghidra/              12.x     — native ARM64 analysis
httptoolkit  /usr/bin/httptoolkit      1.26.1   — traffic interception
mitmdump     ~/.local/bin/mitmdump     12.2.3   — CLI proxy
python3      /usr/bin/python3          3.13     — scripting
keytool      /usr/bin/keytool          —        — generate keystores
openssl      /usr/bin/openssl          —        — certificates
strings      /usr/bin/strings          —        — extract strings
readelf      /usr/bin/readelf          —        — ELF symbols
```

Scripts included in `.opencode/skills/apk-modding/scripts/`:
- `batch-apktool.sh` — full flow (decompile, compile, align, sign, install, info)
- `patch_shared_prefs_defaults.py` — change SharedPreferences defaults
- `neutralize_yhf_dialogs.py` — neutralize modder dialogs
- `ziprepack.py` — repack with correct compression
- `strip_sign_and_sign.py` — strip signatures, align, sign
- `nightmare.py` — ARM64 hex patching (find/replace instructions in .so)

---

## Standard operational flow

### Phase 1 — Triage

```bash
# APK metadata
aapt dump badging app.apk | head -20

# If it's a .apks / .xapk bundle, extract base.apk first
unzip -l app.apk | grep -q "base.apk" && unzip -o app.apk "base.apk" -d extracted/
[ -f extracted/base.apk ] && BASE=extracted/base.apk || BASE=app.apk

# Pull installed splits from device (if needed)
# adb shell pm path com.target.app | cut -d: -f2 | xargs -I{} adb pull {}

# Count DEX and .so files
unzip -l app.apk | grep -c "classes.*\.dex"
unzip -l app.apk | grep -c "\.so$"

# Modder detection
unzip -p app.apk classes*.dex | strings -a | grep -iE "Liteapks|9mod|ī/íì|īi/ïi|bin/ghost|p000/p001"

# Flutter detection
unzip -l app.apk | grep -i "libapp.so\|libflutter.so"

# Pairip detection
unzip -p app.apk classes*.dex | strings -a | grep -c "pairip"
unzip -l app.apk | grep -i "pairipcore"

# Dex2C/VM shell detection
unzip -l app.apk | grep -i "libstub.so\|protected_by_np\|libcxapkmod"

# Current signature
apksigner verify --verbose --print-certs app.apk
```

### Phase 2 — Decompilation

```bash
# Java (for reading)
jadx -d jadx-out/ --no-res app.apk

# Smali (for patching) — ALL DEX files
API=35
for num in "" $(seq 2 20); do
    fname="classes${num}.dex"
    unzip -l app.apk | grep -q "$fname" || continue
    unzip -p app.apk "$fname" > "$fname"
    baksmali d "$fname" -o "dex${num}_out/" --api "$API"
done

# Resources (if manifest/XML needs editing)
apktool d app.apk -o apktool-out/
```

### Phase 3 — Analysis and target search

```bash
# SharedPreferences keys (license/premium)
rg -n '"premium"|"noads"|"pro"|"isPremium"|"max_' dex*_out/ --glob "**/*.smali"

# Billing / IAP
rg -n 'BillingClient|queryPurchases|getPurchase|startPurchase' dex*_out/

# Encryption
rg -n 'Cipher;->getInstance|SecretKeySpec|MessageDigest' dex*_out/

# Reflection
rg -n 'getDeclaredMethod|getDeclaredField|Class.forName|Method;->invoke' dex*_out/

# Root detection
rg -n '"/su"|magisk|busybox|ro.kernel.qemu|isDebuggerConnected' dex*_out/

# Native load
rg -n 'System.loadLibrary|System.load' dex*_out/

# Modder call-sites (yhf/liteapks)
rg -n "invoke-.*(ī/íì|īi/ïi|p000/p001|p002i/p003i|q6/c|w6/b|d6/a|a/b/pookie)" dex*_out --glob "**/*.smali" \
  | rg -v "^dex\d*_out/(ī|īi|p000|p002i|q6|w6|d6|a)/"
```

### Phase 4 — Patching

#### Strategy A: Change SharedPreferences defaults

Common pattern:
```java
this.isPremium = prefs.getBoolean("premium", false);
```

In smali, change `const/4 v2, 0x0` → `0x1`:
```smali
const-string v1, "premium"
const/4 v2, 0x0              # ← change to 0x1
invoke-interface {v0, v1, v2}, ...getBoolean...
```

Automated:
```bash
python3 .opencode/skills/apk-modding/scripts/patch_shared_prefs_defaults.py \
  --roots dex_out dex2_out --keys premium noads pro --write
```

**Limitation:** If the app re-syncs from Play Billing or server, the value gets overwritten. Use Strategy C.

#### Strategy B: Force method return

Replace the entire method body:
```smali
.method public isPremium()Z
    .registers 1
    const/4 v0, 0x1
    return v0
.end method
```

Immune to SharedPreferences re-sync. If there are multiple check methods (5+), patch them all.

#### Strategy C: Getter hook by key name

Intercept `getBoolean(key, default)` at the start and return `true` if the key matches:
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
    # ... original body
```

Survives Play Billing re-sync because it intercepts the **read**, not the stored value.

#### Strategy D: Suppress re-login dialogs and auth toasts

```smali
# Suppress re-login broadcast
.method ...sendReLoginBroadcast()V
    .registers 0
    return-void
.end method

# Suppress ReLoginDialogActivity launch
.method ...launchReLoginDialog()V
    .registers 0
    return-void
.end method

# Suppress only auth toasts (leave other toasts)
if-eqz p1, :show
const-string v0, "uthenticat"
invoke-virtual {p1, v0}, Ljava/lang/String;->contains(Ljava/lang/CharSequence;)Z
move-result v0
if-eqz v0, :show
return-void
:show
# ... original toast code
```

#### Strategy E: Numeric limit patching

```smali
const-string v1, "max_favorites"
const/16 v2, 0x5              # ← change to 0x63 (99) or 0x7FFFFFFF
invoke-interface {v0, v1, v2}, ...getInt...
```

#### Strategy F: Neutralize modder dialogs (yhf/liteapks)

**DO NOT delete modder classes** — the launcher Activity has direct DEX references. Deleting causes `NoClassDefFoundError`.

Automated:
```bash
python3 .opencode/skills/apk-modding/scripts/neutralize_yhf_dialogs.py \
  --roots dex_out dex2_out --write
```

This neutralizes `public static *(Context)` methods → `return-void` or `return null`.

**Afterwards, remove `invoke-static` calls in Activities to these methods.**

### Phase 5 — Reassembly

```bash
# Only reassemble modified DEX files
API=35
for d in dex_out dex2_out; do
    num=$(echo "$d" | sed 's/dex//;s/_out//')
    [ -z "$num" ] && num="" || num="$num"
    smali assemble "$d" --api "$API" -o "classes${num}_new.dex"
done
```

### Phase 6 — Repackaging

```bash
# With script (recommended)
python3 .opencode/skills/apk-modding/scripts/ziprepack.py \
  --in app.apk --out hacked.apk \
  --replace classes.dex=classes_new.dex classes2.dex=classes2_new.dex

# Or with batch-apktool.sh
.opencode/skills/apk-modding/scripts/batch-apktool.sh rebuild apktool-out/
```

**Compression rules (Android 14–16):**
- `.so` → STORE (no compression) + page-aligned with `zipalign -p`
- `resources.arsc` → STORE
- `classes*.dex` → STORE (with Python zipfile; with zip/apktool it may DEFLATE)
- Rest → DEFLATE
- Keep `META-INF/services/`; remove only `.SF/.RSA/.DSA/.EC` and `MANIFEST.MF`

### Phase 7 — Signing and installation

```bash
# Align
zipalign -p -f 4 hacked.apk hacked_aligned.apk

# Sign (v1+v2+v3)
apksigner sign \
  --ks "$HOME/.android/debug.keystore" --ks-pass pass:android \
  --ks-key-alias androiddebugkey \
  --v1-signing-enabled true --v2-signing-enabled true --v3-signing-enabled true \
  --out hacked_signed.apk hacked_aligned.apk

# Verify
apksigner verify --verbose --print-certs hacked_signed.apk

# Install
adb shell settings put global package_verifier_enable 0
adb install hacked_signed.apk
adb shell settings put global package_verifier_enable 1
```

Automated:
```bash
.opencode/skills/apk-modding/scripts/strip_sign_and_sign.py \
  --in hacked.apk --out hacked_signed.apk
adb install hacked_signed.apk
```

---

## Full flow in one command

```bash
.opencode/skills/apk-modding/scripts/batch-apktool.sh all app.apk
# decompile + open editor
# edit smali...
.opencode/skills/apk-modding/scripts/batch-apktool.sh rebuild app_out/
.opencode/skills/apk-modding/scripts/batch-apktool.sh install app_out_signed.apk
```

---

## Modder detection (2025–2026)

### Profiles

| Modder | Signature | Statically patchable? |
|---|---|---|
| **yhf / liteapks** | `ī/íì/`, `īi/ïi/` | ⚠️ Partial (Java yes, native no) |
| **yhf (2025+)** | `p000/p001/`, `p002i/p003i/` | ⚠️ Partial (renamed) |
| **黯笙** | `bin.mt.signature.KillerApplication` | ✅ Yes (pure Java) |
| **Kunkka** | `LSPAppComponentFactoryStub` + `assets/lspatch/config.json` | ✅ Yes (via LSPosed) |
| **zhou45** | `libstub.so` + `assets/protected_by_np` | ❌ No (Dex2C VM shell) |
| **辰夕** | `libcxapkmod.so` + `assets/cxapkDex/*.Epic` | ❌ No (native VM) |
| **幻幻喵** | `libmiaomiaohuan.so` + `miaomiaohuan0` prefix | ❌ No |

### Decision tree

```
Has libstub.so + assets/classes0.jar?
  → YES: Static dead end. Hack the original APK.
  → NO: Has ī/íì + native methods (up.process, bi.b)?
         → YES: Try neutralizing <clinit> that call EntryPoint.stub
         → If it crashes: Partial dead end.
         → If it works: ✅
  → NO: Has only ī/íì with Java methods (iaw.w, iab.b)?
         → YES: Neutralize normally ✅
  → NO: No ī/íì or libstub?
         → YES: It's the original or a clean mod. Apply Strategies A-F ✅
```

---

## Signature check bypass

### Java-level (smali patch)

Look for `getPackageInfo(GET_SIGNATURES)` and neutralize the comparison.

### Native-level (.so patch with Ghidra/radare2)

```bash
# Extract .so
unzip -p app.apk lib/arm64-v8a/libnative.so > libnative.so

# Search for verification strings
strings libnative.so | grep -iE "sign|cert|integrity|verify|package"

# Open in radare2
r2 -A libnative.so
# > afl~JNI
# > s sym.JNI_OnLoad
# > pdf

# Ghidra: trace abort() → XREFs → find condition → patch
```

### Runtime (Frida, no APK patching)

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

### Detection
```bash
unzip -p app.apk classes*.dex | strings -a | grep -c "pairip"
unzip -l app.apk | grep -i "pairipcore"
```

### Minimal bypass (smali only)

If the app only has Pairip for license verification (no vault dependencies):
1. Neutralize `SignatureCheck.verifyIntegrity(Context)V` → `return-void`
2. Neutralize `StartupLauncher.launch()V` → `return-void`

**DO NOT neutralize `VMRunner.invoke` or `VMRunner.setContext`** — the entire app depends on them to decrypt strings.

### Full bypass (vault strings compromised)

If the APK is already modded and vault strings are empty:
1. Replace `Application` class in AndroidManifest (remove Pairip wrapper)
2. Patch `VMRunner.invoke` → return null
3. Patch protobuf field lookup for empty names
4. Create `SafeExceptionHandler` to catch NPE in background threads
5. Wrap crypto init in try-catch
6. Stub `FlutterSecureStorage` → `success(null)`

---

## Frida Gadget embedding (rootless redistributable APK)

For apps with `libstub.so` (Dex2C) where smali is not patchable:

1. Download `frida-gadget` for arm64
2. Place in `lib/arm64-v8a/libfrida-gadget.so`
3. Config in `assets/frida-gadget.config` (listen mode)
4. Inject `System.loadLibrary("frida-gadget")` in `<clinit>()` of Application
5. Connect: `frida -H 127.0.0.1:27042 -p <pid> -l hook.js`

**Lessons learned (Frida 17.15.3):**
- ✅ Gadget .so in `lib/arm64-v8a/` + config in `assets/`
- ❌ `"type": "script"` with external file → ignored in Frida 17.x
- Prioritize finding a mod without `libstub.so` (patchable in smali)

---

## Unity / IL2CPP modding (games)

```bash
# Detect IL2CPP
unzip -l app.apk | grep -i "libil2cpp.so\|global-metadata.dat"

# Dump IL2CPP
# Use Il2CppDumper (Linux): extracts libil2cpp.so + global-metadata.dat
# Generates dump.cs with all classes/methods

# Hook with Frida
# Use frida-il2cpp-bridge for dynamic IL2CPP method hooking
```

---

## Android 16+ Developer Verifier bypass

`com.google.android.verifier` blocks installation of APKs with unregistered certificates on Android 16+ (BR/ID/SG/TH).

Bypass (DEX patching of the verifier app):
1. `onVerificationRequired` → call `reportVerificationBypassed(1)`
2. Platform policy flag (45681539) → return `Long(0)` = NONE
3. Forced backport flag (45749715) → return `Boolean.TRUE`

Requires installing the patched verifier as a system app (Magisk module or ADB with root).

---

## Morphe patcher (programmatic alternative)

To maintain patches across versions, use Morphe patcher with fingerprints:

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
- `arandomhooman/hoomans-morphe-patches` (★92) — additional patches

---

## Case study template

```markdown
# Case: [App] [Version]

## Metadata
- App: com.example.app
- Version: 1.2.3
- Source: APKMirror / adb pull
- Goal: unlock premium / remove ads / remove modder dialog

## Inspection
- DEX: N | Native: Yes/No | Modder: yhf/none
- Protection: SharedPreferences / Play Billing / native check

## Analysis
- SP keys: premium, noads, max_favorites
- Methods: isPremium()Z, checkLicense()V
- DEX injection: classes3.dex | Call-sites: classes2.dex

## Patches
| File | Method | Change | Strategy |
|---|---|---|---|
| classes2.dex | isPremium()Z | return true | B |

## Result
- ✅ Premium unlocked / ❌ Billing re-sync reverts (use C)

## Lesson
[One sentence]
```

---

## Troubleshooting

| Symptom | Likely cause | Solution |
|---|---|---|
| `INSTALL_FAILED_UPDATE_INCOMPATIBLE` | Signing certificate differs from original | Uninstall original app before installing the mod |
| `INSTALL_FAILED_INVALID_APK` | Incorrect compression or unaligned APK | Verify `zipalign -p 4` and compression rules |
| `NoClassDefFoundError` on startup | `META-INF/services/` or a modder class was deleted | Restore `META-INF/services/`; do not delete modder classes |
| App crashes after smali patch | Insufficient registers or wrong return type | Adjust `.registers` and verify return types |
| `libfrida-gadget.so` does not load | Wrong architecture or missing config | Use arm64, place config in `assets/frida-gadget.config` |
| Play Integrity reverts the mod | Server-side token verification | Cannot be patched; hide root or modify own backend |
| Traffic not intercepted | QUIC/HTTP3 or native SSL pinning | Use HTTP Toolkit or BoringSSL-specific hooks |
| Modder dialog persists | Call-sites not removed across all Activities | Search for `invoke-static` to modder methods in all DEX files |

---

## References

- **Cases:** `cases/` (GPS Emulator, CamScanner, YouTube Morphe, AdGuard, GPS Data, Liteapks Store)
- **Google APIs:** `google-apis.md` (API key replacement, AOSP testkey)
- **Full toolbox:** `reports/android-re-toolbox.md` (80+ tools, 16 categories)
- **Russian forums:** 4PDA (`4pda.to`) — MT Manager, NP Manager, Batch ApkTool, Lucky Patcher
- **Master list:** `jbro129/android-modding` (★739, 821 lines, 50+ categorized tools)

### Related skills

> **Recommended workflow:** use `android-reverse-engineering` for triage, protection analysis, and API endpoint extraction; then `apk-modding` to implement persistent patches.

- **`frida-expert`** — Complete Frida cookbook for Android: SSL pinning (14 libraries), root bypass (5 vectors), crypto intercept, native connect hook. Use for runtime bypass before or instead of smali patching.
- **`android-reverse-engineering`** — General APK RE (Java, Kotlin, native, SSL pinning, root bypass, Frida, MASTG). Use for analysis and research before modding.
- **`flutter-reverse-engineering`** — Deep Flutter/Dart RE (libapp.so, Dart VM internals, blutter, reFlutter, BoringSSL hooking). Use when the APK is Flutter.
- **`ghidra-pyghidra`** — Ghidra + pyghidra as a tool (headless analysis, Python scripting, automated decompilation). Use for deep native ARM64 analysis.
- **`httptoolkit-android`** — HTTP Toolkit on Android (interception mechanism, troubleshooting). Use for traffic capture.
- **`android-cleanup`** — Post-pentesting Android device cleanup (proxy, iptables, CA certs, Frida Gadget, Magisk modules). Use after modding/dynamic analysis sessions.

---

## Changelog

- 2026-07-19 (v5): 2026 update: cleanup golden rule, tools with versions (HTTP Toolkit, mitmdump), .apks/.xapk bundle handling in triage, expanded runtime signature bypass, troubleshooting section, reinforced cross-references to `android-reverse-engineering`.
- 2026-07-18 (v4): Rewritten as operational playbook for the agent. Focus on workspace Linux PC tools. Removed secondary on-device tools. Standard 7-phase flow. Strategies A-F. Modder detection 2025-2026. Signature check bypass (Java, native, runtime). PairipCore. Frida Gadget. Unity/IL2CPP. Android 16+ verifier. Morphe patcher. Automation scripts.
