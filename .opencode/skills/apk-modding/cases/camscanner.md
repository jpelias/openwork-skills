# Case 2: CamScanner 7.20.5 — Java light protection

**Modder approach:**
- Only 3 packages injected: `ī/íì/`, `īi/ïi/`, `bin/ghost/`
- Signature killer (`ApkSignatureKillerEx`) present but DORMANT (not in manifest)
- DEX is clean, decompiles perfectly
- Only set `key_max_dir_count=9999`; did NOT activate premium features
- Original 7.21.5 is Flutter + ijiami → impenetrable. Pirate used older 7.20.5 (Java/Kotlin)

**SOLUTION:**
1. Removed 2 `invoke-static` calls from `MainActivity.smali` (classes4.dex)
2. Neutralized 7 dialog methods to no-ops (classes12.dex)
3. Forced 3 premium methods to always return `true` (classes8.dex)
4. Kept `META-INF/services/` (prevents Kotlin ServiceLoader crash)

**Result:** No dialogs, premium enabled, redistributable.
