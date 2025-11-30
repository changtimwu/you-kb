import yt_dlp
import json

def check_playlist(url):
    ydl_opts = {
        'skip_download': True,
        'ignoreerrors': True,
        'quiet': True,
        'extract_flat': True, # Try flat first
    }
    
    print("--- Flat Extraction ---")
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        if 'entries' in info:
            first_entry = list(info['entries'])[0]
            print(json.dumps(first_entry, indent=2))
        else:
            print("No entries found")

    print("\n--- Full Extraction (First Item) ---")
    # Now try full extraction for one item to see what we get
    if 'entries' in info:
        first_url = first_entry.get('url')
        if first_url:
             # If flat extraction gives just ID, construct URL
            if 'youtube' in url and len(first_url) == 11: # Video ID
                 first_url = f"https://www.youtube.com/watch?v={first_url}"
            
            ydl_opts_full = {
                'skip_download': True,
                'ignoreerrors': True,
                'quiet': True,
                'writesubtitles': True, # We want to check this
            }
            with yt_dlp.YoutubeDL(ydl_opts_full) as ydl:
                info_full = ydl.extract_info(first_url, download=False)
                # Check for 'subtitles' and 'automatic_captions'
                print("Subtitles keys:", info_full.get('subtitles', {}).keys())
                print("Auto Captions keys:", info_full.get('automatic_captions', {}).keys())
                print("Duration:", info_full.get('duration'))
                print("Title:", info_full.get('title'))

if __name__ == "__main__":
    # Use Google Developers channel (should have many videos)
    url = "https://www.youtube.com/@GoogleDevelopers/videos" 
    # Or a smaller one if that's too big, but we just want first entry
    check_playlist(url)
