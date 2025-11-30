import os
import yt_dlp

def download_subtitles(url, output_dir, lang='en'):
    """
    Downloads subtitles for a given YouTube URL (video, playlist, or channel).
    """
    ydl_opts = {
        'skip_download': True,  # We only want subtitles
        'writesubtitles': True,
        'writeautomaticsub': True, # Fallback to auto-generated subs
        'subtitleslangs': [lang],
        'outtmpl': os.path.join(output_dir, '%(playlist_title)s', '%(title)s.%(ext)s'),
        'ignoreerrors': True,
        'quiet': False,
        'no_warnings': False,
    }

    # Adjust output template if it's a single video to avoid creating a 'NA' folder
    # However, yt-dlp handles playlist_title as 'NA' if not present. 
    # To be cleaner, we can check if it's a playlist first, but let's trust yt-dlp for now
    # and maybe refine the path if needed. 
    # Actually, for single videos, %(playlist_title)s might be empty or NA.
    # Let's use a more robust output template.
    
    ydl_opts['outtmpl'] = os.path.join(output_dir, '%(uploader)s', '%(title)s.%(ext)s')

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            
            # If it's a playlist or channel, info will have 'entries'
            if 'entries' in info:
                print(f"Found playlist/channel: {info.get('title', 'Unknown')}")
                # We can just let download=True (which is actually extract_info with download=True by default, 
                # but we set skip_download=True in opts) handle the iteration.
                ydl.download([url])
            else:
                print(f"Found video: {info.get('title', 'Unknown')}")
                ydl.download([url])
                
        except Exception as e:
            print(f"Error processing URL {url}: {e}")

def _get_video_info(url):
    """
    Helper function to get info for a single video.
    """
    ydl_opts = {
        'skip_download': True,
        'ignoreerrors': True,
        'quiet': True,
        'no_warnings': True, # Suppress warnings to keep output clean
        'writesubtitles': True, # Check for subtitles
        'extractor_args': {'youtube': {'player_client': ['default', 'ios']}}, # Avoid web_safari issues
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                return None
            
            # Check available subtitles
            subs = list(info.get('subtitles', {}).keys())
            auto_subs = list(info.get('automatic_captions', {}).keys())
            
            return {
                'title': info.get('title', 'Unknown'),
                'duration': info.get('duration', 0),
                'subtitles': subs,
                'auto_subtitles': auto_subs,
                'url': url
            }
    except Exception:
        return None

def list_videos(url, limit=None):
    """
    Lists videos in a playlist/channel with their details.
    
    Args:
        url: YouTube playlist/channel URL
        limit: Maximum number of videos to process (None for all)
    """
    import concurrent.futures
    
    # 1. Get list of video URLs using extract_flat
    ydl_opts_flat = {
        'skip_download': True,
        'ignoreerrors': True,
        'quiet': True,
        'extract_flat': True,
    }
    
    video_urls = []
    print("Fetching video list...")
    with yt_dlp.YoutubeDL(ydl_opts_flat) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            if 'entries' in info:
                for entry in info['entries']:
                    if entry and entry.get('url'):
                        # Handle case where flat extraction gives just ID or full URL
                        v_url = entry['url']
                        if len(v_url) == 11 and 'youtube' not in v_url: # Likely an ID
                             v_url = f"https://www.youtube.com/watch?v={v_url}"
                        video_urls.append(v_url)
            else:
                # Single video
                video_urls.append(url)
        except Exception as e:
            print(f"Error fetching list: {e}")
            return []

    # Apply limit if specified
    if limit and limit > 0:
        video_urls = video_urls[:limit]
        print(f"Found {len(info.get('entries', []))} videos total. Processing first {len(video_urls)} videos...")
    else:
        print(f"Found {len(video_urls)} videos. Fetching details...")
    
    from tqdm import tqdm
    results = []
    # 2. Fetch details in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_url = {executor.submit(_get_video_info, url): url for url in video_urls}
        
        # Use tqdm for progress bar
        pbar = tqdm(concurrent.futures.as_completed(future_to_url), total=len(video_urls), unit="video")
        for future in pbar:
            data = future.result()
            if data:
                results.append(data)
                # Update description with truncated title to avoid scrolling
                title = data.get('title', 'Unknown')
                # Truncate to 40 chars and remove newlines if any
                short_title = (title[:40] + '..') if len(title) > 40 else title
                pbar.set_description(f"Processing: {short_title}")
    
    return results

if __name__ == "__main__":
    # Simple test
    pass
