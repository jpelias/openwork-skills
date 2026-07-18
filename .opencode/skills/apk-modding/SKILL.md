---
name: apk-modding
description: >
  Modify and hack Android APKs: decompile (jadx, baksmali), patch smali to change license/premium defaults,
  force method return values, neutralize modder-injected dialogs (yhf/liteapks patterns), reassemble DEX files,
  repackage with proper ZIP handling, sign and install. Covers native .so analysis (Ghidra, radare2, Frida)
  for apps with JNI_OnLoad signature/integrity checks, ARM64 hex patching, and Google API key replacement.
  Includes case studies (GPS Emulator, CamScanner, YouTube Morphe, AdGuard, GPS Data), Morphe patcher
  integration, PairipCore/Dex2C bypass, Frida Gadget embedding, signature killers (ApkSignatureKiller,
  APKKiller, SRPatch-X), virtual engines (VirtualApp, LSPatch), Unity/IL2CPP modding, and a curated
  ecosystem of 50+ modding tools. Use for authorized testing, research, or modifying your own apps.
---

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
  grep -rn "invoke.*ī/íì\|invoke.*īi/ïi\|invoke.*p000/p001\|invoke.*a/b/pookie\|invoke.*d6/a\|invoke.*w6/b\|invoke.*q6/c\|invoke.*p6/e" dex*_out/ --include="*.smali" \
    | grep -vE "^dex[0-9]*_out/ī/|^dex_out/ī/|^dex[0-9]*_out/īi/|^dex_out/īi/|^dex[0-9]*_out/p000/|^dex_out/p000/"
  → The calls are often in classes2.dex (MainActivity), not in the DEX with the injection
  → The grep -v excludes results FROM files inside injected packages, not calls TO them

□ List ALL injected methods (public/private/static/constructor/<clinit>)
  for pkg in "ī/íì" "īi/ïi" "p000/p001" "p002i/p003i" "a/b/pookie" "d6/a"; do
    find dex*_out/$pkg/ -name "*.smali" 2>/dev/null | xargs grep "\.method " 2>/dev/null
  done

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

**⚠️ Limitation:** This approach patches the **stored default value**. If the app re-syncs preferences from Play Billing or a server, the stored value may be overwritten back to `false`. For apps with Play Billing, use Step 5d (hook getter by key name) instead, which intercepts the read and survives re-sync.

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
        
        # Collect ALL matches first (positions are valid against original content)
        matches = []
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
            
            matches.append((sig_start, end_pos + len('.end method'), sig_line,
                            return_type, pkg, class_name, method_name))
        
        if not matches: continue
        
        # Apply patches from BOTTOM to TOP to preserve positions
        for sig_start, end_pos, sig_line, return_type, pkg, class_name, method_name in reversed(matches):
            if return_type == 'V':
                new_body = f'{sig_line}\n    .registers 1\n    return-void\n.end method'
            else:
                new_body = (f'{sig_line}\n    .registers 2\n'
                            f'    new-instance v0, L{pkg}/{class_name};\n'
                            f'    invoke-direct {{v0}}, L{pkg}/{class_name};-><init>()V\n'
                            f'    return-object v0\n.end method')
            content = content[:sig_start] + new_body + content[end_pos:]
        
        # Write file ONCE after all patches applied
        with open(path, 'w') as f: f.write(content)
        for _, _, _, _, pkg, class_name, method_name in matches:
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

### Step 5d: Patching strategy — Hook getter by key name

Changing `const/4 v2, 0x0` to `0x1` works for simple apps, but some apps re-sync preferences from Play Billing or a server, overwriting your patched default. A more resilient approach is to **intercept the getter by key name** so it always returns `true` regardless of the stored value.

In smali, inject at the start of the `getBoolean` method:

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
    # ... original method body continues here
```

This survives Play Billing re-sync because it intercepts the **read**, not the stored value. The `endsWith` check allows matching key suffixes even if the full key includes a package prefix.

**Source:** `arandomhooman/hoomans-morphe-patches` — `EnablePremiumPatch.kt` (BlockerHero)

### Step 5e: Patching strategy — Suppress re-login dialogs and auth toasts

When you force premium features without a valid login, the app may:
1. Try to sync with the server → gets 401 → launches a `ReLoginDialogActivity`
2. Show "Unauthenticated" toasts repeatedly

**Suppress re-login broadcast** (fake UID causes server 401):
```smali
# Find the method that sends re-login broadcast, replace with:
.method ...sendReLoginBroadcast()V
    .registers 0
    return-void
.end method
```

**Suppress ReLoginDialogActivity launch**:
```smali
# Find the method that launches the dialog, replace with:
.method ...launchReLoginDialog()V
    .registers 0
    return-void
.end method
```

**Suppress auth-error toasts only** (leave other toasts working):
```smali
# At the start of the toast helper method:
if-eqz p1, :show
const-string v0, "uthenticat"          # matches "Authentication" / "Unauthenticated"
invoke-virtual {p1, v0}, Ljava/lang/String;->contains(Ljava/lang/CharSequence;)Z
move-result v0
if-eqz v0, :show
return-void
:show
# ... original toast code continues
```

**Sources:**
- `rushiranpise/morphe-patches` — `YearlyUnlockPatch.kt` (CamScanner): suppresses `SendReLoginBroadcast` + `LaunchReLoginDialog`
- `arandomhooman/hoomans-morphe-patches` — `EnablePremiumPatch.kt` (BlockerHero): suppresses auth-error toasts

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

**⚠️ Compression strategy — use mixed STORE/DEFLATE, not all-STORE:**

| File type | Compression | Why |
|---|---|---|
| `.so` (native libs) | `ZIP_STORED` | Required by Android; compressed .so causes `dlopen` failures |
| `resources.arsc` | `ZIP_STORED` | **Android 11+ requirement** — compressed resources.arsc causes install failure |
| DEX files (`classes*.dex`) | `ZIP_STORED` with Python `zipfile` | Python's `zipfile.ZIP_DEFLATED` corrupts APK ZIP structure when building from scratch (confirmed in YouTube Morphe tests). If using `apktool b` or `zip` command, DEFLATED works fine for DEX — the issue is Python-specific, not DEFLATED itself |
| Everything else | `ZIP_DEFLATED` | Smaller APK, no issues with non-native/non-resource files |

```python
import zipfile, os, shutil

ORIG = 'original.apk'
OUT = 'hacked.apk'
SIG_EXTS = {'.SF', '.RSA', '.DSA', '.EC'}
STORE_EXTS = {'.so', '.arsc'}
STORE_NAMES = {'resources.arsc'}

# Only replace patched DEXes. Keep all other files ORIGINAL.
patched_dexes = {
    'classes4.dex': 'classes4_new.dex',
    'classes8.dex': 'classes8_new.dex',
    'classes12.dex': 'classes12_new.dex',
}
new_data = {k: open(v, 'rb').read() for k, v in patched_dexes.items() if os.path.exists(v)}

with zipfile.ZipFile(ORIG, 'r') as zin:
    with zipfile.ZipFile(OUT, 'w') as zout:
        for item in zin.infolist():
            fn = item.filename
            # CRITICAL: Only strip signature files, KEEP services/
            if fn.startswith('META-INF/'):
                ext = os.path.splitext(fn)[1].upper()
                base = os.path.basename(fn).upper()
                if ext in SIG_EXTS or base == 'MANIFEST.MF':
                    continue
            # Determine compression: STORE for .so, resources.arsc, DEX; DEFLATE for rest
            if fn in STORE_NAMES or os.path.splitext(fn)[1].lower() in STORE_EXTS or fn.endswith('.dex'):
                compress = zipfile.ZIP_STORED
            else:
                compress = zipfile.ZIP_DEFLATED
            if fn in new_data:
                zout.writestr(item, new_data[fn], compress_type=compress)
            else:
                zout.writestr(item, zin.read(item.filename), compress_type=compress)
```

**After repackaging, always run zipalign before signing:**
```bash
zipalign -p -f 4 hacked.apk hacked_aligned.apk
```

`-p` aligns uncompressed `.so` files to page boundaries (required for Android 15+).

**Source:** `test1ng-guy/android-sandbox-explorer` — `repack.py`

### Step 8: Sign and install

```bash
KS="$HOME/.android/debug.keystore"
[ ! -f "$KS" ] && keytool -genkey -v -keystore "$KS" \
    -storepass android -alias androiddebugkey -keypass android \
    -keyalg RSA -keysize 2048 -validity 10000 \
    -dname "CN=Android Debug,O=Android,C=US"

apksigner sign --ks "$KS" --ks-pass pass:android --ks-key-alias androiddebugkey \
    --v1-signing-enabled true --v2-signing-enabled true \
    --out hacked_signed.apk hacked_aligned.apk

# Disable Play Protect verification
adb shell settings put global package_verifier_enable 0
adb install hacked_signed.apk
adb shell settings put global package_verifier_enable 1
```

**⚠️ Always sign the zipaligned APK (`hacked_aligned.apk`), not the unaligned one.** Signing before zipalign invalidates the alignment.

### Split APK handling

Many modern apps ship as split APKs (`base.apk` + `split_config.arm64_v8a.apk` + `split_config.xxhdpi.apk` etc.). To handle them:

```bash
# 1. Pull all splits from device
adb shell pm path com.example.app
# Output:
#   package:/data/app/.../base.apk
#   package:/data/app/.../split_config.arm64_v8a.apk
#   package:/data/app/.../split_config.en.apk
adb pull /data/app/.../base.apk original/
adb pull /data/app/.../split_*.apk original/

