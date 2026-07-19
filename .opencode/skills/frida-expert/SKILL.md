---
name: frida-expert
description: >
  Frida Expert cookbook for Android dynamic instrumentation. SSL pinning bypass (OkHttp, Cronet, TrustManager, Flutter, WebView, TrustKit, Netty, PhoneGap, IBM WorkLight, Squareup), root detection bypass (file checks, commands, packages, system properties, Build.FINGERPRINT), anti-Frida bypass (strstr, fopen, memmem), crypto interception (Cipher, Mac, MessageDigest), native connect hook (SOCKS5 proxy redirection), Flutter BoringSSL bypass, CModule, memory scanning, DexClassLoader hooking, anti-suicide. Use for authorized dynamic analysis, SSTI/SSL bypass, root hiding, and runtime instrumentation.
---

# Frida Expert Cookbook

Cookbook consolidado de Frida para Android, con scripts verificados de [Frida CodeShare](https://codeshare.frida.re/browse) y [HTTP Toolkit Frida](https://github.com/httptoolkit/frida-interception-and-unpinning). Cada seccion incluye el script listo para copiar/pegar y su explicacion.

## Setup

```bash
# Verificar instalacion
frida --version  # 17.15.3+
adb devices      # Debe mostrar el dispositivo

# Ejecutar script contra app
frida -U -l script.js -f com.target.app
frida -U -l script.js com.target.app  # attach (sin spawn)
frida -U --codeshare akabe1/frida-multiple-unpinning -f com.target.app

# Mantener vivo en background
tail -f /dev/zero | frida -U -l script.js -f com.target.app
```

**Regla de oro:** `Java.perform()` envuelve TODO el codigo Java. `setTimeout` solo funciona dentro de `Java.perform()`. NUNCA hagas `return undefined` en un hook Java — usa `return arguments[0]`, `return ArrayList.$new()`, o el tipo de retorno esperado.

---

## 1. SSL/TLS Pinning Bypass Cookbook

Cada app usa una libreria distinta para SSL pinning. Aqui estan los hooks clasificados por libreria. **Usa todos simultaneamente** con `frida -U -l all_bypass.js`.

### 1.1 TrustManagerImpl — Android 7+ (el mas comun)

```javascript
Java.perform(function() {
    var TrustManagerImpl = Java.use('com.android.org.conscrypt.TrustManagerImpl');
    var ArrayList = Java.use("java.util.ArrayList");

    // checkTrustedRecursive — bypass principal
    TrustManagerImpl.checkTrustedRecursive.overloads.forEach(function(o) {
        o.implementation = function() {
            console.log('[+] TMI.checkTrustedRecursive bypassed');
            return ArrayList.$new();
        };
    });

    // verifyChain — capa adicional
    TrustManagerImpl.verifyChain.overloads.forEach(function(o) {
        o.implementation = function(untrustedChain) {
            console.log('[+] TMI.verifyChain bypassed');
            return untrustedChain;
        };
    });
});

// Para GMS (Google Mobile Services) — muchos Google apps usan su propio conscrypt
Java.perform(function() {
    try {
        var GMS_TMI = Java.use('com.google.android.gms.org.conscrypt.TrustManagerImpl');
        var ArrayList = Java.use("java.util.ArrayList");
        GMS_TMI.checkTrustedRecursive.overloads.forEach(function(o) {
            o.implementation = function() {
                console.log('[+] GMS TMI.checkTrustedRecursive bypassed');
                return ArrayList.$new();
            };
        });
        GMS_TMI.verifyChain.overloads.forEach(function(o) {
            o.implementation = function(chain) { return chain; };
        });
    } catch(e) { console.log('[-] GMS TrustManagerImpl not found'); }
});
```

### 1.2 OkHttp v3 — CertificatePinner (quadruple bypass)

```javascript
Java.perform(function() {
    var CertificatePinner = Java.use('okhttp3.CertificatePinner');

    // Overload 1: check(String, List<Certificate>)
    try {
        CertificatePinner.check.overload('java.lang.String', 'java.util.List').implementation = function(host, certs) {
            console.log('[+] OkHttp3: check bypassed for ' + host);
        };
    } catch(e) {}

    // Overload 2: check(String, Certificate) — deprecated
    try {
        CertificatePinner.check.overload('java.lang.String', 'java.security.cert.Certificate').implementation = function(h, c) {
            console.log('[+] OkHttp3(v2): check bypassed for ' + h);
        };
    } catch(e) {}

    // Overload 3: check(String, Certificate[])
    try {
        CertificatePinner.check.overload('java.lang.String', '[Ljava.security.cert.Certificate;').implementation = function(h, c) {
            console.log('[+] OkHttp3(v3): check bypassed for ' + h);
        };
    } catch(e) {}

    // Overload 4: check$okhttp (Kotlin)
    try {
        CertificatePinner.check$okhttp.overload('java.lang.String', 'kotlin.jvm.functions.Function0').implementation = function(h, f) {
            console.log('[+] OkHttp3(Kotlin): check bypassed for ' + h);
        };
    } catch(e) {}
});
```

### 1.3 SquareUp OkHttp v2 (obsoleto pero presente en apps legacy)

```javascript
Java.perform(function() {
    try {
        var SquarePinner = Java.use('com.squareup.okhttp.CertificatePinner');
        SquarePinner.check.overload('java.lang.String', 'java.security.cert.Certificate').implementation = function(){};
        SquarePinner.check.overload('java.lang.String', 'java.util.List').implementation = function(){};
        console.log('[+] SquareUp OkHttp v2 bypassed');
    } catch(e) {}
});
```

### 1.4 Cronet / Chromium (Google apps modernas)

```javascript
Java.perform(function() {
    try {
        var CronetEngine = Java.use('org.chromium.net.impl.CronetEngineBuilderImpl');
        CronetEngine.enablePublicKeyPinningBypassForLocalTrustAnchors.overload('boolean').implementation = function(a) {
            console.log('[+] Cronet: enablePublicKeyPinningBypassForLocalTrustAnchors called');
            return this.enablePublicKeyPinningBypassForLocalTrustAnchors(true);
        };
        CronetEngine.addPublicKeyPins.overload('java.lang.String', 'java.util.Set', 'boolean', 'java.util.Date').implementation = function(h, p, i, d) {
            console.log('[+] Cronet: addPublicKeyPins bypassed for ' + h);
            return this.addPublicKeyPins(h, p, i, d);
        };
    } catch(e) { console.log('[-] Cronet not found'); }
});
```

### 1.5 Conscrypt CertPinManager

```javascript
Java.perform(function() {
    try {
        var CertPinManager = Java.use('com.android.org.conscrypt.CertPinManager');
        CertPinManager.isChainValid.overload('java.lang.String', 'java.util.List').implementation = function(h, l) {
            console.log('[+] CertPinManager.isChainValid bypassed: ' + h);
            return true;
        };
        CertPinManager.checkChainPinning.overload('java.lang.String', 'java.util.List').implementation = function(h, l) {
            console.log('[+] CertPinManager.checkChainPinning bypassed: ' + h);
        };
    } catch(e) {}
});
```

### 1.6 TrustKit (Datatheorem)

```javascript
Java.perform(function() {
    try {
        var OkHostnameVerifier = Java.use('com.datatheorem.android.trustkit.pinning.OkHostnameVerifier');
        OkHostnameVerifier.verify.overloads.forEach(function(o) {
            o.implementation = function(h) {
                console.log('[+] TrustKit OkHostnameVerifier bypassed: ' + h);
                return true;
            };
        });
    } catch(e) {}

    try {
        var PinningTrustManager = Java.use('com.datatheorem.android.trustkit.pinning.PinningTrustManager');
        PinningTrustManager.checkServerTrusted.implementation = function(chain, authType) {
            console.log('[+] TrustKit PinningTrustManager bypassed');
        };
    } catch(e) {}
});
```

### 1.7 WebView — SSL Error Handler

```javascript
Java.perform(function() {
    // Android WebViewClient
    try {
        var wvc = Java.use('android.webkit.WebViewClient');
        wvc.onReceivedSslError.overload('android.webkit.WebView', 'android.webkit.SslErrorHandler', 'android.net.http.SslError').implementation = function(v, h, e) {
            console.log('[+] WebView SSL error bypassed, calling handler.proceed()');
            h.proceed();
        };
    } catch(e) {}

    // Cordova WebViewClient
    try {
        var cordova = Java.use('org.apache.cordova.CordovaWebViewClient');
        cordova.onReceivedSslError.overload('android.webkit.WebView', 'android.webkit.SslErrorHandler', 'android.net.http.SslError').implementation = function(v, h, e) {
            console.log('[+] Cordova WebView SSL error bypassed');
            h.proceed();
        };
    } catch(e) {}
});
```

### 1.8 Flutter SSL Pinning Packages

```javascript
Java.perform(function() {
    try {
        var HttpCP = Java.use('diefferson.http_certificate_pinning.HttpCertificatePinning');
        HttpCP.checkConnexion.overload("java.lang.String", "java.util.List", "java.util.Map", "int", "java.lang.String").implementation = function(h) {
            console.log('[+] Flutter HttpCertificatePinning bypassed: ' + h);
            return true;
        };
    } catch(e) {}
    try {
        var SslPP = Java.use('com.macif.plugin.sslpinningplugin.SslPinningPlugin');
        SslPP.checkConnexion.overload("java.lang.String", "java.util.List", "java.util.Map", "int", "java.lang.String").implementation = function(h) {
            console.log('[+] Flutter SslPinningPlugin bypassed: ' + h);
            return true;
        };
    } catch(e) {}
});
```

### 1.9 IBM WorkLight / MobileFirst

```javascript
Java.perform(function() {
    try {
        var WLClient = Java.use('com.worklight.wlclient.api.WLClient');
        WLClient.getInstance().pinTrustedCertificatePublicKey.overloads.forEach(function(o) {
            o.implementation = function(cert) {
                console.log('[+] WorkLight pinTrustedCertificatePublicKey bypassed');
            };
        });
    } catch(e) {}
    try {
        var HostVerifier = Java.use('com.worklight.wlclient.certificatepinning.HostNameVerifierWithCertificatePinning');
        HostVerifier.verify.overloads.forEach(function(o) {
            o.implementation = function(host) {
                console.log('[+] WorkLight HostNameVerifier bypassed: ' + host);
                return true;
            };
        });
    } catch(e) {}
});
```

### 1.10 Otros: Fabric, Netty, PhoneGap, Appcelerator

```javascript
Java.perform(function() {
    // Fabric
    try{Java.use('io.fabric.sdk.android.services.network.PinningTrustManager').checkServerTrusted.implementation=function(){console.log('[+] Fabric bypassed');};}catch(e){}
    // Netty
    try{Java.use('io.netty.handler.ssl.util.FingerprintTrustManagerFactory').checkTrusted.implementation=function(){console.log('[+] Netty bypassed');};}catch(e){}
    // PhoneGap
    try{Java.use('nl.xservices.plugins.sslCertificateChecker').execute.overload('java.lang.String','org.json.JSONArray','org.apache.cordova.CallbackContext').implementation=function(a,b,c){console.log('[+] PhoneGap bypassed: '+a);return true;};}catch(e){}
    // Appcelerator
    try{Java.use('appcelerator.https.PinningTrustManager').checkServerTrusted.implementation=function(){console.log('[+] Appcelerator bypassed');};}catch(e){}
    // Apache AbstractVerifier
    try{Java.use('org.apache.http.conn.ssl.AbstractVerifier').verify.overloads.forEach(function(o){o.implementation=function(h){console.log('[+] Apache AbstractVerifier bypassed: '+h);};});}catch(e){}
    // CWAC-Netsecurity
    try{Java.use('com.commonsware.cwac.netsecurity.conscrypt.CertPinManager').isChainValid.implementation=function(h){console.log('[+] CWAC bypassed: '+h);return true;};}catch(e){}
});
```

---

## 2. Root Detection Bypass Cookbook

Script completo que cubre 5 vectores de deteccion de root: archivos, comandos, paquetes, system properties, y Build.FINGERPRINT.

```javascript
// root_bypass_complete.js — Basado en HTTP Toolkit android-disable-root-detection.js

(function() {
    var loggedOnce = false;
    function logFirst() { if (!loggedOnce) { console.log("[Root] Detection blocked"); loggedOnce = true; } }

    var libc = Process.findModuleByName("libc.so");
    var rootPaths = [
        "/system/bin/su","/system/xbin/su","/sbin/su","/su/bin/su","/data/local/bin/su",
        "/data/local/xbin/su","/data/adb/magisk","/sbin/.magisk","/system/app/Superuser.apk",
        "/data/adb/ksu","/system/xbin/busybox","/system/app/Kinguser.apk"
    ];
    var rootPkgs = [
        "com.noshufou.android.su","eu.chainfire.supersu","com.koushikdutta.superuser",
        "com.dimonvideo.luckypatcher","com.topjohnwu.magisk","me.weishu.kernelsu"
    ];

    // 1. NATIVE: hook fopen, access, stat, lstat
    [ "fopen", "access", "stat", "lstat" ].forEach(function(fn) {
        var addr = libc.findExportByName(fn);
        if (!addr) return;
        Interceptor.attach(addr, {
            onEnter: function(args) { this.path = args[0].readUtf8String(); },
            onLeave: function(retval) {
                var p = (this.path||"").toLowerCase();
                var blocked = rootPaths.some(function(r) { return p.indexOf(r.slice(1).toLowerCase()) !== -1; });
                if (blocked || p.includes("magisk") || p.endsWith("/su")) {
                    if (fn === "fopen") retval.replace(ptr(0));
                    else retval.replace(ptr(-1));
                    logFirst();
                }
            }
        });
    });

    Java.perform(function() {
        var File = Java.use("java.io.File");
        // 2. JAVA: File.exists + length + FileInputStream
        var origExists = File.exists;
        File.exists.implementation = function() {
            var path = this.getAbsolutePath();
            if (rootPaths.indexOf(path) !== -1 || path.includes("magisk")) { logFirst(); return false; }
            return origExists.call(this);
        };
        var origLength = File.length;
        File.length.implementation = function() {
            var path = this.getAbsolutePath();
            if (rootPaths.indexOf(path) !== -1) { logFirst(); return 0; }
            return origLength.call(this);
        };
        try {
            var FIS = Java.use("java.io.FileInputStream");
            FIS.$init.overload('java.io.File').implementation = function(f) {
                if (rootPaths.indexOf(f.getAbsolutePath()) !== -1) {
                    logFirst(); throw Java.use("java.io.FileNotFoundException").$new(f.getAbsolutePath());
                }
                return this.$init(f);
            };
        } catch(e) {}

        // 3. BUILD: TAGS, TYPE, FINGERPRINT
        var Build = Java.use("android.os.Build");
        Build.TAGS.value = "release-keys";
        Build.TYPE.value = "user";
        try { Build.FINGERPRINT.value = Build.FINGERPRINT.value.replace(/(test-keys|dev-keys|userdebug)/, "release-keys").replace(/generic/, "google/raven/raven"); } catch(e) {}

        // 4. SYSTEM PROPERTIES: ro.debuggable=0, ro.secure=1
        var spg = libc.findExportByName("__system_property_get");
        if (spg) {
            Interceptor.attach(spg, {
                onEnter: function(args) { this.key = args[0].readCString(); this.ret = args[1]; },
                onLeave: function() {
                    var props = {"ro.debuggable":"0","ro.secure":"1","ro.build.tags":"release-keys"};
                    if (props[this.key] !== undefined) {
                        var val = Memory.allocUtf8String(props[this.key]);
                        Memory.copy(this.ret, val, props[this.key].length + 1);
                        logFirst();
                    }
                }
            });
        }

        // 5. PACKAGES: getPackageInfo + getInstalledPackages
        var APM = Java.use("android.app.ApplicationPackageManager");
        APM.getPackageInfo.overload('java.lang.String', 'int').implementation = function(pkg, flags) {
            if (rootPkgs.indexOf(pkg) !== -1) { logFirst(); pkg = "invalid.nonexistent.pkg"; }
            return this.getPackageInfo(pkg, flags);
        };
        APM.getInstalledPackages.overload('int').implementation = function(flags) {
            var pkgs = this.getInstalledPackages(flags);
            var arr = Java.use("java.util.ArrayList").$new();
            var iter = pkgs.iterator();
            while (iter.hasNext()) {
                var pkg = iter.next();
                if (rootPkgs.indexOf(pkg.packageName.value) === -1) arr.add(pkg);
            }
            return arr;
        };

        // 6. COMMANDS: Runtime.exec + ProcessBuilder + ProcessImpl.start
        var Runtime = Java.use("java.lang.Runtime");
        Runtime.exec.overload("java.lang.String").implementation = function(cmd) {
            if (cmd && (cmd.indexOf("su") !== -1 || cmd.indexOf("magisk") !== -1 || cmd.indexOf("getprop") !== -1)) {
                logFirst();
                var IOException = Java.use("java.io.IOException");
                throw IOException.$new("Command not found");
            }
            return this.exec(cmd);
        };
        Runtime.exec.overload('[Ljava.lang.String;').implementation = function(cmdArray) {
            var cmd = cmdArray.length > 0 ? cmdArray[0] : "";
            if (cmd && (cmd === "su" || cmd === "which" || cmd.indexOf("magisk") !== -1)) {
                logFirst(); return this.exec([""]);
            }
            return this.exec(cmdArray);
        };

        try {
            var ProcessBuilder = Java.use("java.lang.ProcessBuilder");
            ProcessBuilder.command.overload('java.util.List').implementation = function(commands) {
                var arr = commands.toArray();
                if (arr.length > 0 && (arr[0].toString() === "su" || arr[0].toString().indexOf("magisk") !== -1)) {
                    logFirst(); return this.command(Java.use("java.util.Arrays").asList([""]));
                }
                return this.command(commands);
            };
        } catch(e) {}

        console.log("== Root detection bypass complete ==");
    });
})();
```

---

## 3. Anti-Frida / Anti-Debug Bypass

```javascript
// anti_frida_bypass.js
(function() {
    var libc = Process.findModuleByName("libc.so");

    // 1. Hook strstr para filtrar "frida", "gum", "agent", "linjector" en /proc/self/maps
    var strstr = libc.findExportByName("strstr");
    if (strstr) {
        Interceptor.attach(strstr, {
            onEnter: function(args) { this.needle = args[1].readCString(); },
            onLeave: function(retval) {
                if (this.needle && /frida|gum|agent|gadget|linjector|xposed/i.test(this.needle)) {
                    retval.replace(ptr(0)); // NULL = not found
                }
            }
        });
    }

    // 2. Hook ptrace(PTRACE_TRACEME) — evita bloqueo de attach
    var ptrace = Process.findModuleByName(null).findExportByName
        ? Module.findExportByName(null, "ptrace")
        : null;
    if (!ptrace) ptrace = libc.findExportByName("ptrace");
    if (ptrace) {
        Interceptor.attach(ptrace, {
            onLeave: function(retval) { retval.replace(0); }
        });
    }

    // 3. Android Debug.isDebuggerConnected + anti-suicide
    Java.perform(function() {
        try {
            var Debug = Java.use("android.os.Debug");
            Debug.isDebuggerConnected.implementation = function() { return false; };
        } catch(e) {}
        // Anti-suicide
        try { Java.use("java.lang.System").exit.implementation = function(c) {
            console.log("[Anti] System.exit(" + c + ") blocked");
        };} catch(e) {}
        try { Java.use("android.os.Process").killProcess.implementation = function(p) {
            console.log("[Anti] killProcess(" + p + ") blocked");
        };} catch(e) {}
    });
})();
```

---

## 4. Crypto Interception

```javascript
// crypto_intercept.js
Java.perform(function() {
    function bytesToHex(b) {
        var hex = [];
        for (var i = 0; i < b.length; i++) hex.push(("0"+(b[i]&0xFF).toString(16)).slice(-2));
        return hex.join("");
    }

    var Cipher = Java.use("javax.crypto.Cipher");
    Cipher.doFinal.overload("[B").implementation = function(input) {
        var algo = this.getAlgorithm();
        console.log("[Cipher] Algorithm: " + algo + " Input(" + input.length + "): " + bytesToHex(input));
        var result = this.doFinal(input);
        console.log("[Cipher] Output(" + result.length + "): " + bytesToHex(result));
        return result;
    };

    try {
        Cipher.doFinal.overload("[B", "int", "int").implementation = function(input, offset, len) {
            var algo = this.getAlgorithm();
            console.log("[Cipher] Algorithm: " + algo + " Input(" + len + ")");
            var result = this.doFinal(input, offset, len);
            console.log("[Cipher] Output(" + result.length + "): " + bytesToHex(result));
            return result;
        };
    } catch(e) {}

    var Mac = Java.use("javax.crypto.Mac");
    Mac.doFinal.overload("[B").implementation = function(input) {
        console.log("[HMAC] Algorithm: " + this.getAlgorithm() + " Input(" + input.length + "): " + bytesToHex(input));
        var result = this.doFinal(input);
        console.log("[HMAC] Output: " + bytesToHex(result));
        return result;
    };

    var MD = Java.use("java.security.MessageDigest");
    MD.digest.overload("[B").implementation = function(input) {
        console.log("[Hash] " + this.getAlgorithm() + " Input(" + input.length + ")");
        return this.digest(input);
    };

    // SecretKeySpec + IvParameterSpec (capturar claves)
    var SKS = Java.use("javax.crypto.spec.SecretKeySpec");
    SKS.$init.overload("[B", "java.lang.String").implementation = function(key, algo) {
        console.log("[KEY] Algorithm: " + algo + " Key(" + key.length + "): " + bytesToHex(key));
        return this.$init(key, algo);
    };
    var IV = Java.use("javax.crypto.spec.IvParameterSpec");
    IV.$init.overload("[B").implementation = function(iv) {
        console.log("[IV] " + bytesToHex(iv));
        return this.$init(iv);
    };
});
```

---

## 5. Network Interception — OkHttp3 Interceptor

Hookea toda request/response en OkHttp3 sin depender de proxy:

```javascript
// okhttp_interceptor.js
Java.perform(function() {
    var OkHttpClient = Java.use("okhttp3.OkHttpClient");
    var Builder = Java.use("okhttp3.OkHttpClient$Builder");
    var Interceptor = Java.use("okhttp3.Interceptor");

    var LoggingInterceptor = Java.registerClass({
        name: "com.frida.LoggingInterceptor",
        implements: [Interceptor],
        methods: {
            intercept: function(chain) {
                var request = chain.request();
                var url = request.url().toString();
                var method = request.method();
                var headers = request.headers().toString();
                console.log("[OkHttp] >>> " + method + " " + url);
                console.log("[OkHttp] Headers: " + headers);

                var requestBody = request.body();
                if (requestBody) {
                    var buffer = Java.use("okio.Buffer").$new();
                    requestBody.writeTo(buffer);
                    console.log("[OkHttp] Body: " + buffer.readUtf8());
                }

                var response = chain.proceed(request);
                var responseBody = response.body().string();
                console.log("[OkHttp] <<< " + response.code() + " Body(" + responseBody.length + "): " + responseBody.substring(0, 500));

                var MediaType = Java.use("okhttp3.MediaType");
                var ResponseBody = Java.use("okhttp3.ResponseBody");
                return response.newBuilder().body(ResponseBody.create(MediaType.parse("application/json"), responseBody)).build();
            }
        }
    });

    // Hook addInterceptor para inyectar nuestro interceptor
    Builder.addInterceptor.overload('okhttp3.Interceptor').implementation = function(interceptor) {
        console.log("[OkHttp] Interceptor added");
        return this.addInterceptor(interceptor);
    };
});
```

---

## 6. Native Connect Hook — Redirigir todo el trafico como VPN

Hookea `connect()` de libc para redirigir todos los sockets TCP a tu proxy. No requiere configurar proxy en el sistema. Basado en HTTP Toolkit `native-connect-hook.js`:

```javascript
// native_connect_hook.js — Configurar PROXY_HOST y PROXY_PORT antes
var PROXY_HOST = "127.0.0.1";
var PROXY_PORT = 8080;
var PROXY_HOST_BYTES = PROXY_HOST.split('.').map(function(p) { return parseInt(p, 10); });
var IGNORED_PORTS = [];

var libc = Process.findModuleByName("libc.so");
var connect = libc.findExportByName("connect");

Interceptor.attach(connect, {
    onEnter: function(args) {
        var fd = args[0].toInt32();
        var addrPtr = ptr(args[1]);
        var family = addrPtr.readU16();
        var port = ((addrPtr.add(2).readU8() << 8) | addrPtr.add(3).readU8());
        var sockType = Socket.type(fd);

        if (sockType === 'tcp' || sockType === 'tcp6') {
            if (port === PROXY_PORT) return; // ya es el proxy

            if (IGNORED_PORTS.indexOf(port) !== -1) return;

            // Guardar destino original (opcional, para SOCKS5)
            this.originalPort = port;
            this.originalAddr = addrPtr.add(4).readByteArray(sockType === 'tcp6' ? 16 : 4);

            // Sobreescribir destino con el proxy
            var portBytes = addrPtr.add(2);
            portBytes.writeU16(PROXY_PORT);
            addrPtr.add(4).writeByteArray(PROXY_HOST_BYTES);
            console.log("[Redirect] TCP " + fd + " -> " + PROXY_HOST + ":" + PROXY_PORT);
        }
    },
    onLeave: function(retval) {}
});

console.log("== Native connect hook active ==");
```

---

## 7. Flutter / Dart — BoringSSL Bypass

Flutter usa BoringSSL dentro de `libflutter.so`. No tiene simbolos exportados — hay que buscar patrones de bytes. Script oficial de HTTP Toolkit:

```bash
# Usar directamente desde HTTP Toolkit
frida -U \
  -l config.js \
  -l android/android-system-certificate-injection.js \
  -l android/android-disable-flutter-certificate-pinning.js \
  -f com.flutter.app
```

**Como funciona:** Escanea `libflutter.so` buscando las funciones:
- `dart::bin::SSLCertContext::CertificateCallback` (patron ARM64: `ff c3 00 d1 fe 57 01 a9...`)
- `X509_STORE_CTX_get_current_cert` (anclada a la anterior)
- `bssl::x509_to_buffer` + `i2d_X509` (para comparar el certificado contra nuestro CA)

Cuando el cert **no** pasa la validacion de BoringSSL, verifica si el DER del cert coincide con nuestro CA. Si coincide, fuerza `retval = 1` (aceptado).

---

## 8. Memory Scanning & CModule

```javascript
// memory_scan.js
Java.perform(function() {
    // Buscar string en memoria
    var results = Memory.scanSync(ptr("0x7000000000"), 0x10000000, "68 65 6c 6c 6f"); // "hello"
    results.forEach(function(r) {
        console.log("[Memory] Found at: " + r.address + " -> " + r.address.readCString());
    });

    // Buscar patron con wildcards
    var pattern = "48 8b ?? ?? 48 85 ?? 74 ?? e8 ?? ?? ?? ??";
    var wildcardResults = Memory.scanSync(Module.findBaseAddress("libtarget.so"), 0x100000, pattern);
    console.log("[Pattern] Found " + wildcardResults.length + " matches");
});

// CModule: hook nativo en C puro (mas rapido y stealthy)
var cm = new CModule(`
#include <gum/guminterceptor.h>
void on_enter(GumInvocationContext *ic) {
    // Acceder a argumentos nativos
    int fd = GPOINTER_TO_INT(gum_invocation_context_get_nth_argument(ic, 0));
    gum_invocation_context_get_nth_argument(ic, 1); // addr
}
void on_leave(GumInvocationContext *ic) {
    // Modificar retorno
    gum_invocation_context_replace_return_value(ic, gint_to_gpointer(0));
}
`);

var addr = Module.findExportByName("libc.so", "connect");
Interceptor.attach(addr, {
    onEnter: new NativeCallback(cm.on_enter, 'void', ['pointer']),
    onLeave: new NativeCallback(cm.on_leave, 'void', ['pointer'])
});
```

---

## 9. DexClassLoader Hook

```javascript
Java.perform(function() {
    var DexClassLoader = Java.use("dalvik.system.DexClassLoader");
    DexClassLoader.$init.implementation = function(dexPath, optDir, libPath, parent) {
        console.log("[DEX-LOAD] Loading: " + dexPath);
        return this.$init(dexPath, optDir, libPath, parent);
    };
    DexClassLoader.loadClass.implementation = function(name) {
        console.log("[DEX-CLASS] " + name);
        return this.loadClass(name);
    };

    // Hook PathClassLoader tambien (mas comun en apps modernas)
    var PathClassLoader = Java.use("dalvik.system.PathClassLoader");
    PathClassLoader.$init.overload('java.lang.String', 'java.lang.ClassLoader').implementation = function(path, parent) {
        console.log("[PATH-LOAD] " + path);
        return this.$init(path, parent);
    };
});
```

---

## 10. Anti-Suicide + Process Kill Prevention

```javascript
Java.perform(function() {
    var System = Java.use("java.lang.System");
    System.exit.implementation = function(code) {
        console.log("[!] BLOCKED System.exit(" + code + ")");
    };
    var Runtime = Java.use("java.lang.Runtime");
    Runtime.exit.implementation = function(code) {
        console.log("[!] BLOCKED Runtime.exit(" + code + ")");
    };
    var Process = Java.use("android.os.Process");
    Process.killProcess.implementation = function(pid) {
        console.log("[!] BLOCKED Process.killProcess(" + pid + ")");
    };
});
```

---

## 11. Objection (Comandos Esenciales)

```bash
objection -g com.app explore

# SSL Pinning
android sslpinning disable          # 5 capas automaticas

# Root Detection
android root disable                 # 7 checks automaticos

# Hooking
android hooking list classes
android hooking watch class com.app.SomeClass
android hooking watch method com.app.SomeClass.someMethod --dump-args --dump-return

# Intents
android intent launch_activity com.app.SomeActivity
android intent launch_service com.app.SomeService

# Storage
android keystore list
android clipboard monitor

# Memory
android heap search instances com.app.SomeClass
android heap execute js --eval "send(JSON.stringify(this.value));"
```

## 12. FLAG_SECURE Bypass

```javascript
// disable-flag-secure.js — permite screenshots/grabacion durante analisis
Java.perform(function () {
  var LayoutParams = Java.use("android.view.WindowManager$LayoutParams");
  var FLAG_SECURE = LayoutParams.FLAG_SECURE.value;
  var Window = Java.use("android.view.Window");
  var Activity = Java.use("android.app.Activity");

  function strip(value) { return value & (~FLAG_SECURE); }

  Window.setFlags.overload('int', 'int').implementation = function(flags, mask) {
    return this.setFlags.call(this, strip(flags), strip(mask));
  };
  Window.addFlags.implementation = function(flags) {
    return this.addFlags.call(this, strip(flags));
  };
  Activity.onResume.implementation = function() {
    this.onResume();
    var self = this;
    Java.scheduleOnMainThread(function() {
      try { self.getWindow().clearFlags(FLAG_SECURE); } catch(err) {}
    });
  };
});
```

---

## Troubleshooting

| Error | Solucion |
|---|---|
| `Java.perform()` never runs | Envolver TODO el codigo Java en `Java.perform(function() { ... })` |
| `setTimeout is not defined` | Solo usar `setTimeout` dentro de `Java.perform()` |
| Frida se cierra solo al hacer spawn | Usar `tail -f /dev/zero \| frida -U ...` |
| `TypeError: cannot read property 'overload'` | El metodo no existe con esa firma. Hacer catch y listar overloads validos. |
| Multiples sesiones de Frida | `frida-ps -U` y `kill $(pgrep frida)` en el dispositivo antes de re-attach |
| `return undefined` en hook Java | Java no acepta `undefined`. Usar `return arguments[0]`, `ArrayList.$new()`, o el tipo esperado |
| SSL pinning persiste | La app puede usar librerias no cubiertas. Probar con `--codeshare akabe1/frida-multiple-unpinning` |
| `SIGABRT` en JNI | Probablemente `return undefined` en un hook. Siempre retornar un valor del tipo correcto. |
| Dispositivo sin internet tras Frida | Usar skill `android-cleanup` para restaurar proxy/iptables/certs. |

---

## Referencias

- **Frida CodeShare:** https://codeshare.frida.re/browse
- **HTTP Toolkit Frida Scripts:** https://github.com/httptoolkit/frida-interception-and-unpinning
- **Frida Docs:** https://frida.re/docs/android/
- **Objection:** https://github.com/sensepost/objection
- **Medusa (90+ modulos Frida):** https://github.com/Ch0pin/medusa
- **Auto-Frida (automatizacion):** https://github.com/ommirkute/Auto-Frida
- **phantom-frida (stealth server):** https://github.com/TheQmaks/phantom-frida
- **clsdumper (DEX dump + anti-Frida):** https://github.com/TheQmaks/clsdumper
- **frida-ui (web UI):** https://github.com/adityatelange/frida-ui
- **frida-jdwp-loader (sin root):** https://github.com/frankheat/frida-jdwp-loader
- **Frida-Labs (ejercicios):** https://github.com/DERE-ad2001/Frida-Labs
- **Awesome Frida:** https://github.com/dweinstein/awesome-frida

### Skills relacionados

- **`hacktricks-reference`** — Indice completo de herramientas, tecnicas y cursos de HackTricks Wiki para Android.
- **`android-reverse-engineering`** — Triaje, analisis estatico, y contexto general de RE antes de instrumentar con Frida.
- **`apk-modding`** — Parcheo persistente (smali/nativo) para bypass que no requieren Frida en runtime.
- **`httptoolkit-android`** — HTTP Toolkit como alternativa grafica a Frida para captura de trafico.
- **`android-cleanup`** — Limpieza post-Frida (proxy, iptables, certs, Frida Gadget).
- **`flutter-reverse-engineering`** — Analisis profundo de Flutter/Dart; Frida para BoringSSL bypass.

---

## Changelog

- 2026-07-19 (v1): Creacion inicial. Consolidacion de scripts de Frida CodeShare (akabe1, dzonerzy, fadeevab, owen800q) y HTTP Toolkit (Tim Perry). SSL pinning (14 librerias), root bypass (5 vectores), anti-Frida, crypto intercept, OkHttp3 interceptor, native connect hook, Flutter BoringSSL, CModule, memory scanning, DexClassLoader, anti-suicide, Objection commands, troubleshooting.
