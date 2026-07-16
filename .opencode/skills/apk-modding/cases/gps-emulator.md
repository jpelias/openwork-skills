# Case 1: GPS Emulator 3.29 — Native multi-layer protection

**Modder approach:**
- 9 native `.so` libraries injected
- DEX files encrypted with APK signature as key
- 4-layer circular signature verification (`gho.u` → `gho.gC` → `cp.r` → `cup.c`)
- Native `execute()` method shows branding dialog

**Attempts that FAILED:**
- Patching `.so` at `0x386cc` (was actually WellKnownClasses loader, not signature check)
- 3-patch approach (`execute=ret`, `gho.u=return input`, `gho.z=ret`) → app works but `noads`/`numerofavoritos` not set
- 4-patch approach (adding `gho.gC=return jclass`) → `ExceptionInInitializerError` (wrong return type)

**SOLUTION: Hack the ORIGINAL APK**
- Original has zero native libraries, zero `bin.ghost`, clean DEX
- Only 12 smali lines changed: defaults `false→true`, `10→1000`
- Result: all PRO features enabled, no dialog, redistributable
