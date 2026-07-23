---
name: android-login-fix
description: Diagnose and fix Android apps that reject valid credentials on rooted devices. Covers Play Integrity bypass (Zygisk + PIF), Mediatek CTA socket blocking, debugger wait state, Chrome Custom Tabs dependency, and Magisk DenyList. Use when an app login fails with "wrong credentials", "something went wrong", or hangs on a rooted Android device.
---

# Android Login Fix on Rooted Devices

Systematic diagnosis and permanent fix for apps that reject login on rooted
Android devices. The root cause is almost always **Play Integrity** (Google's
device attestation), not filesystem root detection.

---

## Quick Checklist (in order)

1. `settings get global wait_for_debugger` — must be `0`
2. `settings get global debug_app` — must be empty
3. Chrome must be **enabled** (many apps use Custom Tabs for OAuth)
4. Magisk DenyList enforced + app added + Google Play Services added
5. Magisk Manager hidden/disabled
6. **Zygisk enabled + Play Integrity Fix module installed**
7. On Mediatek devices: CTA socket check bypassed

---

## 1. Debugger Wait State

**Symptom:** App hangs at startup, logcat shows `waiting for the debugger on port 8100`.

**Check:**
```bash
settings get global wait_for_debugger   # must be 0
settings get global debug_app           # must be empty
```

**Fix:**
```bash
settings put global wait_for_debugger 0
settings put global debug_app ""
am force-stop <package>
```

---

## 2. Chrome Disabled

**Symptom:** Login spinner forever, no network requests to app's servers.
Logcat shows no errors. App uses Chrome Custom Tabs for OAuth login.

**Check:**
```bash
pm list packages -d | grep chrome     # if Chrome appears here, it's disabled
dumpsys package com.android.chrome | grep enabled=
# enabled=1 or enabled=0 = OK. enabled=3 = DISABLED.
```

**Fix:**
```bash
su -c 'pm enable com.android.chrome'
# or: pm enable com.android.chrome  (if permissions allow)
```

---

## 3. Magisk DenyList + Manager

**Check:**
```bash
su -c 'magisk --denylist status'          # must say "enforced"
su -c 'magisk --denylist ls'              # must include the app
pm list packages | grep magisk            # should NOT appear (hidden)
```

**Fix:**
```bash
su -c 'magisk --denylist add <package>'
su -c 'magisk --denylist add com.google.android.gms com.google.android.gms.unstable'
su -c 'magisk --denylist add com.google.android.gsf'
su -c 'magisk --denylist enable'
su -c 'pm disable com.topjohnwu.magisk'
```

---

## 4. Zygisk + Play Integrity Fix (THE KEY FIX)

Most apps (Reddit, banking, streaming) use Play Integrity API via Google Play
Services to verify device integrity. Rooted devices fail this check even with
DenyList.

### 4.1 Enable Zygisk

Magisk 24+ required. Check version:
```bash
su -c 'magisk -c'
```

Enable Zygisk:
```bash
# Via SQLite
su -c 'magisk --sqlite "insert or replace into settings (key,value) values (\"zygisk\",\"1\")"'
# Or create flag file
su -c 'touch /data/adb/magisk/zygisk_enabled'
# Reboot required
su -c 'reboot'
```

Verify after reboot:
```bash
su -c 'grep -l zygisk /proc/*/maps' | head -1   # should find zygote process
```

### 4.2 Install Play Integrity Fix

Download latest from: https://github.com/osm0sis/PlayIntegrityFork/releases

```bash
# Push and install
adb push playintegrityfix.zip /data/local/tmp/
adb shell su -c 'magisk --install-module /data/local/tmp/playintegrityfix.zip'
# Reboot
adb shell su -c 'reboot'
```

After reboot, Google Play Services must be in DenyList (see section 3).

---

## 5. Mediatek CTA Socket Blocking

**Specific to Mediatek devices (UMIDIGI, etc.).**

