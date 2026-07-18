/**
 * Root Detection Bypass
 * Oculta root, Magisk, Frida, y herramientas de debugging.
 * Usar cuando la app crashea o niega funcionalidad al detectar root.
 *
 * Alternativa preferida: Magisk DenyList (más fiable y permanente)
 * Usar este script solo si Magisk DenyList no está disponible.
 *
 * Uso: frida -U -f com.app -l root-detection-bypass.js
 */

Java.perform(function() {
    console.log('[+] Root Detection Bypass');

    // ============================================================
    // 1. Build.TAGS → "release-keys" (no "test-keys")
    // ============================================================
    try {
        var Build = Java.use('android.os.Build');
        Build.TAGS.value = 'release-keys';
        console.log('[+] Build.TAGS → release-keys');
    } catch(e) {}

    // ============================================================
    // 2. File.exists → filtrar paths sospechosos
    // ============================================================
    try {
        var File = Java.use('java.io.File');
        var originalExists = File.exists.overload();
        File.exists.implementation = function() {
            var path = this.getAbsolutePath().toLowerCase();
            var blocked = ['su', 'magisk', 'frida', 'xposed', 'substrate',
                          'busybox', 'supersu', 'daemonsu'];
            for (var i = 0; i < blocked.length; i++) {
                if (path.indexOf(blocked[i]) >= 0) {
                    return false;
                }
            }
            return originalExists.call(this);
        };
        console.log('[+] File.exists → filtered');
    } catch(e) {}

    // ============================================================
    // 3. SystemProperties.get → filtrar propiedades de root
    // ============================================================
    try {
        var SystemProperties = Java.use('android.os.SystemProperties');
        if (SystemProperties.get.overloads.length > 0) {
            var originalGet = SystemProperties.get.overload(
                'java.lang.String', 'java.lang.String');
            originalGet.implementation = function(key, def) {
                if (key.indexOf('ro.debuggable') >= 0) return '0';
                if (key.indexOf('ro.secure') >= 0) return '1';
                if (key.indexOf('ro.build.tags') >= 0) return 'release-keys';
                if (key.indexOf('ro.build.type') >= 0) return 'user';
                return originalGet.call(this, key, def);
            };
            console.log('[+] SystemProperties.get → filtered');
        }
    } catch(e) {}

    // ============================================================
    // 4. Debug.isDebuggerConnected → false
    // ============================================================
    try {
        var Debug = Java.use('android.os.Debug');
        Debug.isDebuggerConnected.implementation = function() {
            return false;
        };
        console.log('[+] Debug.isDebuggerConnected → false');
    } catch(e) {}

    // ============================================================
    // 5. PackageManager → ocultar apps de root
    // ============================================================
    try {
        var PM = Java.use('android.app.ApplicationPackageManager');
        var originalGAI = PM.getApplicationInfo.overload(
            'java.lang.String', 'int');
        PM.getApplicationInfo.implementation = function(pkg, flags) {
            var blocked = ['magisk', 'supersu', 'de.robv.android.xposed',
                          'org.freeandroid.root', 'com.noshufou.android.su'];
            if (blocked.indexOf(pkg) >= 0) {
                throw Java.use('android.content.pm.PackageManager$NameNotFoundException')
                    .$new();
            }
            return originalGAI.call(this, pkg, flags);
        };
        console.log('[+] PackageManager → filtered');
    } catch(e) {}

    console.log('[+] ROOT DETECTION BYPASS COMPLETO');
});
