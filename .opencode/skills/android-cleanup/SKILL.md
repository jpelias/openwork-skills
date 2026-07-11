---
name: android-cleanup
description: >
  Clean up an Android device after pentesting, reverse engineering, SSL interception,
  or Frida instrumentation sessions. Use when the device has no internet, apps won't
  load, browsers show blank pages, or traffic is still being redirected to a dead proxy.
  Covers: global proxy settings, iptables NAT, bind mounts, CA certificates,
  WebView command-line flags, Frida Gadget, and Magisk DenyList.
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
¿App sin internet pero ping funciona?
  → settings list global | grep -i proxy  →  ¿global_http_proxy_host configurado?
  → iptables -t nat -L -n                 →  ¿reglas DNAT/REDIRECT?
  → mount | grep bind                     →  ¿bind mounts de CA activos?
  → ls /data/local*/*command-line*        →  ¿flags de WebView inyectados?
  → ps -A | grep frida                    →  ¿frida-server corriendo?
  → ls /data/local/tmp/libgadget*         →  ¿Frida Gadget presente?
```

## Cleanup Script (run in order)

### 1. Kill Frida server and gadget

```bash
# Kill frida-server if running
adb shell su -c "killall frida-server 2>/dev/null; killall frida-server-* 2>/dev/null"

# Remove Frida Gadget
adb shell su -c "rm -f /data/local/tmp/libgadget.so /data/local/tmp/libgadget.config.so"
adb shell su -c "rm -rf /data/local/tmp/android-unpinner"
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

Also check for custom chains left by pentesting tools:
```bash
adb shell su -c "iptables-save | grep -vE '^(#|:.*\[)' | grep -vE 'oem_|fw_|bw_|st_|tetherctrl_|routectrl_|wakeupctrl_|idletimer_'"
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

# Uninstall if needed
# adb uninstall <package>
```

### 6. Remove WebView/Chrome command-line flags

```bash
# These files inject flags into WebView/Chrome
adb shell su -c "rm -f /data/local/tmp/webview-command-line \
  /data/local/tmp/android-webview-command-line \
  /data/local/tmp/content-shell-command-line \
  /data/local/webview-command-line \
  /data/local/android-webview-command-line \
  /data/local/chrome-command-line \
  /data/local/content-shell-command-line"
```

### 7. Remove HTTP Toolkit artifacts

```bash
adb shell su -c "rm -rf /data/local/tmp/.httptoolkit"
adb shell su -c "rm -f /data/local/tmp/httptoolkit-ca.pem /data/local/tmp/*.pem"
adb shell su -c "rm -f /data/local/tmp/adirf-server*"
```

### 8. Clean up pentesting files from /sdcard

```bash
adb shell rm -f /sdcard/*.pcap /sdcard/*.pem /sdcard/*.cer /sdcard/*.der
adb shell rm -f /sdcard/mitm-der.cer /sdcard/htk-ca.der
adb shell rm -f /sdcard/hosts /sdcard/base.apk /sdcard/manager.apk
```

### 9. Verify cleanup

```bash
# Proxy settings must be empty
adb shell settings list global | grep -i proxy

# No DNAT/REDIRECT rules
adb shell su -c "iptables -t nat -L -n | grep -E 'DNAT|REDIRECT'"

# No bind mounts
adb shell su -c "mount | grep bind"

# No frida processes
adb shell su -c "ps -A | grep -i frida"

# No command-line flag files
adb shell su -c "find /data/local /data/local/tmp -name '*command-line*' 2>/dev/null"
```

### 10. Reboot

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

## Base Directory

/home/usuario/Documentos/.opencode/skills/android-cleanup
