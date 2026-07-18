// hook_crypto.js — Intercepta operaciones criptográficas en Android
// Uso: frida -U -f com.example.app -l hook_crypto.js --no-pause
//
// Captura: Cipher.doFinal, Mac.doFinal, MessageDigest.digest, SecretKeySpec
// Autorizado: solo para auditorías con alcance firmado.

Java.perform(function() {
    console.log("[*] Crypto hook loaded");

    function bytesToHex(bytes) {
        var hex = [];
        for (var i = 0; i < bytes.length; i++) {
            hex.push(("0" + (bytes[i] & 0xFF).toString(16)).slice(-2));
        }
        return hex.join("");
    }

    function bytesToAscii(bytes) {
        var str = [];
        for (var i = 0; i < bytes.length; i++) {
            var b = bytes[i] & 0xFF;
            if (b >= 0x20 && b <= 0x7E) {
                str.push(String.fromCharCode(b));
            } else {
                str.push(".");
            }
        }
        return str.join("");
    }

    // === Cipher (AES, DES, RSA, etc.) ===
    try {
        var Cipher = Java.use("javax.crypto.Cipher");

        Cipher.doFinal.overload("[B").implementation = function(input) {
            var algo = this.getAlgorithm();
            var op = "?";
            try { op = this.getOpmode ? this.getOpmode() : "?"; } catch(e) {}
            console.log("\n[Cipher] Algorithm: " + algo + " | Op: " + op);
            console.log("[Cipher] Input  (" + input.length + "B): " + bytesToHex(input));
            console.log("[Cipher] Input  (ASCII): " + bytesToAscii(input));

            var result = this.doFinal(input);
            console.log("[Cipher] Output (" + result.length + "B): " + bytesToHex(result));
            console.log("[Cipher] Output (ASCII): " + bytesToAscii(result));
            return result;
        };

        Cipher.doFinal.overload("[B", "int", "int").implementation = function(input, offset, len) {
            var algo = this.getAlgorithm();
            console.log("[Cipher] " + algo + " doFinal(buf, " + offset + ", " + len + ")");
            return this.doFinal(input, offset, len);
        };
    } catch(e) {
        console.log("[!] Cipher hook failed: " + e);
    }

    // === Mac (HMAC) ===
    try {
        var Mac = Java.use("javax.crypto.Mac");
        Mac.doFinal.overload("[B").implementation = function(input) {
            var algo = this.getAlgorithm();
            console.log("\n[MAC] Algorithm: " + algo);
            console.log("[MAC] Input: " + bytesToHex(input));
            var result = this.doFinal(input);
            console.log("[MAC] Output: " + bytesToHex(result));
            return result;
        };
    } catch(e) {}

    // === MessageDigest (Hash: SHA-256, MD5, etc.) ===
    try {
        var MD = Java.use("java.security.MessageDigest");
        MD.digest.overload("[B").implementation = function(input) {
            var algo = this.getAlgorithm();
            console.log("\n[Hash] Algorithm: " + algo);
            console.log("[Hash] Input: " + bytesToHex(input));
            var result = this.digest(input);
            console.log("[Hash] Output: " + bytesToHex(result));
            return result;
        };

        MD.digest.overload().implementation = function() {
            var algo = this.getAlgorithm();
            var result = this.digest();
            console.log("[Hash] " + algo + " (no input): " + bytesToHex(result));
            return result;
        };
    } catch(e) {}

    // === SecretKeySpec (captura de claves) ===
    try {
        var SKS = Java.use("javax.crypto.spec.SecretKeySpec");
        SKS.$init.overload("[B", "java.lang.String").implementation = function(key, algo) {
            console.log("\n[SecretKey] Algorithm: " + algo);
            console.log("[SecretKey] Key (" + key.length + "B): " + bytesToHex(key));
            console.log("[SecretKey] Key (ASCII): " + bytesToAscii(key));
            return this.$init(key, algo);
        };
    } catch(e) {}

    // === IvParameterSpec (captura de IVs) ===
    try {
        var IV = Java.use("javax.crypto.spec.IvParameterSpec");
        IV.$init.overload("[B").implementation = function(iv) {
            console.log("[IV] (" + iv.length + "B): " + bytesToHex(iv));
            return this.$init(iv);
        };
    } catch(e) {}

    // === KeyGenerator (generación de claves) ===
    try {
        var KG = Java.use("javax.crypto.KeyGenerator");
        KG.generateKey.implementation = function() {
            var key = this.generateKey();
            console.log("[KeyGen] Generated key for: " + this.getAlgorithm());
            return key;
        };
    } catch(e) {}

    // === Android Keystore ===
    try {
        var KeyStore = Java.use("java.security.KeyStore");
        KeyStore.getKey.implementation = function(alias, password) {
            console.log("[Keystore] getKey: " + alias);
            return this.getKey(alias, password);
        };
    } catch(e) {}
});
