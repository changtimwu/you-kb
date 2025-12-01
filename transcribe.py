import os
import time
import yt_dlp
import google.generativeai as genai

def get_api_key():
    try:
        with open('myapikey.txt', 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        print("Error: myapikey.txt not found.")
        return None

def download_audio(url, output_dir='downloads'):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # We want m4a or mp4 audio for Gemini
    # Gemini supports: mp3, mp4, mpeg, mpga, m4a, wav, aac
    ydl_opts = {
        'format': 'bestaudio[ext=m4a]/bestaudio[ext=mp4]/bestaudio',
        'outtmpl': os.path.join(output_dir, '%(id)s.%(ext)s'),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'm4a',
        }],
        'quiet': False,
    }
    
    print(f"Downloading audio from {url}...")
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        # The filename might change due to post-processing
        # We can predict it based on the ID and preferred codec
        video_id = info['id']
        final_path = os.path.join(output_dir, f"{video_id}.m4a")
        return final_path

def transcribe_audio(audio_path, api_key, model_name="gemini-2.5-flash-preview-09-2025"):
    genai.configure(api_key=api_key)
    
    print(f"Uploading {audio_path} to Gemini...")
    myfile = genai.upload_file(audio_path)
    print(f"File uploaded: {myfile.name}")
    
    # Wait for processing
    while myfile.state.name == "PROCESSING":
        print("Processing audio file...")
        time.sleep(2)
        myfile = genai.get_file(myfile.name)
        
    if myfile.state.name == "FAILED":
        print("File processing failed.")
        return None

    print(f"Generating transcript using {model_name}...")
    model = genai.GenerativeModel(model_name)
    
    try:
        prompt = "Generate a transcript of this audio in WebVTT format. The output must start with 'WEBVTT'. Timestamps must be in 'HH:MM:SS.mmm' format and start from 00:00:00.000."
        result = model.generate_content([myfile, prompt])
        return result.text
    except Exception as e:
        print(f"Error generating content: {e}")
        return None

if __name__ == "__main__":
    video_url = "https://www.youtube.com/watch?v=VEoTbQS0cD8"
    api_key = get_api_key()
    
    if api_key:
        try:
            audio_file = download_audio(video_url)
            if audio_file and os.path.exists(audio_file):
                print(f"Audio ready at {audio_file}")
                # User mentioned "gemini 2.5 flash".
                transcript = transcribe_audio(audio_file, api_key, model_name="gemini-2.5-flash-preview-09-2025")
                if transcript:
                    print("\n--- Transcript ---\n")
                    # print(transcript) # Don't print the whole VTT to console, it's long
                    print(transcript[:500] + "...")
                    
                    # Save transcript
                    # Clean up markdown code blocks if present
                    if transcript.startswith("```vtt"):
                        transcript = transcript[6:]
                    elif transcript.startswith("```"):
                        transcript = transcript[3:]
                    if transcript.endswith("```"):
                        transcript = transcript[:-3]
                    
                    transcript = transcript.strip()
                    
                    transcript_file = audio_file.replace('.m4a', '.vtt')
                    with open(transcript_file, 'w') as f:
                        f.write(transcript)
                    print(f"\nTranscript saved to {transcript_file}")
            else:
                print("Audio download failed or file not found.")
        except Exception as e:
            print(f"An error occurred: {e}")
    else:
        print("No API key found.")
