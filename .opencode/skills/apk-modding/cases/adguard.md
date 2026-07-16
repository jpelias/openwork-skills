# Case 5: AdGuard Premium 4.14.0 — Call sites in different DEX

**The trap**: Injected classes were in `classes3.dex` but calls were in `classes2.dex` (`MainActivity.smali:1517+1519`). Searching only classes3 found nothing.

**SOLUTION:**
1. Decompiled ALL 3 DEXes, searched EVERY dex_out/
2. Found 2 classic yhf calls: `pk.process()` + `bi.b()` in MainActivity.smali
3. Removed both lines, neutralized iaw/iab as backup
4. Also found `d6/a.a()` call in K3/a.smali — removed
5. Left `p6/e` and `q6/c` untouched (legitimate text rendering)

**Lesson**: Call sites are often in a DIFFERENT DEX than the injection. Always decompile and search ALL DEX files.