# 2. Patch base.apk normally (smali patches go here)
# 3. If injecting a .so, inject into the architecture split (split_config.arm64_v8a.apk)

# 4. Sign ALL APKs with the same key
for apk in original/base.apk original/split_*.apk; do
    apksigner sign --ks "$KS" --ks-pass pass:android \
        --ks-key-alias androiddebugkey \
        --v1-signing-enabled true --v2-signing-enabled true \
        --out "signed/$(basename $apk)" "$apk"
done

# 5. Install all at once
adb install-multiple signed/base.apk signed/split_*.apk
```

**Source:** `test1ng-guy/android-sandbox-explorer` — `repack.py`

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
grep -rn "Typeface.createFromAsset\|AlertDialog.Builder.*create\(\)" jadx_out/sources/ --include="*.java" \
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
| AdGuard 4.14.0 | [adguard.md](cases/adguard.md) | Call sites in DIFFERENT DEX + 5-layer license state |
| Liteapks Store 1.0.18 | [liteapks-store.md](cases/liteapks-store.md) | Self-protected app: shell + encrypted payload + InMemoryDexClassLoader |

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
- Re-signing alone works if you don't modify DEX content (Test 1 ✅). Re-signing fails if you need to modify DEX content, because `libgoogle3.so` validates DEX integrity hash

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

**⚠️ Important:** Tests 2-6 were performed on the Morphe-modified APK, which already has the native DEX integrity check bypassed by Morphe's own patches. On **stock YouTube** (without Morphe's native patches), modifying DEX content would trigger `libgoogle3.so`'s hash check regardless of repackaging method.

| # | Method | DEX modified? | Result |
|---|---|---|---|
| 1 | `apksigner sign` direct (no content change) | No | ✅ Works |
| 2 | Extract + `zip -0` + sign | Yes | ✅ Works (Morphe) |
| 3 | `zipfile.ZIP_DEFLATED` + sign | Yes | ❌ ZIP corruption (Python zipfile issue, not native check) |
| 4 | `zipfile.ZIP_STORED` + sign | Yes | ✅ Works (Morphe) |
| 5 | Hex-edit raw DEX + apkzlib | Yes | ❌ DEX checksum invalid |
| 6 | **baksmali → smali + apkzlib** + sign | Yes | ✅ **Works** (Morphe) |
| 7 | apkzlib noop (realign only) + sign | No | ✅ Works |
| 8 | apkzlib delete+add (identical data) + sign | No | ✅ Works |

**Conclusion**: YouTube's native libs do NOT validate the APK certificate (signature). However, `libgoogle3.so` (58 MB) **does validate DEX content integrity** on stock YouTube — it stores a hash of the DEX files and compares it at `JNI_OnLoad`. Tests 2-6 above passed because they were run on the Morphe APK, which already bypasses this check. On stock YouTube, the same DEX modifications would trigger `abort()`.

The crashes observed during testing were caused by two separate issues:
1. **ZIP corruption** from Python `zipfile.ZIP_DEFLATED` → use `zip -0` (STORE), `zipfile.ZIP_STORED`, or apkzlib instead. This is a Python `zipfile` bug, not a DEFLATED compression issue — `apktool b` and `zip` command handle DEFLATED correctly.
2. **DEX checksum invalidation** from hex-editing raw DEX → use baksmali/smali for proper DEX generation

`libgoogle3.so` and `libelements.so` are **identical** between stock and Morphe (SHA256 verified) — no native patches are needed for re-signing, only for DEX content changes.

**The four real solutions for Google apps with DEX integrity checks:**
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
| apktool | `/usr/bin/apktool` | Decode/rebuild APK resources + smali (alternative to baksmali/smali for apps needing resource/manifest edits) |
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

## Morphe patcher — programmatic alternative to manual smali

Manual smali editing works but is fragile: offsets change between versions, and patches must be redone for every update. The **Morphe patcher** ecosystem provides a Kotlin DSL that automates patching with fingerprints and version-agnostic method matching.

### Repositories

| Repo | Stars | Description |
|---|---|---|
| `MorpheApp/morphe-manager` | ★6341 | Morphe app patcher for Android (the engine) |
| `rushiranpise/morphe-patches` | ★173 | 50+ app patches maintained (AdGuard, CamScanner, AccuWeather, etc.) |
| `arandomhooman/hoomans-morphe-patches` | ★92 | Additional patches (BlockerHero, etc.) |
| `Paresh-Maheshwari/morphe-ai` | ★114 | AI-powered multi-agent pipeline for APK analysis and patch writing |

### How it works

Instead of manually editing smali, you define a `bytecodePatch` with `Fingerprint` objects that locate methods by signature patterns, then inject instructions:

```kotlin
val enablePremiumPatch = bytecodePatch(
    name = "Enable Premium",
    description = "Unlocks premium features.",
) {
    compatibleWith(Compatibility(
        name = "BlockerHero",
        packageName = "com.blockerhero",
        targets = listOf(AppTarget("1.5.0")),
    ))

    execute {
        // Hook getBoolean by key name — survives Play Billing re-sync
        PrefsGetBooleanFingerprint.method.addInstructionsWithLabels(
            0,
            """
                const-string v0, "com.blockerhero.KEY_IS_PREMIUM"
                invoke-virtual {p1, v0}, Ljava/lang/String;->endsWith(Ljava/lang/String;)Z
                move-result v0
                if-eqz v0, :original
                const/4 v0, 0x1
                return v0
            """,
            ExternalLabel("original", method.getInstruction(0)),
        )
    }
}
```

### When to use Morphe patcher vs manual smali

| | Manual smali | Morphe patcher |
|---|---|---|
| One-off patch | ✅ Faster | Overkill |
| Maintaining patches across versions | ❌ Fragile | ✅ Fingerprints adapt |
| Sharing with community | ❌ Hard to distribute | ✅ Versionable, shareable |
| Apps with many patch targets | ❌ Tedious | ✅ Scales well |
| Learning how patches work | ✅ Transparent | ❌ Abstracted |

---

## Runtime signature bypass (PMS Hook, IO redirection)

When an app performs signature verification at runtime (not in native code), there are two runtime techniques that avoid patching the app entirely. These require root + Xposed/LSPosed or a virtualization framework.

### PMS Hook (PM Proxy)

Hook `ActivityThread.sPackageManager` and `ApplicationPackageManager.mPM` via Java dynamic proxy to return a spoofed signature when the app calls `getPackageInfo(GET_SIGNATURES)`:

```java
public static void hookPMS(Context context, String originalSignature, String appPkgName) {
    Class<?> activityThreadClass = Class.forName("android.app.ActivityThread");
    Method currentActivityThreadMethod = activityThreadClass.getDeclaredMethod("currentActivityThread");
    Object currentActivityThread = currentActivityThreadMethod.invoke(null);

    Field sPackageManagerField = activityThreadClass.getDeclaredField("sPackageManager");
    sPackageManagerField.setAccessible(true);
    Object sPackageManager = sPackageManagerField.get(currentActivityThread);

    Class<?> iPackageManagerInterface = Class.forName("android.content.pm.IPackageManager");
    Object proxy = Proxy.newProxyInstance(
        iPackageManagerInterface.getClassLoader(),
        new Class<?>[]{iPackageManagerInterface},
        new PmsHookBinderInvocationHandler(sPackageManager, originalSignature, appPkgName, 0)
    );

    // Replace sPackageManager in ActivityThread
    sPackageManagerField.set(currentActivityThread, proxy);

    // Replace mPM in ApplicationPackageManager
    PackageManager pm = context.getPackageManager();
    Field mPmField = pm.getClass().getDeclaredField("mPM");
    mPmField.setAccessible(true);
    mPmField.set(pm, proxy);
}
```

The `InvocationHandler` intercepts `getPackageInfo` calls and returns a `PackageInfo` with the original signature bytes.

**Source:** `ZJ595/AndroidReverse` (★2222) — Lesson 6: 签名校验对抗的多种姿势

### IO redirection

Redirect file reads so that when the app opens its own APK to verify the signature, it reads the **original unmodified APK** instead of the patched one.

Tools:
- **VirtualApp** (`asLody/VirtualApp`) — virtualization engine that can intercept file I/O
- **Ratel** (`virjarRatel/ratel-core`) — RAT framework with IO redirection support
- **SVC TraceHook** — ptrace + seccomp sandbox for syscall-level redirection

**Source:** `ZJ595/AndroidReverse` (★2222) — Lesson 6: IO重定向

### Triangle verification (三角校验)

A more complex pattern than simple circular verification:

```
libnative.so ──checks──> classes.dex
classes.dex  ──checks──> dynamically loaded dex (extracted at runtime, deleted after check)
dynamic dex  ──checks──> libnative.so
```

Each component verifies the next in a triangle. Patching one breaks the chain. Requires patching all three simultaneously or using runtime hooks.

**Source:** `ZJ595/AndroidReverse` (★2222) — Lesson 6

---

## Android 16+ Developer Verifier bypass

Starting September 2026, `com.google.android.verifier` (a pre-installed system service) blocks APK installs on certified Android 16+ devices in BR/ID/SG/TH when the signing certificate isn't in Google's developer registry. Policy is controlled by phenotype flags pulled from Google's servers.

**Impact:** Sideloading patched APKs on Android 16+ certified devices in affected regions may be blocked even with unknown sources enabled.

**Bypass layers (DEX patching of the verifier app):**

| Layer | Method | Patch |
|---|---|---|
| 1 | `onVerificationRequired` / `onVerificationRetry` | Call `reportVerificationBypassed(1)` immediately |
| 2 | Platform policy flag (45681539) | Return `Long(0)` = NONE (no blocking) |
| 3 | Forced backport flag (45749715) | Return `Boolean.TRUE` (short-circuit path) |

**⚠️ Requirements:**
- Patched verifier APK must be installed as a **system app** (replacing the original) via Magisk module or ADB with root
- The verifier holds `DEVELOPER_VERIFICATION_AGENT` privilege
- ADB installs are exempt from verification regardless

**Source:** `rushiranpise/morphe-patches` — `AndroidVerifierBypassPatch.kt`

---

## PairipCore license bypass

PairipCore (`libpairipcore.so`) is a Google Play license verification library that encrypts app strings in a vault and validates the APK signature against the Play Store. It wraps the app's `Application` class via `com.pairip.application.Application`.

### Detection

```bash
# Check for Pairip presence
unzip -p app.apk classes*.dex | strings -a | grep -c "pairip"
# > 0 = Pairip present

