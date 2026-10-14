import os
import subprocess
import json

def transcribe_video(
    video_path: str,
    whisper_model: str = "base",
    temp_dir: str = "outputs/temp",
    output_json: str = None
) -> list[dict]:
    """
    Extracts audio from video and transcribes it using local Whisper.
    Returns a list of dicts: {"start": ..., "end": ..., "text": ...}
    If output_json already exists on disk, returns the cached transcript.
    """
    if output_json and os.path.exists(output_json):
        print(f"Loading cached transcript from {output_json}...")
        try:
            with open(output_json, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video not found: {video_path}")
        
    try:
        import whisper
    except ImportError:
        raise ImportError(
            "Whisper is not installed. To transcribe fresh audio, install openai-whisper: "
            "pip install openai-whisper"
        )
        
    os.makedirs(temp_dir, exist_ok=True)
    temp_wav_path = os.path.join(temp_dir, "temp_audio.wav")
    
    # 1. Extract audio via ffmpeg
    print(f"Extracting audio from {video_path}...")
    if os.path.exists(temp_wav_path):
        os.remove(temp_wav_path)
        
    try:
        import imageio_ffmpeg
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        ffmpeg_exe = "ffmpeg"
        
    cmd = [
        ffmpeg_exe,
        "-i", video_path,
        "-vn",                 # Disable video
        "-acodec", "pcm_s16le",# Audio codec
        "-ar", "16000",        # Audio sample rate
        "-ac", "1",            # Audio channels
        "-y",                  # Overwrite output file
        temp_wav_path
    ]
    
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        raise RuntimeError(f"{ffmpeg_exe} not found. Please install ffmpeg or imageio-ffmpeg.")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"ffmpeg failed to extract audio: {e}")
        
    if not os.path.exists(temp_wav_path):
         raise RuntimeError("ffmpeg failed to create the audio file.")

    # 2. Transcribe using Whisper
    print(f"Transcribing audio using Whisper model '{whisper_model}'...")
    try:
        model = whisper.load_model(whisper_model)
    except Exception as e:
         # Clean up
         if os.path.exists(temp_wav_path):
             os.remove(temp_wav_path)
         raise RuntimeError(f"Failed to load whisper model: {e}")

    result = model.transcribe(temp_wav_path)
    
    segments = []
    for seg in result.get("segments", []):
        segments.append({
            "start": seg["start"],
            "end": seg["end"],
            "text": seg["text"].strip()
        })
        
    print(f"Transcription complete. Found {len(segments)} segments.")
    
    if output_json:
        import json
        import shutil
        out_dir = os.path.dirname(output_json)
        if os.path.exists(out_dir):
            shutil.rmtree(out_dir)
        os.makedirs(out_dir, exist_ok=True)
        with open(output_json, "w", encoding="utf-8") as f:
            json.dump(segments, f, indent=4)
        print(f"Saved audio transcript to {output_json}")
    
    # 3. Clean up
    if os.path.exists(temp_wav_path):
        os.remove(temp_wav_path)
        
    return segments

if __name__ == "__main__":
    import argparse
    import json
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True)
    parser.add_argument("--model", default="base")
    parser.add_argument("--out", default=None, help="Path to save the output JSON (e.g., outputs/transcribed_audio_folder/audio_transcription.json)")
    args = parser.parse_args()
    
    res = transcribe_video(args.video, args.model, output_json=args.out)
    if not args.out:
        print(json.dumps(res, indent=2))
