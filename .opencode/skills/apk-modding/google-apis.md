## Google APIs (Maps, Places) & Signature Strategy

### The problem

Google Maps SDK for Android and Google Places SDK validate the API key on **Google's servers** by sending:
- `package_name` — from `AndroidManifest.xml`
- `cert_fingerprint` — SHA-1 of the APK signing certificate

If you re-sign the APK with `debug.keystore`, the fingerprint changes. Google rejects the API key.

**There is no client-side bypass.** The validation happens inside Google Play Services, not in the app.

### ⛔ PROHIBIDO: Crear APIs, registrarse en servicios, o usar navegador para consolas cloud

**NUNCA, bajo ninguna circunstancia, el agente debe:**

1. Crear una API key de Google (Maps, Places, Firebase, etc.)
2. Navegar a `console.cloud.google.com`, `console.firebase.google.com`, o similares
3. Registrarse, crear cuentas, o habilitar APIs en Google Cloud Platform
4. Usar el navegador para cualquier consola de administracion cloud
5. Hacer lo mismo con AWS, Azure, Mapbox, o cualquier otro proveedor de APIs cloud

**Motivo:** El agente no tiene capacidad de completar formularios web complejos (Angular Material, React), no puede resolver CAPTCHAs, no tiene metodo de pago, y no debe gastar tiempo en tareas imposibles. Ademas, el usuario NO quiere que se haga.

**Alternativas validas:**
- Usar APK original con firma valida + Frida en runtime
- Buscar keys unrestricted en APKs ya moddeadas (resources.arsc)
- Firmar con AOSP testkey si se encuentra una key compatible
- Reemplazar Google Maps con OSMDroid/tiles directos

### The solution: sign with AOSP testkey + find unrestricted API key

Modders use a well-known **AOSP testkey** (publicly available in the Android source tree) and embed an **unrestricted** Google API key (no SHA-1 restriction, or restricted only by package name) taken from another modded app.

#### Step A: Download the AOSP testkey

```bash
# Download from AOSP source (public)
curl -sL "https://android.googlesource.com/platform/build/+/master/target/product/security/testkey.pk8?format=TEXT" | base64 -d > /tmp/aosp_testkey.pk8
curl -sL "https://android.googlesource.com/platform/build/+/master/target/product/security/testkey.x509.pem?format=TEXT" | base64 -d > /tmp/aosp_testkey.x509.pem

# Convert to PKCS12 keystore for apksigner
openssl pkcs8 -in /tmp/aosp_testkey.pk8 -inform DER -out /tmp/aosp_testkey.pem -nocrypt
openssl pkcs12 -export -in /tmp/aosp_testkey.x509.pem -inkey /tmp/aosp_testkey.pem \
    -out /tmp/aosp_testkey.p12 -passout pass:android -name aosp
```

- SHA-1: `61ED377E85D386A8DFEE6B864BD85B0BFAA5AF81`
- Subject: `CN=Android, OU=Android, O=Android, L=Mountain View, ST=California, C=US`

#### Step B: Sign with AOSP testkey

```bash
# Keystore is cached at the skill directory:
#   .opencode/skills/apk-modding/aosp_testkey.p12  (password: android, alias: aosp)

apksigner sign --ks .opencode/skills/apk-modding/aosp_testkey.p12 \
    --ks-pass pass:android --ks-key-alias aosp --ks-type PKCS12 \
    --v1-signing-enabled true --v2-signing-enabled true \
    --out app_final.apk app_patched.apk
```

#### Step C: Find an unrestricted Google API key

Scan existing modded/cracked APKs in your collection for API keys:

```python
import zipfile, re, os, glob

for apk in glob.glob(os.path.expanduser("~/Descargas/*.apk")):
    try:
        with zipfile.ZipFile(apk) as z:
            keys = set()
            for fn in z.namelist():
                try:
                    data = z.read(fn)
                    for m in re.finditer(rb'AIza[\w-]{35}', data):
                        keys.add(m.group().decode())
                except: pass
            if keys:
                print(f"\n{os.path.basename(apk)}:")
                for k in sorted(keys): print(f"  {k}")
    except: pass
```

**How to pick the right key:** Look for keys in `resources.arsc` (not in `AndroidManifest.xml`) of modded apps. Resource keys are often unrestricted (the modder uses them for multiple apps with different package names). Manifest keys are typically restricted.

**Test each candidate:** Replace `com.google.android.geo.API_KEY` in the manifest and test. A working key shows NO `Authorization failure` or `INVALID_ARGUMENT` in logcat.

#### Step D: Replace the API key in the manifest

```bash
# Extract manifest from original APK
unzip -p app.apk AndroidManifest.xml > manifest_bin.xml

# Replace the key (binary XML, UTF-16-LE encoding)
python3 -c "
data = bytearray(open('manifest_bin.xml', 'rb').read())
old = 'ORIGINAL_KEY_39_CHARS'.encode('utf-16-le')
new = 'NEW_UNRESTRICTED_KEY'.encode('utf-16-le')
idx = data.find(old)
assert idx >= 0, 'Original key not found'
data[idx:idx+len(new)] = new
open('manifest_patched.xml', 'wb').write(data)
"
```

