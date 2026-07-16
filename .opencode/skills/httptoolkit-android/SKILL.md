---
name: httptoolkit-android
description: >
  Understand and troubleshoot HTTP Toolkit traffic interception on Android.
  Covers the real mechanism (Android VPN + Magisk tmpfs cert injection — not
  iptables, not Frida), why it breaks on certain apps (custom CA stores, mTLS),
  live investigation commands, real-time traffic analysis, and root vs non-root
  behavior. Use when HTTP Toolkit can't capture an app's traffic, the device
  has no internet after a session, or you need to know exactly what is happening.
---

# HTTP Toolkit on Android — Internals & Troubleshooting

Deep technical reference for how HTTP Toolkit intercepts Android traffic: the real mechanisms (reverse-engineered from source code and live sessions), why it breaks on certain apps, and how to fix them. Based on analysis of HTTP Toolkit v1.26.1 Pro on a rooted Android 10 device.

## Quick Decision Tree

```
Capturing Android traffic?
  ├─ Rooted device → HTTP Toolkit "Android via ADB" → works for most apps
  │   └─ Some apps break → check "Why Some Apps Fail" below
  ├─ Non-rooted device → cert goes to user store (Android 7+ ignores it)
  │   └─ VPN still works but can't decrypt HTTPS → effectively useless
  └─ Alternative → Frida native-connect-hook.js (see android-reverse-engineering)
```

## The Real Mechanism

HTTP Toolkit uses **three independent pieces** working together:

### 1. Android VPN Service (ProxyVpnService)

The Android companion app (`tech.httptoolkit.android.v1`) creates a system-level VPN using `android.net.VpnService`. This captures ALL TCP/IP traffic from the device and routes it to the desktop proxy.

**Key classes in the APK:**
- `ProxyVpnService` — extends `VpnService`, manages the VPN tunnel
- `ProxyVpnRunnable` — worker thread processing TCP packets (MTU 1500)
- `ProxyVpnRunnable` — logs show `TCP|169.254.x.x:port → 192.168.x.x:8001`

The VPN interface appears as `tun0` with a link-local IP (169.254.x.x).

### 2. Certificate Injection via Magisk tmpfs

HTTP Toolkit does **NOT** remount `/system`. Instead, it uses a `tmpfs` mount on top of `/system/etc/security/cacerts/`, preserving the original certs and adding its own. This is handled by a shell script pushed to the device:

```
mount -t tmpfs tmpfs /system/etc/security/cacerts
cp original-certs/* /system/etc/security/cacerts/
cp httptoolkit-ca.0 /system/etc/security/cacerts/
# On Android 14+: also bind-mount into /apex/com.android.conscrypt/cacerts
```

The cert appears in the Magisk tmpfs overlay, not directly in `/system`:
```
tmpfs on /system/etc/security/cacerts type tmpfs (rw,seclabel,relatime)
```

### 3. Desktop Proxy (Mockttp)

HTTP Toolkit uses its own proxy engine (**Mockttp**), not mitmproxy. Mockttp handles:
- The `/config` endpoint (returns `{"certificate":"<PEM>"}` to the Android app)
- TLS interception with certificate from `~/.config/httptoolkit/ca.pem`
- All HTTP/HTTPS traffic forwarding

The desktop GUI communicates with the Android app via **adbkit** (Node.js ADB library), sending the ACTIVATE intent with connection parameters.

### Complete Flow

```
┌─────────────────────────────────────────────────────────────────┐
│  Desktop (PC)                                                   │
│  ┌──────────┐   ADB    ┌────────────────┐                      │
│  │ Electron │─────────→│ Android App    │                      │
│  │ GUI      │ ACTIVATE │ (VPN Service)  │                      │
│  └──────────┘ intent   └───────┬────────┘                      │
│       │                        │                               │
│  ┌────▼──────┐          ┌──────▼────────┐                      │
│  │ Mockttp   │◄─────────│ VPN tunnel    │                      │
│  │ proxy     │   TCP    │ (tun0)        │                      │
│  │ :8001     │          │ 169.254.x.x   │                      │
│  └───────────┘          └───────────────┘                      │
│                                                          Android│
└─────────────────────────────────────────────────────────────────┘

App traffic → VPN captures → ADB/USB/WiFi tunnel → Mockttp proxy
Mockttp → MITM decrypt → re-encrypt with CA cert → back to app
App → verifies cert against tmpfs cacerts → TRUSTS ✅
```

## How the Desktop Communicates with the Android App

From the Pro source code (`android-adb-shared.ts`):

