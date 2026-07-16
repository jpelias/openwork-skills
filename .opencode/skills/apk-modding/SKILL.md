# APK Modding & Hacking Skill

## Golden Rule

**If the original APK exists, hack the original. If not, neutralize the modder's code without deleting it.**

Modders add protection layers (encrypted DEX, multi-layer signature verification, native anti-tamper) that are orders of magnitude harder to bypass than the original app's simple license/SharedPreferences checks.

## Silver Rule

**Never delete `META-INF/services/` or the entire `META-INF/` directory. Only delete signature files (`.SF`, `.RSA`, `.DSA`, `.EC`, `MANIFEST.MF`).**

Deleting `META-INF/services/` breaks Kotlin `ServiceLoader` — the app crashes with: `Module with the Main dispatcher is missing. Add dependency providing the Main dispatcher, e.g. 'kotlinx-coroutines-android'`.

---

## Workflow

### ⚠️ MANDATORY CHECKLIST — DO NOT SKIP ANY STEP

Before applying any patch, verify ALL of these:

```
□ Decompile ALL DEX files (not just the one with injection)
  unzip -l app.apk | grep classes | awk '{print $4}'  →  list every DEX
  baksmali d classesN.dex -o dexN_out/ for EVERY N

□ Search for injected call sites in EVERY dexN_out/
  grep -rn "ī/íì\|īi/ïi\|p000/p001\|a/b/pookie\|d6/a\|w6/b\|q6/c\|p6/e" dex*_out/ | grep invoke | grep -v "ī/íì/\|īi/ïi/"
  → The calls are often in classes2.dex (MainActivity), not in the DEX with the injection

□ List ALL injected methods (public/private/static/constructor/<clinit>)
  find dexN_out/ī/íì/ -name "*.smali" | xargs grep "\.method "

□ Neutralize ALL of them — not just the obvious dialog methods

□ Remove ALL invoke-static calls from the app code to injected methods

□ Reassemble ONLY the DEXes you modified — keep others original
```

**⚠️ Most common failure**: searching only the DEX that contains the injected classes (e.g., classes3.dex) while the CALL SITES are in a different DEX (e.g., classes2.dex where MainActivity lives).

### Step 1: Get the APK

```bash
# From device with root (for split APKs)
adb shell pm path com.example.app
adb pull /data/app/com.example.app-*/base.apk original/
adb pull /data/app/com.example.app-*/split_*.apk original/

# Or download from APKMirror/APKPure (original, not mod)
```

### Step 2: Initial inspection

```bash
# Count DEX files
unzip -l app.apk | grep -c "classes.*\.dex"

# Count native libraries
unzip -l app.apk | grep -c "\.so$"

# Check if DEX is clean (jadx)
jadx -d out/ --no-res app.apk 2>&1 | grep "ERROR" | wc -l
# < 100 errors = clean DEX. Millions = encrypted/corrupted DEX.

# Search for modder packages
unzip -p app.apk classes*.dex | strings -a | grep -iE "Liteapks|9mod|ī/íì|īi/ïi|bin/ghost"
```

### Step 3: Decompile with jadx (Java analysis)

```bash
jadx -d jadx-out/ --no-res app.apk
```

**What to find:**
- `getBoolean("premium"`, `getBoolean("noads"` — license/PRO checks
- `getInt("max_` — configurable limits
- `if (!premium)` — conditional premium blocks
- `BillingClient`, `startPurchase` — IAP code

### Step 4: Disassemble with baksmali (smali patching)

```bash
API=35  # Target SDK from `aapt dump badging app.apk | grep targetSdk`
for num in "" $(seq 2 20); do
    fname="classes${num}.dex"
    unzip -l app.apk | grep -q "$fname" || continue
    unzip -p app.apk "$fname" > "$fname"
    baksmali d "$fname" -o "dex${num}_out/" --api "$API"
done
```

**Find SharedPreferences keys:**
```bash
grep -rn '"premium"\|"noads"\|"pro"\|"numerofavoritos"\|"max_' dex*_out/ --include="*.smali"
```

### Step 5a: Patching strategy — Change defaults

Most apps use this pattern:
```java
this.isPremium = prefs.getBoolean("premium", false);
```

