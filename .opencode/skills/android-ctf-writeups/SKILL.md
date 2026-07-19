---
name: android-ctf-writeups
description: >
  Android RE techniques extracted from real CTF writeups (bi0s Pentest Blog, June 2026). Covers: Frida NativeFunction, stub .so replacement, strcmp hook via Java.choose, Deobfuscator hooking, WebView XSS + deep link injection, SSL bypass with android-unpinner, XOR key recovery, native JNI retval.replace, universal crypto detection, anti-Frida pthread_create bypass, fwrite hook, AES static key. Use to learn practical techniques from real CTF scenarios.
---

# Android CTF Writeups

Practical techniques extracted from [bi0s Pentest Blog](https://pentest.bi0s.in/blog/), organized by category.

## Frida — Native

### Direct NativeFunction call
**Rude Frida (Pwnsec CTF)**  
`libRudeFrida.so` with root check + `FridaCheck()` (default ports). Root bypass: CodeShare @fdciabdul. Anti-Frida bypass: phantom-frida. Flag via `get_flag(int, int)`:
```javascript
const f = Process.getModuleByName('libRudefrida.so').getExportByName('_Z8get_flagii');
const myNative = new NativeFunction(f, ['void'], ['int', 'int']);
myNative(1330, 7); // params add up to 0x539 (1337)
```

### Interceptor.attach + retval.readCString()
**Freeda Native Hook (HeroCTF)**  
RootBeer bypass + `libv3.so` with `get_flag()` that returns pointer to flag:
```javascript
Interceptor.attach(Module.findExportByName('libv3.so', 'get_flag'), {
    onLeave(retval) { console.log(retval.readCString()); }
});
```

### retval.replace() to force boolean
**A Strange Door (Payatu CTF)**  
`libctf.so` with `checkPasscode(String)` → `retval.replace(1)` forces true:
```javascript
const f = Process.getModuleByName('libctf.so').getExportByName('Java_com_payatu_astragedoor_LoginActivity_checkPasscode');
Interceptor.attach(f, { onLeave(retval) { retval.replace(1); } });
```

## Frida — Anti-protections

### Stub .so replacement
**Freaky Frida (Pwnsec CTF)**  
Obfuscated `libnative-lib.so` crashes the app. Replace with stub:
```c
__attribute__((visibility("default")))
int JNI_OnLoad(void *vm, void *reserved) { return 0x00010006; }
```
```bash
gcc -shared -fPIC -nostdlib -o libnative-lib.so stub.c
apktool d app.apk && cp libnative-lib.so app/lib/x86_64/libnative-lib.so
apktool b app && uber-apk-signer -a app.apk
```
Then hook `strcmp` + `Java.choose` to interact with existing instance.

### pthread_create bypass (anti-Frida thread)
**Apkocalypse (l3ak CTF)**  
Anti-Frida thread via `pthread_create`. Bypass with `Interceptor.replace`:
```javascript
var pthread_create = new NativeFunction(Module.findExportByName('libc.so', 'pthread_create'),
    'int', ['pointer', 'pointer', 'pointer', 'pointer']);
Interceptor.replace(pthread_create, new NativeCallback(function(ptr0, ptr1, ptr2, ptr3) {
    if (ptr1.isNull() && ptr3.isNull()) return -1; // block suspicious thread
    return pthread_create(ptr0, ptr1, ptr2, ptr3);
}, 'int', ['pointer', 'pointer', 'pointer', 'pointer']));
```

### fwrite hook (capture before unlink)
**Apkocalypse (l3ak CTF)**  
App writes flag to file and deletes it with `unlink()`. Hook `fwrite`:
```javascript
Interceptor.attach(Module.findExportByName('libc.so', 'fwrite'), {
    onEnter(args) {
        var size = args[1].toInt32() * args[2].toInt32();
        console.log(Memory.readUtf8String(args[0], size));
    }
});
```

## Frida — Java

### Deobfuscator hooking
**Cute Frida (Pwnsec CTF)**  
`Deobfuscator$app$Release.getString(long)` with 5 specific values:
```javascript
var f = Java.use("com.joom.paranoid.Deobfuscator$app$Release");
[-548601664941, -3140818349, -28910622125, -308083496365, -338148267437]
    .forEach(l => console.log(f.getString(l)));
```

### Universal crypto detection
**Knight (P3RF3CTR00T CTF)**  
AES + base64 ciphertext. Hook ALL cryptographic functions:
```bash
frida --codeshare L0WK3Y-IAAN/crypto-detection -f com.app
```

## WebView / Deep Links

### javascript: injection via deep link
**Path Finder (Payatu CTF)**  
`@JavascriptInterface` exposes `AndroidFunction.showFlag()`. Bypass `contains("payatu.com")` with JS comment:
```bash
am start -a android.intent.action.VIEW -d "ctf://payatu/web?url=javascript:AndroidFunction.showFlag()//payatu.com"
```

## Network

### SSL bypass + API tampering
**Shadow Vault (Pearl CTF)**  
Hardcoded creds `Player118:Gv8@kz#1qP$Xy!tM`. SSL pinning bypass with `android-unpinner`. Burp: modify `latitude=100&longitude=200` in POST.

## Static Analysis

### XOR key recovery (Kotlin)
**DROID (Squirrel CTF)**  
`key[] ^ expected[] = flag`. `ComposerKt.reuseKey = 207` hardcoded. Python script:
```python
result = ''.join(chr(e ^ k) for e, k in zip(expected, key))
```

### Native strcmp in Ghidra
**Gate Keeper (Payatu CTF)**  
`libnative-lib.so` → `submitKey()` calls `strcmp(input, "undefined")`. Flag if match.

### Hidden ELF in resources
**Firmware (Cyberchaze CTF)**  
`firmware.bin` in `res/raw/` → 7zip password `nullc0n_2025` from `strings.xml` → executable ELF → `strings | grep flag`.

### AES static key
**Droid Cryptor (m0leC0n CTF)**  
`SUPER_SECRET_KEY = "YWYwYjAyYjkzNmRhZjU3Yg=="` (base64). AES/ECB/PKCS5Padding with IV → CyberChef.

---

## Related skills

- **`frida-expert`** — Complete Frida cookbook
- **`android-reverse-engineering`** — Static analysis and triage
- **`apk-modding`** — Persistent patching
- **`hacktricks-reference`** — External resources index

## Changelog

- 2026-07-19 (v1): Extracted from hacktricks-reference. 13 techniques from real CTFs organized by category.
