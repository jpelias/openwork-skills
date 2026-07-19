---
name: docker-androidre
description: >
  Pipeline completo de Android RE usando el contenedor Docker cryptax/android-re (apkid, jadx, apktool, apkleaks, radare2, uber-apk-signer, baksmali, droidlysis, frida-server). Use para triaje automatizado, decompilacion, busqueda de secrets, y analisis nativo sin instalar herramientas en el host. Use ONLY when working with APK files and the android-retools container is available.
---

# Docker Android RE Pipeline

Contenedor `cryptax/android-re` con todas las herramientas de RE preinstaladas.

## Setup

```bash
docker pull cryptax/android-re:2024.02
docker run -d --name android-retools \
  -p 6022:22 -p 6900:5900 -p 6800:8000 \
  -v /tmp/retools:/workshop \
  cryptax/android-re:2024.02
```

**Acceso:**
```bash
ssh -p 6022 -X root@127.0.0.1   # SSH + X11 (pass: mypass)
vncviewer 127.0.0.1::6900       # VNC escritorio grafico
```

**Copiar archivos:**
```bash
docker cp app.apk android-retools:/workshop/app.apk       # host → container
docker cp android-retools:/tmp/jadx-out ./jadx-out        # container → host
```

---

## Pipeline completo

```bash
APK=/workshop/app.apk

# 1. Identificar protecciones
apkid $APK
# Output: anti-debug, anti-vm, compiler, packer, obfuscator

# 2. Metadatos del APK
aapt dump badging $APK | head -20
# Output: package, version, SDK, permissions, activities exportadas

# 3. Buscar secrets
apkleaks -f $APK
# Output: API keys, Firebase URLs, passwords, tokens

# 4. Decompilar Java
jadx -d /tmp/jadx-out/ $APK
find /tmp/jadx-out/ -name "*.java" | wc -l  # clases decompiladas

# 5. Decompilar Smali (para parcheo)
apktool d $APK -o /tmp/smali-out/

# 6. Analisis automatizado
cd /opt/droidlysis && python3 droidlysis.py --input $APK --output /tmp/report/

# 7. Strings
strings $APK | grep -iE 'api|key|secret|token|password|http'

# 8. Analisis nativo
unzip -p $APK lib/arm64-v8a/libnative.so > /tmp/libnative.so
r2 -A /tmp/libnative.so -c 'afl~JNI' -q  # funciones JNI

# 9. Firmar APK modificado
uber-apk-signer -a $APK --allowResign -o /tmp/signed/
```

---

## Herramientas dentro del container

| Herramienta | Uso | Path |
|---|---|---|
| **apkid** | Detectar compilador/packer/obfuscador | `apkid` |
| **jadx** | Decompilar DEX → Java | `/opt/jadx/bin/jadx` |
| **apktool** | Decompilar/compilar recursos + smali | `/opt/apktool/apktool` |
| **baksmali/smali** | DEX ↔ smali | `/opt/smali`, `/opt/baksmali` |
| **apkleaks** | Buscar secrets en APK | `apkleaks` |
| **radare2** | Analisis nativo (.so) | `/opt/radare2/bin/r2` |
| **androguard** | Analisis Python de APK | `androguard` |
| **dex2jar** | DEX → JAR | `/opt/dex-tools-v2.4/d2j-dex2jar.sh` |
| **uber-apk-signer** | Firmar APK (v1+v2+v3+v4) | `/opt/uber-apk-signer.jar` |
| **droidlysis** | Analisis automatizado | `/opt/droidlysis/droidlysis.py` |
| **jd-gui** | GUI Java decompiler | `/opt/jd-gui.jar` |
| **frida-server** | Servidor Frida para dispositivo | `/opt/frida-server-android-arm` |

---

## Casos de uso tipicos

### Triaje rapido de un APK desconocido
```bash
docker cp misteriosa.apk android-retools:/workshop/app.apk
docker exec android-retools bash -c 'apkid /workshop/app.apk && aapt dump badging /workshop/app.apk | head -10 && apkleaks -f /workshop/app.apk'
```

### Buscar que ofuscador usa
```bash
docker exec android-retools bash -c 'apkid /workshop/app.apk | grep compiler'
# Output: compiler : DexProtector, DexGuard, ProGuard/R8, etc.
```

### Extraer todas las URLs y endpoints
```bash
docker exec android-retools bash -c '
  jadx -d /tmp/jadx-out/ /workshop/app.apk 2>/dev/null
  grep -rn "http" /tmp/jadx-out/ | grep -oP "https?://[^\"<> ]+" | sort -u
'
```

### Encontrar claves hardcodeadas
```bash
docker exec android-retools bash -c '
  apkleaks -f /workshop/app.apk 2>/dev/null | grep -E "API_Key|Password|Secret|Token"
'
```

### Decompilar + abrir en GUI (VNC)
```bash
# Conectar por VNC: vncviewer 127.0.0.1::6900
# En el escritorio grafico:
jadx-gui /workshop/app.apk
# o
java -jar /opt/jd-gui.jar /workshop/jadx-out/
```

---

## Limpieza

```bash
docker stop android-retools && docker rm android-retools
```

## Troubleshooting

| Error | Solucion |
|---|---|
| `Permission denied` en /tmp/retools | Usar `docker cp` en vez de copia directa |
| jadx errores de decompilacion | Normal en APKs con ofuscacion avanzada. Usar smali/radare2 |
| droidlysis no encontrado | Ejecutar desde `/opt/droidlysis/` con Python |
| Out of memory | Aumentar memoria Docker: `docker run -m 4g ...` |

---

## Skills relacionados

- **`android-reverse-engineering`** — Metodologia RE, que buscar en cada capa
- **`apk-modding`** — Parcheo smali y reempaquetado (usa apktool + uber-apk-signer del container)
- **`frida-expert`** — Instrumentacion dinamica (complementa al container con Frida host)

## Changelog

- 2026-07-19 (v1): Creacion. Pipeline completo con cryptax/android-re:2024.02.
