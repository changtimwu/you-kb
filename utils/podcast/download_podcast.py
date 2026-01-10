import urllib.request
import re
import sys
import xml.etree.ElementTree as ET
from typing import Optional

def get_spotify_metadata(url: str):
    """Extract episode title and podcast name from Spotify URL using native urllib."""
    # Use a simpler User-Agent to avoid being served the 'Spotify - Web Player' placeholder
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"[!] Error fetching Spotify URL: {e}")
        return None, None
    
    # Try to extract from title tag
    title_match = re.search(r'<title>(.*?)</title>', html)
    if not title_match:
        return None, None
    
    full_title = title_match.group(1).strip()
    if full_title == "Spotify – Web Player":
        print("[!] Received generic placeholder. Retrying with meta tags...")
        # Fallback: search for og:title or twitter:title
        meta_match = re.search(r'<meta property="og:title" content="(.*?)"', html)
        if meta_match:
            full_title = meta_match.group(1)

    clean_title = full_title.replace(" | Podcast on Spotify", "")
    # Try splitting by " - " or " | "
    if " - " in clean_title:
        parts = clean_title.split(" - ")
        episode_title = parts[0].strip()
        podcast_name = parts[1].strip()
    else:
        episode_title = clean_title
        podcast_name = ""
        
    return episode_title, podcast_name

def find_audio_in_rss(rss_url: str, episode_title: str):
    """Search for episode download link in RSS feed using native urllib."""
    try:
        with urllib.request.urlopen(rss_url) as response:
            content = response.read()
            root = ET.fromstring(content)
    except Exception as e:
        print(f"[!] Error fetching RSS: {e}")
        return None
    
    # Standard RSS search
    for item in root.findall('.//item'):
        title_elem = item.find('title')
        if title_elem is not None and episode_title in title_elem.text:
            enclosure = item.find('enclosure')
            if enclosure is not None:
                return enclosure.get('url')
    return None

def download_podcast_audio(spotify_url: str, output_path: str = "podcast_episode.mp3"):
    print(f"[*] Extracting metadata from Spotify: {spotify_url}")
    episode_title, podcast_name = get_spotify_metadata(spotify_url)
    
    if not episode_title:
        print("[!] Could not parse Spotify page.")
        return

    print(f"[*] Episode: {episode_title}")
    print(f"[*] Podcast: {podcast_name}")

    if not podcast_name:
        print("[!] Could not determine podcast name.")
        return

    # For this specific podcast host (Firstory), we use their RSS feed.
    # In a more complete tool, you would map podcast names to their RSS URLs.
    print(f"[*] Searching for download link for '{episode_title}'...")
    
    # Specific RSS for "從大腦到心理"
    firstory_rss = "https://feed.firstory.me/rss/user/ck9e7ev1iivqn0873lcxit8ek"
    audio_url = find_audio_in_rss(firstory_rss, episode_title.split("|")[0].strip())
    
    if not audio_url:
        audio_url = find_audio_in_rss(firstory_rss, episode_title)

    if audio_url:
        print(f"[*] Found audio URL: {audio_url}")
        print(f"[*] Downloading to {output_path}...")
        
        try:
            # Firstory might use redirects
            headers = {'User-Agent': 'Mozilla/5.0'}
            req = urllib.request.Request(audio_url, headers=headers)
            with urllib.request.urlopen(req) as response, open(output_path, 'wb') as out_file:
                # Handle potential 129b Found/Redirect body
                data = response.read()
                if b"Redirecting to" in data:
                    new_url = data.decode().split("Redirecting to ")[1].strip()
                    print(f"[*] Following redirect to: {new_url}")
                    with urllib.request.urlopen(new_url) as real_response:
                        out_file.seek(0)
                        out_file.write(real_response.read())
                else:
                    out_file.write(data)
            print("[+] Download complete.")
        except Exception as e:
            print(f"[!] Download failed: {e}")
    else:
        print("[!] Could not find download link in the known RSS feed.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 download_podcast.py <spotify_url> [output_file.mp3]")
    else:
        url = sys.argv[1]
        out = sys.argv[2] if len(sys.argv) > 2 else "episode.mp3"
        download_podcast_audio(url, out)