# Check for libpairipcore.so
unzip -l app.apk | grep -i "pairipcore"
```

### How it works

```
Application.attachBaseContext()
  → VMRunner.setContext(Context)        # Native VM init
  → SignatureCheck.verifyIntegrity(Context)  # APK signature check
  → VMRunner.invoke(id, args)          # Encrypted string decryption
      → libpairipcore.so               # Native VM execution
```

The `VMRunner.invoke(String, Object[])` method is the central API — it's called from hundreds of places across the app (ads SDKs, analytics, Firebase, WorkManager) to decrypt strings at runtime. These strings are encrypted in the DEX and can only be decrypted by the native VM.

### Bypass strategies

#### Strategy A: Minimal bypass (smali only)

If the app only has Pairip for license verification (no vault dependencies):

1. Neutralize `SignatureCheck.verifyIntegrity(Context)V` → `return-void`
2. Neutralize `StartupLauncher.launch()V` → `return-void`

**⚠️ Do NOT neutralize `VMRunner.invoke` or `VMRunner.setContext`** — the entire app depends on them for string decryption.

#### Strategy B: Full bypass (when vault strings are compromised)

If the APK is already modded and vault strings are empty/corrupted, use the multi-layer approach:

| Layer | Action | Purpose |
|---|---|---|
| 1 | Replace `Application` class in AndroidManifest | Remove Pairip's Application wrapper entirely |
| 2 | Patch `VMRunner.invoke` to return null | Prevent crash when vault strings are empty |
| 3 | Patch protobuf field lookup for empty names | `getDeclaredField("")` → return first field |
| 4 | Create `SafeExceptionHandler` | Catch NPE from empty vault strings on background threads |
| 5 | Wrap crypto init in try-catch | `TinkConfig.register()` fails with empty algorithm names |
| 6 | Stub `FlutterSecureStorage` → `success(null)` | EncryptedSharedPreferences fails with empty cipher |
| 7 | Patch `getSystemService()` vault strings | Restore "connectivity", "wifi", "location", etc. |
| 8 | Auto-detect Kotlin property vault strings | Restore property names from getter signatures |

#### Strategy C: Morphe patcher

The Morphe ecosystem has dedicated patches:

```kotlin
// hoo-dles/morphe-patches — DisableLicenseCheckPatch.kt
ProcessLicenseResponseFingerprint.method.addInstruction(0, "const/4 p1, 0x0")
ValidateLicenseResponseFingerprint.method.returnEarly()
```

### Automated tools

| Tool | Language | Coverage |
|---|---|---|
| `TechnoIndian/RKPairip` | Python | Full automated pipeline (decompile → patch → rebuild → sign) |
| `carpedm20/android-hack/patch_pairip.sh` | Bash | Shell script for quick patching |
| `hoo-dles/morphe-patches` | Kotlin | Morphe patch for license check bypass |
| `rushiranpise/morphe-patches/PairIp.kt` | Kotlin | Shared Pairip utilities |

**Sources:**
- `Rt39/Merc_translation_andriod` — `PAIRIP_BYPASS_GUIDE.md` (comprehensive guide)
- `TechnoIndian/RKPairip` — Automated Python bypass tool
- `hoo-dles/morphe-patches` — `DisableLicenseCheckPatch.kt`
- `carpedm20/android-hack` — `patch_pairip.sh`

---

## Dex2C / VM shell dead-ends

Some modders use Dex2C compilers or VM shells that translate DEX bytecode to native ARM64 code inside a `.so` library. The original app logic (including dialogs, license checks, and app initialization) runs inside a virtual machine in native code — **completely invisible to static smali analysis**.

### Modder profiles

| Modder | Signature | Technique | Static bypass possible? |
|---|---|---|---|
| **zhou45** | `libstub.so` + `assets/protected_by_np` | YJ-Dex2C VM shell (`yjaq.xyz`) | ❌ No — DEX encrypted in `assets/classes0.jar` |
| **yhf / liteapks** | `ī/íì/`, `īi/ïi/`, `p000/p001/` | Java dialog injection + `libstub.so` for native dialogs | ⚠️ Partial — Java dialogs yes, native dialogs no |
| **辰夕** | `libcxapkmod.so` + `assets/cxapkDex/*.Epic` | Native code injection | ❌ No |
| **幻幻喵** | `libmiaomiaohuan.so` + `miaomiaohuan0` prefix | Custom native hooking | ❌ No |
| **黯笙** | `bin.mt.signature.KillerApplication` | Signature killer + certificate spoof | ✅ Yes (Java only) |
| **Kunkka** | `LSPAppComponentFactoryStub` + `assets/lspatch/config.json` | LSPatch Xposed module injection | ✅ Yes (patchable via LSPosed) |

### Detection

```bash
# Dex2C/VM shell markers
unzip -p app.apk classes*.dex | strings -a | grep -iE "YJ-Dex2C|yjaq\.xyz|libstub|libcxapkmod|protected_by_np"

# Check for encrypted DEX
unzip -l app.apk | grep "classes0.jar\|classes\.jar"
```

### Decision tree

```
¿Tiene libstub.so + assets/classes0.jar?
  → SÍ: Dead end. Hack the original APK.
  → NO: ¿Tiene ī/íì + métodos nativos (up.process, bi.b)?
         → SÍ: Intenta neutralizar los <clinit> que llaman EntryPoint.stub
         → Si se cuelga: Dead end parcial. El nativo mezcla diálogo + init.
         → Si funciona: ✅
  → NO: ¿Tiene solo ī/íì con métodos Java (iaw.w, iab.b)?
         → SÍ: Neutralizar normalmente ✅
  → NO: ¿No tiene ī/íì ni libstub?
         → SÍ: Es el original o un mod limpio. Aplicar Step 5 normalmente ✅
```

**Source:** `we1005/MT-31b-LLM-TUI-Reverse-Agent` — Modder profiling and dead-end classification

---

## Frida Gadget — embedding Frida in redistributable APKs

When native code cannot be patched with smali (e.g. Dex2C/VM shells like `libstub.so`), Frida can hook the dialog at runtime. For a redistributable APK without root, use **Frida Gadget** embedded inside the APK.

### Proven technique: Frida-server (rooted device)

This is the quickest way to confirm the hook works before attempting Gadget embedding:

```bash
# Start frida-server on rooted device
adb shell "su -c '/data/local/tmp/frida-server -D &'"

# Hook the app at startup
frida -U -f com.example.app -l hook.js
```

**Hook script** (suppresses liteapks/yhf dialogs by filtering `Dialog.show()` stack traces):
```javascript
Java.perform(function() {
    var Dialog = Java.use("android.app.Dialog");
    Dialog.show.implementation = function() {
        var Exception = Java.use("java.lang.Exception");
        var e = Exception.$new();
        var stack = e.getStackTrace();
        for (var i = 0; i < Math.min(stack.length, 15); i++) {
            var frame = stack[i].toString();
            if (frame.indexOf("\u012B") >= 0 || frame.indexOf("iaw") >= 0 || 
                frame.indexOf("iab") >= 0 || frame.indexOf("p001") >= 0 ||
                frame.indexOf("p002") >= 0 || frame.indexOf("EntryPoint") >= 0) {
                return; // Suppress the dialog
            }
        }
        return this.show(); // Allow legitimate dialogs
    };
});
```

This chain was confirmed: `MainActivity.onCreate → bi.b(native) → AlertDialog.show()` — suppressed at `Dialog.show()` level.

**Injection point for loadLibrary:** Inject `System.loadLibrary("frida-gadget")` into the Application class's `<clinit>()` — NOT `attachBaseContext()` (which may not be called if overridden by proxies). For this specific APK, the correct class was `uk.lgl.MultiDexApplication` in `classes11.dex`.

### Gadget embedding: lessons learned (Frida 17.15.3)

**What works:**
- Gadget .so in `lib/arm64-v8a/libfrida-gadget.so` ✅
- Config in `assets/frida-gadget.config` → gadget loads in listen mode ✅
- Connecting externally: `frida -H 127.0.0.1:27042 -p <pid> -l hook.js` ✅

**What fails:**
- Config in `lib/arm64-v8a/libfrida-gadget.config.so` → gadget doesn't load at all ❌
- `"type": "script"` with external file path → silently ignored, falls back to listen ❌
- `"type": "script"` with inline `"script"` field → also ignored ❌
- Script at `/sdcard/`, `/data/local/tmp/`, or app private dir → all ignored ❌

**Root cause:** Frida 17.x appears to have a regression or undocumented change in how the gadget handles script mode on Android. The config is read but the script execution path is silently skipped. This needs further investigation with a different Frida version or the `frida-java-bridge` npm package (required since Frida 17 removed the built-in Java bridge).

**Practical recommendation:** Prioritize finding a mod without `libstub.so` (smali-patchable). Frida Gadget embedding for Frida 17.x needs more research.

**Sources:**
- HackTricks Frida tutorial — config location reference
- Frida 17.15.3 release notes — Java bridge removed from GumJS
- Tested on PixeLeap v1.1.3.0 (ViP): 2 successful frida-server runs, 10 failed Gadget embedding attempts

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
| Liteapks markers not found but dialog appears | Modder changed package names (`p000/p001/` instead of `ī/íì/`) | Use behavioral detection: `grep -rn "Typeface.createFromAsset" jadx_out/ --include="*.java"` |
| Modder injection found but `strings` shows nothing | Encrypted/obfuscated strings in DEX | Decompile with jadx+baksmali, search smali by behavior |
| YouTube shows `adcontext=` in QOE pings | Mod didn't fully disable ad system | Check account/premium smali patches are applied |
| `ClassNotFoundException: Executor$CppProxy` | Python `zipfile` corrupted ZIP structure | Use `zip -0` (STORE) or apkzlib for repackaging |
| Hex-edited DEX causes crash but smali'd DEX works | Raw DEX has invalid internal checksum (Adler32/SHA1) | Always use baksmali→smali, never hex-edit DEX directly |
| Liteapks dialog still appears after URL replacement | Dialog class (`com/zx/cmz/Strings` + `LB`) fetches content from multiple sources | Find ALL references: URLs, promotional strings, dialog trigger in MainActivity |
| App forces re-login after premium patch | Fake UID causes server 401 → `ReLoginDialogActivity` | Suppress `sendReLoginBroadcast` and `launchReLoginDialog` (see Step 5e) |
| "Unauthenticated" toast spam | Premium toggle syncs with server → 401 | Suppress auth-error toasts only (see Step 5e) |
| `INSTALL_FAILED` on Android 16+ in BR/ID/SG/TH | `com.google.android.verifier` blocks unsigned APKs | Patch verifier or push as system app (see Android 16+ section) |
| `resources.arsc` compressed → install fails on Android 11+ | Python `ZIP_DEFLATED` on `resources.arsc` | Use `ZIP_STORED` for `resources.arsc` and `.so` (see Step 7) |

---

## References / Sources

### Morphe patcher ecosystem
- [MorpheApp/morphe-manager](https://github.com/MorpheApp/morphe-manager) (★6341) — Morphe app patcher engine
- [rushiranpise/morphe-patches](https://github.com/rushiranpise/morphe-patches) (★173) — 50+ app patches (AdGuard, CamScanner, AccuWeather, etc.)
- [arandomhooman/hoomans-morphe-patches](https://github.com/arandomhooman/hoomans-morphe-patches) (★92) — Additional patches (BlockerHero)
- [Paresh-Maheshwari/morphe-ai](https://github.com/Paresh-Maheshwari/morphe-ai) (★114) — AI-powered APK patching pipeline

### Android reverse engineering courses
- [ZJ595/AndroidReverse](https://github.com/ZJ595/AndroidReverse) (★2222) — 《安卓逆向这档事》 — Lesson 6: signature verification bypass, PMS Hook, IO redirection, triangle verification
- [Evil0ctal/AndroidReverse101](https://github.com/Evil0ctal/AndroidReverse101) — Indonesian Android RE course (smali basics)

### Modding tool collections
- [jbro129/android-modding](https://github.com/jbro129/android-modding) (★739) — Curated list of Android modding tools, templates, and tutorials
- [gmh5225/awesome-game-security](https://github.com/gmh5225/awesome-game-security) (★3159) — Game security resources, includes android-modding archive
- [alphaSeclab/android-security](https://github.com/alphaSeclab/android-security) (★354) — Android security resources

### Repackaging tools
- [test1ng-guy/android-sandbox-explorer](https://github.com/test1ng-guy/android-sandbox-explorer) — `repack.py`: split APK handling, zipalign, resources.arsc uncompressed, mixed compression

### Runtime bypass frameworks
- [asLody/VirtualApp](https://github.com/asLody/VirtualApp) — Virtual engine for Android (IO redirection)
- [virjarRatel/ratel-core](https://github.com/virjarRatel/ratel-core) — RAT framework with IO redirection
- [fourbrother/HookPmsSignature](https://github.com/fourbrother/HookPmsSignature) — PMS signature hook

### Reverse engineering tools
- [Konloch/bytecode-viewer](https://github.com/Konloch/bytecode-viewer) (★15565) — Java/Android APK RE suite
- [vaibhavpandeyvpz/apkstudio](https://github.com/vaibhavpandeyvpz/apkstudio) (★4283) — Cross-platform APK RE IDE
- [APKLab/APKLab](https://github.com/APKLab/APKLab) (★3911) — Android RE workbench for VS Code
- [JesusFreke/smali](https://github.com/JesusFreke/smali) — baksmali/smali assembler/disassembler
- [iBotPeaches/Apktool](https://github.com/iBotPeaches/Apktool) — APK decode/rebuild tool
\n+---

Actualización y ampliación — 2026-07-18

Este skill ha sido ampliado para cubrir escenarios modernos (2025–2026), añadir automatización práctica y reforzar verificaciones de empaquetado y firma. Cambios clave:

- Nuevos scripts de automatización en .opencode/skills/apk-modding/scripts/:
  - patch_shared_prefs_defaults.py — cambia valores por defecto (premium/noads) de manera masiva y segura en smali
  - neutralize_yhf_dialogs.py — neutraliza métodos estáticos de diálogos de modders (yhf/liteapks y variantes) sin borrar clases
  - ziprepack.py — reempaqueta APK con reglas de compresión correctas (STORE para .so/.arsc/DEX) y preserva META-INF/services
  - strip_sign_and_sign.py — limpia firmas antiguas, alinea y firma con keystore de depuración si es necesario

- Firma APK v1/v2/v3/v4: verificación y recomendaciones actualizadas
  - Verifique siempre antes y después de firmar: apksigner verify --verbose --print-certs app.apk
  - Habilite v2 y v3; v4 es opcional (streaming). apksigner gestiona automáticamente compatibilidad por SDK

- Split APKs, APKS/APKM y bundles (AAB): flujo actualizado
  - Cómo generar universal APK con bundletool y extraer splits para parchear base.apk

- Network Security Config (Android 7+): receta para permitir CAs de usuario/mitm en pruebas sin Frida

- Detección 2025–2026 de patrones de modders
  - p002i/p003i, q6/c, w6/b, d6/a y rutas renombradas; búsqueda basada en comportamiento y call-sites

- Checklist de empaquetado reforzado (Android 14–16)
  - .so y resources.arsc sin compresión (STORE), DEX sin compresión cuando se reescriben con zipfile
  - zipalign -p para alinear .so a páginas (Android 15+ exige correcta alineación para mmap eficiente)

Referencias rápidas a los nuevos archivos:

- .opencode/skills/apk-modding/scripts/patch_shared_prefs_defaults.py
- .opencode/skills/apk-modding/scripts/neutralize_yhf_dialogs.py
- .opencode/skills/apk-modding/scripts/ziprepack.py
- .opencode/skills/apk-modding/scripts/strip_sign_and_sign.py

Uso responsable: Igual que el skill original, todo lo descrito se aplica exclusivamente a aplicaciones propias, investigación autorizada o entornos donde el propietario ha otorgado permiso explícito.

Sección nueva: Verificación y firma (v1/v2/v3/v4)

1) Comprobar firmas actuales

   apksigner verify --verbose --print-certs app.apk

   - Si ve errores de JAR signature (v1) tras reconstrucción, es normal si ha eliminado MANIFEST.MF. Android 7+ usa v2+/v3.

2) Recomendación de firmado

   - Use apksigner con v2 y v3 activados; v1 opcional para compatibilidad heredada (Android 6-).
   - Ejemplo (keystore de depuración):

     apksigner sign \
       --ks "$HOME/.android/debug.keystore" --ks-pass pass:android \
       --ks-key-alias androiddebugkey \
       --v1-signing-enabled true --v2-signing-enabled true --v3-signing-enabled true \
       --out hacked_signed.apk hacked_aligned.apk

3) Verificar post-firma

   apksigner verify --verbose --print-certs hacked_signed.apk

Sección nueva: Split APKs, APKS/APKM y bundles

- Dispositivos modernos suelen instalar splits (base + split_config.*). Parchee lógicamente en base.apk (código/DEX) y firme todos los splits con la misma clave.
- Si dispone de .apks (bundletool), extraiga universal APK para análisis:

  java -jar bundletool.jar extract-apks \
    --apks app.apks \
    --device-spec device.json \
    --output-dir extracted/

- Para generar .apks a partir de .aab (propio y autorizado):

  java -jar bundletool.jar build-apks \
    --bundle app.aab \
    --output app.apks \
    --ks $HOME/.android/debug.keystore \
    --ks-pass pass:android \
    --ks-key-alias androiddebugkey \
    --connected-device

Sección nueva: Detección de patrones de modders (2025–2026)

- Además de ī/íì y īi/ïi, observe variantes: p000/p001, p002i/p003i, q6/c, w6/b, d6/a, a/b/pookie. Las llamadas suelen estar en classes2.dex (Activities) aunque la inyección viva en classes3+. Busque SIEMPRE call-sites en TODOS los DEX.
- Grep efectivo (ripgrep):

  rg -n "invoke-.*(ī/íì|īi/ïi|p000/p001|p002i/p003i|q6/c|w6/b|d6/a|a/b/pookie)" dex*_out --glob "**/*.smali" \
    | rg -v "^dex\d*_out/(ī|īi|p000|p002i|q6|w6|d6|a)/"

