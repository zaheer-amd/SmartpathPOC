"""
SmartPath Simulation Authoring Engine — Build Pipeline
Usage: python -m pipeline.build_pipeline
Run from: c:\SmartPath\simulation_module\
"""

import json
import os
import sys

from pipeline.frame_extractor import extract_all_frames
from pipeline.graph_compiler import compile_graph

# ── Configuration ──────────────────────────────────────────────
MODULE_ROOT    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                 # resolves to: c:\SmartPath\simulation_module\

INPUT_VIDEO    = os.path.join(MODULE_ROOT, "inputs", "demo_recording.mp4")
INPUT_METADATA = os.path.join(MODULE_ROOT, "inputs", "raw_metadata.json")
OUTPUT_FRAMES  = os.path.join(MODULE_ROOT, "outputs", "frames")

# Output goes to knowledge/ in the monorepo root for discoverability
MONOREPO_ROOT  = os.path.dirname(MODULE_ROOT)  # c:\SmartPath\
GRAPH_OUTPUT   = os.path.join(MONOREPO_ROOT, "knowledge", "scenario_graph.json")

# Also copy frames to webview/assets/ for the static site
WEBVIEW_ASSETS = os.path.join(MODULE_ROOT, "webview", "assets")


def main():
    print("=" * 60)
    print("  SmartPath Simulation Authoring Engine — Build Pipeline")
    print("=" * 60)
    
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
    
    # Also write a copy into the webview directory for standalone serving
    webview_graph_path = os.path.join(MODULE_ROOT, "webview", "scenario_graph.json")
    with open(webview_graph_path, "w", encoding="utf-8") as f:
        json.dump(graph, f, indent=2)
    print(f"  [OK] Also copied to {webview_graph_path}")
    
    print("\n" + "=" * 60)
    print(f"  BUILD COMPLETE — {graph['total_states']} states compiled.")
    print(f"  Serve the simulation: cd simulation_module/webview && python -m http.server 9000")
    print("=" * 60)


if __name__ == "__main__":
    main()
