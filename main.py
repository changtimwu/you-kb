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

    download_subtitles(args.url, args.output, args.lang)
    print("Download complete.")

if __name__ == "__main__":
    main()