Checklist reforzado de empaquetado (Android 14–16)

- .so sin compresión (STORE) y página-alineados con zipalign -p 4
- resources.arsc sin compresión (STORE)
- DEX sin compresión (STORE) cuando usa Python zipfile para reempaquetar; con zip/apktool puede DEFLATE, pero mantenga coherencia
- Mantener META-INF/services/; eliminar solo .SF/.RSA/.DSA/.EC y MANIFEST.MF
- Verificar con apksigner verify y aapt dump badging

Automatización: scripts incluidos

- Consulte .opencode/skills/apk-modding/scripts/README.md para uso y ejemplos. Todos los scripts trabajan sobre salidas de baksmali (dexN_out/) y generan backups automáticos.

Limitaciones y decisiones

- Si detecta libstub.so + assets/classes0.jar (Dex2C/VM shell), es vía muerta estática: priorice versiones originales o enfoque dinámico (Frida/LSPosed) con autorización explícita.
- Si hay comprobaciones nativas de integridad DEX en .so (p.ej., libgoogle3.so), la vía robusta es parche nativo (Ghidra/radare2) o runtime hook confirmado con Frida antes de redistribuir.

## Estrategias de parcheo avanzadas (2025–2026)

### Estrategia A: Parcheo de defaults en SharedPreferences

