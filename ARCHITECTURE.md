# YouTube Subtitle Downloader Architecture

This document describes the high-level architecture and component interaction of the YouTube Subtitle Downloader.

## System Architecture

```text
+-------------+
| User (CLI)  |
+------+------+
       |
       | Run Command
       v
+---------------------------------------------------------------+
|                           main.py                             |
+-------+-----------------------------------------------+-------+
        |                                               |
        | 1. List/Download Info                         | 2. Fallback (No Subs)
        v                                               v
+-------+-------+                               +-------+-------+
| downloader.py |                               | transcribe.py |
+-------+-------+                               +-------+-------+
        |                                               |
        | Get Metadata & Subs                           | Get Audio / Generate VTT
        v                                               v
+-------+-------+                               +-------+-------+
|    yt-dlp     |<------------------------------+   Gemini API  |
+-------+-------+          (Get Audio)          +-------+-------+
        |                                               |
        | Save .vtt                                     | Save .vtt
        v                                               v
+-------+-----------------------------------------------+-------+
|                     downloads/ directory                      |
+---------------------------------------------------------------+
```

## Component Breakdown

### 1. `main.py` (Orchestrator)
- **Role:** Handles command-line arguments and manages the high-level execution flow.
- **Key Responsibilities:**
    - Parsing CLI inputs (`url`, `--lang`, `--list`, `--limit`).
    - Handling interactive prompts for batch downloads.
    - Orchestrating the fallback to AI transcription if standard subtitles are unavailable.

### 2. `downloader.py` (Subtitle Manager)
- **Role:** Interfaces with `yt-dlp` to extract existing subtitle data.
- **Key Responsibilities:**
    - `list_videos()`: Fetches metadata for multiple videos in parallel using a `ThreadPoolExecutor`.
    - `download_subtitles()`: Downloads official or auto-generated `.vtt` files.
    - Implements custom output templates (`%(uploader)s/%(title)s.%(ext)s`).

### 3. `transcribe.py` (AI Transcription Fallback)
- **Role:** Provides audio-to-text capabilities when YouTube subtitles are missing.
- **Key Responsibilities:**
    - `download_audio()`: Extracts high-quality audio (m4a) using `yt-dlp`.
    - `transcribe_audio()`: Uploads audio to Google Generative AI (Gemini) and prompts it to generate a WebVTT formatted transcript.
    - Handles API key management via `myapikey.txt`.

### 4. `research_subs.py` (Diagnostic Tool)
- **Role:** A standalone utility for debugging.
- **Key Responsibilities:**
    - Performs deep inspections of YouTube metadata structures to verify how `yt-dlp` sees subtitles and automatic captions.

## Data Flow
1. **Input:** User provides a YouTube URL.
2. **Metadata Fetch:** `yt-dlp` extracts video/playlist information.
3. **Decision Point:**
    - If subtitles exist: Downloaded directly.
    - If subtitles missing: `main.py` triggers `transcribe.py` to download audio and request a transcript from Gemini.
4. **Storage:** All results are stored in the `downloads/` directory, categorized by the uploader's channel name.
