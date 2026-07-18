// flutter_ssl_bypass.js — SSL pinning bypass para apps Flutter (BoringSSL en libflutter.so)
// Uso: frida -U -f com.example.app -l flutter_ssl_bypass.js --no-pause
//
// Flutter usa BoringSSL compilado dentro de libflutter.so, no el del sistema.
// Este script hookea las funciones de verificación SSL nativas.
// Autorizado: solo para auditorías con alcance firmado.

function tryHook(moduleName) {
    var mod = Process.findModuleByName(moduleName);
    if (!mod) return false;

    console.log("[*] Found " + moduleName + " at " + mod.base);

    // SSL_CTX_set_custom_verify — Flutter usa esta función para pinning
    var sslCtxSetCustomVerify = Module.findExportByName(moduleName, "SSL_CTX_set_custom_verify");
    if (sslCtxSetCustomVerify) {
        Interceptor.attach(sslCtxSetCustomVerify, {
            onEnter: function(args) {
                args[2] = NULL; // NULL callback = no custom verification
                console.log("[+] SSL_CTX_set_custom_verify bypassed in " + moduleName);
            }
        });
    }

    // SSL_set_custom_verify — variante por conexión
    var sslSetCustomVerify = Module.findExportByName(moduleName, "SSL_set_custom_verify");
    if (sslSetCustomVerify) {
        Interceptor.attach(sslSetCustomVerify, {
            onEnter: function(args) {
                args[2] = NULL;
                console.log("[+] SSL_set_custom_verify bypassed in " + moduleName);
            }
        });
    }

    // SSL_CTX_set_verify — verificación tradicional
    var sslCtxSetVerify = Module.findExportByName(moduleName, "SSL_CTX_set_verify");
    if (sslCtxSetVerify) {
        Interceptor.attach(sslCtxSetVerify, {
            onEnter: function(args) {
                args[1] = ptr(0); // SSL_VERIFY_NONE = 0
                console.log("[+] SSL_CTX_set_verify bypassed in " + moduleName);
            }
        });
    }

    // ssl_verify_cert_chain — verificación de cadena de certificados
    var sslVerifyCertChain = Module.findExportByName(moduleName, "ssl_verify_cert_chain");
    if (sslVerifyCertChain) {
        Interceptor.replace(sslVerifyCertChain, new NativeCallback(function(ssl, cert) {
            console.log("[+] ssl_verify_cert_chain bypassed in " + moduleName);
            return 1; // success
        }, "int", ["pointer", "pointer"]));
    }

    return true;
}

// Intentar en múltiples módulos posibles
var modules = [
    "libflutter.so",
    "libssl.so",
    "libcrypto.so",
    "libboringssl.so",
    "libcronet.so",
    "libsscronet.so"
];

var found = false;
modules.forEach(function(m) {
    if (tryHook(m)) found = true;
});

// Fallback: buscar en cualquier módulo
if (!found) {
    console.log("[*] Searching for SSL functions in all modules...");
    var sslCtxSetCustomVerify = Module.findExportByName(null, "SSL_CTX_set_custom_verify");
    if (sslCtxSetCustomVerify) {
        Interceptor.attach(sslCtxSetCustomVerify, {
            onEnter: function(args) {
                args[2] = NULL;
                console.log("[+] SSL_CTX_set_custom_verify bypassed (global)");
            }
        });
    }
}

console.log("[*] Flutter SSL bypass loaded");