```typescript
// 1. Install cert via tmpfs (requires root or Shizuku)
await installSystemCertWithRoot(deviceClient, certContent);

// 2. Build setup params
const setupParams = {
    addresses: ["192.168.x.x"],     // PC IPs
    port: 8001,                      // proxy port
    localTunnelPort: 8001,           // ADB reverse tunnel port
    enableSocks: false,
    certFingerprint: "<SPKI hash>"   // from generateSPKIFingerprint()
};

// 3. Create ADB reverse tunnel
await adbClient.reverse('tcp:8001', 'tcp:8001');

// 4. Send ACTIVATE intent (requires INJECT_EVENTS permission,
//    handled by adbkit library)
await adbClient.startActivity({
    wait: true,
    action: 'tech.httptoolkit.android.ACTIVATE',
    data: 'https://android.httptoolkit.tech/connect/?data=<urlSafeBase64>'
});
```

The Android app receives this via `RemoteControlMainActivity`, parses the base64 JSON, connects to the proxy, downloads the certificate, verifies the SPKI fingerprint, and starts the VPN.

### Certificate Fingerprint

HTTP Toolkit uses **SPKI fingerprint** (SHA-256 of SubjectPublicKeyInfo), NOT the certificate fingerprint. Generated by Mockttp's `generateSPKIFingerprint()`:

```bash
# Get SPKI fingerprint from Mockttp
node -e "
const { generateSPKIFingerprint } = require('mockttp');
const fs = require('fs');
generateSPKIFingerprint(fs.readFileSync('cert.pem', 'utf8')).then(fp => console.log(fp));
"
```

### Protocol Between App and Proxy

The Android app validates the proxy by requesting through it:

```
1. App → HTTP proxy at address:port
2. GET http://android.httptoolkit.tech/config → expects {"certificate":"<PEM>"}
3. If /config fails → GET http://amiusing.httptoolkit.tech/certificate → expects raw PEM
4. App computes SPKI fingerprint, compares with expected value
5. Match → starts VPN with the validated ProxyConfig
```

## Verifying HTTP Toolkit Is Active

```bash
export PATH=$PATH:~/Android/Sdk/platform-tools

# 1. VPN interface present?
adb shell ip link show dev tun0            # Should exist

# 2. Certificate in Magisk tmpfs?
adb shell mount | grep "tmpfs.*cacerts"    # tmpfs on /system/etc/security/cacerts

# 3. ADB reverse tunnel active?
adb reverse --list                         # tcp:XXXX tcp:XXXX

# 4. Mockttp proxy listening on desktop?
ss -tlnp | grep -E "800[0-9]"

# 5. Android app running?
adb shell ps -A | grep httptoolkit

# 6. Full state snapshot:
echo "=== VPN ===" && adb shell ip link show dev tun0 2>/dev/null
echo "=== CERT ===" && adb shell mount | grep cacerts
echo "=== TUNNEL ===" && adb reverse --list
echo "=== PROXY ===" && ss -tlnp | grep -E "800[0-9]"
echo "=== APP ===" && adb shell ps -A | grep httptoolkit
```

## Real-Time Traffic Analysis

### Option A: HTTP Toolkit GUI (Limited)

The GUI buffers captured traffic in Electron's memory. No real-time access until you export the HAR. The internal API at port 28000-28001 provides server management (interceptors, config) but does **NOT** expose captured flows.

### Option B: mitmdump with -w Flag (Recommended)

Run mitmdump alongside HTTP Toolkit's proxy or standalone:

```bash
# Start mitmdump writing flows to disk in real-time
mitmdump --mode regular -p 8080 -w captura.flows &

# Agent reads flows as they arrive:
python3 -c "
from mitmproxy import io
with open('captura.flows', 'rb') as f:
    for flow in io.FlowReader(f).stream():
        print(f'{flow.request.method} {flow.request.pretty_url[:150]}')
"
```

### Option C: HTTP Toolkit Server API

The internal REST API (port 28000/28001) can activate interceptors programmatically:

```bash
# Requires auth token from the running process
TOKEN=$(cat /proc/$(pgrep -f httptoolkit-server)/environ | tr '\0' '\n' | grep HTK_SERVER_TOKEN | cut -d= -f2)
ORIGIN="https://app.httptoolkit.tech"

# List interceptors
curl -H "Origin: $ORIGIN" -H "Authorization: Bearer $TOKEN" \
  http://localhost:28000/interceptors

# Activate Android ADB interceptor (requires deviceId in POST body)
curl -X POST -H "Origin: $ORIGIN" -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"deviceId":"0123456789ABCDEF"}' \
  http://localhost:28000/interceptors/android-adb/activate/8001
```

## What Breaks and Why

### Apps with Custom CA Stores

Some apps bundle their own CA certificates and bypass Android's `TrustManager`.

