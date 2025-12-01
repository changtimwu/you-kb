import argparse
import os
from downloader import download_subtitles, list_videos

def main():
    parser = argparse.ArgumentParser(description="Download subtitles from YouTube videos, playlists, or channels.")
    parser.add_argument("url", help="YouTube video, playlist, or channel URL")
    parser.add_argument("--lang", default="en", help="Subtitle language code (default: en)")
    parser.add_argument("--output", default="downloads", help="Output directory (default: downloads)")
    parser.add_argument("--list", action="store_true", help="List videos and their subtitle info without downloading")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of videos to process (default: all)")

    args = parser.parse_args()

    if args.list:
        print(f"Listing videos for: {args.url}")
        videos = list_videos(args.url, limit=args.limit)
        print(f"\n--- Found {len(videos)} videos ---")
        for v in videos:
            print(f"Title: {v['title']}")
            print(f"URL: {v['url']}")
            print(f"Duration: {v['duration']}s")
            print(f"Subtitles: {', '.join(v['subtitles']) if v['subtitles'] else 'None'}")
            print(f"Auto-Subtitles: {', '.join(v['auto_subtitles']) if v['auto_subtitles'] else 'None'}")
            print("-" * 20)
        
        # Calculate statistics
        total_videos = len(videos)
        videos_with_subs = sum(1 for v in videos if v['subtitles'])
        videos_with_auto_subs = sum(1 for v in videos if v['auto_subtitles'])
        videos_with_any_subs = sum(1 for v in videos if v['subtitles'] or v['auto_subtitles'])
        total_duration = sum(v['duration'] for v in videos)
        avg_duration = total_duration / total_videos if total_videos > 0 else 0
        
        # Display statistics
        print("\n" + "=" * 60)
        print("STATISTICS")
        print("=" * 60)
        print(f"Total videos processed:        {total_videos}")
        print(f"Videos with subtitles:         {videos_with_subs} ({videos_with_subs/total_videos*100:.1f}%)" if total_videos > 0 else "Videos with subtitles:         0")
        print(f"Videos with auto-subtitles:    {videos_with_auto_subs} ({videos_with_auto_subs/total_videos*100:.1f}%)" if total_videos > 0 else "Videos with auto-subtitles:    0")
        print(f"Videos with any subtitles:     {videos_with_any_subs} ({videos_with_any_subs/total_videos*100:.1f}%)" if total_videos > 0 else "Videos with any subtitles:     0")
        print(f"Average duration:              {int(avg_duration//60)}m {int(avg_duration%60)}s ({avg_duration:.0f}s)")
        print(f"Total duration:                {int(total_duration//3600)}h {int((total_duration%3600)//60)}m ({total_duration:.0f}s)")
        print("=" * 60)
        return

    # Create output directory if it doesn't exist
    if not os.path.exists(args.output):
        os.makedirs(args.output)

    print(f"Starting download for: {args.url}")
    print(f"Output directory: {args.output}")
    print(f"Language: {args.lang}")

    result = download_subtitles(args.url, args.output, args.lang)
    
    # Check if we need to fallback to transcription for a single video
    if result and result.get('type') == 'video' and not result.get('downloaded'):
        print("\n--- No subtitles found. Attempting transcription with Gemini... ---")
        
        try:
            from transcribe import get_api_key, download_audio, transcribe_audio
            
            api_key = get_api_key()
            if not api_key:
                print("Skipping transcription: No API key found in myapikey.txt")
                return

            # Download audio
            # Use the same output directory
            audio_file = download_audio(args.url, args.output)
            
            if audio_file and os.path.exists(audio_file):
                print(f"Audio downloaded to: {audio_file}")
                
                # Transcribe
                transcript = transcribe_audio(audio_file, api_key)
                
                if transcript:
                    # Save as VTT
                    # Clean up markdown code blocks if present (just in case, though transcribe.py might handle it, 
                    # but transcribe.py's main block handles it, not the function itself? 
                    # Let's check transcribe.py's transcribe_audio function. 
                    # It returns result.text directly. The cleaning was in the main block of transcribe.py.
                    # So we should clean it here or move cleaning to transcribe_audio.
                    # For now, let's clean it here to be safe.
                    
                    if transcript.startswith("```vtt"):
                        transcript = transcript[6:]
                    elif transcript.startswith("```"):
                        transcript = transcript[3:]
                    if transcript.endswith("```"):
                        transcript = transcript[:-3]
                    transcript = transcript.strip()

                    # Construct output filename
                    # We want it to match the structure: output_dir/uploader/title.vtt
                    # But download_audio returns a path like output_dir/id.m4a
                    # We can use the info from result['info'] to get title and uploader
                    
                    info = result.get('info', {})
                    title = info.get('title', 'Unknown')
                    uploader = info.get('uploader', 'Unknown')
                    
                    # Sanitize filenames (simple version)
                    def sanitize(name):
                        return "".join([c for c in name if c.isalpha() or c.isdigit() or c in (' ', '-', '_')]).rstrip()
                    
                    # yt-dlp sanitization is more complex, but let's try to respect the output structure
                    # downloader.py uses: os.path.join(output_dir, '%(uploader)s', '%(title)s.%(ext)s')
                    
                    # For simplicity, let's save it alongside the audio file first, then try to move it?
                    # Or just save it where the user expects.
                    
                    # Let's try to match the folder structure created by downloader.py
                    # If downloader.py created the folder, it might be there.
                    # But since download failed, maybe the folder wasn't created?
                    # yt-dlp usually creates directories.
                    
                    # Let's just save it as [VideoID].vtt in the output folder for now to be safe and consistent with the audio file,
                    # OR try to use the title if possible.
                    
                    # Actually, the user might prefer the same structure.
                    # Let's stick to the audio file's name but with .vtt extension, 
                    # which is what transcribe.py did in its main block.
                    
                    vtt_path = audio_file.replace('.m4a', '.vtt').replace('.mp4', '.vtt')
                    
                    with open(vtt_path, 'w') as f:
                        f.write(transcript)
                    print(f"Transcript saved to: {vtt_path}")
                    
                else:
                    print("Transcription failed.")
            else:
                print("Audio download failed.")
                
        except ImportError:
            print("Error: Could not import transcribe module. Make sure transcribe.py is in the directory.")
        except Exception as e:
            print(f"An error occurred during transcription: {e}")

    print("Done.")

if __name__ == "__main__":
    main()
