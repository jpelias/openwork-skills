---
name: android-cleanup
description: >
  Clean up an Android device after pentesting, reverse engineering, SSL interception,
  or Frida instrumentation sessions. Use when the device has no internet, apps won't
  load, browsers show blank pages, or traffic is still being redirected to a dead proxy.
  Covers: global proxy settings, iptables NAT, bind mounts, CA certificates,
  WebView command-line flags, Frida Gadget files, Magisk bypass modules, and SELinux.
---

# Android Cleanup Skill

## Purpose

Restore an Android device to a clean, usable state after pentesting, SSL interception,
Frida instrumentation, or reverse engineering sessions.

## ⚠️ The #1 Cause of "No Internet After Pentesting"

**`settings put global http_proxy` persists across reboots and is NOT cleaned automatically.**

Android's global HTTP proxy setting survives reboots. If it points to a dead proxy server,
every app that respects system proxy settings (Chrome, YouTube, Gmail, Vivaldi, most apps)
will fail to connect. Ping and root-level TCP still work, masking the real issue.

**Always check this first:**
```bash
adb shell settings list global | grep -i proxy
```

## Quick Diagnostic Flow

```
App without internet but ping works?
  → settings list global | grep -i proxy  →  global_http_proxy_host configured?
  → iptables -t nat -L -n                 →  DNAT/REDIRECT rules?
  → mount | grep bind                     →  Active CA bind mounts?
  → ls /data/local*/*command-line*        →  WebView flags injected?
  → ps -A | grep frida                    →  frida-server running?
  → ls /data/local/tmp/*gadget*            →  Frida Gadget present?
  → ls /data/local/tmp/*frida*             →  Frida server binaries?
  → ls /data/adb/modules/                  →  Magisk bypass modules?
  → getenforce                            →  SELinux Permissive?
```

## Cleanup Script (run in order)

### 1. Kill Frida server and gadget

```bash
# Kill frida-server if running
adb shell su -c "killall frida-server 2>/dev/null; killall frida-server-* 2>/dev/null"

# Remove Frida server binary itself (skill was missing this)
adb shell su -c "rm -f /data/local/tmp/frida-server /data/local/tmp/frida-server-*"

# Remove Frida Gadget (libgadget pattern + Objection-style uuid-named gadgets)
adb shell su -c "rm -f /data/local/tmp/libgadget.so /data/local/tmp/libgadget.config.so"
adb shell su -c "rm -f /data/local/tmp/frida-gadget-*.so /data/local/tmp/frida-gadget-*.config"
adb shell su -c "rm -f /data/local/tmp/libfrida-gadget*.so"
adb shell su -c "rm -rf /data/local/tmp/android-unpinner"

# Remove leftover Frida scripts and binaries
adb shell su -c "rm -f /data/local/tmp/frida_script.js /data/local/tmp/*.js"
adb shell su -c "rm -f /data/local/tmp/frida*"
```

### 2. Remove system-wide HTTP proxy (CRITICAL)

```bash
adb shell settings delete global global_http_proxy_host
adb shell settings delete global global_http_proxy_port
adb shell settings delete global global_http_proxy_exclusion_list
adb shell settings delete global global_proxy_pac_url
```

### 3. Flush iptables (all tables)

```bash
adb shell su -c "iptables -t nat -F"
adb shell su -c "iptables -t filter -F"
adb shell su -c "iptables -t mangle -F"
```

Also check for and delete custom chains left by pentesting tools:
```bash
# List non-system chains
adb shell su -c "iptables-save | grep -vE '^(#|:.*\[)' | grep -vE 'oem_|fw_|bw_|st_|tetherctrl_|routectrl_|wakeupctrl_|idletimer_'"

# Delete custom chains in all tables (repeat for each table if needed)
adb shell su -c "iptables -t nat -X 2>/dev/null; iptables -t filter -X 2>/dev/null; iptables -t mangle -X 2>/dev/null"
```

### 4. Unmount CA certificate bind mounts

```bash
# Find bind mounts on /system/etc/security/cacerts
adb shell su -c "mount | grep 'system/etc/security/cacerts' | while read line; do
  mp=\$(echo \$line | awk '{print \$3}')
  umount \"\$mp\" 2>/dev/null
done"
```

### 5. Remove proxy/VPN apps if installed by pentesting

```bash
# List suspicious apps
adb shell pm list packages | grep -iE 'proxy|vpn|tunnel|packet|capture|firewall|adguard'

# Check if any of these are pentesting artifacts and uninstall them:
# Common offenders: com.greenecomputing.linphone, capture.packet, app.greyshirts.sslcapture
# adb uninstall <package>
```

### 6. Remove WebView/Chrome command-line flags

```bash
# These files inject flags into WebView/Chrome
adb shell su -c "rm -f /data/local/tmp/webview-command-line \
  /data/local/tmp/android-webview-command-line \
  /data/local/tmp/content-shell-command-line \
  /data/local/tmp/chrome-command-line \
  /data/local/webview-command-line \
  /data/local/android-webview-command-line \
  /data/local/chrome-command-line \
  /data/local/content-shell-command-line"
```

