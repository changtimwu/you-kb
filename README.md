# YouTube Subtitle Downloader

A Python CLI tool to download subtitles from YouTube videos, playlists, and channels. Features parallel processing for fast subtitle extraction from large playlists.

## Features

- 📥 Download subtitles from individual videos, playlists, or entire channels
- 📊 List videos with subtitle availability before downloading
- ⚡ Parallel processing for efficient handling of large playlists (600+ videos)
- 📈 Progress bar with real-time updates showing current video being processed
- 📉 Statistics summary showing subtitle availability and duration metrics
- 🎯 Limit processing to a specific number of videos
- 🌍 Support for multiple subtitle languages
- 🔄 Automatic fallback to auto-generated subtitles

## Installation

1. Clone this repository:
```bash
git clone <your-repo-url>
cd ytkb
```

2. Create a virtual environment (recommended):
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### List Videos and Check Subtitle Availability

```bash
python main.py <URL> --list
```

**Example:**
```bash
python main.py "https://www.youtube.com/playlist?list=PLxxxxxx" --list
```

**With limit:**
```bash
python main.py "https://www.youtube.com/playlist?list=PLxxxxxx" --list --limit 10
```

### Download Subtitles

**Single video:**
```bash
python main.py "https://www.youtube.com/watch?v=VIDEO_ID"
```

**Playlist:**
```bash
python main.py "https://www.youtube.com/playlist?list=PLAYLIST_ID"
```

**Channel:**
```bash
python main.py "https://www.youtube.com/@ChannelName/videos"
```

**With custom language:**
```bash
python main.py "https://www.youtube.com/watch?v=VIDEO_ID" --lang es
```

**With custom output directory:**
```bash
python main.py "https://www.youtube.com/watch?v=VIDEO_ID" --output my_subtitles
```

## Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `url` | YouTube video, playlist, or channel URL | Required |
| `--list` | List videos and subtitle info without downloading | False |
| `--limit N` | Limit number of videos to process | All videos |
| `--lang LANG` | Subtitle language code (e.g., en, es, fr) | en |
| `--output DIR` | Output directory for downloaded subtitles | downloads |

## Statistics Output

When using `--list`, you'll see a statistics summary including:
- Total videos processed
- Number of videos with subtitles (with percentage)
- Number of videos with auto-generated subtitles (with percentage)
- Average video duration
- Total playlist duration

**Example output:**
```
============================================================
STATISTICS
============================================================
Total videos processed:        647
Videos with subtitles:         1 (0.2%)
Videos with auto-subtitles:    0 (0.0%)
Videos with any subtitles:     1 (0.2%)
Average duration:              22m 14s (1334s)
Total duration:                239h 59m (863940s)
============================================================
```

## Output Format

Subtitles are saved in `.vtt` format, organized by uploader:
```
downloads/
└── ChannelName/
    ├── Video Title 1.en.vtt
    ├── Video Title 2.en.vtt
    └── ...
```

## Performance

- Uses parallel processing with 10 concurrent workers
- Efficiently handles large playlists (tested with 600+ videos)
- Real-time progress updates to avoid appearing frozen

## Dependencies

- `yt-dlp` - YouTube video/subtitle extraction
- `tqdm` - Progress bar display

## Troubleshooting

**Private videos:** Some videos in playlists may be private. These will show an error but won't stop the overall process.

**No subtitles available:** Not all videos have subtitles. The tool will attempt to download auto-generated subtitles as a fallback.

**JavaScript runtime warnings:** The tool is configured to avoid these warnings by using the iOS client, but you may occasionally see them for certain videos.

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