In smali:
```smali
const-string v1, "premium"
const/4 v2, 0x0              # ← change to 0x1 (false → true)
invoke-interface {v0, v1, v2}, ...getBoolean...
```

**Python patcher script:**
```python
import os

for root, dirs, files in os.walk('baksmali_out'):
    for fname in files:
        if not fname.endswith('.smali'): continue
        path = os.path.join(root, fname)
        with open(path) as f: lines = f.read().split('\n')
        
        modified = False
        i = 0
        while i < len(lines):
            line = lines[i]
            if 'const-string' in line and '"noads"' in line:
                for j in range(1, 4):
                    if i + j >= len(lines): break
                    future = lines[i + j]
                    if 'const/4' in future and '0x0' in future and \
                       'getBoolean' not in future:
                        lines[i + j] = future.replace('0x0', '0x1')
                        modified = True
                        break
                    if 'invoke-interface' in future: break
            i += 1
        
        if modified:
            with open(path, 'w') as f: f.write('\n'.join(lines))
```

### Step 5b: Patching strategy — Force method return value

When the check is inside a method, replace it entirely:
```python
import os, re

smali_file = 'dex8_out/com/example/AccountPrefs.smali'
with open(smali_file) as f: lines = f.readlines()

# Patch from bottom to top to preserve line numbers
for start_line, end_line in [(1091, 1139), (1041, 1089), (387, 470)]:
    header = lines[start_line - 1].strip()
    new_method = [
        header + '\n',
        '    .registers 1\n', '\n',
        '    const/4 v0, 0x1\n', '\n',
        '    return v0\n',
        '.end method\n',
    ]
    lines[start_line - 1:end_line] = new_method

with open(smali_file, 'w') as f: f.writelines(lines)
```

### Step 5c: Patching strategy — Neutralize modder dialogs

**DO NOT delete modder classes** — the launcher Activity holds direct DEX references. Deleting causes `NoClassDefFoundError`.

**⚠️ CRITICAL: Neutralize ALL dialog methods, not just the obvious ones.**

The modder yhf injects up to 8 dialog classes with `public static` methods taking `Context`. Neutralize ALL of them:

```bash
# 1. Find ALL injected packages with public static Context methods
find baksmali_out/ -name "*.smali" ! -path "*/android/*" ! -path "*/com/*" \
  | xargs grep -l "\.method public static.*Context" \
  | while read f; do
    grep "\.method public static.*Context" "$f" | \
      sed "s|baksmali_out/||;s|\.smali||;s|/|.|g"
done

# 2. For each found method, neutralize to no-op
```

**Automated neutralizer script:**

```python
import os, re

for root, dirs, files in os.walk('baksmali_out'):
    # Skip framework packages
    if any(x in root for x in ['android/', 'androidx/', 'com/google/', 'dalvik/', 'java/', 'kotlin/']):
        continue
    
    for fname in files:
        if not fname.endswith('.smali'): continue
        path = os.path.join(root, fname)
        with open(path) as f: content = f.read()
        
        # Find all public static methods with Context parameter
        for m in re.finditer(r'\.method public static (\w+)\(Landroid/content/Context;\)(L[\w/$]+;|V)', content):
            method_name = m.group(1)
            return_type = m.group(2)  # 'V' for void, 'L...;' for object
            method_start = m.start()
            
            # Find .end method
            end_pos = content.find('.end method', method_start)
            if end_pos < 0: continue
            
            # Skip if already simple (<= 4 lines = not a dialog builder)
            body_lines = content[method_start:end_pos].count('\n')
            if body_lines <= 4: continue
            
            # Get full method signature
            sig_start = content.rfind('.method public static', 0, method_start + 1)
            sig_line = content[sig_start:content.find('\n', sig_start)]
            class_name = fname.replace('.smali', '')
            pkg = root.replace('baksmali_out/', '')
            
            # Replace with no-op
            if return_type == 'V':
                new_body = f'{sig_line}\n    .registers 1\n    return-void\n.end method'
            else:
                new_body = f'{sig_line}\n    .registers 2\n    new-instance v0, L{pkg}/{class_name};\n    invoke-direct {{v0}}, L{pkg}/{class_name};-><init>()V\n    return-object v0\n.end method'
            
            content = content[:sig_start] + new_body + content[end_pos + len('.end method'):]
            with open(path, 'w') as f: f.write(content)
            print(f'Neutralized: {pkg}/{class_name}->{method_name}(Context)')
```