El patrón más común en apps de pago simple:
```java
this.isPremium = prefs.getBoolean("premium", false);
```

En smali, cambiar `const/4 v2, 0x0` → `0x1` modifica el valor por defecto. **Limitación**: si la app re-sincroniza desde Play Billing o servidor, el valor almacenado sobreescribe el default.

**Cuándo usar:** Apps sin Billing, apps con licencia local, apps que solo leen SharedPreferences.
**Cuándo NO usar:** Apps con Play Billing, apps con licencia server-side. Usar Estrategia C.

### Estrategia B: Forzar retorno de método

Reemplazar todo el cuerpo de un método de comprobación:
```smali
.method public isPremium()Z
    .registers 1
    const/4 v0, 0x1
    return v0
.end method
```

**Ventaja:** Inmune a re-sync de SharedPreferences.
**Desventaja:** Si hay múltiples métodos de comprobación (5+ en AdGuard), hay que parchear todos.

### Estrategia C: Hook de getter por nombre de clave

Interceptar `getBoolean(key, default)` al inicio del método y retornar `true` si la clave coincide:
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

**Ventaja:** Sobrevive re-sync de Play Billing porque intercepta la **lectura**, no el valor almacenado.
**Fuente:** `arandomhooman/hoomans-morphe-patches` — BlockerHero

### Estrategia D: Supresión de diálogos de re-login y toasts de auth

Cuando se fuerza premium sin login válido, la app puede:
1. Sincronizar con servidor → 401 → lanzar `ReLoginDialogActivity`
2. Mostrar toasts "Unauthenticated" repetidamente

**Suprimir broadcast de re-login:**
```smali
.method ...sendReLoginBroadcast()V
    .registers 0
    return-void
.end method
```

**Suprimir lanzamiento de ReLoginDialogActivity:**
```smali
.method ...launchReLoginDialog()V
    .registers 0
    return-void
.end method
```

**Suprimir solo toasts de auth (dejar otros toasts funcionando):**
```smali
# Al inicio del helper de toast:
if-eqz p1, :show
const-string v0, "uthenticat"
invoke-virtual {p1, v0}, Ljava/lang/String;->contains(Ljava/lang/CharSequence;)Z
move-result v0
if-eqz v0, :show
return-void
:show
# ... código original de toast
```

**Fuentes:**
- `rushiranpise/morphe-patches` — CamScanner YearlyUnlockPatch
- `arandomhooman/hoomans-morphe-patches` — BlockerHero EnablePremiumPatch

### Estrategia E: Parcheo de límites numéricos

Apps con límites configurables (favoritos, exportaciones, dispositivos):
```java
int maxFavorites = prefs.getInt("max_favorites", 5);
```

En smali:
```smali
const-string v1, "max_favorites"
const/16 v2, 0x5              # ← cambiar a 0x63 (99) o 0x3E7 (999)
invoke-interface {v0, v1, v2}, ...getInt...
```

Para límites grandes, usar `const v2, 0x7FFFFFFF` (Integer.MAX_VALUE) o `const-wide/32 v2, 0x7FFFFFFF`.

### Estrategia F: Parcheo de trial/periodo de prueba

Apps con trial por timestamp:
```java
long trialEnd = prefs.getLong("trial_end", 0);
if (System.currentTimeMillis() > trialEnd) { /* expired */ }
```

Opciones:
1. **Extender trial:** cambiar el default a `Long.MAX_VALUE` (0x7FFFFFFFFFFFFFFF)
2. **Desactivar comprobación:** reemplazar el método `isTrialExpired()Z` → `return false`
3. **Hook de comparación:** interceptar `System.currentTimeMillis()` y retornar 0 (siempre dentro de trial)

---

## Perfiles de modders — Catálogo ampliado (2025–2026)

### Modders Java-patchables (smali)

| Modder | Firma | Paquetes inyectados | Técnica | ¿Parcheable estático? |
|---|---|---|---|---|
| **yhf / liteapks** | `ī/íì/`, `īi/ïi/` | `bi`, `wl`, `wi`, `bl`, `iaw`, `iab`, `pk` | Diálogos Java + a veces `libstub.so` | ⚠️ Parcial (Java sí, nativo no) |
| **yhf (2025+)** | `p000/p001/`, `p002i/p003i/` | Renombrado de `ī/íì/` | Mismo, paquetes renombrados | ⚠️ Parcial |
| **黯笙** | `bin.mt.signature.KillerApplication` | Signature killer + cert spoof | Java puro | ✅ Sí |
| **Kunkka** | `LSPAppComponentFactoryStub` + `assets/lspatch/config.json` | LSPatch Xposed injection | Xposed module | ✅ Sí (via LSPosed) |

### Modders con VM shell / Dex2C (vía muerta estática)

| Modder | Firma | Archivos clave | Técnica | ¿Parcheable estático? |
|---|---|---|---|---|
| **zhou45** | `libstub.so` + `assets/protected_by_np` | `assets/classes0.jar` | YJ-Dex2C VM shell (`yjaq.xyz`) | ❌ No |
| **辰夕** | `libcxapkmod.so` + `assets/cxapkDex/*.Epic` | Native code injection | VM nativa | ❌ No |
| **幻幻喵** | `libmiaomiaohuan.so` + prefijo `miaomiaohuan0` | Custom native hooking | Hook nativo | ❌ No |

### Detección rápida de perfil

```bash
# 1. ¿Tiene libstub.so? → zhou45 (Dex2C, vía muerta)
unzip -l app.apk | grep -i "libstub\|protected_by_np"

# 2. ¿Tiene ī/íì o p000/p001? → yhf/liteapks
unzip -p app.apk classes*.dex | strings -a | grep -c "ī/íì\|p000/p001"

# 3. ¿Tiene bin.mt.signature? → 黯笙 (Java, parcheable)
unzip -p app.apk classes*.dex | strings -a | grep -c "bin.mt.signature"

# 4. ¿Tiene LSPatch config? → Kunkka (Xposed)
unzip -l app.apk | grep -i "lspatch/config.json"

# 5. ¿Tiene libcxapkmod? → 辰夕 (VM nativa)
unzip -l app.apk | grep -i "libcxapkmod\|cxapkDex"

# 6. ¿Tiene libmiaomiaohuan? → 幻幻喵
unzip -l app.apk | grep -i "miaomiaohuan"
```

### Árbol de decisión

```
¿Tiene libstub.so + assets/classes0.jar?
  → SÍ: Dead end estático. Hackear el APK original.
  → NO: ¿Tiene ī/íì + métodos nativos (up.process, bi.b)?
         → SÍ: Intentar neutralizar <clinit> que llaman EntryPoint.stub
         → Si se cuelga: Dead end parcial. El nativo mezcla diálogo + init.
         → Si funciona: ✅
  → NO: ¿Tiene solo ī/íì con métodos Java (iaw.w, iab.b)?
         → SÍ: Neutralizar normalmente ✅
  → NO: ¿No tiene ī/íì ni libstub?
         → SÍ: Es el original o un mod limpio. Aplicar Step 5 normalmente ✅
```

---

## Plantilla de case study

Para documentar nuevos casos, usar esta plantilla:

```markdown
# Case: [Nombre App] [Versión]

## Metadata
- **App:** com.example.app
- **Versión:** 1.2.3
- **Fuente APK:** APKMirror / APKPure / adb pull
- **Fecha:** 2026-XX-XX
- **Objetivo:** Desbloquear premium / eliminar ads / quitar diálogo modder

## Inspección inicial
- DEX files: N
- Native libs: Sí/No (listar .so)
- Modder detectado: yhf / ninguno / otro
- Protección: SharedPreferences / Play Billing / native check

## Análisis
- Claves SharedPreferences encontradas: premium, noads, max_favorites
- Métodos de comprobación: isPremium()Z, isPro()Z, checkLicense()V
- DEX con inyección: classes3.dex
- DEX con call-sites: classes2.dex (MainActivity)

## Parches aplicados
| Archivo | Método | Cambio | Estrategia |
|---|---|---|---|
| classes2.dex | isPremium()Z | return true | B |
| classes2.dex | getBoolean("premium") | default 0x0→0x1 | A |

## Resultado
- ✅ Premium desbloqueado
- ✅ Sin diálogos de modder
- ✅ Sin crashes
- ⚠️ Nota: re-sync de Billing puede revertir (usar Estrategia C si ocurre)

## Lección clave
[Una frase con el aprendizaje principal]
```

---

## Morphe patcher — Alternativa programática al smali manual

El smali manual es frágil: los offsets cambian entre versiones y los parches deben redimensionarse para cada update. El ecosistema **Morphe patcher** provee un DSL en Kotlin que automatiza el parcheo con fingerprints y matching de métodos version-agnostic.

### Repositorios

| Repo | Stars | Descripción |
|---|---|---|
| `MorpheApp/morphe-manager` | ★6341 | Morphe app patcher para Android (el engine) |
| `rushiranpise/morphe-patches` | ★173 | 50+ app patches mantenidos (AdGuard, CamScanner, AccuWeather) |
| `arandomhooman/hoomans-morphe-patches` | ★92 | Patches adicionales (BlockerHero) |
| `Paresh-Maheshwari/morphe-ai` | ★114 | Pipeline multi-agente con IA para análisis y patching |

### Cuándo usar Morphe vs smali manual

| | Smali manual | Morphe patcher |
|---|---|---|
| Parche one-off | ✅ Más rápido | Overkill |
| Mantener patches entre versiones | ❌ Frágil | ✅ Fingerprints adaptan |
| Compartir con comunidad | ❌ Difícil | ✅ Versionable, compartible |
| Apps con muchos targets | ❌ Tedioso | ✅ Escala bien |
| Aprender cómo funcionan los patches | ✅ Transparente | ❌ Abstracto |

---

## Bypass de firma en runtime (PMS Hook, IO redirection)

Cuando una app hace verificación de firma en runtime (no en nativo), hay dos técnicas runtime que evitan parchar la app. Requieren root + Xposed/LSPosed o framework de virtualización.

### PMS Hook (PM Proxy)

Hookear `ActivityThread.sPackageManager` y `ApplicationPackageManager.mPM` via Java dynamic proxy para retornar una firma spoofeada cuando la app llama `getPackageInfo(GET_SIGNATURES)`.

**Fuente:** `ZJ595/AndroidReverse` (★2222) — Lesson 6

### IO redirection

Redirigir reads de archivo para que cuando la app abra su propio APK para verificar la firma, lea el **APK original no modificado** en lugar del parcheado.

Tools:
- **VirtualApp** (`asLody/VirtualApp`) — virtualización que intercepta file I/O
- **Ratel** (`virjarRatel/ratel-core`) — RAT framework con IO redirection
- **SVC TraceHook** — ptrace + seccomp para redirección a nivel syscall

### Verificación triangular (三角校验)

Patrón más complejo que verificación circular simple:
```
libnative.so ──checks──> classes.dex
classes.dex  ──checks──> dex cargado dinámicamente (extraído en runtime, borrado tras check)
dynamic dex  ──checks──> libnative.so
```
Cada componente verifica al siguiente en triángulo. Parchear uno rompe la cadena. Requiere parchear los tres simultáneamente o usar hooks runtime.

---

## Android 16+ Developer Verifier bypass

Desde septiembre 2026, `com.google.android.verifier` (servicio del sistema pre-instalado) bloquea instalación de APKs en dispositivos Android 16+ certificados en BR/ID/SG/TH cuando el certificado de firma no está en el registro de desarrolladores de Google. La política se controla via phenotype flags desde servidores de Google.

**Impacto:** Sideloading de APKs parcheados en Android 16+ certificado en regiones afectadas puede bloquearse incluso con unknown sources habilitado.

**Bypass layers (DEX patching del verifier app):**

| Layer | Método | Patch |
|---|---|---|
| 1 | `onVerificationRequired` / `onVerificationRetry` | Llamar `reportVerificationBypassed(1)` inmediatamente |
| 2 | Platform policy flag (45681539) | Retornar `Long(0)` = NONE (no blocking) |
| 3 | Forced backport flag (45749715) | Retornar `Boolean.TRUE` (short-circuit path) |

**Requisitos:**
- APK del verifier parcheado debe instalarse como **system app** (reemplazando el original) via Magisk module o ADB con root
- El verifier tiene privilegio `DEVELOPER_VERIFICATION_AGENT`
- Instalaciones via ADB están exentas de verificación

**Fuente:** `rushiranpise/morphe-patches` — `AndroidVerifierBypassPatch.kt`

---

## PairipCore license bypass

PairipCore (`libpairipcore.so`) es una librería de verificación de licencia de Google Play que encripta strings de la app en un vault y valida la firma del APK contra Play Store. Envuelve la clase `Application` de la app via `com.pairip.application.Application`.

### Detección

```bash
unzip -p app.apk classes*.dex | strings -a | grep -c "pairip"
unzip -l app.apk | grep -i "pairipcore"
```

### Cómo funciona

```
Application.attachBaseContext()
  → VMRunner.setContext(Context)        # Native VM init
  → SignatureCheck.verifyIntegrity(Context)  # APK signature check
  → VMRunner.invoke(id, args)          # Encrypted string decryption
      → libpairipcore.so               # Native VM execution
```

`VMRunner.invoke(String, Object[])` es la API central — se llama desde cientos de sitios en la app (ads SDKs, analytics, Firebase, WorkManager) para desencriptar strings en runtime. Estos strings están encriptados en el DEX y solo pueden desencriptarse via la VM nativa.

### Estrategias de bypass

#### Estrategia A: Bypass mínimo (solo smali)

Si la app solo tiene Pairip para verificación de licencia (sin dependencias del vault):

1. Neutralizar `SignatureCheck.verifyIntegrity(Context)V` → `return-void`
2. Neutralizar `StartupLauncher.launch()V` → `return-void`

**⚠️ NO neutralizar `VMRunner.invoke` o `VMRunner.setContext`** — toda la app depende de ellos para desencriptar strings.

#### Estrategia B: Bypass completo (cuando vault strings están comprometidos)

Si el APK ya está moddeado y los vault strings están vacíos/corruptos, usar enfoque multi-capa:

| Layer | Acción | Propósito |
|---|---|---|
| 1 | Reemplazar clase `Application` en AndroidManifest | Remover wrapper de Pairip |
| 2 | Patch `VMRunner.invoke` → return null | Prevenir crash con vault strings vacíos |
| 3 | Patch protobuf field lookup para nombres vacíos | `getDeclaredField("")` → retornar primer field |
| 4 | Crear `SafeExceptionHandler` | Capturar NPE de vault strings vacíos en background threads |
| 5 | Envolver crypto init en try-catch | `TinkConfig.register()` falla con nombres de algoritmo vacíos |
| 6 | Stub `FlutterSecureStorage` → `success(null)` | EncryptedSharedPreferences falla con cipher vacío |
| 7 | Patch `getSystemService()` vault strings | Restaurar "connectivity", "wifi", "location" |
| 8 | Auto-detectar Kotlin property vault strings | Restaurar nombres de propiedades desde getter signatures |

#### Estrategia C: Morphe patcher

```kotlin
// hoo-dles/morphe-patches — DisableLicenseCheckPatch.kt
ProcessLicenseResponseFingerprint.method.addInstruction(0, "const/4 p1, 0x0")
ValidateLicenseResponseFingerprint.method.returnEarly()
```

### Herramientas automatizadas

| Tool | Lenguaje | Cobertura |
|---|---|---|
| `TechnoIndian/RKPairip` | Python | Pipeline completo automatizado |
| `carpedm20/android-hack/patch_pairip.sh` | Bash | Script shell para patching rápido |
| `hoo-dles/morphe-patches` | Kotlin | Morphe patch para license check |
| `rushiranpise/morphe-patches/PairIp.kt` | Kotlin | Utilidades Pairip compartidas |

**Fuentes:**
- `Rt39/Merc_translation_andriod` — `PAIRIP_BYPASS_GUIDE.md`
- `TechnoIndian/RKPairip` — Automated Python bypass tool

---

## Frida Gadget — Embebiendo Frida en APKs redistribuibles

Cuando el código nativo no puede parchearse con smali (ej. Dex2C/VM shells como `libstub.so`), Frida puede hookear el diálogo en runtime. Para un APK redistribuible sin root, usar **Frida Gadget** embebido dentro del APK.

### Técnica probada: Frida-server (dispositivo con root)

```bash
# Iniciar frida-server en dispositivo con root
adb shell "su -c '/data/local/tmp/frida-server -D &'"

# Hookear la app al inicio
frida -U -f com.example.app -l hook.js
```

**Hook script** (suprime diálogos liteapks/yhf filtrando stack traces de `Dialog.show()`):
```javascript
Java.perform(function() {
    var Dialog = Java.use("android.app.Dialog");
    Dialog.show.implementation = function() {
        var Exception = Java.use("java.lang.Exception");
        var e = Exception.$new();
        var stack = e.getStackTrace();
        for (var i = 0; i < Math.min(stack.length, 15); i++) {
            var frame = stack[i].toString();
            if (frame.indexOf("\u012B") >= 0 || frame.indexOf("iaw") >= 0 || 
                frame.indexOf("iab") >= 0 || frame.indexOf("p001") >= 0 ||
                frame.indexOf("p002") >= 0 || frame.indexOf("EntryPoint") >= 0) {
                return; // Suprimir el diálogo
            }
        }
        return this.show(); // Permitir diálogos legítimos
    };
});
```

