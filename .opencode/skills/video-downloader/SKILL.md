---
name: video-downloader
description: >
  Download videos from 1800+ sites (YouTube, Odysee, ok.ru, VK, Dailymotion, Twitch, Facebook,
  Instagram, TikTok, PeerTube, and many more) with automatic resume on interruption, token
  refresh, cookie-based authentication, format selection, and playlist support. Covers yt-dlp
  as the primary engine, plus aria2c for accelerated downloads and wget as fallback.
---

# Video Downloader Expert

Download videos from virtually any website with automatic resume, robustness against network interruptions, and quality control.

## Prerequisites

```bash
# Core engine
pip install yt-dlp                     # ~ yt-dlp
pip install yt-dlp[default]            # with recommended dependencies

# FFmpeg (required for merging video+audio, conversions, HLS/DASH)
sudo apt install ffmpeg                # Debian/Ubuntu
brew install ffmpeg                    # macOS
winget install ffmpeg                  # Windows

# Optional: download accelerator
sudo apt install aria2c                # for yt-dlp --downloader aria2c
```

Verify installation:

```bash
yt-dlp --version
ffmpeg -version | head -1
aria2c --version | head -1
```

## Universal command with resume

```bash
yt-dlp --continue \
  --retries infinite \
  --fragment-retries infinite \
  --retry-sleep fragment:5,http:10 \
  -o "~/Videos/%(title)s.%(ext)s" \
  "VIDEO_URL"
```

| Option | Effect |
|--------|--------|
| `--continue` | Resumes partial download (default in yt-dlp) |
| `--retries infinite` | Retries file download if it fails |
| `--fragment-retries infinite` | Retries individual fragments (HLS/DASH) |
| `--retry-sleep fragment:5,http:10` | Waits 5s between fragments, 10s between HTTP retries |
| `-o "..."` | Filename template |

If interrupted, run the exact same command again and it will continue automatically.

## Main platforms

| Site | Example URL | Notes |
|-------|---------------|-------|
| **Odysee / LBRY** | `https://odysee.com/@channel:claim/video:claim` | Use page URL, not direct CDN stream |
| **ok.ru** | `https://ok.ru/video/123456789` | Supports login with cookies |
| **VK** | `https://vk.com/video-123456_789` | Requires session cookies |
| **YouTube** | `https://youtube.com/watch?v=xxx` | No restrictions |
| **YouTube (age-restricted)** | `https://youtube.com/watch?v=xxx` | Requires `--cookies-from-browser` |
| **Twitch** | `https://twitch.tv/channel/video/123` | Supports VODs and clips |
| **Facebook** | `https://facebook.com/watch?v=xxx` | Requires cookies |
| **Instagram** | `https://instagram.com/p/xxx/` | Requires login |
| **TikTok** | `https://tiktok.com/@user/video/123` | No restrictions |
| **Dailymotion** | `https://dailymotion.com/video/xxx` | No restrictions |
| **Vimeo** | `https://vimeo.com/123456` | No restrictions |
| **PeerTube** | `https://instance.tube/w/xxx` | Any instance |
| **X / Twitter** | `https://x.com/user/status/123` | No restrictions |
| **Bilibili** | `https://bilibili.com/video/BVxxx` | No restrictions |
| **Rutube** | `https://rutube.ru/video/xxx/` | No restrictions |
| **Archive.org** | `https://archive.org/details/xxx` | No restrictions |
| **Reddit** | `https://reddit.com/r/sub/comments/xxx` | No restrictions |
| **Videa / Indavideo** | `https://videa.hu/videok/xxx` | No restrictions |

Full list: `yt-dlp --list-extractors | less`

## Authentication (sites with login)

### Method 1: Browser cookies (recommended)

```bash
# Firefox
yt-dlp --cookies-from-browser firefox "URL"

# Chrome/Chromium
yt-dlp --cookies-from-browser chrome "URL"

# Brave, Edge, Opera, Vivaldi
yt-dlp --cookies-from-browser brave "URL"
```

This exports cookies from the active browser session (must be logged in on the site).

### Method 2: Cookies file

```bash
# Export cookies to file (with Get cookies.txt extension or similar)
yt-dlp --cookies cookies.txt "URL"
```

### Method 3: Direct credentials

```bash
# Only for sites that support it (VK, etc.)
yt-dlp --username user --password pass "URL"
```

## Quality and format control

### List available formats

```bash
yt-dlp -F "URL"
```

### Select specific quality

