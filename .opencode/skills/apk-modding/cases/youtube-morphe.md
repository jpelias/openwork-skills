# Case 4: YouTube Premium (Morphe) — Full modding pipeline

**The real problem was simpler than expected:**
- Initial crashes were caused by **ZIP corruption** from Python `zipfile`, NOT native signature checks
- `.so` files are IDENTICAL between stock and Morphe (SHA256 verified) — no native patches needed
- The solution: **baksmali → modify smali → smali assemble → apkzlib insert → AOSP sign**

**Technique:**
1. Package `com.google.android.youtube` → `app.morphe.android.youtube`
2. `versionCode = 2147483647` (max int32, blocks Play Store updates)
3. Activity-aliases for 35 themes (5 sets × 7 variants)
4. Smali patches in account/playback classes force `isPremium = true`
5. Ad-free verified: QOE pings omit `adcontext=` parameter

**Liteapks removal — 3 patches across 3 DEX files:**

| DEX | Patch | Effect |
|---|---|---|
| **classes.dex** | Remove `LB.ll()` invocation from `MainActivity.onResume()` | Dialog never created |
| **classes8.dex** | Block `api.morphe.software` fetch → use static links only | No online liteapks content |
| **classes9.dex** | `Strings.smali`: all methods return `""` | Empty text, title, buttons |

**The liteapks injection was:**
- `com/zx/cmz/Strings` — promotional strings (title, message, buttons)
- `com/zx/LB` — AlertDialog fragment with gradient background
- Triggered by `MainActivity` → `LB.ll(Activity)` in `onResume()`

**Working build pipeline:**
```bash
# For each DEX to patch:
baksmali d classesN.dex -o dexN_out/ --api 37
# Edit .smali files
smali assemble dexN_out/ --api 37 -o classesN_patched.dex

# Insert with apkzlib (preserves ZIP structure):
java Insert original.apk output.apk

# Sign with AOSP testkey (works — no native protection):
apksigner sign --ks aosp_testkey.p12 ... --out final.apk
```