**Detection:**
```bash
unzip -l base.apk | grep -iE '\.pem|\.crt|\.der|\.bks|ca-|trust|certif'
```

**Example — SmartLife/Tuya:**
```
assets/pem/AmazonRootCA1.pem     ← AWS IoT Core CAs (MQTT + mTLS)
assets/pem/AmazonRootCA2.pem
assets/pem/AmazonRootCA3.pem
assets/pem/AmazonRootCA4.pem
assets/pem/SFSRootCAG2.pem
```

The MQTT client builds its `SSLContext` from these bundled CAs. The system CA store is never consulted → HTTP Toolkit's injected cert is ignored.

**Solution:** Frida hook on MQTT's SSL context initialization.

### Apps Using Mutual TLS (mTLS)

**Detection:** `.p12`, `.pfx`, `.jks` files in app data.
**Solution:** Extract client cert, configure proxy as upstream.

### Apps Using QUIC (UDP/443)

YouTube and other Google apps use QUIC (UDP) which bypasses the TCP VPN tunnel.

**Symptom:** App traffic doesn't appear in capture.
**Fix:** Block QUIC to force TCP fallback:
```bash
adb shell su -c "iptables -A OUTPUT -p udp --dport 443 -j DROP"
```

### Non-Rooted Devices

The VPN still works (no root needed), but the certificate goes to the **user** trust store. Android 7+ ignores user CAs for apps targeting API 24+ → HTTPS traffic is captured but **encrypted** and unreadable.

**Workarounds:**
- Repack APK with `android:networkSecurityConfig` trusting user CAs
- Embed `frida-gadget` + `native-connect-hook.js`

## Common Misconceptions

| Myth | Reality |
|---|---|
| HTTP Toolkit uses Frida | **False.** The default interceptor (`android-adb`) uses VPN + cert injection only. Frida is a separate interceptor (`android-frida`). |
| HTTP Toolkit uses iptables | **False.** iptables DNAT rules you may see are from separate mitmproxy sessions, not HTTP Toolkit. |
| HTTP Toolkit sets a global proxy | **False.** `http_proxy` remains empty. VPN does the routing. |
| The cert is in /system directly | **False.** It's in a Magisk tmpfs overlay on top of `/system/etc/security/cacerts/`. |
| Closing GUI stops capture immediately | VPN may survive briefly, but the cert cleanup + proxy shutdown happens when Electron fully exits. |
| Works without root for all apps | **False.** VPN works without root, but HTTPS decryption requires the cert in the system trust store (needs root). |

## Live Investigation Playbook

```bash
export PATH=$PATH:~/Android/Sdk/platform-tools

echo "=== VPN ===" && adb shell ip link show dev tun0 2>/dev/null
echo "=== CERT (tmpfs) ===" && adb shell mount | grep "tmpfs.*cacerts"
echo "=== TUNNEL ===" && adb reverse --list
echo "=== PROXY ON PC ===" && ss -tlnp | grep -E "800[0-9]"
echo "=== ANDROID APP ===" && adb shell ps -A | grep httptoolkit
echo "=== FRIDA? ===" && adb shell ps -A | grep frida
echo "=== IPTABLES? ===" && adb shell su -c 'iptables -t nat -L OUTPUT -n' 2>/dev/null
echo "=== PROXY SETTING ===" && adb shell settings get global http_proxy
```

## Replacing the GUI with the CLI Server

The standalone server (`httptoolkit-server start`) can be controlled via its REST API to activate the Android ADB interceptor programmatically:

```bash
# Start the server
httptoolkit-server start --server-port 28000 --mockttp-port 8001 &

# Activate the interceptor (requires device ID)
curl -X POST \
  -H "Origin: https://app.httptoolkit.tech" \
  -H "Content-Type: application/json" \
  http://127.0.0.1:28000/interceptors/android-adb/activate/8001 \
  -d '{"deviceId":"<ADB_DEVICE_ID>"}'
```

This triggers: cert injection via tmpfs, ADB reverse tunnel creation, and ACTIVATE intent delivery.

**However**, the CLI server does **NOT** configure Mockttp's rule to intercept `android.httptoolkit.tech/config` (which returns the certificate to the app). That rule is only added by the Electron GUI when setting up interception through the UI. Without it, the app receives `403 Forbidden` when trying to validate the proxy.

**Result:** The CLI server activates the device (cert, tunnel, app intent) but the proxy won't accept the app's validation request, so no VPN is established. The GUI is currently required for a complete interception setup.

## See Also

- `android-reverse-engineering` skill — for Frida-based SSL pinning bypass
- `android-cleanup` skill — for removing leftover proxy settings and CA certs