**Known injected methods across yhf versions:**

| Package | Method | Version pattern |
|---|---|---|
| `ī/íì/iaw` | `w(Context)V` | Entry dialog |
| `ī/íì/iab` | `b(Context)V` | Exit dialog |
| `ī/íì/bi` | `b(Context)Lī/íì/bi;` | Builder |
| `ī/íì/wl` | `w(Context)Lī/íì/wl;` | Builder |
| `ī/íì/wi` | `b(Context)Lī/íì/wi;` | Builder |
| `ī/íì/bl` | `w(Context)Lī/íì/bl;` | Builder |
| `ī/íì/up` | `process(Context)Lī/íì/up;` | Entry (new 2026) |
| `īi/ïi/pk` | `process(Context)Līi/ïi/pk;` | Entry (alternative) |
| `p000/p001/*` | `b/w(Context)` | Renamed `ī/íì/` (2025+) |
| `p002i/p003i/pk` | `process(Context)` | Renamed `īi/ïi/` (2025+) |
| `a/b/pookie` | `ad(Context)` | Moon Reader variant |
| `d6/a` | `a(Context)V` | GPS Data variant |

**⚠️ After neutralizing, ALSO remove `invoke-static` calls from the Activity to these methods.** Combined with neutralization, this double-guarantees the dialog won't appear.

### Step 6: Reassemble DEX files

```bash
API=35
# ONLY reassemble DEXes you modified. Keep others ORIGINAL.
for d in dex4_out dex8_out dex12_out; do
    num=$(echo "$d" | sed 's/dex_out//' | sed 's/dex//')
    [ -z "$num" ] && num=""
    out="classes${num}_new.dex"
    smali assemble "$d" --api "$API" -o "$out"
    echo "$d -> $out: $?"
done
```

### Step 7: Repackage the APK

```python
import zipfile, os, shutil

ORIG = 'original.apk'
OUT = 'hacked.apk'
SIG_EXTS = {'.SF', '.RSA', '.DSA', '.EC'}

# Only replace patched DEXes. Keep all other files ORIGINAL.
patched_dexes = {
    'classes4.dex': 'classes4_new.dex',
    'classes8.dex': 'classes8_new.dex',
    'classes12.dex': 'classes12_new.dex',
}
new_data = {k: open(v, 'rb').read() for k, v in patched_dexes.items() if os.path.exists(v)}

with zipfile.ZipFile(ORIG, 'r') as zin:
    with zipfile.ZipFile(OUT, 'w', zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            fn = item.filename
            # CRITICAL: Only strip signature files, KEEP services/
            if fn.startswith('META-INF/'):
                ext = os.path.splitext(fn)[1].upper()
                base = os.path.basename(fn).upper()
                if ext in SIG_EXTS or base == 'MANIFEST.MF':
                    continue
            if fn in new_data:
                zout.writestr(item, new_data[fn])
            else:
                zout.writestr(item, zin.read(item.filename))
```

### Step 8: Sign and install

```bash
KS="$HOME/.android/debug.keystore"
[ ! -f "$KS" ] && keytool -genkey -v -keystore "$KS" \
    -storepass android -alias androiddebugkey -keypass android \
    -keyalg RSA -keysize 2048 -validity 10000 \
    -dname "CN=Android Debug,O=Android,C=US"

apksigner sign --ks "$KS" --ks-pass pass:android --ks-key-alias androiddebugkey \
    --v1-signing-enabled true --v2-signing-enabled true \
    --out hacked_signed.apk hacked.apk

# Disable Play Protect verification
adb shell settings put global package_verifier_enable 0
adb install hacked_signed.apk
adb shell settings put global package_verifier_enable 1
```

---

## Modder injection patterns (yhf / liteapks)

### Dialogs

The modder `yhf` injects these packages in ALL their modded APKs:

| Package pattern | Classes | Method | Trigger |
|---|---|---|---|
| `ī/íì/` | `bi`, `wl`, `wi`, `bl` | `.b(Context)` or `.w(Context)` | On app launch |
| `ī/íì/` | `iaw`, `iab` | `.w(Context)` or `.b(Context)` | On app exit |
| `īi/ïi/` | `pk` | `.process(Context)` | On app launch (alternative) |
| `bin/ghost/` | `yrf` | `killPM()`, `killOpen()` | Signature killer (sometimes dormant) |
| **`p000/p001/`** (2025+) | `bi`, `wl`, `wi`, `bl` | Same as `ī/íì/` | Renamed variant |
| **`p002i/p003i/`** (2025+) | `pk` | Same as `īi/ïi/` | Renamed variant |

**⚠️ Package names change across versions.** Always use behavioral detection:
```bash
grep -rn "Typeface.createFromAsset\|AlertDialog.Builder.*create\(\)" jadx_out/sources/ \
  | grep -v "androidx\|com/google\|com/example"
```

**Neutralization strategy:**
1. Search all `MainActivity.smali` files for `invoke-static.*ī/íì\|īi/ïi` — remove those lines
2. For each dialog class (`bi`, `wl`, `wi`, `bl`, `iaw`, `iab`, `pk`), replace their show methods with no-ops
3. DO NOT delete the classes — references exist elsewhere

### Native libraries injected

| File | Purpose |
|---|---|
| `libapminsighta.so` | Telemetry/monitoring |
| `libapminsightb.so` | Telemetry/monitoring |
| `libbuffer_pg.so` | Pangle anti-tamper |
| `libfile_lock_pg.so` | Pangle anti-tamper |

### Obfuscated packages vs modder trash

Packages with names like `o0O0`, `O80`, `p177o8oo88`, `ili111` are **NOT modder code**. They are ProGuard/R8 obfuscation from the original developer. The modder only injects: `ī/íì/`, `īi/ïi/`, `bin/ghost/`.

---

## Case Studies

Real-world examples. See individual files in [cases/](cases/):

| Case | File | Key lesson |
|---|---|---|
| GPS Emulator 3.29 | [gps-emulator.md](cases/gps-emulator.md) | Native multi-layer → hack the ORIGINAL |
| CamScanner 7.20.5 | [camscanner.md](cases/camscanner.md) | Java light protection, 3 DEX patches |
| GPS Data 3.1.03 | [gps-data.md](cases/gps-data.md) | yhf renamed `p000/p001/` — behavioral detection |
| YouTube Morphe | [youtube-morphe.md](cases/youtube-morphe.md) | ZIP corruption, NOT native checks |
| AdGuard 4.14.0 | [adguard.md](cases/adguard.md) | Call sites in DIFFERENT DEX |

---

## Native signature protection (YouTube, Google apps)

### The crash pattern

Google apps with native `.so` libraries can enforce integrity checks during `JNI_OnLoad` — before any Java code runs. The stack looks like:

```text
Activity.onCreate()
 └─ libelements.so : JNI_OnLoad
     └─ libgoogle3.so : JNI_OnLoad_libelements
         └─ SIGABRT
```

Key observations:
- APK installs fine
- Splash screen may appear briefly (false positive)
- App dies when native libs load
- `zip -0` (STORE) fixes ZIP structure issues but NOT native checks
- Re-signing alone is not sufficient

### How to confirm it's a signature check

```bash
# Look for signature-related strings in .so files
strings libelements.so | grep -i sign
strings libgoogle3.so | grep -iE "sign|cert|package|fingerprint"
rabin2 -zz libgoogle3.so   # radare2 string search
objdump -s libgoogle3.so    # raw section dump

# Expected strings if it IS a signature check:
#   "Signature verification failed"
#   "Package signature mismatch"
#   "Certificate check failed"
```

**⚠️ The crash alone does NOT prove it's a signature check.** It could also be: APK integrity, SO integrity, DEX verification, anti-tamper, Play Integrity, SafetyNet, or ZIP structure checks. Full analysis requires: native tombstone, logcat, memory addresses, and `JNI_OnLoad` disassembly.

### Modder techniques to bypass native checks

#### Technique 1: Patch the .so directly (ARM64 hex edit)

Typical pattern in C:
```c
if (signature_valid()) { return JNI_VERSION_1_6; }
abort();
```

