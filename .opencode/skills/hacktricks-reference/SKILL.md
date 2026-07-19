---
name: hacktricks-reference
description: >
  Lightweight index of external links for Android pentesting: HackTricks Wiki, bi0s CTF writeups, Flutter RE (rloura, SensePost, Blutter), labs (DIVA, InsecureShop, OWASP UnCrackable), courses (8kSec, HackTricks Training), communities (Reddit, Awesome Android RE). Use ONLY to discover tools/techniques not covered in specialized skills. Contains no scripts or techniques — only pointers.
---

# HackTricks Android Reference

Index of external resources. For techniques and scripts, consult the specialized skills.

## IoT / Tuya / Smart Life

- [tuya-sign-hacking (135⭐)](https://github.com/nalajcie/tuya-sign-hacking) — Reverse of the HMAC-SHA256 algorithm of the new Tuya API: BMP steganography with Gaussian elimination, native RE of `libjnimain.so`, Frida + Ghidra + gdb
- [jpelias/smartlife-reverse-engineering](https://github.com/jpelias/smartlife-reverse-engineering) — RE of Smart Life v7.9.0: SSL bypass, Frida, APIs
- [jpelias/tuya-local-panel](https://github.com/jpelias/tuya-local-panel) — Tuya local panel

## Featured repos (GitHub Topics)

From the topic [android-reverse-engineering](https://github.com/topics/android-reverse-engineering) (44 repos):

| Repo | ⭐ | Note |
|---|---|---|
| [ax/apk.sh](https://github.com/ax/apk.sh) | 3.8k | Automates pull/decode/rebuild/patch APK + Frida + Objection + split APK |
| [REAndroid/APKEditor](https://github.com/REAndroid/APKEditor) | 2.2k | APK editor without aapt/aapt2 dependency, merge splits |
| [LING71671/open-reverselab](https://github.com/LING71671/open-reverselab) | 852 | 197-article KB + MCP tools + CTF/APK/PE automation workflows |
| [zinja-coder/jadx-mcp-server](https://github.com/zinja-coder/jadx-mcp-server) | 706 | MCP server for JADX-AI — AI-assisted RE |
| [ImKKingshuk/LockKnife](https://github.com/ImKKingshuk/LockKnife) | 511 | TUI + CLI Android security tool with AI agent support |
| [Evil0ctal/AndroidReverse101](https://github.com/Evil0ctal/AndroidReverse101) | 350 | Systematic Android RE course (CN) |
| [Fausto-404/ai-mobile-reverse-skills](https://github.com/Fausto-404/ai-mobile-reverse-skills) | 118 | 6-phase skill with JADX/Burp/IDA/Ghidra MCP |
| [SyscallX-18113/Apkx-Hunter](https://github.com/SyscallX-18113/Apkx-Hunter) | 67 | Static analysis in C, 166 OWASP MASVS patterns, ML scoring |
| [argus-sight/BinSight](https://github.com/argus-sight/BinSight) | 31 | .so analysis via LLM+Capstone |
| [surendrajat/ApkStudio](https://github.com/surendrajat/ApkStudio) | 29 | Cross-platform IDE for Android RE |
| [ax/DEXPatch](https://github.com/ax/DEXPatch) | 15 | Inject System.loadLibrary() surgically into DEX |

- [OWASP MASTG v2.0.0 (June 2026)](https://mas.owasp.org/MASTG/) — Official OWASP guide: 80+ documented techniques (MASTG-TECH-0001 to 0174), tests by MASVS category, tools reference, best practices
- [OWASP MASTG GitHub](https://github.com/OWASP/mastg) — `techniques/android/`, `tests/android/`, `tools/android/`, `Crackmes/`
- [HackTricks Wiki — Android Pentesting](https://hacktricks.wiki/en/mobile-pentesting/android-app-pentesting/)
- [OWASP MASTG-TECH-0156 — Reverse Engineering Flutter](https://mas.owasp.org/MASTG/techniques/android/MASTG-TECH-0156/)

## Writeups and practical cases

- [bi0s Pentest Blog](https://pentest.bi0s.in/blog/) — 50+ Android CTF writeups. Techniques extracted in `android-ctf-writeups`
- [tinyhack — Reversing Flutter app by recompiling Flutter Engine](https://tinyhack.com/2021/03/07/reversing-a-flutter-app-by-recompiling-flutter-engine/)
- [SensePost — Intercepting HTTPS in Flutter with Frida (2025)](https://sensepost.com/blog/2025/intercepting-https-communication-in-flutter-going-full-hardcore-mode-with-frida/)
- [braincoke.fr — Android RE for Beginners: Frida](https://braincoke.fr/blog/2021/03/android-reverse-engineering-for-beginners-frida/)
- [HTTP Toolkit Blog — Android Reverse Engineering](https://httptoolkit.com/blog/android-reverse-engineering/)

## Flutter RE

- [rloura — Reverse Engineering Flutter for Android](https://rloura.wordpress.com/2020/12/04/reversing-flutter-for-android-wip/) — Foundational: snapshot format, Doldrums
- [Blutter](https://github.com/worawit/blutter) — Flutter AOT, Dart VM reconstruction
- [Darter](https://github.com/mildsunrise/darter) — Flutter parser Dart 2.5
- [JEB Dart AOT plugin](https://www.pnfsoftware.com/blog/2022/06/)

## Labs

| App | Practice |
|---|---|
| [DIVA](https://github.com/payatu/Damn-Vulnerable-Android-App) | Root, SQLi, insecure storage, IPC |
| [InsecureShop](https://github.com/hax0rgb/InsecureShop) | Deep links, WebViews, auth |
| [InsecureBankv2](https://github.com/dineshshetty/Android-InsecureBankv2) | Banking, auth, comms |
| [OWASP UnCrackable](https://github.com/OWASP/owasp-mstg/tree/master/Crackmes) | L1-L5 (Java→Kotlin) |
| [Frida-Labs](https://github.com/DERE-ad2001/Frida-Labs) | Frida exercises |

## Courses

- [8kSec Academy — Mobile & AI Security](https://academy.8ksec.io/)
- [HackTricks Training — ARTE/GRTE/AzRTE](https://hacktricks-training.com/courses/)
- [Cyber Helmets](https://cyberhelmets.com/courses/)

## Communities

- [Reddit r/ReverseEngineering](https://www.reddit.com/r/ReverseEngineering/)
- [Awesome Android RE](https://github.com/user1342/Awesome-Android-Reverse-Engineering)

## Learning path

```
DIVA → InsecureShop → InsecureBankv2 → OWASP UnCrackable L1-L3
  → Frida Basics (braincoke.fr, Frida-Labs)
  → Ghidra Basics → JNI → ARM64
  → Flutter (rloura, OWASP MASTG-TECH-0156) → Blutter
```

---

## Related skills

- **`android-ctf-writeups`** — 13 techniques extracted from real CTFs
- **`android-pentesting-checklist`** — Static + dynamic checklist + advanced techniques
- **`android-reverse-engineering`** — Triage, SSL pinning, root bypass, Frida, MASTG
- **`frida-expert`** — Frida cookbook (CodeShare + HTTP Toolkit)
- **`apk-modding`** — Smali/native patching, repackaging
- **`flutter-reverse-engineering`** — Deep Flutter/Dart

## Changelog

- 2026-07-19 (v2): Refactored as lightweight index. Checklist, techniques and CTF writeups extracted to dedicated skills.
- 2026-07-19 (v1): Initial creation with all consolidated material.
