---
name: hacktricks-reference
description: >
  Indice ligero de enlaces externos para Android pentesting: HackTricks Wiki, bi0s CTF writeups, Flutter RE (rloura, SensePost, Blutter), laboratorios (DIVA, InsecureShop, OWASP UnCrackable), cursos (8kSec, HackTricks Training), comunidades (Reddit, Awesome Android RE). Use ONLY to discover tools/techniques not covered in specialized skills. No contiene scripts ni tecnicas — solo punteros.
---

# HackTricks Android Reference

Indice de recursos externos. Para tecnicas y scripts, consultar los skills especializados.

## Wikis y documentacion

- [OWASP MASTG v2.0.0 (Junio 2026)](https://mas.owasp.org/MASTG/) — Guia oficial OWASP: 80+ tecnicas documentadas (MASTG-TECH-0001 a 0174), tests por categoria MASVS, tools reference, best practices
- [OWASP MASTG GitHub](https://github.com/OWASP/mastg) — `techniques/android/`, `tests/android/`, `tools/android/`, `Crackmes/`
- [HackTricks Wiki — Android Pentesting](https://hacktricks.wiki/en/mobile-pentesting/android-app-pentesting/)
- [OWASP MASTG-TECH-0156 — Reverse Engineering Flutter](https://mas.owasp.org/MASTG/techniques/android/MASTG-TECH-0156/)

## Writeups y casos practicos

- [bi0s Pentest Blog](https://pentest.bi0s.in/blog/) — 50+ writeups Android CTF. Tecnicas extraidas en `android-ctf-writeups`
- [tinyhack — Reversing Flutter app by recompiling Flutter Engine](https://tinyhack.com/2021/03/07/reversing-a-flutter-app-by-recompiling-flutter-engine/)
- [SensePost — Intercepting HTTPS in Flutter with Frida (2025)](https://sensepost.com/blog/2025/intercepting-https-communication-in-flutter-going-full-hardcore-mode-with-frida/)
- [braincoke.fr — Android RE for Beginners: Frida](https://braincoke.fr/blog/2021/03/android-reverse-engineering-for-beginners-frida/)
- [HTTP Toolkit Blog — Android Reverse Engineering](https://httptoolkit.com/blog/android-reverse-engineering/)

## Flutter RE

- [rloura — Reverse Engineering Flutter for Android](https://rloura.wordpress.com/2020/12/04/reversing-flutter-for-android-wip/) — Fundacional: snapshot format, Doldrums
- [Blutter](https://github.com/worawit/blutter) — Flutter AOT, Dart VM reconstruction
- [Darter](https://github.com/mildsunrise/darter) — Flutter parser Dart 2.5
- [JEB Dart AOT plugin](https://www.pnfsoftware.com/blog/2022/06/)

## Laboratorios

| App | Practica |
|---|---|
| [DIVA](https://github.com/payatu/Damn-Vulnerable-Android-App) | Root, SQLi, insecure storage, IPC |
| [InsecureShop](https://github.com/hax0rgb/InsecureShop) | Deep links, WebViews, auth |
| [InsecureBankv2](https://github.com/dineshshetty/Android-InsecureBankv2) | Banking, auth, comms |
| [OWASP UnCrackable](https://github.com/OWASP/owasp-mstg/tree/master/Crackmes) | L1-L5 (Java→Kotlin) |
| [Frida-Labs](https://github.com/DERE-ad2001/Frida-Labs) | Ejercicios Frida |

## Cursos

- [8kSec Academy — Mobile & AI Security](https://academy.8ksec.io/)
- [HackTricks Training — ARTE/GRTE/AzRTE](https://hacktricks-training.com/courses/)
- [Cyber Helmets](https://cyberhelmets.com/courses/)

## Comunidades

- [Reddit r/ReverseEngineering](https://www.reddit.com/r/ReverseEngineering/)
- [Awesome Android RE](https://github.com/user1342/Awesome-Android-Reverse-Engineering)

## Ruta de aprendizaje

```
DIVA → InsecureShop → InsecureBankv2 → OWASP UnCrackable L1-L3
  → Frida Basics (braincoke.fr, Frida-Labs)
  → Ghidra Basics → JNI → ARM64
  → Flutter (rloura, OWASP MASTG-TECH-0156) → Blutter
```

---

## Skills relacionados

- **`android-ctf-writeups`** — 13 tecnicas extraidas de CTFs reales
- **`android-pentesting-checklist`** — Checklist estatico + dinamico + tecnicas avanzadas
- **`android-reverse-engineering`** — Triaje, SSL pinning, root bypass, Frida, MASTG
- **`frida-expert`** — Cookbook Frida (CodeShare + HTTP Toolkit)
- **`apk-modding`** — Parcheo smali/nativo, repackaging
- **`flutter-reverse-engineering`** — Flutter/Dart profundo

## Changelog

- 2026-07-19 (v2): Refactorizado como indice ligero. Checklist, tecnicas y CTF writeups extraidos a skills dedicados.
- 2026-07-19 (v1): Creacion inicial con todo el material consolidado.