Patch to always succeed:
```asm
; Original:
BL  verify_signature
CBZ W0, crash_label

; Patched:
MOV W0, #1      ; always return true
NOP
NOP
```

ARM64 bypass instructions:
| Instruction | Hex (LE) | Effect |
|---|---|---|
| `MOV W0, #1` | `20 00 80 52` | Return true/1 |
| `MOV X0, #0` | `00 00 80 D2` | Return 0 |
| `RET` | `C0 03 5F D6` | Return immediately |
| `NOP` | `1F 20 03 D5` | No operation |
| `B <label>` | varies | Unconditional jump past crash |

#### Technique 2: Runtime hooking (Frida / LSPosed / Zygisk)

Hook `JNI_OnLoad` or the validation function at runtime:
```javascript
// Frida script
Interceptor.attach(Module.findExportByName("libelements.so", "JNI_OnLoad"), {
    onLeave(retval) { retval.replace(0x10006); } // JNI_VERSION_1_6
});
```

Requires root + Frida/LSPosed on device. Not redistributable.

#### Technique 3: Reuse pre-patched .so files

Many modders extract and reuse already-patched `libelements.so` / `libgoogle3.so` from previous working versions, adapting only Java changes as needed.

#### Technique 4: Remove library loading (rarely works for YouTube)

```java
// Patch smali to catch loadLibrary failures
try {
    System.loadLibrary("elements");
} catch (Throwable ignored) {}
```

Modern YouTube versions require these libs for core functionality — this technique usually breaks video playback.

### ZIP requirements for APKs with native libs — definitive test results

**Tested on YouTube 21.26.364 (Morphe) with AOSP testkey:**

| # | Method | DEX modified? | Result |
|---|---|---|---|
| 1 | `apksigner sign` direct (no content change) | No | ✅ Works |
| 2 | Extract + `zip -0` + sign | Yes | ✅ Works |
| 3 | `zipfile.ZIP_DEFLATED` + sign | Yes | ❌ ZIP corruption |
| 4 | `zipfile.ZIP_STORED` + sign | Yes | ✅ Works |
| 5 | Hex-edit raw DEX + apkzlib | Yes | ❌ DEX checksum invalid |
| 6 | **baksmali → smali + apkzlib** + sign | Yes | ✅ **Works** |
| 7 | apkzlib noop (realign only) + sign | No | ✅ Works |
| 8 | apkzlib delete+add (identical data) + sign | No | ✅ Works |

**Conclusion**: The problem was NEVER native signature verification. `libgoogle3.so` and `libelements.so` are **identical** between stock and Morphe (SHA256 verified). The crashes were caused by:
1. Python `zipfile` corrupting ZIP structure → use `zip -0` or apkzlib instead
2. Hex-editing raw DEX leaving invalid checksums → use baksmali/smali for proper DEX generation
3. Not a signature check — YouTube's native libs don't validate the APK certificate in this version

**Conclusion**: YouTube's `libgoogle3.so` (58 MB) validates DEX content integrity (not ZIP structure, not APK signature). The native library stores a hash of the DEX files and compares it at `JNI_OnLoad`. Even Google's own `apkzlib` (which perfectly preserves ZIP structure) triggers the check when DEX content changes.

**The three real solutions for Google apps:**
1. **Patch the .so** — find the DEX hash check in `libgoogle3.so` (Ghidra → trace `abort()` XREFs → patch or NOP the check)
2. **Update the expected hash** — find where the expected hash is stored in the .so and update it to match the modified DEX
3. **Runtime hooking** — LSPosed/Frida intercept validation at runtime (not redistributable)
4. **Re-sign only, no content changes** — works but can't modify app behavior

### Finding native method addresses

```bash
# Extract JNINativeMethod arrays from relocations
readelf -r lib.so | grep R_AARCH64_RELATIV
```

Each `JNINativeMethod` entry = 24 bytes (name ptr + sig ptr + fn ptr). The pointers are zero in the static file — actual addresses are in relocation entries.

### ARM64 instruction encoding reference

| Instruction | Hex (little-endian) | Usage |
|---|---|---|
| `ret` | `c0 03 5f d6` | Return immediately (void functions) |
| `nop` | `1f 20 03 d5` | No operation |
| `mov x0, xzr` | `e0 03 1f aa` | Return 0 / null |
| `mov x0, x2` | `e0 03 02 aa` | Return input param (Object functions) |
| `mov x0, x1` | `e0 03 01 aa` | Return jclass (Object functions) |
| `movz w20, #1` | `34 00 80 52` | Set w20 = 1 (true) |

