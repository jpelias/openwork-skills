# Foros y Comunidad — Android Modding & SSL Pinning (2024-2026)

## Comunidades más activas

| Comunidad | Enfoque | Actividad |
|---|---|---|
| **r/Magisk** | Root, ocultación, Play Integrity | Muy alta (varios hilos/día) |
| **XDA Developers** | Modding, módulos, herramientas | Alta |
| **r/Pentesting** | SSL bypass, Frida, setups | Alta |
| **r/androidroot** | Root, bypass detección, HttpCanary | Alta |
| **r/ReverseEngineering** | SSL system-wide, hooks, binarios | Media |
| **r/HowToHack** | APK modding, Frida, Flutter | Media |
| **r/bugbounty** | Mobile pentesting, Burp, pinning | Media |
| **4PDA** (ruso) | Módulos bancarios rusos, firmwares | Alta (requiere registro) |

---

## Herramientas NUEVAS (no cubiertas antes)

### eCapture — Captura TLS a nivel kernel
- Tecnología: **eBPF** (kernel ≥5.5)
- Captura tráfico TLS en claro **sin modificar la app**
- Sin Frida, sin proxy, sin root (solo kernel module)
- Alternativa emergente al SSL unpinning tradicional (XDA Ene 2026)

### KernelSU + susfs — Root sin Magisk
- Opera a nivel kernel, no inyecta en Zygote
- **Indetectable** por apps que buscan Zygisk
- `susfs` añade capacidades de ocultación adicionales
- Preferido sobre Magisk para banking apps (2025-2026)

### MT Manager / NP Manager
- Herramientas de modding APK **directamente en Android**
- Muy usadas en XDA y 4PDA
- Sucesoras de APK Easy Tool (descontinuado 2024)

### APK Toolkit v1.7
- Sucesor de APK Easy Tool en Windows
- GUI completa para decompilar/recompilar/firmar APKs

### TrickyStore + PlayIntegrityFork
- Tricky Store: suplanta keystore de hardware
- PlayIntegrityFork: reemplazo de Play Integrity Fix (descontinuado Jun 2025)
- Consiguen **MEETS_STRONG_INTEGRITY** con bootloader desbloqueado

---

## Técnicas novedosas de la comunidad

### Flutter + iptables (consenso 2025-2026)
La comunidad converge en que Flutter requiere iptables, no proxy:
```bash
# Instalar cert como system con MoveCertificates (Magisk)
# Redirigir tráfico con iptables
iptables -t nat -A OUTPUT -p tcp --dport 443 -j DNAT --to-destination <MITM_IP>:8080
```

### Magisk Alpha/Kitsune + NeoZygisk para STRONG integrity
Stack moderno para banking apps:
```
Kitsune Magisk + NeoZygisk + TrickyStore (keybox válido) + PlayIntegrityFork
```
Consigue STRONG_INTEGRITY con bootloader desbloqueado.

### LSPosed como vector de ataque (CloudSEK 2026)
- **Digital Lutera**: módulo LSPosed que inyecta SMS falsos, suplanta IMSI
- APK original intacto (firma válida) — indetectable por Play Protect
- C2 vía Socket.IO en tiempo real
- Objetivo: sistemas de pago con SIM-binding

---

## Stack moderno anti-detección (XDA 2025-2026)

```
KernelSU-Next / APatch (evitar Zygisk)
├── PlayIntegrityFix [Inject] (KOWX712)
├── TEESimulator RS v6.0.1  
├── Tricky Store v1.4.1
├── Zygisk Next / NeoZygisk (solo si necesario)
├── HMA-OSS (Hide My Applist)
└── KSUWebUI Standalone (configuración)
```

---

## Herramientas por categoría (consenso comunidad)

| Categoría | #1 | #2 | #3 |
|---|---|---|---|
| Proxy/MITM | mitmproxy | Burp Suite | HTTP Toolkit |
| Bypass SSL | Frida scripts | objection | apk-mitm |
| Análisis estático | jadx-gui | MobSF | Ghidra |
| Instrumentación | Frida | Objection | fridump |
| Root/Módulos | Magisk Alpha | KernelSU | TrickyStore |
| Emuladores | AVD + rootAVD | Genymotion | Corellium (iOS) |
| Modding APK | MT Manager | APK Toolkit | APKLab (VSCode) |
| Stealth Frida | phantom-frida | fridare | Auto-Frida |
