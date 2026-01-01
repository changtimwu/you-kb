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
+-----------------------------------------------------------------------+
|                               main.py                                 |
+-------+-------------------------------+-------+---------------+-------+
        |                               |               |
        | 1. List/Download              | 2. Fallback   | 3. RAG Chat
        v                               v               v
+-------+-------+               +-------+-------+       +-------+-------+
| downloader.py |               | transcribe.py |       |    rag.py     |
+-------+-------+               +-------+-------+       +-------+-------+
        |                               |               |       ^
        | Get Metadata & Subs           | Audio To VTT  | Index | Query
        v                               v               v       |
+-------+-------+               +-------+-------+       +-------+-------+
|    yt-dlp     |<--------------+   Gemini API  |<------+   LanceDB     |
+-------+-------+               +-------+-------+       +-------+-------+
        |                               |                       ^
        | Save .vtt                     | Save .vtt             |
        v                               v                       |
+-------+-------------------------------+-----------------------+-------+
|                     downloads/ directory                              |
+-----------------------------------------------------------------------+
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

### 4. `rag.py` (RAG Engine)
- **Role:** Handles vector database indexing and semantic search.
- **Key Responsibilities:**
    - `create_kb()`: Parses `.vtt` files from `downloads/`, chunks them, and generates embeddings.
    - `get_embedding()`: Interfaces with Gemini's `text-embedding-004`.
    - `chat_with_kb()`: Performs similarity search in **LanceDB** and generates context-aware responses using Gemini.

### 5. `research_subs.py` (Diagnostic Tool)
- **Role:** A standalone utility for debugging.
- **Key Responsibilities:**
    - Performs deep inspections of YouTube metadata structures to verify how `yt-dlp` sees subtitles and automatic captions.

## Data Flow
1. **Input:** User provides a YouTube URL.
2. **Metadata Fetch:** `yt-dlp` extracts video/playlist information.
3. **Decision Point:**
    - If subtitles exist: Downloaded directly.
    - If subtitles missing: `main.py` triggers `transcribe.py` to download audio and request a transcript from Gemini.
4. **RAG Indexing:** `main.py --kb-create` triggers `rag.py` to index the `downloads/` directory into a LanceDB table.
5. **RAG Chat:** `main.py --chat` allows the user to query the knowledge base. `rag.py` retrieves relevant chunks from LanceDB and sends them as context to Gemini.
6. **Storage:**
    - Transcripts (.vtt) are in `downloads/`.
    - Vector data is in `.lancedb/`.
