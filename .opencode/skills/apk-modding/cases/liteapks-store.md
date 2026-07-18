# Case: Liteapks Store — Self-protected app analysis

## App info

- **Package**: `com.liteapks.androidapps`
- **Version**: 1.0.18 (code 18)
- **APK**: 15MB, 1 DEX file (shell), 2 native libs, encrypted payload
- **Status**: Protected with same techniques the modder injects into other apps

## Protection structure

```
APK
├── classes.dex (shell only, 15 classes in com.liteapks.protect.runtime)
├── lib/arm64-v8a/libliteprotect.so (27KB)
├── assets/
│   ├── mbridge_download_dialog_view.xml ← Mintegral/MBridge ad SDK presence
│   └── r9fa1a6a25f4b85c4/r7240e8dfb23fb26d/
│       ├── rfcaf516adf0a5268.dat (9.3MB) ← encrypted main DEX
│       ├── r67f3024d763b8386.dat (3.1MB) ← encrypted secondary data
│       └── rc66b76c1de44ffed.dat (619 bytes) ← config/metadata
└── META-INF/
```

## How it loads

```
ShellApplication.onCreate()
  → Reads config from runtime/j.smali → runtime/h.smali
  → Gets real Application class name from config
  → Class.forName() to load it
  → Reflectively calls Application.attach(baseContext)
  → installDelegateApplication() replaces shell with real app
```

The real app: `com.liteapks.androidapps.MainApplication`

## Loaded classes (Frida enumeration)

### App classes (com.liteapks.androidapps.*)
- `MainApplication` — real Application (loaded from encrypted payload)
- `HomeActivity` — main activity
- UI: `PostVerticalView`, `PostCarousel`, `CategoryView`, `TabView`, `TitleView`, `Spacing8View`
- `DownloadForegroundService`, `DownloadState`
- Models: `ContentType`, `Type`

### Mintegral/MBridge ad SDK (com.mbridge.msdk.*)
- `config.manager.a` — config manager
- `tracker.f` — tracking
- `foundation.controller.a` — core controller
- `mbsignalcommon.commonwebview.c` — webview signals
- `dycreator.baseview.a` — ad creative view

### Protection shell (com.liteapks.protect.runtime.*)
- `ShellApplication` — proxy Application
- `EarlyInitProvider` — ContentProvider for early init
- Classes `a` through `l` — encrypted config handling, contains key material

## DEX loading

The decrypted DEX is loaded via `InMemoryDexClassLoader(ByteBuffer[], ClassLoader)`. The DEX never touches disk — only a 199-byte `.vdex` metadata file exists at:
```
/data/data/com.liteapks.androidapps/oat/arm64/Anonymous-DexFile@2100347524.vdex
```

## Dumping attempts (for rebuilding without shell)

| Method | Result |
|---|---|
| `frida-dexdump` | Found 22 DEX regions, largest 9.7MB. Failed: access violation on memory reads |
| `/proc/pid/mem` | Zero-filled at expected addresses (memory layout changed between process restarts) |
| `InMemoryDexClassLoader` hook | Constructor overload mismatch with Frida 17 Java bridge |
| `Java.choose` + reflection | Found instance but no accessible fields |
| Direct file copy | Only 199-byte .vdex (metadata, not DEX) |

**Conclusion for rebuilding**: The DEX CAN be extracted, but requires either:
- Debugging frida-dexdump for Frida 17.x compatibility
- Finding the decryption key in `libliteprotect.so` with Ghidra and decrypting the .dat files
- Using a different Frida version (16.x) where the Java bridge still works with `InMemoryDexClassLoader`

## Network analysis

| Domain/IP | Purpose | Blockable? |
|---|---|---|
| `104.26.15.14:443` (Cloudflare) | liteapks.com API | ❌ Would break the app |
| Mintegral/MBridge (hosts blocked) | Ads | ✅ Already blocked |

All 5 persistent connections go to Cloudflare CDN. No other ad/tracking domains detected in real-time traffic (possibly blocked by hosts file or not yet triggered).

## What's already blocked (hosts file)

| Category | Domains |
|---|---|
| Mintegral/MBridge | mintegral.com, api.mintegral.com, sdk.mintegral.com, mbridge.com, mobvsdk.com, mtg-*.mtgglobals.com |
| General tracking | TikTok, Meta/Facebook, Google Analytics, Criteo, Taboola, Outbrain, etc. |

## Key lessons

1. **The modder protects their own app** with the same shell + encrypted payload + native lib technique they inject into modded APKs
2. **InMemoryDexClassLoader** makes the DEX invisible to disk analysis — requires memory dumping
3. **frida-dexdump** needs debugging for Frida 17.x compatibility
4. **Network-level blocking** (hosts file) is the only viable defense without dumping the DEX
5. The app downloads APKs to `cache/apk_downloaded/` — found `Network_Analyzer_Pro_v4.0.1_-_Patched.apk`
