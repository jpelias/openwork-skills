/**
 * Conscrypt TrustManager Bypass
 * Hookea TODOS los métodos de verificación de certificados de Conscrypt.
 * Funciona en Android 7+ (API 24+).
 *
 * Uso: frida -U -f com.app -l conscrypt-trustmanager-bypass.js
 */

Java.perform(function() {
    console.log('[+] Conscrypt TrustManager Bypass');

    setTimeout(function() {
        try {
            var TMI = Java.use('com.android.org.conscrypt.TrustManagerImpl');
            var ArrayList = Java.use('java.util.ArrayList');
            var HashSet = Java.use('java.util.HashSet');

            // ============================================================
            // checkTrustedRecursive — método principal de validación
            // En Android 10, firma: (X509Certificate[], byte[], byte[], String, boolean, ...)
            // Devuelve List<X509Certificate> — NO devolver undefined
            // ============================================================
            try {
                TMI.checkTrustedRecursive.overloads.forEach(function(o) {
                    o.implementation = function() {
                        // Buscar primer argumento que sea lista y devolverlo
                        var args = Array.prototype.slice.call(arguments);
                        for (var i = 0; i < args.length; i++) {
                            if (args[i] !== null && args[i].size && args[i].size() > 0) {
                                return args[i];
                            }
                        }
                        return ArrayList.$new();
                    };
                });
                console.log('[+] checkTrustedRecursive → bypassed (' +
                    TMI.checkTrustedRecursive.overloads.length + ' overloads)');
            } catch(e) {
                console.log('[-] checkTrustedRecursive error: ' + e);
            }

            // ============================================================
            // verifyChain — método usado por Smart Life (Tuya)
            // En Android 10, firma: (List, List, String, boolean, byte[], byte[])
            // IMPORTANTE: no filtrar overloads — hookear TODOS
            // ============================================================
            try {
                TMI.verifyChain.overloads.forEach(function(o) {
                    var sig = o.toString();
                    o.implementation = function() {
                        var args = Array.prototype.slice.call(arguments);
                        // Devolver la cadena de certificados original (primer List)
                        for (var i = 0; i < args.length; i++) {
                            if (args[i] !== null && args[i].size !== undefined && args[i].size() > 0) {
                                return args[i];
                            }
                        }
                        return ArrayList.$new();
                    };
                });
                console.log('[+] verifyChain → bypassed (' +
                    TMI.verifyChain.overloads.length + ' overloads)');
            } catch(e) {
                console.log('[-] verifyChain error: ' + e);
            }

            // ============================================================
            // isCertTrusted → siempre true
            // ============================================================
            try {
                TMI.isCertTrusted.overloads.forEach(function(o) {
                    o.implementation = function() { return true; };
                });
                console.log('[+] isCertTrusted → true');
            } catch(e) {}

            console.log('[+] TRUSTMANAGER BYPASS COMPLETO');

        } catch(e) {
            console.log('[-] TrustManagerImpl no disponible: ' + e);
        }
    }, 300);
});