**Symptom:** App has ZERO TCP connections (check with `cat /proc/net/tcp | grep <uid>`).
Logcat shows:
```
[socket]:check permission begin!
[socket] e:java.lang.ClassNotFoundException: com.mediatek.cta.CtaUtils
```
OkHttp `sendRequest>>` and `sendRequest<<` happen in the same millisecond
(request intercepted and dropped).

**Root cause:** Mediatek modified `framework.jar` intercepts all Java socket
creations and calls `com.mediatek.cta.CtaUtils`. If that class is missing,
sockets silently fail.

**Fix:** Provide the missing `CtaUtils` class via Magisk module.

### CtaUtils.java (stub)
```java
package com.mediatek.cta;
import android.content.Context;

public class CtaUtils {
    public static CtaUtils getInstance() { return new CtaUtils(); }
    public static CtaUtils getInstance(Context ctx) { return getInstance(); }
    public boolean checkPermission(Context ctx) { return true; }
    public boolean checkPermission(String p) { return true; }
    public boolean isCtaSupported() { return false; }
    public boolean isAllowed(String a) { return true; }
    public boolean isAllowed(Context c, String a) { return true; }
}
```

### Compile and package
```bash
# Compile to DEX
javac -source 1.8 -target 1.8 -bootclasspath $ANDROID_JAR -d build/ CtaUtils.java
$ANDROID_SDK/build-tools/30.0.3/d8 --lib $ANDROID_JAR --output build/ build/com/mediatek/cta/CtaUtils.class

# Create Magisk module
mkdir -p /data/adb/modules/cta_bypass/system/framework
cp build/classes.dex /data/adb/modules/cta_bypass/system/framework/mediatek-cta.jar

cat > /data/adb/modules/cta_bypass/module.prop << EOF
id=cta_bypass
name=CTA Fix
version=v1
versionCode=1
description=Stub com.mediatek.cta.CtaUtils
EOF

cat > /data/adb/modules/cta_bypass/system.prop << EOF
ro.vendor.mtk_cta_set=0
ro.mtk_cta_enable=0
persist.mtk_cta=0
persist.mtk_cta_support=0
EOF

# Reboot
```

---

## Verification

After all fixes applied, verify the app can make connections:
```bash
APP_UID=$(dumpsys package <pkg> | grep userId= | head -1 | sed 's/.*=//;s/ .*//')
su -c 'cat /proc/net/tcp' | awk -v u=$APP_UID '$8==u' | wc -l
# Must return > 0
```

Check Play Integrity (optional):
```bash
# Open Play Store, search "Play Integrity Checker", run it
# Should show: MEETS_BASIC_INTEGRITY, MEETS_DEVICE_INTEGRITY
```

---

## Common Pitfalls

| Symptom | Likely Cause |
|---|---|
| "Incorrect username/password" | Play Integrity failing (not credentials) |
| "Something went wrong" | Play Integrity or OAuth flow interrupted |
| Spinner forever, no network requests | Chrome disabled or CTA blocking |
| App pauses at startup | `wait_for_debugger` or `debug_app` set |
| OkHttp sendRequest instant (same ms) | CTA intercepting sockets |
| 0 TCP connections for app UID | CTA blocking on Mediatek |

---

## Session Example (Reddit on UMIDIGI BISON)

1. `wait_for_debugger=1` + `debug_app=com.reddit.frontpage` → cleared
2. Chrome disabled → enabled via `pm enable`
3. Magisk 30.7 had DenyList but no Zygisk → enabled Zygisk via SQLite
4. Play Integrity Fix module installed (osm0sis fork)
5. Google Play Services + GSF added to DenyList
6. Mediatek CTA: `CtaUtils` class missing → compiled stub, Magisk module  
7. Two reboots later: Reddit login successful

**Key insight:** The error message changed from "wrong credentials" to
"something went wrong" after fixing network/CTA — this confirmed the app was
now reaching Reddit's servers but failing Play Integrity. PIF + Zygisk was
the final fix.