**Punto de inyección para loadLibrary:** Inyectar `System.loadLibrary("frida-gadget")` en el `<clinit>()` de la clase Application — NO en `attachBaseContext()` (que puede no llamarse si hay proxies).

### Gadget embedding: lecciones aprendidas (Frida 17.15.3)

**Qué funciona:**
- Gadget .so en `lib/arm64-v8a/libfrida-gadget.so` ✅
- Config en `assets/frida-gadget.config` → gadget carga en modo listen ✅
- Conexión externa: `frida -H 127.0.0.1:27042 -p <pid> -l hook.js` ✅

**Qué falla:**
- Config en `lib/arm64-v8a/libfrida-gadget.config.so` → gadget no carga ❌
- `"type": "script"` con archivo externo → ignorado, fallback a listen ❌
- Script en `/sdcard/`, `/data/local/tmp/`, o dir privado de app → todos ignorados ❌

**Recomendación práctica:** Priorizar encontrar un mod sin `libstub.so` (parcheable en smali). Frida Gadget embedding para Frida 17.x necesita más investigación.

---

## Ecosistema de herramientas de modding (curado de GitHub y foros rusos/chinos)

### Herramientas de parcheo de APK

| Herramienta | Repo | ★ | Lenguaje | Uso |
|---|---|---|---|---|
| **ApkForge** | `All1eexx/ApkForge` | — | Python | Pipeline completo: decompile → patch Java/Kotlin/C++ → sign. Config-driven via JSON. |
| **UltimatePatcher** | `Schwartzblat/UltimatePatcher` | ★11 | Java/Python | Patcher genérico que trabaja con Java en lugar de smali. Compila patch Java → extrae smali → inyecta en APK original. |
| **MoovitPatcher** | `Schwartzblat/MoovitPatcher` | ★16 | Python | Patcher específico para Moovit: desbloquea premium y elimina ads. |
| **SPECTRE** | `alphakremlin/spectre-apk-patcher` | — | Python | Smali Premium & Entitlement Cracker Tool para RE. |
| **NP-Manager** | `githubXiaowangzi/NP-Manager` | ★1704 | — | Herramienta china: control flow obfuscation, Dex2C, Res obfuscation, Dex/jar/smali conversion, APK/dex/jar obfuscation y string encryption. |
| **MT Manager** | (app Android) | — | — | App Android con editor de smali, DEX viewer, y ApkSignatureKill integrado. Muy popular en foros rusos/chinos. |
| **ApkEditor** | `PatrickAlex2019/ApkEditor` | ★360 | Java | APP reverse compilation, APK localization, APK cracking, APK signature. |
| **APKToolGUI** | `AndnixSH/APKToolGUI` | — | — | GUI para apktool, signapk, zipalign y baksmali. |
| **ApkEasyTool** | (XDA) | — | — | GUI ligera para ApkTool con adb-support. |
| **apk.sh** | `ax/apk.sh` | ★3809 | Shell | Script que automatiza RE de Android: decompile, patch, repack, sign, install. |
| **DexPatcher** | `DexPatcher/dexpatcher-tool` | ★445 | Java | Patcher de bytecode Dalvik. Permite parchear DEX sin recompilar todo. |
| **Re-ApkPatcher** | `huanli233/Re-ApkPatcher` | ★14 | Kotlin | Patch APK usando Java/Kotlin code (Code & Resource). |

### Signature killers y bypass de integridad

| Herramienta | Repo | ★ | Técnica |
|---|---|---|---|
| **ApkSignatureKiller** | `L-JINBIN/ApkSignatureKiller` | ★960 | One-click APK signature verification crack. |
| **ApkSignatureKillerEx** | `L-JINBIN/ApkSignatureKillerEx` | ★814 | Nueva versión MT去签 y对抗. |
| **APKKiller** | `aimardcr/APKKiller` | ★449 | Bypass APK Signatures Verify & Integrity Check usando Reflection. |
| **SRPatch-X** | `KhunHtetzNaing/SRPatch-X` | ★93 | APK signature killer con PMS Hook, IO Hook, y SVC Hook. Extrae `libSRPatch.so` del SRPatch original. |
| **ApkSignatureKill (MT)** | `SectionTN/ApkSignatureKill` | ★17 | ApkSignatureKill usado en MT Manager. |

### Frida anti-detección y herramientas

| Herramienta | Repo | ★ | Uso |
|---|---|---|---|
| **Fridare** | `suifei/fridare` | ★808 | Automatización de modificación de frida-server para iOS/Android. Cambia nombres y puertos para evadir detección. GUI v4.0.0 con Fyne. |
| **strongR-frida-android** | `hluwa/strongR-frida-android` / `CrackerCat/strongR-frida-android` | ★699 | Versión anti-detección de frida-server para Android. |
| **FRIDA-DEXDump** | `hluwa/frida-dexdump` | ★4559 | Búsqueda y dump de DEX en memoria. |
| **frida_dump** | `lasting-yang/frida_dump` | ★2056 | Frida dump dex, frida dump so. |
| **frida-il2cpp-bridge** | `vfsfitvnm/frida-il2cpp-bridge` | — | Frida module para debug, dump, manipular IL2CPP. |
| **frida-il2cpp** | `AeonLucid/frida-il2cpp` | — | Helper library para Unity il2cpp games. |
| **r2frida** | `nowsecure/r2frida` | — | Radare2 + Frida combinados. |
| **fridump** | `Nightbringer21/fridump` | — | Universal memory dumper usando Frida. |
| **frida-unpack** | `dstmath/frida-unpack` | — | Frida-based shelling tool (unpacker). |
| **Patch Apk** | `NickstaDB/patch-apk` | — | Wrapper para inyectar Objection/Frida gadget en APK. |
| **Frida-Script-Runner** | `z3n70/Frida-Script-Runner` | ★371 | Web-based Frida framework para Android & iOS pentesting. |
| **frida-script-gen** | `thecybersandeep/frida-script-gen` | ★215 | Genera Frida bypass scripts para Android APK root y SSL checks. |

### Hooking frameworks nativos

| Herramienta | Repo | ★ | Lenguaje | Uso |
|---|---|---|---|---|
| **Dobby** | `jmpews/Dobby` | ★4780 | C++ | Hook framework ligero multiplataforma multi-arquitectura. |
| **xHook** | `iqiyi/xHook` | ★4343 | C | PLT hook library para Android native ELF. |
| **SandHook** | `asLody/SandHook` | ★2222 | Java | Android ART Hook / Native Inline Hook / Single Instruction Hook. Soporta 4.4-11.0. |
| **LSPlant** | `LSPosed/LSPlant` | ★1321 | C++ | Hook framework para Android Runtime (ART). |
| **And64InlineHook** | `Rprop/And64InlineHook` | — | C++ | Lightweight ARMv8-A Inline Hook Library. |
| **Android_Inline_Hook** | `GToad/Android_Inline_Hook` | — | C | Native library hooking para thumb-2 y arm32. |
| **whale** | `asLody/whale` | — | C | Hook Framework para Android/iOS/Linux/MacOS. |
| **KittyMemory** | `MJx0/KittyMemory` | — | C++ | Runtime code patching para Android e iOS. |

### Virtual engines (sandboxing y hooking sin root)

| Herramienta | Repo | ★ | Uso |
|---|---|---|---|
| **VirtualApp** | `asLody/VirtualApp` | ★11040 | Virtual Engine para Android. Permite clonar apps, hooking, IO redirection. |
| **BlackBox** | `FBlackBox/BlackBox` | ★2587 | Virtual engine: clonar y correr apps virtuales. Integra Xposed framework. |
| **SpaceCore** | `FSpaceCore/SpaceCore` | ★841 | Virtual Android system engine para clonar apps. |
| **LSPatch** | `LSPosed/LSPatch` | ★9261 | Non-root Xposed framework basado en LSPosed. Permite injectar módulos Xposed sin root. |
| **NPatch** | `7723mod/NPatch` | ★1830 | Fork de LSPatch basado en LSPosed, non-root Xposed framework. |

### Obfuscación y protección (para entender lo que hay que bypassar)

| Herramienta | Repo | ★ | Uso |
|---|---|---|---|
| **Obfuscapk** | `ClaudiuGeorgiu/Obfuscapk` | ★1265 | Obfuscación automática de APKs (black-box). |
| **BlackObfuscator** | `CodingGay/BlackObfuscator` | ★1114 | Obfuscador para APK DexFile. |
| **AndResGuard** | `shwenzhang/AndResGuard` | — | Proguard resource para Android (WeChat team). |
| **Dex2C** | `springmusk026/Dex2C-Tool` | — | Convierte DEX bytecode a C/C++ nativo. |
| **BlackDex** | `CodingGay/BlackDex` | ★6402 | Android unpack (dexdump) tool. Soporta Android 5.0-12 sin root. |

### Unity / IL2CPP modding (juegos)

