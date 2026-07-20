# Android Security Assessment Report Template
## Mobile Application Reverse Engineering / Pentest

> **Usage:** fill all sections. Remove lines that don't apply to the target.
> Save as: `reports/MASVS-<TargetApp>-<Date>.md`

---

## 1. Executive Summary

- **Application Name**: `com.example.target`
- **Version**: `X.Y.Z` (Build: `NNNNN`)
- **SHA-256 (base APK)**: `aabbccdd...`
- **Source**: Play Store / APKMirror / Client-provided / Device extraction
- **Date**: `YYYY-MM-DD`
- **Analyst**: `[Name]`
- **Device**: Android `NN` (`API NN`), Magisk/KernelSU, rooted ARM64
- **Scope**: Static analysis (jadx), Dynamic analysis (Frida + mitmproxy), Network interception

## 2. Findings Summary

| Count | Severity | Count |
|-------|----------|-------|
| Critical | 🔴 | `N` |
| High | 🟠 | `N` |
| Medium | 🟡 | `N` |
| Low | 🔵 | `N` |
| Info | ⚪ | `N` |

### Primary MASVS Categories Affected
- [ ] MASVS-STORAGE — Data Storage & Privacy
- [ ] MASVS-CRYPTO — Cryptography
- [ ] MASVS-AUTH — Authentication & Session Management
- [ ] MASVS-NETWORK — Network Communication
- [ ] MASVS-PLATFORM — Platform Interaction
- [ ] MASVS-CODE — Code Quality & Build Settings
- [ ] MASVS-RESILIENCE — Resilience Against Reverse Engineering

---

## 3. Findings (Individual)

### Finding MASVS-XXX.YYY — [Short Name]

| Field | Value |
|---|---|
| ID | `MASVS-NETWORK-001` |
| Category | `MASVS-NETWORK` |
| Severity | 🔴 Critical / 🟠 High / 🟡 Medium / 🔵 Low / ⚪ Info |
| CVSS 3.1 | `X.Y` |
| MASTG Test | `MSTG-NETWORK-002` |
| Status | `Open` / `Acknowledged` / `Mitigated` |

#### Description
What was found and why it matters.

#### Evidence
```
- Type: [screenshot / code snippet / mitmproxy flow / Frida log / adb command output]
- Location: [class/method/file/offset]
- Attached: [file name]
```

#### Proof of Concept
Steps to reproduce:
1. ...
2. ...
3. ...

#### Remediation
Specific, actionable fix.

#### References
- `https://owasp.org/...`

---

## 4. Technical Annex

### 4.1 Application Architecture
- **Pattern**: MVP / MVVM / Clean Architecture / Other
- **Frameworks**: OkHttp / Ktor / Cronet / Flutter / React Native / Unity IL2CPP / gRPC
- **Obfuscation**: ProGuard / R8 / DexGuard / StringFog / None
- **Dynamic Loading**: DexClassLoader / Dynamic Feature Module / None

### 4.2 Exported Components
| Type | Name | Exported | Permission | Risk |
|---|---|---|---|---|
| Activity | `...` | true/false | `...` | ... |
| Service | `...` | true/false | `...` | ... |
| Provider | `...` | true/false | `...` | ... |
| Receiver | `...` | true/false | `...` | ... |

### 4.3 Network Endpoints
| Method | Path | Protocol | Auth | Notes |
|---|---|---|---|---|
| `GET` | `/api/v1/...` | HTTPS | Bearer | Called from `X.java:NN` |
| `POST`| `/grpc.Service/Method`| gRPC | mTLS | Body: protobuf (see decode) |

### 4.4 Native Analysis (if applicable)
| Library | Address | Function | Action |
|---|---|---|---|
| `libnative.so` | `0xABCDEF00` | `verifySignature()` | Patched NOP → returns 1 |
| `libil2cpp.so` | `0x12345600` | `get_IsPremium()` | Patched → MOV W0,#1 ; RET |

### 4.5 Crypto Summary
- Algorithms found: [AES-GCM / AES-ECB / MD5 / SHA1 / ...]
- Key storage: [Hardcoded / Keystore / EncryptedSharedPrefs / Native memory]
- Weaknesses: [ECB mode, hardcoded IV, predictable key, etc.]

---

## 5. Evidence Annex

### Attachments Checklist
- [ ] `screenshots/` — jadx screenshots, mitmproxy flows, terminal output
- [ ] `captures/` — mitmproxy `.flows` files, tcpdump `.pcap`
- [ ] `scripts/` — Frida JS files used, with comments
- [ ] `patches/` — diff of patched smali / native .so
- [ ] `reports/mobsf/` — MobSF JSON report (if used)
- [ ] `decompiled/` — jadx output directory (or parts if large)
- [ ] `artifacts/` — extracted certs, keys, protobuf schemas, Il2CppDumper output

---

## 6. Methodology & Tools

| Phase | Tool(s) | Version | Notes |
|---|---|---|---|
| Triage | jadx, apktool, aapt | `1.5.1`, `2.7.0` | One-shot triage script |
| Static | jadx, Fernflower | `1.5.1` | Full decompile |
| Dynamic | Frida, Objection | `17.x`, `1.12.x` | SSL pinning, root, anti-Frida |
| Network | mitmproxy / HTTP Toolkit | `12.x` | native-connect-hook.js |
| Native | Ghidra / radare2 | `12.x` / `6.1.x` | ARM64 analysis, patching |
| Automation | MobSF (Docker) | `latest` | Preliminary scan |

---

## 7. Disclaimer

> This assessment was performed on the specific version(s) listed above. Results may
> not apply to other versions. All testing was done with explicit authorization or on
> applications owned by the analyst. Unauthorized testing against third-party services
> violates the Computer Fraud and Abuse Act (CFAA) and comparable laws worldwide.