#### Step E: Verify Maps are loading

```bash
adb logcat -c
adb install app_final.apk
adb shell am start -n com.example.app/.MainActivity
sleep 6
adb logcat -d | grep -i "maps"

# GOOD: "Google Android Maps SDK: Google Play services maps renderer version"
# BAD:  "Google Android Maps SDK: Authorization failure"
```

### Case study: Unwetter (de.mdiener.unwetter.gm)

| Step | Action |
|---|---|
| Ads removed | Patched `Lmn;->a()` → always return `true` in `classes5.dex` |
| API key | `AIzaSyBUbCyLwfqOtyl086vxiw3flTPSsJncAmg` from Rain Alarm Premium `resources.arsc` |
| Signature | AOSP testkey (SHA-1 `61ED377E...`) |
| Result | Ads removed, Google Maps working, redistributable |

### Case study: Rain Alarm Premium (de.mdiener.rain.usa)

This modded app by farsroid.com demonstrates the technique:
- Package: `de.mdiener.rain.usa` (same developer as Unwetter)
- Signed with: AOSP testkey (SHA-1 `61ED377E85D386A8DFEE6B864BD85B0BFAA5AF81`)
- Manifest API key: `AIzaSyAvWgO1yJA0CaJdX4D75xE0-BMcd-Dc-MI` (restricted to AOSP testkey + package)
- Resource API key: `AIzaSyBUbCyLwfqOtyl086vxiw3flTPSsJncAmg` (unrestricted — usable in other apps)

### Preferred method

The Rain Alarm / AOSP testkey technique is the **recommended approach** when the app uses the native Google Maps SDK (`SupportMapFragment`, `MapView`). It requires finding one unrestricted API key (scan cracked APKs) and signing with the AOSP testkey. The key works across all apps signed with the same testkey.

### Most powerful method: Amap SDK + Google tiles overlay (no API key, no Google Play Services)

**BryantTileMap** (GitHub ★43) demonstrates the ultimate technique: use a free third-party map SDK (Amap/高德) as the rendering container, then overlay Google Maps tiles via `UrlTileProvider`. This completely eliminates the Google Maps SDK, Google Play Services, and API key requirements.

**Why this beats everything else:**

| | Google Maps SDK | Rain Alarm | AlpineQuest | **Amap + tiles** |
|---|---|---|---|---|
| API key | Requiere | Key libre | No | **No** |
| Google Play Services | Requiere | Requiere | No | **No** |
| SDK completo (gestos, cámara) | Sí | Sí | Motor propio | **Sí (Amap)** |
| Firma importa | SHA-1 check | AOSP testkey | No | **No** |
| Offline | No | No | Sí | **Sí (cache)** |
| Redistribuible | No | Sí | Sí | **Sí** |

**The technique:**

```java
// Amap SDK (free, Chinese, no Google dependency) as map container
// Overlay Google tiles on top via UrlTileProvider
TileOverlayOptions tileOverlay = new TileOverlayOptions()
    .tileProvider(new UrlTileProvider(256, 256) {
        @Override
        public URL getTileUrl(int x, int y, int zoom) {
            // Google tile server — NO API KEY required
            String url = "http://mt0.google.com/vt/"
                + "lyrs=" + layer + "@" + version
                + "&hl=en&gl=US"
                + "&x=" + x + "&y=" + y + "&z=" + zoom
                + "&s=Galil.png";
            return new URL(url);
        }
    });
aMap.addTileOverlay(tileOverlay);
```

**Google tile layers (`lyrs` parameter):**

| Layer | `lyrs` value | Format | Max zoom |
|---|---|---|---|
| Map (roads) | `m` | PNG | 19 |
| Satellite | `s` | JPEG | 20 |
| Satellite + labels | `y` | PNG+JPEG | 20 |
| Terrain | `t` | PNG | 15 |
| Terrain + labels | `p` | PNG | 15 |
| Labels only (overlay) | `h` | PNG | 20 |
| Bike | `m,bike` | PNG | 20 |
| Transit | `m,transit%3Acomp%7Cvm%3A1` | PNG | 20 |

**Real tile URLs from GitHub projects:**

```
# Roads
http://mt0.google.com/vt/lyrs=m@444000000&hl=en&src=app&x={x}&y={y}&z={z}&s={s}

# Satellite  
http://khm0.google.com/kh/v=817&src=app&x={x}&y={y}&z={z}&s={s}

# Hybrid (satellite + labels overlay)
Layer 1: http://khm0.google.com/kh/v=817&src=app&x={x}&y={y}&z={z}&s={s}  (satellite)
Layer 2: http://mt0.google.com/vt/lyrs=h@444000000&src=app&x={x}&y={y}&z={z}&s={s}  (labels)

# Terrain
http://mt0.google.com/vt/lyrs=t@132,r@444000000&src=app&x={x}&y={y}&z={z}&s={s}

# Chinese servers (faster in Asia)
http://mt2.google.cn/vt/lyrs=y@167000000&hl=zh-CN&gl=cn&x={x}&y={y}&z={z}&s=Galil.png
```

