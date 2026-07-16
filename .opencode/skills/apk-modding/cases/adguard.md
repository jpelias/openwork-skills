# Case 5: AdGuard Premium 4.14.0 — Call sites in different DEX + 5-layer license state

**The trap**: Injected classes were in `classes3.dex` but calls were in `classes2.dex` (`MainActivity.smali:1517+1519`). Searching only classes3 found nothing.

**SOLUTION (manual smali):**
1. Decompiled ALL 3 DEXes, searched EVERY dex_out/
2. Found 2 classic yhf calls: `pk.process()` + `bi.b()` in MainActivity.smali
3. Removed both lines, neutralized iaw/iab as backup
4. Also found `d6/a.a()` call in K3/a.smali — removed
5. Left `p6/e` and `q6/c` untouched (legitimate text rendering)

**Lesson**: Call sites are often in a DIFFERENT DEX than the injection. Always decompile and search ALL DEX files.

---

## 5-layer license state (from Morphe patcher)

The Morphe patch for AdGuard (`rushiranpise/morphe-patches` — `AdGuardUnlockLifetimePatch.kt`) reveals that AdGuard's license state flows through **5 distinct paths** that all need patching:

```
Path 1 — License screen (AboutLicenseViewModel):
  B0/a.A() StateFlow → mapper B0/a$k → B0/a.u() → B0/a.t() → network

Path 2 — Promo/Check license dialog (PromoViewModel):
  B0/a field StateFlow → mapper B0/a$j → B0/a.r() → B0/a.q() → network
  q() result feeds needShowCheckLicenseDialog via MutableLiveData.postValue()
  When Free/Unknown → shows "Check license" dialog → opens purchase URL in Chrome
```

**5 patch layers:**

| Layer | Method | Patch | Purpose |
|---|---|---|---|
| 1 | Inject `getPaidLicense()` | Static helper returning `PaidLicense("", Personal, Lifetime, 1, 3, "")` | Reusable license object |
| 2 | `B0/a.s()` | Return `PaidLicense` | Non-reactive cache reads |
| 3 | `B0/a.B(LE0/i)` | Replace incoming state with `PaidLicense` | Event bus propagation |
| 4 | `B0/a.t()` | Return `PaidLicense` | License screen StateFlow |
| 5 | `B0/a.q()` | Return `PaidLicense` | Promo/check-license dialog StateFlow |

**Without Layer 5**, network returns Free → dialog shows "Check license" → opens purchase URL in Chrome. All 5 layers must be patched.

**Source:** `rushiranpise/morphe-patches` — `AdGuardUnlockLifetimePatch.kt`
