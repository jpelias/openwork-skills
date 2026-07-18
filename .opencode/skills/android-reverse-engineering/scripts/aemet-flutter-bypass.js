/**
 * AEMET Flutter Bypass
 * Para apps Flutter que usan BoringSSL + Cronet.
 * NO necesitan Conscrypt hooks porque Flutter no usa Java SSL.
 *
 * Uso: frida -U -f es.aemet -l aemet-flutter-bypass.js --no-pause
 * Requiere: mitmdump --mode regular --listen-port 8080
 *           Certificado CA en sistema (/system/etc/security/cacerts/)
 */

// Configuración del proxy (ajustar IP)
var PROXY_HOST = '192.168.1.187';
var PROXY_PORT = 8080;

Java.perform(function() {
    console.log('[+] AEMET Flutter Bypass iniciado');

    // 1. Forzar proxy del sistema
    setTimeout(function() {
        try {
            // System.setProperty para proxy HTTP
            var System = Java.use('java.lang.System');
            System.setProperty('http.proxyHost', PROXY_HOST);
            System.setProperty('http.proxyPort', String(PROXY_PORT));
            System.setProperty('https.proxyHost', PROXY_HOST);
            System.setProperty('https.proxyPort', String(PROXY_PORT));
            console.log('[+] System proxy properties set');
        } catch(e) { console.log('[-] System properties error: ' + e); }

        // Android settings proxy
        try {
            var Settings = Java.use('android.provider.Settings');
            var Global = Settings.Global;
            var uri = Java.use('android.net.Uri');
            // Settings.Global.putString via content resolver
            console.log('[+] Proxy override via System properties');
        } catch(e) {}
    }, 500);
});

// 2. HostnameVerifier → confiar siempre
Java.perform(function() {
    setTimeout(function() {
        try {
            var hv = Java.use('javax.net.ssl.HostnameVerifier');
            hv.verify.implementation = function() { return true; };
            console.log('[+] HostnameVerifier → true');
        } catch(e) {}
    }, 1000);
});

// 3. Hooks nativos BoringSSL (por si acaso Flutter intenta validar)
setTimeout(function() {
    var fn = Module.findExportByName('libssl.so', 'SSL_CTX_set_verify');
    if (fn) {
        Interceptor.attach(fn, {
            onEnter: function(args) { args[1] = ptr(0); }
        });
        console.log('[+] BoringSSL SSL_CTX_set_verify → SSL_VERIFY_NONE');
    }
}, 1500);

console.log('[+] AEMET Flutter Bypass completo');
