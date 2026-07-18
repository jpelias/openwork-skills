/**
 * WebView SSL Bypass
 * Ignora errores SSL en WebView — necesario para apps con contenido web
 * (React Native, miniapps, paneles de dispositivos).
 *
 * Uso: frida -U -f com.app -l webview-ssl-bypass.js
 */

Java.perform(function() {
    console.log('[+] WebView SSL Bypass');

    setTimeout(function() {
        // ============================================================
        // WebViewClient.onReceivedSslError → handler.proceed()
        // Ignora TODOS los errores SSL en WebView
        // ============================================================
        try {
            var WebViewClient = Java.use('android.webkit.WebViewClient');
            WebViewClient.onReceivedSslError.overload(
                'android.webkit.WebView',
                'android.webkit.SslErrorHandler',
                'android.net.http.SslError'
            ).implementation = function(view, handler, error) {
                var primaryError = error.getPrimaryError();
                console.log('[+] WebView SSL error #' + primaryError + ' → proceed');
                handler.proceed();  // Continuar a pesar del error
            };
            console.log('[+] WebViewClient.onReceivedSslError → proceed()');
        } catch(e) {
            console.log('[-] WebViewClient error: ' + e);
        }

        // ============================================================
        // SslError.hasError → false
        // Previene que se reporten errores SSL
        // ============================================================
        try {
            var SslError = Java.use('android.net.http.SslError');
            SslError.hasError.overload('int').implementation = function(error) {
                return false;
            };
            console.log('[+] SslError.hasError → false');
        } catch(e) {
            console.log('[-] SslError error: ' + e);
        }

        // ============================================================
        // HostnameVerifier → siempre true
        // ============================================================
        try {
            var hv = Java.use('javax.net.ssl.HostnameVerifier');
            hv.verify.implementation = function(hostname, session) {
                return true;
            };
            console.log('[+] HostnameVerifier.verify → true');
        } catch(e) {
            console.log('[-] HostnameVerifier error: ' + e);
        }

        console.log('[+] WEBVIEW SSL BYPASS COMPLETO');

    }, 500);
});
