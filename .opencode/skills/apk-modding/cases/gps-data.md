# Case 3: GPS Data 3.1.03 — Modder changed package names

**The trap**: The modder yhf used `p000/p001/` and `p002i/p003i/` instead of the classic `ī/íì/` and `īi/ïi/`. String search for `Liteapks` and `title.ttf` found NOTHING. The injection was only found via behavioral detection.

**SOLUTION:**
1. Found via `grep -rn "Typeface.createFromAsset\|AlertDialog.Builder"` in non-standard packages
2. `MainActivity.java:2390-2391` called `pk.process(this)` + `bi.b(this)` → removed lines 8353+8355 in smali
3. Premium already enabled (`D0.e.k()` always true, `premium_version_purchased` default true)
4. Google Maps: replaced manifest API key + signed with AOSP testkey