### Finding string references in ARM64

```python
# ADD (immediate, 64-bit) encoding: (word & 0xFF800000) == 0x91000000
# sh = (word >> 22) & 1
# imm12 = (word >> 10) & 0xFFF
# Rn = (word >> 5) & 0x1F

# ADRP encoding: (word & 0x9F000000) == 0x90000000
# Rd = word & 0x1F
# immlo = (word >> 29) & 0x3
# immhi = (word >> 5) & 0x7FFFF
# imm = sign_extend((immhi << 2) | immlo, 21)
# target_page = (pc & ~0xFFF) + (imm << 12)

# CRITICAL: The compiler may emit 3 ADRP instructions followed by 3 ADD instructions.
# Search for ADD first, then look backwards up to 12 instructions for matching ADRP.
```

### JNI JNIEnv offset reference (ARM64, 8 bytes per entry)

| Offset | Function | Use |
|---|---|---|
| 0x030 | FindClass | Load Java class |
| 0x108 | GetMethodID | Get instance method ID |
| 0x128 | CallBooleanMethod | Call method returning boolean |
| 0x388 | GetStaticMethodID | Get static method ID |
| 0x3a0 | CallStaticObjectMethodA | Call static method (array args) |
| 0x478 | CallStaticVoidMethodA | Call static void method (array args) |
| 0x488 | GetStaticFieldID | Get static field ID |
| 0x6b8 | RegisterNatives | Register native methods |
| 0x720 | ExceptionCheck | Check for pending exception |

---

See [google-apis.md](google-apis.md) for Google Maps/Places API key replacement, AOSP testkey signing, and Amap tile overlay techniques.

---

## Tool paths

| Tool | Path | Use |
|---|---|---|
| adb | `~/Android/Sdk/platform-tools/adb` | Device connection |
| jadx | `/usr/local/bin/jadx` | Decompile DEX → Java |
| baksmali | `/usr/bin/baksmali` | Disassemble DEX → smali |
| smali | `/usr/bin/smali` | Assemble smali → DEX |
| apksigner | `/usr/bin/apksigner` | Sign APK |
| aapt | `/usr/bin/aapt` | Inspect APK manifest |
| r2 | `/usr/local/bin/r2` | Disassemble .so (ARM64) |
| readelf | `/usr/bin/readelf` | ELF relocations |
| keytool | `/usr/bin/keytool` | Generate keystore |
| strings | `/usr/bin/strings` | Extract strings |
| openssl | `/usr/bin/openssl` | Convert PK8→PKCS12, inspect certs |
| curl | `/usr/bin/curl` | Download AOSP testkey |
| base64 | `/usr/bin/base64` | Decode AOSP gitiles blobs |
| frida | `~/.local/bin/frida` | Runtime hooking (dynamic analysis) |
| apktool | `/usr/bin/apktool` | Decode/rebuild APK resources |
| ghidra | `/opt/ghidra/` | ARM64 disassembly + decompilation |

## Native analysis workflow (`.so` patches) — from crash to fix

When an APK crashes during `JNI_OnLoad`, the goal is to identify exactly what condition triggers the crash — not to assume it's a signature check.

```
JNI_OnLoad → ??? → abort()
                    ↑
               FIND THIS
```

### Step 1: Get the full crash data

```bash
adb logcat > logcat.txt                        # Full logcat
adb shell "su -c 'ls /data/tombstones'"        # List tombstones (needs root)
adb pull /data/tombstones/tombstone_XX          # Pull the tombstone
```

Key data in the tombstone:
```text
SIGABRT / SIGSEGV
abort()
Fatal signal
backtrace (full stack)
```

### Step 2: Extract the native libraries

```bash
unzip app.apk -d extract/
# Libraries are in: lib/arm64-v8a/
# Extract: libelements.so, libgoogle3.so, etc.
```

### Step 3: Search symbols and strings

