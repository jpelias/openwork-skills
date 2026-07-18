# Conocimiento de Repos Externos — Android SSL Pinning Bypass

Información extraída de los repos más relevantes de GitHub sobre bypass SSL pinning, pentesting Android e ingeniería inversa.

---

## 1. TrustMeAlready (ViRb3) — 1,498⭐ [ARCHIVADO]

**Tipo:** Módulo Xposed (system-wide)
**Estado:** Archivado (2023). Autor recomienda Frida.

**Técnica:** Hookea `com.android.org.conscrypt.TrustManagerImpl.checkTrustedRecursive` vía Xposed Zygote. Devuelve `ArrayList<X509Certificate>` vacío para engañar a Conscrypt.

**Limitaciones críticas:**
- No cubre OkHttp3 CertificatePinner (issue #2, abierto)
- No cubre apps con pinning nativo (.so)
- No cubre Flutter
- Solo Android 7+ (Conscrypt)
- No soporta configuración por app

**Relevancia:** Técnica de `checkTrustedRecursive` que nosotros usamos exitosamente en Smart Life.

---

## 2. FridaBypassKit (okankurtuluss) — 142⭐

**Tipo:** Script Frida universal (un solo archivo)

**4 módulos en uno:**
| Módulo | Técnicas |
|---|---|
| Root bypass | `File.exists()` + `Runtime.exec()` (Fake Process) + `PackageManager.getPackageInfo()` + `UnixFileSystem.checkAccess()` |
| SSL bypass | `TrustManagerImpl.verifyChain()` + `checkTrustedRecursive()` |
| Emulator bypass | `TelephonyManager.getNetworkOperatorName()` + `getLine1Number()` |
| Debug bypass | `Debug.isDebuggerConnected()` + `waitingForDebugger()` |

**Técnica destacada:** Fake Process — cuando la app ejecuta `su`, devuelve un `Process` sintético con streams vacíos y exitValue=0. La app cree que el comando funcionó.

**Relevancia:** Las técnicas de root bypass son más completas que las nuestras. Deberíamos incorporar `UnixFileSystem.checkAccess()` y `Runtime.exec()` con Fake Process.

---

## 3. Mobile-PT (SNGWN) — 122⭐

**Tipo:** Toolkit completo de pentesting móvil

**Scripts Frida específicos:**
| Script | Plataforma |
|---|---|
| `ssl-pinning-bypass.js` | Universal (OkHttp3, HttpsURLConnection, X509TrustManager, Volley, NSURLSession) |
| `root-detection-bypass.js` | Android |
| `anti-debugging-bypass.js` | Android |
| `flutter-ssl-pinning-bypass.js` | Flutter |
| `flutter-platform-channel-monitor.js` | Flutter |
| `flutter-http-monitor.js` | Flutter (DartHttpClient) |
| `jailbreak-detection-bypass.js` | iOS |
| `biometric-bypass.js` | iOS |

**Guías documentadas:**
- Setup Frida en Android/iOS
- Configurar Burp Suite para Android 7+
- Metodología de 5 fases (Info Gathering → Static → Dynamic → Security Testing → Reporting)
- Checklist OWASP Mobile Top 10

**Relevancia:** Los scripts de Flutter son los más avanzados que hemos visto. Cubren SSL pinning, platform channels y HTTP monitoring específico de Flutter.

---

## 4. Android-CertKiller (51j0) — 138⭐

**Tipo:** Parcheo estático de APK (repackaging)

**Técnica:** Modifica `AndroidManifest.xml` para aceptar certificados de usuario:
```xml
<network-security-config>
  <base-config>
    <trust-anchors>
      <certificates src="system" />
      <certificates src="user" />  <!-- clave -->
    </trust-anchors>
  </base-config>
</network-security-config>
```

**Limitaciones:**
- Solo cubre Android 7+ networkSecurityConfig
- NO cubre OkHttp, TrustManager custom, Flutter, WebView
- Inútil contra pinning a nivel de código
- Pierde la firma original (detectable por Play Integrity)

**Relevancia:** Técnica muy limitada. Solo útil para apps que exclusivamente dependen de `networkSecurityConfig` para pinning (caso raro).

---

## 5. Fridare (suifei) — 804⭐

**Tipo:** Stealth Frida (ofuscación de fingerprints)

**Técnica:** Repacketea binarios Frida sin recompilar, reemplazando strings detectables:
- `frida_server_` → nombre aleatorio de 5 letras
- `frida-agent.dylib/.so` → renombrado
- `gum-` → 3 primeras letras del nombre aleatorio
- `frida:rpc` → renombrado
- `frida-main-loop` → renombrado
- Puerto e interfaz D-Bus configurables

**Detecciones que evade:**
- Escaneos de `/proc` (cmdline, maps, task comm, fd readlink)
- D-Bus service names
- Puertos por defecto (27042)
- Símbolos exportados
- Nombres de thread (gmain, gdbus, pool-spawner)
- Labels SELinux

**Relevancia:** Para Android 14+ con PaIRip anti-Frida, esto es imprescindible. En Android 10 no fue necesario, pero es buena práctica.

---

## 6. Flutter SSL Pinning Bypass (Horangi) — 85⭐

**Tipo:** Script Frida específico para Flutter

**Técnica:** Memory scan de `libflutter.so` buscando patrón de bytes de la función de validación de certificados, luego hook nativo.

**Diferencias con bypass nativo:**
| Nativo | Flutter |
|---|---|
| `Java.use("X509TrustManager")` | `Memory.scanSync(libflutter.so, pattern)` |
| Símbolos Java documentados | Patrones de bytes en C++ |
| Portable entre apps | Patrón rompe entre versiones de Flutter |

**Relevancia:** Confirma que Flutter necesita un enfoque completamente diferente. Nuestra experiencia con AEMET (que no tenía pinning) fue más fácil porque no necesitamos este bypass.

---

## 7. Frida-libcurlUnpinning (d0gkiller87) — 38⭐

**Tipo:** Script Frida para apps con libcurl nativo (NDK)

**Técnica:** Hookea `curl_easy_setopt` nativo y bloquea:
- `CURLOPT_SSL_VERIFYPEER` (64) → fuerza 0
- `CURLOPT_SSL_VERIFYHOST` (81) → fuerza 0
- `CURLOPT_PINNEDPUBLICKEY` (10230) → fuerza NULL

**Cuándo es necesario:** Apps que hacen HTTPS desde C/C++ (NDK) con libcurl, sin pasar por Java. Los bypasses Java estándar no funcionan.

**Relevancia:** Si encontramos una app que no usa OkHttp ni Java HTTP client, debemos verificar si usa libcurl nativo.

---

## Resumen de técnicas para nuestro skill

### Lo que YA tenemos (confirmado que funciona)
- ✅ Conscrypt `checkTrustedRecursive` bypass (Smart Life)
- ✅ Conscrypt `verifyChain` bypass (Smart Life)
- ✅ OkHttp CertificatePinner bypass
- ✅ WebView SSL error bypass
- ✅ Root detection bypass (File.exists + SystemProperties + Build.TAGS)
- ✅ Cert injection (825 bytes, sin -text)
- ✅ Magisk DenyList para root bypass permanente

### Lo NUEVO que deberíamos añadir
- 🔧 `Runtime.exec()` con Fake Process (de FridaBypassKit)
- 🔧 `UnixFileSystem.checkAccess()` para bypass más profundo (de FridaBypassKit)
- 🔧 `PackageManager.getPackageInfo()` para ocultar apps de root (de FridaBypassKit)
- 🔧 `Memory.scanSync()` para bypass Flutter nativo (de Horangi)
- 🔧 `curl_easy_setopt` hook para apps NDK (de d0gkiller87)
- 🔧 Fridare/stealth Frida para Android 14+ (de suifei)
- 🔧 Scripts Flutter HTTP monitor y platform channel monitor (de Mobile-PT)