**Implementation steps for modding an existing app:**

1. Remove `com.google.android.geo.API_KEY` meta-data from `AndroidManifest.xml`
2. Replace `SupportMapFragment`/`GoogleMap` references with Amap SDK equivalents
3. Add Amap SDK dependency (or bundle the JAR in the APK)
4. Replace `getMapAsync(OnMapReadyCallback)` with direct `UrlTileProvider` setup
5. Remove Google Play Services dependency from manifest if possible
6. Sign with any keystore — Amap doesn't validate signatures

**References:**
- [YangsBryant/BryantTileMap](https://github.com/YangsBryant/BryantTileMap) — Full Android example
- [domlysz/BlenderGIS servicesDefs.py](https://github.com/domlysz/BlenderGIS) — Complete tile URL definitions for all providers
- [osmdroid/osmdroid](https://github.com/osmdroid/osmdroid) (★3072) — Alternative map SDK, no Google needed

### Case study: AlpineQuest — Direct tile URLs (no API key required)

AlpineQuest uses a **custom tile engine** that fetches map tiles directly from Google's public tile servers without the Google Maps SDK. This completely avoids API key requirements. The tile server configuration is stored in `.aqx` XML files in `res/raw/`.

**How Google tile URLs work (no API key):**

Google's public tile servers (`mt0.google.com`, `khm0.google.com`) serve map tiles without API key authentication when the request includes:
- `Referer: http://maps.google.com/` header
- `src=app` parameter
- A session token parameter `s={$s}`

**Real tile URLs from `res/raw/maps_builtin_google.aqx`:**

| Layer | URL pattern | Servers | Zoom |
|---|---|---|---|
| **Roads (GMAPS)** | `http://mt0.google.com/vt/lyrs=m@{$g}&hl=en&src=app&x={$x}&y={$y}&z={$z}&s={$s}` | mt0, mt1 | 1-19 |
| **Satellite (GEARTH)** | `http://khm0.google.com/kh/v={$gv}&src=app&x={$x}&y={$y}&z={$z}&s={$s}` | khm0, khm1 | 1-20 |
| **Terrain (GTERR)** | `http://mt0.google.com/vt/lyrs=t@{$gt},r@{$g}&hl=x-local&src=app&x={$x}&y={$y}&z={$z}&s={$s}` | mt0, mt1 | 1-15 |
| **Hybrid layer (GROADS)** | `http://mt0.google.com/vt/lyrs=h@{$g}&hl=x-local&src=app&x={$x}&y={$y}&z={$z}&s={$s}` | mt0, mt1 | 1-20 |
| **Bike layer** | `lyrs=m@{$g},bike` | mt0, mt1 | 1-20 |
| **Transit layer** | `lyrs=m@{$g},transit%3Acomp%7Cvm%3A1` | mt0, mt1 | 1-20 |

Parameters (version-dependent, found in `<param>` tags):
```
google-m = 444000000  (maps version)
google-t = 132        (terrain version)
google-v = 817        (satellite/kh version)
```

**AQX file format** (AlpineQuest tile source definition):
```xml
<?xml version="1.0" encoding="utf-8" ?>
<aqx version="9">
    <name>Google Maps</name>
    <source id="GMAPS" type="roads" logo="google">
        <zoom-levels z="1,2,...,19" china-offset="true">
            <update-delay>1M</update-delay>
            <referer><![CDATA[http://maps.google.com/]]></referer>
            <server><![CDATA[http://mt0.google.com/vt/lyrs=m@{$g}&hl=en&src=app&x={$x}&y={$y}&z={$z}&s={$s}]]></server>
            <server><![CDATA[http://mt1.google.com/vt/lyrs=m@{$g}&hl=en&src=app&x={$x}&y={$y}&z={$z}&s={$s}]]></server>
        </zoom-levels>
    </source>
</aqx>
```

**Detection:**
```bash
# Find .aqx files in the APK
unzip -l app.apk | grep "\.aqx"

# Find Google tile URLs in code
unzip -p app.apk classes*.dex | strings -a | grep -E "mt[0-9]\.google\.com/vt/|khm[0-9]\.google\.com/kh/"
```

**When to use this approach:**
- App uses raw tile URLs instead of Google Maps SDK
- App has its own `MapView`/tile rendering code (not `SupportMapFragment`)
- App caches tiles in custom format (`.AQX`, `.sqlite`, `.mbtiles`)
- You need offline-capable maps without any Google Play Services dependency
