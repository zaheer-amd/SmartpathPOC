"""
SmartPath Simulation Authoring Engine — Build Pipeline
Usage: python build.py (or python -m simulation.build)
Run from: c:/SmartPath/simulation/
"""

import json
import os
import sys

from pipeline.s1_frame_extractor import extract_all_frames, copy_keyframes_as_states
from pipeline.s7_graph_compiler import compile_graph

# ── Configuration ──────────────────────────────────────────────
MODULE_ROOT    = os.path.dirname(os.path.abspath(__file__))
                 # resolves to: c:\SmartPath\simulation\

INPUT_VIDEO    = os.path.join(MODULE_ROOT, "inputs", "demo_recording.mp4")
INPUT_METADATA = os.path.join(MODULE_ROOT, "inputs", "raw_metadata.json")
OUTPUT_FRAMES  = os.path.join(MODULE_ROOT, "outputs", "frames")

# Output goes to webview and workstation/knowledge for discoverability
MONOREPO_ROOT  = os.path.dirname(MODULE_ROOT)  # c:\SmartPath\
GRAPH_OUTPUT   = os.path.join(MODULE_ROOT, "webview", "scenario_graph.json")
WORKSTATION_GRAPH = os.path.join(MONOREPO_ROOT, "workstation", "knowledge", "scenario_graph.json")

# Also copy frames to webview/assets/ for the static site
WEBVIEW_ASSETS = os.path.join(MODULE_ROOT, "webview", "assets")


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--auto", action="store_true", help="Run automated keyframe detection + Whisper + Gemini pipeline")
    parser.add_argument("--gemini-key", type=str, default=os.environ.get("GEMINI_API_KEY"), help="Gemini API key")
    parser.add_argument("--whisper-model", type=str, default="base", help="Whisper model size (tiny/base/small)")
    args = parser.parse_args()

    print("=" * 60)
    print("  SmartPath Simulation Authoring Engine — Build Pipeline")
    print("=" * 60)

    if args.auto:
        print("\n[0/4] Running automated extraction pipeline...")
        # Step 0a: Detect keyframes via SSIM
        from pipeline.s2_keyframe_detector import detect_keyframes
        kf_dir = os.path.join(MODULE_ROOT, "outputs", "keyframes")
        keyframes = detect_keyframes(INPUT_VIDEO, kf_dir)

        # Step 0b: Transcribe audio via Whisper
        from pipeline.s3_audio_transcriber import transcribe_video
        audio_out = os.path.join(MODULE_ROOT, "outputs", "transcribed_audio_folder", "audio_transcription.json")
        transcript = transcribe_video(INPUT_VIDEO, whisper_model=args.whisper_model, output_json=audio_out)

        # Step 0c: Extract ground-truth text anchors via RapidOCR
        from pipeline.s4_ocr_engine import process_keyframes_ocr
        keyframes = process_keyframes_ocr(keyframes)

        # Step 0d: Generate metadata via Gemini Vision with OCR anchors
        from pipeline.s5_metadata_generator import generate_metadata
        if not args.gemini_key:
             print("  [ERR] --gemini-key or GEMINI_API_KEY environment variable is required for --auto mode.")
             sys.exit(1)
        raw_states = generate_metadata(keyframes, transcript, args.gemini_key)
        
        # Write the auto-generated metadata to disk
        with open(INPUT_METADATA, "w", encoding="utf-8") as f:
            json.dump(raw_states, f, indent=4)
        print(f"  [OK] Auto-generated raw_metadata.json with {len(raw_states)} states")
        
        # In auto mode, keyframes are already extracted. We just copy them.
        frame_map = copy_keyframes_as_states(keyframes, OUTPUT_FRAMES)
        
    else:
        # ── Step 1: Validate inputs exist ──────────────────────────
        print("\n[1/4] Validating inputs...")
        if not os.path.exists(INPUT_VIDEO):
            print(f"  [ERR] ERROR: Video not found: {INPUT_VIDEO}")
            sys.exit(1)
        if not os.path.exists(INPUT_METADATA):
            print(f"  [ERR] ERROR: Metadata not found: {INPUT_METADATA}")
            sys.exit(1)
        print(f"  [OK] Video:    {INPUT_VIDEO}")
        print(f"  [OK] Metadata: {INPUT_METADATA}")
        
        # ── Step 2: Parse raw metadata ─────────────────────────────
        print("\n[2/4] Parsing raw_metadata.json...")
        with open(INPUT_METADATA, "r", encoding="utf-8") as f:
            raw_states = json.load(f)
        
        if not isinstance(raw_states, list) or len(raw_states) == 0:
            print("  [ERR] ERROR: Metadata must be a non-empty JSON array.")
            sys.exit(1)
        
        print(f"  [OK] Found {len(raw_states)} workflow states.")
        
        # ── Step 3: Extract frames ─────────────────────────────────
        print(f"\n[3/4] Extracting frames from video...")
        frame_map = extract_all_frames(INPUT_VIDEO, raw_states, OUTPUT_FRAMES)

    
    # Copy frames to webview assets
    import shutil
    os.makedirs(WEBVIEW_ASSETS, exist_ok=True)
    for state_id, frame_path in frame_map.items():
        dest = os.path.join(WEBVIEW_ASSETS, os.path.basename(frame_path))
        shutil.copy2(frame_path, dest)
    print(f"  [OK] Copied frames to webview/assets/")
    
    # Update frame_map to use webview-relative paths for the graph
    webview_frame_map = {
        state_id: f"assets/{os.path.basename(path)}"
        for state_id, path in frame_map.items()
    }
    
    # ── Step 4: Compile scenario graph ─────────────────────────
    print(f"\n[4/4] Compiling scenario_graph.json...")
    graph = compile_graph(raw_states, webview_frame_map, GRAPH_OUTPUT)
    
    # Also write a copy into workstation/knowledge for discoverability
    if os.path.exists(os.path.dirname(WORKSTATION_GRAPH)):
        with open(WORKSTATION_GRAPH, "w", encoding="utf-8") as f:
            json.dump(graph, f, indent=2)
        print(f"  [OK] Synchronized graph to {WORKSTATION_GRAPH}")
    
    # Copy raw metadata for the calibration tool
    import shutil
    webview_metadata_source = os.path.join(MODULE_ROOT, "webview", "raw_metadata_source.json")
    shutil.copy2(INPUT_METADATA, webview_metadata_source)
    
    print("\n" + "=" * 60)
    print(f"  BUILD COMPLETE — {graph['total_states']} states compiled.")
    print(f"  Serve the simulation: cd simulation/webview && python -m http.server 9000")
    print("=" * 60)


if __name__ == "__main__":
    main()
