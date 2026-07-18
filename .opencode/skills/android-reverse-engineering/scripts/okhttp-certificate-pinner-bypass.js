/**
 * OkHttp CertificatePinner Bypass
 * Bloquea CertificatePinner.check() y evita que se configure en OkHttpClient.Builder.
 *
 * Uso: frida -U -f com.app -l okhttp-certificate-pinner-bypass.js
 */

Java.perform(function() {
    console.log('[+] OkHttp CertificatePinner Bypass');

    setTimeout(function() {
        // ============================================================
        // Bloquear CertificatePinner.check() — hacerlo no-op
        // ============================================================
        try {
            var cp = Java.use('okhttp3.CertificatePinner');
            var overloads = cp.check.overloads;
            overloads.forEach(function(o) {
                o.implementation = function() {
                    // No hacer nada — no lanzar excepción
                    return;
                };
            });
            console.log('[+] CertificatePinner.check → no-op (' +
                overloads.length + ' overloads)');
        } catch(e) {
            console.log('[-] CertificatePinner no disponible');
        }

        // ============================================================
        // Bloquear OkHttpClient.Builder.certificatePinner()
        // Evita que se configure ningún pin
        // ============================================================
        try {
            var builder = Java.use('okhttp3.OkHttpClient$Builder');
            builder.certificatePinner.overload('okhttp3.CertificatePinner')
                .implementation = function(pinner) {
                    console.log('[+] CertificatePinner BLOCKED in builder');
                    return this;  // No hacer nada, devolver builder sin cambios
                };
            console.log('[+] OkHttpClient.Builder.certificatePinner → blocked');
        } catch(e) {
            console.log('[-] Builder.certificatePinner no disponible');
        }

        console.log('[+] OKHTTP BYPASS COMPLETO');

    }, 500);
});