```bash
# By format ID (e.g.: 137+140 = 1080p video + AAC audio)
yt-dlp -f 137+140 "URL"

# Best video quality + best audio
yt-dlp -f "bestvideo+bestaudio" "URL"

# Maximum resolution (but may change codec)
yt-dlp -f "bestvideo[height<=1080]+bestaudio" "URL"

# Audio only (mp3, opus, m4a)
yt-dlp -f bestaudio --extract-audio --audio-format mp3 "URL"
```

### Preferred codec

```bash
# Prefer h264 (more compatible)
yt-dlp -f "bestvideo[height<=1080][vcodec*=avc1]+bestaudio" "URL"

# Prefer AV1 (better compression)
yt-dlp -f "bestvideo[height<=1080][vcodec*=av01]+bestaudio" "URL"

# Prefer VP9 (quality-compression tradeoff)
yt-dlp -f "bestvideo[height<=1080][vcodec*=vp9]+bestaudio" "URL"
```

## Playlists and channels

```bash
# Download entire playlist
yt-dlp --continue --retries infinite "https://youtube.com/playlist?list=..."

# Video range within playlist
yt-dlp --playlist-start 5 --playlist-end 15 "https://..."

# Max N videos
yt-dlp --max-downloads 10 "https://..."

# Download only the most recent channel videos
yt-dlp --dateafter 20240101 "https://youtube.com/@Channel/videos"

# Organize in folders by playlist
yt-dlp -o "%(playlist_title)s/%(playlist_index)s - %(title)s.%(ext)s" "URL"
```

## Subtitles

```bash
# Download automatic subtitles (YouTube, etc.)
yt-dlp --write-subs --sub-langs es,en --skip-download "URL"

# Embedded subtitles (burned into video)
yt-dlp --embed-subs "URL"

# AI-generated subtitles (YouTube ASR)
yt-dlp --write-auto-subs --sub-langs es "URL"
```

## Download acceleration

```bash
# With aria2c (parallel downloads)
yt-dlp --downloader aria2c \
  --downloader-args "aria2c:-x 16 -s 16 -k 1M" \
  "URL"

# Parallel fragments for HLS/DASH
yt-dlp --concurrent-fragments 4 "URL"
```

| Option | Effect |
|--------|--------|
| `-x 16` | 16 connections per server |
| `-s 16` | 16 splits per file |
| `-k 1M` | Chunk size: 1 MB |

## Helper script: robust download with auto-retry

Save as `~/bin/dl-video`:

```bash
#!/bin/bash
# dl-video — robust video download
# Usage: dl-video URL [yt-dlp-options]

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
    echo "✓ Download completed successfully."
else
    echo "✗ Failed after multiple retries. Run again to resume."
fi
exit $EXIT_CODE
```

```bash
chmod +x ~/bin/dl-video
# Usage
dl-video "https://odysee.com/@channel/video"
dl-video "https://ok.ru/video/123" --cookies-from-browser firefox
```

## Common troubleshooting

| Problem | Cause | Solution |
|----------|-------|----------|
| **403 Forbidden** | Expired CDN token | Use page URL (not direct stream). `yt-dlp` renews tokens automatically. |
| **GEO blocked** | Regional restriction | `--geo-bypass` or use VPN/proxy `--proxy http://...` |
| **"Sign in to confirm age"** | Age-restricted YouTube | `--cookies-from-browser firefox` with active session |
| **Does not resume** | Server without Range support | Use `--fragment-retries infinite` for HLS fragments |
| **Audio out of sync** | Bad format combination | Use `-f bestvideo+bestaudio` or `-f "bv*+ba"` |
| **TLS/SSL error** | System certificates | `yt-dlp --no-check-certificate` (only as last resort) |
| **yt-dlp outdated** | Broken extractor due to site changes | `pip install -U yt-dlp` |
| **Cookies expired** | Browser session expired | Log in again in the browser |

## Updating

```bash
# yt-dlp releases new versions every week
pip install -U yt-dlp

# Check available extractors after updating
yt-dlp --list-extractors | grep -i ok
```

## Best practices summary

1. **Use page URL, never direct stream** — `yt-dlp` renews tokens automatically.
2. **Always `--continue`** — it's the default, but being explicit doesn't hurt.
3. **For long playlists, use `--retries infinite` and `--fragment-retries infinite`** — network interruptions are inevitable with long lists.
4. **Prefer `--cookies-from-browser` over credentials** — avoids storing passwords.
5. **Update `yt-dlp` frequently** — sites change their APIs and extractors break.
6. **`ffprobe` to verify integrity** after downloading:

```bash
ffprobe -v quiet -show_entries format=duration,size -of csv=p=0 "video.mp4"
```