| Herramienta | Repo | ★ | Uso |
|---|---|---|---|
| **Il2CppDumper** | `Perfare/Il2CppDumper` | — | Dumper de IL2CPP. |
| **Zygisk-Il2CppDumper** | `Perfare/Zygisk-Il2CppDumper` | ★3229 | Dump de il2cpp data en runtime via Zygisk. |
| **Il2CppInspector** | `djkaty/Il2CppInspector` | — | Herramienta automatizada para RE de Unity IL2CPP binaries. |
| **UnityResolve.hpp** | `issuimo/UnityResolve.hpp` | ★453 | Unity engine C++ API (Mono/il2cpp) para Windows, Android, Linux. |
| **ByNameModding** | `geokar2006/ByNameModding` | — | Modding il2cpp games por classes, methods, fields names. |
| **IL2CPP_Resolver** | `sneakyevilSK/IL2CPP_Resolver` | — | Run-time API resolver para IL2CPP Unity. |

### Mod menu templates (para juegos)

| Template | Repo | Uso |
|---|---|---|
| **PlatinmodsMenu** | `FrostyHacker/PlatinmodsMenu` | Mod menu template de Platinmods. |
| **Android-Mod-Menu** | `LGLTeam/Android-Mod-Menu` | Mod menu template. |
| **FrostyMenu** | `FrostyHacker/FrostyMenu` | Mod menu template. |
| **FloatingModMenu** | `MrIkso/FloatingModMenu` | Mod menu template flotante. |
| **Android-Hooking-Patching-Template** | `LGLTeam/Android-Hooking-Patching-Template` | Hooking y patching template. |

### Herramientas de análisis y hex editing

| Herramienta | Repo | ★ | Uso |
|---|---|---|---|
| **Bytecode-Viewer** | `Konloch/bytecode-viewer` | ★15566 | GUI con múltiples decompilers: JADX, Fernflower, Krakatau, smali. |
| **ApkStudio** | `vaibhavpandeyvpz/apkstudio` | ★4316 | IDE cross-platform Qt6 para RE de Android. |
| **ImHex** | `WerWolv/ImHex` | — | Hex Editor para RE. |
| **ARM-Converter** | `MikaCybertron/ARM-Converter` | — | Conversor offline ARM64/ARM/THUMB instruction → hex. |
| **KMrite** | `BryanGIG/KMrite` | — | Escritura en lib.so con offset y hex bytes. |

### Lista maestra de referencia

La lista más completa de herramientas de modding de Android está en `jbro129/android-modding` (★739), con 821 líneas categorizando:
- Mod Menu Templates (20+)
- Dumping and Unpacking (IL2CPP, UE4, BlackDex)
- Packing and Protection (Obfuscapk, BlackObfuscator, DexGuard)
- C++ Libraries (KittyMemory, ByNameModding, IL2CPP_Resolver)
- Hooking Libraries (Dobby, xHook, SandHook, LSPlant)
- Modding Projects and Tutorials
- Modding Tools (ApkSignatureKiller, APKKiller, apk-mitm)
- IDA and RE Platforms (Ghidra, Cutter, IDA plugins)
- Frida (FRIDA-DEXDump, strongR-frida, r2frida)
- Virtual Engines (VirtualApp, BlackBox, LSPatch)
- Other (injectors, memory hacks)

---

## Herramientas rusas y chinas (curado de 4PDA y foros relacionados)

### Editores APK on-device (muy populares en foros rusos)

| Herramienta | Versión | Origen | Uso |
|---|---|---|---|
| **MT Manager** | 2.26.7 | `mt2.cn` (China) | Editor APK dual-panel on-device: traducción, clonación, cifrado, firma, optimización. Incluye DEX editor, ApkSignatureKill integrado. Muy popular en 4PDA. |
| **NP Manager** | 3.1.41 | `MT_吹牛儿` (China) | Editor APK on-device: control flow obfuscation, Dex2C, Res obfuscation, Dex/jar/smali conversion, string encryption. Basado en MT Manager. |
| **APK Editor Pro** | 2.7.0 | `TimScriptov` | Editor APK on-device: cambio de strings, reemplazo de imágenes, modificación de layout, eliminación de ads, cambio de permisos. Soporta patches. |
| **Batch ApkTool** | 3.8.1 | `BurSoft` (Rusia) | Utilidad Windows para recompilación correcta de APK. Desarrollada en colaboración con profesionales de modificación. Interfaz rusa. |
| **TranslatorApk** | — | 4PDA | Programa para traducción cómoda de archivos .apk. |

### Herramientas de parcheo y bypass (foros rusos)

| Herramienta | Versión | Origen | Uso |
|---|---|---|---|
| **Lucky Patcher** | 12.10.6 | `ChelpuS` | Patcher universal para la mayoría de apps y juegos. Emula compras in-app, elimina ads, elimina verificación de licencia, modifica permisos. Requiere Android 4.0+. |
| **Frida Injector - Pocket Edition** | 3.1 | `Иван Тимашков` | Inyecta código en apps directamente en el teléfono. Requiere root o espacio virtual. GitHub: `TimScriptov/Frida-Injector-for-Android`. |
| **App Cloner** | — | 4PDA | Clonación de APK sin root. |

### Foros rusos de referencia (4PDA)

| Hilo | URL | Contenido |
|---|---|---|
| **MT Manager** | `4pda.to/forum/index.php?showtopic=548542` | Hilo oficial: traducción, firma, modding, crack y optimización APK. |
| **NP Manager** | `4pda.to/forum/index.php?showtopic=966965` | Hilo oficial: edición, traducción, clonación, cifrado, firma, optimización. |
| **Batch ApkTool** | `4pda.to/forum/index.php?showtopic=557858` | Utilidad para recompilación correcta de APK. |
| **APK Editor Pro** | `4pda.to/forum/index.php?showtopic=575450` | Editor APK on-device con patches. |
| **Lucky Patcher** | `4pda.to/forum/index.php?showtopic=298302` | Patcher universal. |
| **Frida Injector PE** | `4pda.to/forum/index.php?showtopic=998591` | Frida en Android on-device. |
| **Nueva forma de modificar apps** | `4pda.to/forum/index.php?showtopic=209346` | Tutorial de modificación/traducción de apps con APK Manager. |
| **Instrucciones de edición de recursos** | `4pda.to/forum/index.php?showtopic=540887` | Catálogo de manuales de edición de recursos del sistema. |
| **Edición de recursos del sistema** | `4pda.to/forum/index.php?showtopic=196047` | Discusión de métodos de edición de recursos del sistema. |

### Patrones de la comunidad rusa

- **MT Manager y NP Manager** son las herramientas más usadas en foros rusos para modding on-device (sin PC).
- **Batch ApkTool** es el estándar para modding en PC (Windows) en la comunidad rusa.
- **Lucky Patcher** sigue siendo ampliamente usado para bypass de licencias y emulación de compras.
- Los tutoriales de 4PDA cubren principalmente traducción y modificación de recursos del sistema, no tanto crack de premium (eso se discute menos abiertamente).
- La comunidad rusa prefiere herramientas con interfaz y flujo de trabajo en ruso.

---

## Foros y comunidades de referencia

### Comunidades técnicas (recomendadas para aprendizaje)

| Foro | URL | Enfoque |
|---|---|---|
| **XDA Developers** | `xda-developers.com` | Desarrollo Android, modding legal, ROMs, kernels, Magisk. |
| **Reverse Engineering SE** | `reverseengineering.stackexchange.com` | RE genérico, Q&A técnico de alto nivel. |
| **Reddit r/revanced** | `reddit.com/r/revanced` | ReVanced, Morphe patcher, patches open-source. |
| **Reddit r/androidroot** | `reddit.com/r/androidroot` | Root, Magisk, módulos. |
| **Frida Slack** | `frida.io` | Soporte oficial de Frida. |
| **OWASP Mobile Slack** | `owasp.org` | MASTG/MASVS, seguridad móvil. |

### Foros rusos/chinos (distribución de mods — precaución legal)

| Foro | URL | Enfoque | Notas |
|---|---|---|---|
| **4PDA** | `4pda.to` | Foro ruso, muy completo técnico | Requiere registro. Contenido técnico fuerte + distribución. |
| **Androeed** | `androeed.ru` | Foro ruso de mods | Similar a 4PDA. |
| **Platinmods** | `platinmods.com` | Mods de APK, discusión técnica | Distribuye APKs modificadas. |
| **BlackMod** | `blackmod.net` | Mods de juegos Android | Distribución de mods premium. |
| **HappyMod** | `happymod.com` | Mods de juegos | Plataforma de distribución. |

### Canales Discord/Telegram

- **Morphe patcher Discord** — discusión de patches, fingerprints, desarrollo
- **Frida community** — soporte técnico de Frida
- **Magisk Discord** — desarrollo de módulos Magisk/Zygisk
- **LSPosed Discord** — desarrollo de módulos Xposed

---

## Changelog

- 2026-07-18 (v3): Añadidos 4 scripts de automatización, guía de firma v2/v3/v4, bundles/splits, patrones 2026, checklist Android 14–16, estrategias de parcheo A-F, catálogo ampliado de perfiles de modders, plantilla de case study, Morphe patcher, PMS Hook/IO redirection, Android 16+ Developer Verifier bypass, PairipCore bypass, Frida Gadget embedding, ecosistema completo de herramientas (parcheo, signature killers, Frida anti-detección, hooking nativo, virtual engines, obfuscación, Unity/IL2CPP, mod menus, hex editing), foros y comunidades de referencia, herramientas rusas/chinas de 4PDA (MT Manager, NP Manager, Batch ApkTool, Lucky Patcher, APK Editor, Frida Injector PE), y batch-apktool.sh (equivalente Linux de Batch ApkTool).
