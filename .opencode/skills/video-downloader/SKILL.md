---
name: video-downloader
description: >
  Download videos from 1800+ sites (YouTube, Odysee, ok.ru, VK, Dailymotion, Twitch, Facebook,
  Instagram, TikTok, PeerTube, and many more) with automatic resume on interruption, token
  refresh, cookie-based authentication, format selection, and playlist support. Covers yt-dlp
  as the primary engine, plus aria2c for accelerated downloads and wget as fallback.
---

# Video Downloader Expert

Download videos from virtually any website with automatic reanudación, robustez ante cortes de red, y control de calidad.

## Prerequisites

```bash
# Core engine
pip install yt-dlp                     # ~ yt-dlp
pip install yt-dlp[default]            # con dependencias recomendadas

# FFmpeg (necesario para fusionar video+audio, conversiones, HLS/DASH)
sudo apt install ffmpeg                # Debian/Ubuntu
brew install ffmpeg                    # macOS
winget install ffmpeg                  # Windows

# Opcional: acelerador de descargas
sudo apt install aria2c                # para yt-dlp --downloader aria2c
```

Verificar instalación:

```bash
yt-dlp --version
ffmpeg -version | head -1
aria2c --version | head -1
```

## Comando universal con reanudación

```bash
yt-dlp --continue \
  --retries infinite \
  --fragment-retries infinite \
  --retry-sleep fragment:5,http:10 \
  -o "~/Videos/%(title)s.%(ext)s" \
  "URL_DEL_VIDEO"
```

| Opción | Efecto |
|--------|--------|
| `--continue` | Reanuda descarga parcial (por defecto en yt-dlp) |
| `--retries infinite` | Reintenta la descarga del archivo si falla |
| `--fragment-retries infinite` | Reintenta fragmentos individuales (HLS/DASH) |
| `--retry-sleep fragment:5,http:10` | Espera 5s entre fragmentos, 10s entre reintentos HTTP |
| `-o "..."` | Plantilla de nombre de archivo |

Si se corta, se vuelve a ejecutar **exactamente el mismo comando** y continúa automáticamente.

## Plataformas principales

| Sitio | URL de ejemplo | Notas |
|-------|---------------|-------|
| **Odysee / LBRY** | `https://odysee.com/@canal:claim/video:claim` | Usar URL de la página, no el stream CDN directo |
| **ok.ru** | `https://ok.ru/video/123456789` | Soporta login con cookies |
| **VK** | `https://vk.com/video-123456_789` | Requiere cookies de sesión |
| **YouTube** | `https://youtube.com/watch?v=xxx` | Sin restricciones |
| **YouTube (age-restricted)** | `https://youtube.com/watch?v=xxx` | Requiere `--cookies-from-browser` |
| **Twitch** | `https://twitch.tv/canal/video/123` | Soporta VODs y clips |
| **Facebook** | `https://facebook.com/watch?v=xxx` | Requiere cookies |
| **Instagram** | `https://instagram.com/p/xxx/` | Requiere login |
| **TikTok** | `https://tiktok.com/@user/video/123` | Sin restricciones |
| **Dailymotion** | `https://dailymotion.com/video/xxx` | Sin restricciones |
| **Vimeo** | `https://vimeo.com/123456` | Sin restricciones |
| **PeerTube** | `https://instancia.tube/w/xxx` | Cualquier instancia |
| **X / Twitter** | `https://x.com/user/status/123` | Sin restricciones |
| **Bilibili** | `https://bilibili.com/video/BVxxx` | Sin restricciones |
| **Rutube** | `https://rutube.ru/video/xxx/` | Sin restricciones |
| **Archive.org** | `https://archive.org/details/xxx` | Sin restricciones |
| **Reddit** | `https://reddit.com/r/sub/comments/xxx` | Sin restricciones |
| **Videa / Indavideo** | `https://videa.hu/videok/xxx` | Sin restricciones |

Lista completa: `yt-dlp --list-extractors | less`

## Autenticación (sitios con login)

### Método 1: Cookies del navegador (recomendado)

```bash
# Firefox
yt-dlp --cookies-from-browser firefox "URL"

# Chrome/Chromium
yt-dlp --cookies-from-browser chrome "URL"

# Brave, Edge, Opera, Vivaldi
yt-dlp --cookies-from-browser brave "URL"
```

Esto exporta las cookies de la sesión activa del navegador (debe tener sesión iniciada en el sitio).

### Método 2: Archivo de cookies

```bash
# Exportar cookies a archivo (con extensión Get cookies.txt o similar)
yt-dlp --cookies cookies.txt "URL"
```

### Método 3: Credenciales directas

```bash
# Solo para sitios que lo soporten (VK, etc.)
yt-dlp --username usuario --password contraseña "URL"
```

## Control de calidad y formato

### Listar formatos disponibles

```bash
yt-dlp -F "URL"
```

### Seleccionar calidad específica

```bash
# Por ID de formato (ej: 137+140 = video 1080p + audio AAC)
yt-dlp -f 137+140 "URL"

# Mejor calidad video + mejor audio
yt-dlp -f "bestvideo+bestaudio" "URL"

# Máxima resolución (pero puede cambiar codec)
yt-dlp -f "bestvideo[height<=1080]+bestaudio" "URL"

# Solo audio (mp3, opus, m4a)
yt-dlp -f bestaudio --extract-audio --audio-format mp3 "URL"
```

