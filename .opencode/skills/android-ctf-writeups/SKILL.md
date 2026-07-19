---
name: android-ctf-writeups
description: >
  Tecnicas de Android RE extraidas de CTF writeups reales (bi0s Pentest Blog, Junio 2026). Cubre: Frida NativeFunction, stub .so replacement, strcmp hook via Java.choose, Deobfuscator hooking, WebView XSS + deep link injection, SSL bypass con android-unpinner, XOR key recovery, native JNI retval.replace, crypto detection universal, anti-Frida pthread_create bypass, fwrite hook, AES static key. Use para aprender tecnicas practicas de escenarios reales de CTF.
---

# Android CTF Writeups

Tecnicas practicas extraidas de [bi0s Pentest Blog](https://pentest.bi0s.in/blog/), organizadas por categoria.

## Frida — Native

### NativeFunction call directo
**Rude Frida (Pwnsec CTF)**  
`libRudeFrida.so` con root check + `FridaCheck()` (puertos default). Bypass root: CodeShare @fdciabdul. Bypass anti-Frida: phantom-frida. Flag via `get_flag(int, int)`:
```javascript
const f = Process.getModuleByName('libRudefrida.so').getExportByName('_Z8get_flagii');
const myNative = new NativeFunction(f, ['void'], ['int', 'int']);
myNative(1330, 7); // params suman 0x539 (1337)
```

### Interceptor.attach + retval.readCString()
**Freeda Native Hook (HeroCTF)**  
RootBeer bypass + `libv3.so` con `get_flag()` que retorna puntero a flag:
```javascript
Interceptor.attach(Module.findExportByName('libv3.so', 'get_flag'), {
    onLeave(retval) { console.log(retval.readCString()); }
});
```

### retval.replace() para forzar boolean
**A Strange Door (Payatu CTF)**  
`libctf.so` con `checkPasscode(String)` → `retval.replace(1)` fuerza true:
```javascript
const f = Process.getModuleByName('libctf.so').getExportByName('Java_com_payatu_astragedoor_LoginActivity_checkPasscode');
Interceptor.attach(f, { onLeave(retval) { retval.replace(1); } });
```

## Frida — Anti-protecciones

### Stub .so replacement
**Freaky Frida (Pwnsec CTF)**  
`libnative-lib.so` ofuscado crashea la app. Reemplazar con stub:
```c
__attribute__((visibility("default")))
int JNI_OnLoad(void *vm, void *reserved) { return 0x00010006; }
```
```bash
gcc -shared -fPIC -nostdlib -o libnative-lib.so stub.c
apktool d app.apk && cp libnative-lib.so app/lib/x86_64/libnative-lib.so
apktool b app && uber-apk-signer -a app.apk
```
Luego hook `strcmp` + `Java.choose` para interactuar con instancia existente.

### pthread_create bypass (anti-Frida thread)
**Apkocalypse (l3ak CTF)**  
Thread anti-Frida via `pthread_create`. Bypass con `Interceptor.replace`:
```javascript
var pthread_create = new NativeFunction(Module.findExportByName('libc.so', 'pthread_create'),
    'int', ['pointer', 'pointer', 'pointer', 'pointer']);
Interceptor.replace(pthread_create, new NativeCallback(function(ptr0, ptr1, ptr2, ptr3) {
    if (ptr1.isNull() && ptr3.isNull()) return -1; // bloquear thread sospechoso
    return pthread_create(ptr0, ptr1, ptr2, ptr3);
}, 'int', ['pointer', 'pointer', 'pointer', 'pointer']));
```

### fwrite hook (capturar antes de unlink)
**Apkocalypse (l3ak CTF)**  
App escribe flag a archivo y lo borra con `unlink()`. Hookear `fwrite`:
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
`Deobfuscator$app$Release.getString(long)` con 5 valores especificos:
```javascript
var f = Java.use("com.joom.paranoid.Deobfuscator$app$Release");
[-548601664941, -3140818349, -28910622125, -308083496365, -338148267437]
    .forEach(l => console.log(f.getString(l)));
```

### Crypto detection universal
**Knight (P3RF3CTR00T CTF)**  
AES + base64 ciphertext. Hookear TODAS las funciones criptograficas:
```bash
frida --codeshare L0WK3Y-IAAN/crypto-detection -f com.app
```

## WebView / Deep Links

### javascript: injection via deep link
**Path Finder (Payatu CTF)**  
`@JavascriptInterface` expone `AndroidFunction.showFlag()`. Bypass de `contains("payatu.com")` con comentario JS:
```bash
am start -a android.intent.action.VIEW -d "ctf://payatu/web?url=javascript:AndroidFunction.showFlag()//payatu.com"
```

## Network

### SSL bypass + API tampering
**Shadow Vault (Pearl CTF)**  
Creds hardcoded `Player118:Gv8@kz#1qP$Xy!tM`. SSL pinning bypass con `android-unpinner`. Burp: modificar `latitude=100&longitude=200` en POST.

## Static Analysis

### XOR key recovery (Kotlin)
**DROID (Squirrel CTF)**  
`key[] ^ expected[] = flag`. `ComposerKt.reuseKey = 207` hardcoded. Python script:
```python
result = ''.join(chr(e ^ k) for e, k in zip(expected, key))
```

### Native strcmp en Ghidra
**Gate Keeper (Payatu CTF)**  
`libnative-lib.so` → `submitKey()` llama `strcmp(input, "undefined")`. Flag si coincide.

### Hidden ELF in resources
**Firmware (Cyberchaze CTF)**  
`firmware.bin` en `res/raw/` → 7zip password `nullc0n_2025` de `strings.xml` → ELF ejecutable → `strings | grep flag`.

### AES static key
**Droid Cryptor (m0leC0n CTF)**  
`SUPER_SECRET_KEY = "YWYwYjAyYjkzNmRhZjU3Yg=="` (base64). AES/ECB/PKCS5Padding con IV → CyberChef.

---

## Skills relacionados

- **`frida-expert`** — Cookbook Frida completo
- **`android-reverse-engineering`** — Triaje y analisis estatico
- **`apk-modding`** — Parcheo persistente
- **`hacktricks-reference`** — Indice de recursos externos

## Changelog

- 2026-07-19 (v1): Extraido de hacktricks-reference. 13 tecnicas de CTFs reales organizadas por categoria.