```bash
readelf -Ws libgoogle3.so > symbols.txt
strings libgoogle3.so > strings.txt

grep -i sign strings.txt
grep -i cert strings.txt
grep -i integrity strings.txt
grep -i verify strings.txt
grep -i package strings.txt
```

Possible finds: `"Signature verification failed"`, `"Package signature mismatch"`, `"Certificate check failed"`, `"Integrity check"`.

### Step 4: Open in Ghidra

```text
File → Import → libgoogle3.so
Language: AARCH64 (ARM64 little-endian)
Auto-analyze: yes

Symbol Tree → search:
  JNI_OnLoad
  JNI_OnLoad_libelements
```

### Step 6: Find the condition

In Ghidra's decompiler, trace from `JNI_OnLoad` looking for:
```c
abort();
__android_log_assert(...);
__assert2(...);
raise(SIGABRT);
exit(...);
```

The goal is NOT the abort — it's finding what CHECK triggers it.

### Step 5: Follow the execution to abort()

In Ghidra's decompiler, trace from `JNI_OnLoad` looking for:
```c
abort();
__android_log_assert(...);
__assert2(...);
raise(SIGABRT);
exit(...);
```

The goal is NOT the abort — it's finding what CHECK triggers it.

### Step 6: Find the condition

Typical pattern:
```c
if (!verify_signature()) { abort(); }    // ── or ──
if (!verify_integrity())  { abort(); }    // ── or ──
if (check_failed)         { abort(); }
```