### Codec preferido

```bash
# Preferir h264 (más compatible)
yt-dlp -f "bestvideo[height<=1080][vcodec*=avc1]+bestaudio" "URL"

# Preferir AV1 (mejor compresión)
yt-dlp -f "bestvideo[height<=1080][vcodec*=av01]+bestaudio" "URL"

# Preferir VP9 (compromiso calidad-compresión)
yt-dlp -f "bestvideo[height<=1080][vcodec*=vp9]+bestaudio" "URL"
```

## Playlists y canales

```bash
# Descargar toda la playlist
yt-dlp --continue --retries infinite "https://youtube.com/playlist?list=..."

# Rango de videos dentro de la playlist
yt-dlp --playlist-start 5 --playlist-end 15 "https://..."

# Máximo N videos
yt-dlp --max-downloads 10 "https://..."

# Descargar solo los videos más recientes del canal
yt-dlp --dateafter 20240101 "https://youtube.com/@Canal/videos"

# Organizar en carpetas por playlist
yt-dlp -o "%(playlist_title)s/%(playlist_index)s - %(title)s.%(ext)s" "URL"
```

## Subtítulos

```bash
# Descargar subtítulos automáticos (YouTube, etc.)
yt-dlp --write-subs --sub-langs es,en --skip-download "URL"

# Subtítulos incrustados (quemados en el video)
yt-dlp --embed-subs "URL"

# Subtítulos generados por IA (YouTube ASR)
yt-dlp --write-auto-subs --sub-langs es "URL"
```

## Aceleración de descarga

```bash
# Con aria2c (descargas paralelas)
yt-dlp --downloader aria2c \
  --downloader-args "aria2c:-x 16 -s 16 -k 1M" \
  "URL"

# Fragmentos paralelos para HLS/DASH
yt-dlp --concurrent-fragments 4 "URL"
```

| Opción | Efecto |
|--------|--------|
| `-x 16` | 16 conexiones por servidor |
| `-s 16` | 16 splits por archivo |
| `-k 1M` | Tamaño de chunk: 1 MB |

## Script auxiliar: descarga robusta con auto-reintento

Guardar como `~/bin/dl-video`:

```bash
#!/bin/bash
# dl-video — descarga robusta de vídeos
# Uso: dl-video URL [opciones-yt-dlp]

URL="$1"
shift

yt-dlp --continue \
  --retries infinite \
  --fragment-retries infinite \
  --retry-sleep "fragment:5,http:10" \
  --no-update \
  "$@" \
  -o "~/Videos/%(title)s.%(ext)s" \
  "$URL"

EXIT_CODE=$?
if [ $EXIT_CODE -eq 0 ]; then
    echo "✓ Descarga completada exitosamente."
else
    echo "✗ Falló tras múltiples reintentos. Ejecute de nuevo para retomar."
fi
exit $EXIT_CODE
```

```bash
chmod +x ~/bin/dl-video
# Uso
dl-video "https://odysee.com/@canal/video"
dl-video "https://ok.ru/video/123" --cookies-from-browser firefox
```

## Solución de problemas comunes

| Problema | Causa | Solución |
|----------|-------|----------|
| **403 Forbidden** | Token CDN expirado | Usar URL de la página (no stream directo). `yt-dlp` renueva tokens automáticamente. |
| **GEO bloqueado** | Restricción regional | `--geo-bypass` o usar VPN/proxy `--proxy http://...` |
| **"Sign in to confirm age"** | YouTube restringido | `--cookies-from-browser firefox` con sesión iniciada |
| **No se reanuda** | Servidor sin soporte Range | Usar `--fragment-retries infinite` para fragmentos HLS |
| **Audio desincronizado** | Mala combinación de formatos | Usar `-f bestvideo+bestaudio` o `-f "bv*+ba"` |
| **Error TLS/SSL** | Certificados del sistema | `yt-dlp --no-check-certificate` (solo como último recurso) |
| **yt-dlp desactualizado** | Extractor roto por cambios del sitio | `pip install -U yt-dlp` |
| **Cookies expiradas** | Sesión del navegador caducada | Volver a iniciar sesión en el navegador |

## Actualización

```bash
# yt-dlp sale con nuevas versiones cada semana
pip install -U yt-dlp

# Ver extractores disponibles después de actualizar
yt-dlp --list-extractors | grep -i ok
```

## Resumen de buenas prácticas

1. **Usar URL de la página, nunca stream directo** — `yt-dlp` renueva tokens automáticamente.
2. **Siempre `--continue`** — viene por defecto, pero explicitarlo no daña.
3. **Para playlists largas, usar `--retries infinite` y `--fragment-retries infinite`** — cortes de red son inevitables en listas largas.
4. **Preferir `--cookies-from-browser` sobre credenciales** — evita almacenar contraseñas.
5. **Actualizar `yt-dlp` frecuentemente** — los sitios cambian sus APIs y los extractores se rompen.
6. **`ffprobe` para verificar integridad** después de descargar:

```bash
ffprobe -v quiet -show_entries format=duration,size -of csv=p=0 "video.mp4"
```
