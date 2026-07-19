---
name: docker-androidre
description: >
  Complete Android RE pipeline using the Docker container cryptax/android-re (apkid, jadx, apktool, apkleaks, radare2, uber-apk-signer, baksmali, droidlysis, frida-server). Use for automated triage, decompilation, secret hunting, and native analysis without installing tools on the host. Use ONLY when working with APK files and the android-retools container is available.
---

# Docker Android RE Pipeline

Container `cryptax/android-re` with all RE tools preinstalled.

## Setup

```bash
docker pull cryptax/android-re:2024.02
docker run -d --name android-retools \
  -p 6022:22 -p 6900:5900 -p 6800:8000 \
  -v /tmp/retools:/workshop \
  cryptax/android-re:2024.02
```

**Access:**
```bash
ssh -p 6022 -X root@127.0.0.1   # SSH + X11 (pass: mypass)
vncviewer 127.0.0.1::6900       # VNC graphical desktop
```

**Copy files:**
```bash
docker cp app.apk android-retools:/workshop/app.apk       # host → container
docker cp android-retools:/tmp/jadx-out ./jadx-out        # container → host
```

---

## Complete pipeline

```bash
APK=/workshop/app.apk

# 1. Identify protections
apkid $APK
# Output: anti-debug, anti-vm, compiler, packer, obfuscator

# 2. APK metadata
aapt dump badging $APK | head -20
# Output: package, version, SDK, permissions, exported activities

# 3. Search for secrets
apkleaks -f $APK
# Output: API keys, Firebase URLs, passwords, tokens

# 4. Decompile Java
jadx -d /tmp/jadx-out/ $APK
find /tmp/jadx-out/ -name "*.java" | wc -l  # decompiled classes

# 5. Decompile Smali (for patching)
apktool d $APK -o /tmp/smali-out/

# 6. Automated analysis
cd /opt/droidlysis && python3 droidlysis.py --input $APK --output /tmp/report/

# 7. Strings
strings $APK | grep -iE 'api|key|secret|token|password|http'

# 8. Native analysis
unzip -p $APK lib/arm64-v8a/libnative.so > /tmp/libnative.so
r2 -A /tmp/libnative.so -c 'afl~JNI' -q  # JNI functions

# 9. Sign modified APK
uber-apk-signer -a $APK --allowResign -o /tmp/signed/
```

---

## Tools inside the container

| Tool | Usage | Path |
|---|---|---|
| **apkid** | Detect compiler/packer/obfuscator | `apkid` |
| **jadx** | Decompile DEX → Java | `/opt/jadx/bin/jadx` |
| **apktool** | Decompile/compile resources + smali | `/opt/apktool/apktool` |
| **baksmali/smali** | DEX ↔ smali | `/opt/smali`, `/opt/baksmali` |
| **apkleaks** | Search for secrets in APK | `apkleaks` |
| **radare2** | Native analysis (.so) | `/opt/radare2/bin/r2` |
| **androguard** | Python analysis of APK | `androguard` |
| **dex2jar** | DEX → JAR | `/opt/dex-tools-v2.4/d2j-dex2jar.sh` |
| **uber-apk-signer** | Sign APK (v1+v2+v3+v4) | `/opt/uber-apk-signer.jar` |
| **droidlysis** | Automated analysis | `/opt/droidlysis/droidlysis.py` |
| **jd-gui** | GUI Java decompiler | `/opt/jd-gui.jar` |
| **frida-server** | Frida server for device | `/opt/frida-server-android-arm` |

---

## Typical use cases

### Quick triage of an unknown APK
```bash
docker cp mysterious.apk android-retools:/workshop/app.apk
docker exec android-retools bash -c 'apkid /workshop/app.apk && aapt dump badging /workshop/app.apk | head -10 && apkleaks -f /workshop/app.apk'
```

### Find which obfuscator it uses
```bash
docker exec android-retools bash -c 'apkid /workshop/app.apk | grep compiler'
# Output: compiler : DexProtector, DexGuard, ProGuard/R8, etc.
```

### Extract all URLs and endpoints
```bash
docker exec android-retools bash -c '
  jadx -d /tmp/jadx-out/ /workshop/app.apk 2>/dev/null
  grep -rn "http" /tmp/jadx-out/ | grep -oP "https?://[^\"<> ]+" | sort -u
'
```

### Find hardcoded keys
```bash
docker exec android-retools bash -c '
  apkleaks -f /workshop/app.apk 2>/dev/null | grep -E "API_Key|Password|Secret|Token"
'
```

### Decompile + open in GUI (VNC)
```bash
# Connect via VNC: vncviewer 127.0.0.1::6900
# On the graphical desktop:
jadx-gui /workshop/app.apk
# or
java -jar /opt/jd-gui.jar /workshop/jadx-out/
```

---

## Cleanup

```bash
docker stop android-retools && docker rm android-retools
```

## Troubleshooting

| Error | Solution |
|---|---|
| `Permission denied` in /tmp/retools | Use `docker cp` instead of direct copy |
| jadx decompilation errors | Normal in APKs with advanced obfuscation. Use smali/radare2 |
| droidlysis not found | Run from `/opt/droidlysis/` with Python |
| Out of memory | Increase Docker memory: `docker run -m 4g ...` |

---

## Related skills

- **`android-reverse-engineering`** — RE methodology, what to look for at each layer
- **`apk-modding`** — Smali patching and repackaging (uses apktool + uber-apk-signer from the container)
- **`frida-expert`** — Dynamic instrumentation (complements the container with Frida host)

## Changelog

- 2026-07-19 (v1): Created. Complete pipeline with cryptax/android-re:2024.02.