**For DEX integrity checks specifically** (like YouTube's `libgoogle3.so`):
```c
// Native code computes hash of classes.dex and compares
if (dex_hash != expected_hash) { abort(); }
```

Search Ghidra for:
- Cross-references to `abort()` → `References To` on the function
- String references: `SHA`, `MessageDigest`, `digest`, `CRC`, `classes.dex`
- Buffer comparisons that lead to abort paths

**Do not assume it's a signature check.** The data being validated could be:
- DEX content hash (YouTube uses this)
- APK file integrity (hash)
- Resource integrity
- Play Integrity / SafetyNet
- Anti-tamper
- DEX checksum from headers

### Ghidra trace: abort() → DEX hash check

When the crash is in `JNI_OnLoad` → `libgoogle3.so` → `abort()`, the goal is to find the DEX hash comparison and patch it.

**Quick trace path:**
```
libgoogle3.so → abort() → XREFs → calling function → memcmp() → hash compare → patch
```

**Step-by-step:**

```bash
# 1. Extract and open in Ghidra
unzip -p app.apk lib/arm64-v8a/libgoogle3.so > libgoogle3.so
# Ghidra: File → Import → libgoogle3.so (AARCH64:LE:64:v8A, auto-analyze)
```

```text
# 2. Find abort()
Symbol Tree → search "abort"
Right click → References → Show References To
```

Look for functions that call `abort()` conditionally:
```c
if (!check()) { abort(); }
if (memcmp(h1, h2, 32)) { abort(); }
if (hash != expected) { abort(); }
```

```text
# 3. Open Decompiler (F4)
Trace backwards from the condition — click the compared function/variable to follow it
```

```text
# 4. Search for hash clues
Search → Program Text → SHA, digest, checksum, memcmp, classes.dex
Window → Defined Strings → search: integrity, verify, signature
```

```text
# 5. Find expected hash (32 bytes for SHA-256)
Look for byte arrays: local_38[0]=0x34; local_38[1]=0xAB; ...
Or memcmp(calculated, expected, 32)
```

```text
# 6. Patch
Right click instruction → Patch Instruction:
  CBNZ X0, fail  →  NOP           (remove branch to abort)
  B fail         →  NOP           (remove unconditional fail)
  BL check       →  MOV W0, #1    (force return true)
```

```text
# 7. Export and repackage
File → Export Program → patched.so
# Replace in APK, zip -0, sign with any key
```

### Step 7: Confirm the function with Frida

```bash
pip install frida-tools
# On Android: push frida-server, run it
```

```javascript
// Hook the suspected function
var addr = Module.findExportByName("libgoogle3.so", "verify_signature");
Interceptor.attach(addr, {
    onLeave(retval) {
        console.log("verify_signature returned:", retval);
        retval.replace(1);  // Force success
    }
});
```

If the crash disappears → function confirmed. This also gives you the exact address to patch.

### Step 8: Patch the binary

Once the exact condition and offset are known:

| Pattern | Original | Patched | ARM64 hex |
|---|---|---|---|
| Boolean return | `BL verify; CBZ W0, crash` | `MOV W0, #1; NOP; NOP` | `20 00 80 52 1F 20 03 D5` |
| Abort after check | `BL verify; CBNZ W0, ok` | `B ok` (unconditional jump) | calculate branch offset |
| Void abort call | `BL verify_integrity` | `NOP` (skip the call) | `1F 20 03 D5` |
| Conditional abort | `CBZ W0, abort_label` | `NOP; NOP` (remove branch) | `1F 20 03 D5` ×2 |

Tools: Ghidra (Patch Instruction), radare2 (`wx`), rizin, Cutter.

### Step 9: Repack and sign

```bash
# Replace the patched .so in the APK
cp patched_libgoogle3.so extract/lib/arm64-v8a/libgoogle3.so

# Repackage with STORE compression
cd extract && zip -0 -r ../patched.apk . && cd ..

# Sign and install
apksigner sign --ks keystore.p12 --ks-pass pass:android \
    --v1-signing-enabled true --v2-signing-enabled true \
    --out final.apk patched.apk
adb install -r final.apk
```

### Critical checklist before patching

Before modifying a single byte, answer:
1. What function calls `abort()`?
2. What condition triggers it?
3. What data is being validated?
4. Is it signature, integrity, Play Integrity, anti-tamper, or something else?
5. Has Frida confirmed the hypothesis?

Without answers, any patch is a guess.

### Minimal toolset for native analysis

```text
jadx       → find System.loadLibrary() in Java
Ghidra     → ARM64 decompilation, trace abort() paths
r2/rizin   → quick disasm, hex patch, string search
Frida      → runtime hooking, confirm function behavior
binutils   → strings, readelf, objdump
ADB        → logcat, tombstones, push/pull
```

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `INSTALL_FAILED_VERIFICATION_FAILURE` | Play Protect blocks unknown signature | `settings put global package_verifier_enable 0` |
| `INSTALL_FAILED_UPDATE_INCOMPATIBLE` | Package signature mismatch with installed version | `adb uninstall` first |
| `ExceptionInInitializerError` at `kotlinx.coroutines` | `META-INF/services/` was deleted | Keep services/, only delete signature files |
| `NoClassDefFoundError` after removing classes | Direct DEX reference to deleted class | Neutralize methods, don't delete classes |
| `ClassNotFoundException: App` in modded APK | DEX encrypted with APK signature | Hack the original APK instead |
| smali assembly errors about `.registers` | Leftover method body code | Check for orphan code after patching |
| App crashes after smali roundtrip on unmodified DEX | baksmali/smali corrupts cross-DEX references | Only reassemble DEXes you patched, keep others original |
| `Authorization failure` in Google Maps | Re-signed APK, API key restricts SHA-1 fingerprint | Sign with AOSP testkey + use unrestricted API key |
| `INVALID_ARGUMENT` from Google Maps SDK | API key has package restriction or Maps SDK not enabled | Find API key without restrictions (see Google APIs section) |
| Liteapks markers not found but dialog appears | Modder changed package names (`p000/p001/` instead of `ī/íì/`) | Use behavioral detection: `grep -rn "Typeface.createFromAsset" jadx_out/` |
| Modder injection found but `strings` shows nothing | Encrypted/obfuscated strings in DEX | Decompile with jadx+baksmali, search smali by behavior |
| YouTube shows `adcontext=` in QOE pings | Mod didn't fully disable ad system | Check account/premium smali patches are applied |
| `ClassNotFoundException: Executor$CppProxy` | Python `zipfile` corrupted ZIP structure | Use `zip -0` (STORE) or apkzlib for repackaging |
| Hex-edited DEX causes crash but smali'd DEX works | Raw DEX has invalid internal checksum (Adler32/SHA1) | Always use baksmali→smali, never hex-edit DEX directly |
| Liteapks dialog still appears after URL replacement | Dialog class (`com/zx/cmz/Strings` + `LB`) fetches content from multiple sources | Find ALL references: URLs, promotional strings, dialog trigger in MainActivity |