### 7. Remove HTTP Toolkit artifacts

```bash
adb shell su -c "rm -rf /data/local/tmp/.httptoolkit"
adb shell su -c "rm -f /data/local/tmp/httptoolkit-ca.pem /data/local/tmp/httptoolkit-*.pem /data/local/tmp/mitm-*.pem"
adb shell su -c "rm -f /data/local/tmp/adirf-server*"
```

### 8. Clean up pentesting files from /sdcard

```bash
adb shell rm -f /sdcard/*.pcap /sdcard/*.pem /sdcard/*.cer /sdcard/*.der
adb shell rm -f /sdcard/mitm-der.cer /sdcard/htk-ca.der
adb shell rm -f /sdcard/hosts /sdcard/base.apk /sdcard/manager.apk
```

### 9. Remove Magisk modules that bypass security

Magisk modules can persist signature bypass, SELinux manipulation, or other hooks across reboots.
These are **not cleaned** by regular uninstall and can silently interfere with apps.

```bash
# List all installed Magisk modules
adb shell su -c "ls /data/adb/modules/"

# Known dangerous modules — remove them:
# sigbypass   → disables APK signature verification (breaks PairipCore, Play Integrity)
# sigspoof    → signature spoofing (same as sigbypass, alternative name)
# riru-*      → Riru/Xposed hooks
# zygisk-*    → Zygisk modules
adb shell su -c "rm -rf /data/adb/modules/sigbypass"
adb shell su -c "rm -rf /data/adb/modules/sigspoof"
adb shell su -c "rm -rf /data/adb/modules/riru_*"
```

**⚠️ After removing Magisk modules, a reboot is required.**

### 10. Restore SELinux to Enforcing

Pentesting tools often set SELinux to `Permissive` to bypass restrictions.
This should be restored to `Enforcing` for normal operation.

```bash
# Check current state
adb shell getenforce

# Restore to Enforcing if Permissive
adb shell su -c "setenforce 1"

# Verify
adb shell getenforce
```

**Note:** `setenforce 1` is temporary (until next reboot). For a permanent change,
ensure no Magisk module or init script is calling `setenforce 0`.

### 11. Verify cleanup

```bash
# Proxy settings must be empty
adb shell settings list global | grep -i proxy

# No DNAT/REDIRECT rules
adb shell su -c "iptables -t nat -L -n | grep -E 'DNAT|REDIRECT'"

# No bind mounts
adb shell su -c "mount | grep bind"

# No frida processes
adb shell su -c "ps -A | grep -i frida"

# No frida files
adb shell su -c "ls /data/local/tmp/*frida* /data/local/tmp/*gadget* 2>/dev/null"

# No command-line flag files
adb shell su -c "find /data/local /data/local/tmp -name '*command-line*' 2>/dev/null"

# No dangerous Magisk modules
adb shell su -c "ls /data/adb/modules/ | grep -iE 'sigbypass|sigspoof|riru|bypass|spoof'"

# SELinux must be Enforcing
adb shell getenforce
```

### 12. Reboot

```bash
adb reboot
```

## Post-Reboot Verification

```bash
# After device boots, launch Chrome and check it uses direct connections
adb shell am start -a android.intent.action.VIEW -d http://example.com
sleep 5
# Must be empty - no connections to proxy IP
adb shell su -c "cat /proc/net/tcp | grep ':1F90'"

# Test basic connectivity
adb shell ping -c 2 google.com
```

## Magisk DenyList Notes

If the DenyList was enabled during pentesting and is causing issues post-cleanup:

```bash
# Check status
adb shell su -c "cat /cache/magisk.log | grep -i deny"

# Disable if needed
adb shell su -c "magisk --denylist disable"

# Or re-enable with clean slate
adb shell su -c "magisk --denylist enable"
adb shell su -c "magisk --denylist rm <package>"
```

## Common Pitfalls

| Symptom | Root Cause | Fix |
|---|---|---|
| Most apps have no internet, ping works | `global_http_proxy` set to dead proxy | Delete global proxy settings |
| Chrome connects to 192.168.x.x:8080 | Proxy in Chrome profile or system settings | Step 2 + Step 6 |
| Apps crash on startup | Frida Gadget still injected | Step 1 |
| Browser shows blank page | WebView command-line flags | Step 6 |
| SSL errors in all apps | CA bind mount still active | Step 4 |
| Specific apps blocked from network | Magisk DenyList interfering | Magisk section |
| Network works but specific ports blocked | Leftover iptables rules | Step 3 |
| App silently fails (no crash, no error) | Magisk `sigbypass`/`sigspoof` module or Frida Gadget leftover | Steps 1 + 9 |
| `libpairipcore.so` crash / PairipCore fails | `sigbypass`/`sigspoof` hooking PackageManager | Step 9 |
| SELinux Permissive persists after reboot | Magisk module or init script calling `setenforce 0` | Step 10 + check `service.sh` |

## Base Directory

/home/usuario/Documentos/.opencode/skills/android-cleanup
