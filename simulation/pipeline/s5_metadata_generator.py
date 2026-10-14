"""
SmartPath Simulation Authoring Engine — Stage 5: Gemini Vision Metadata Generator

Consumes keyframe screenshots, Whisper audio transcripts, and RapidOCR ground-truth
text anchors to generate semantically rich, spatially anchored state metadata.
"""

import os
import json
import time
from typing import Any, Optional
import google.generativeai as genai
from pipeline.s4_ocr_engine import extract_text_anchors, format_anchor_table_for_prompt


def _get_transcript_context(timestamp_ms: int, transcript: list[dict[str, Any]], window_ms: int = 5000) -> str:
    """Gets transcript text around the given timestamp."""
    start_window = timestamp_ms - window_ms
    end_window = timestamp_ms + window_ms

    context = []
    for seg in transcript:
        seg_start_ms = seg["start"] * 1000
        seg_end_ms = seg["end"] * 1000

        if (seg_start_ms <= end_window) and (seg_end_ms >= start_window):
            context.append(seg["text"])

    return " ".join(context)


def generate_metadata(
    keyframes: list[dict[str, Any]],
    transcript: list[dict[str, Any]],
    gemini_api_key: str,
    prompt_file: Optional[str] = None,
    model_name: str = "gemini-2.5-flash"
) -> list[dict[str, Any]]:
    """
    Uses Gemini Vision with OCR ground-truth anchor tables to generate accurate
    workflow state metadata for each keyframe.
    """
    if not gemini_api_key:
        raise ValueError("Gemini API key is required.")

    genai.configure(api_key=gemini_api_key)

    # Resolve prompt file path
    if prompt_file is None:
        module_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        prompt_file = os.path.join(module_root, "inputs", "prompt_for_json.txt")

    with open(prompt_file, "r", encoding="utf-8") as f:
        base_prompt = f.read()

    model = genai.GenerativeModel(model_name)
    raw_states = []

    print(f"\n[Stage 5] Generating metadata for {len(keyframes)} keyframes using {model_name}...")

    for i, kf in enumerate(keyframes):
        print(f"  Processing keyframe {i+1}/{len(keyframes)}...")

        img_path = kf.get("image_path") or kf.get("path")
        if not img_path or not os.path.exists(img_path):
            print(f"  [ERR] Keyframe image not found: {img_path}")
            continue

        # Upload image to Gemini
        img_file = genai.upload_file(img_path)

        # Retrieve or compute OCR anchors
        ocr_table = kf.get("ocr_anchor_table")
        if not ocr_table:
            anchors = extract_text_anchors(img_path)
            ocr_table = format_anchor_table_for_prompt(anchors)

        # Get transcript context
        timestamp_ms = kf.get("timestamp_ms", 0)
        context_text = _get_transcript_context(timestamp_ms, transcript)

        prompt = f"""{base_prompt}

{ocr_table}

NARRATOR TRANSCRIPT CONTEXT AT THIS POINT ({kf.get('timestamp_str', '00:00')}):
'{context_text}'
Incorporate any policy limits, codes, or trainee actions mentioned in the narration into instructional_hint.

Return strictly valid JSON as an array containing a single object for this specific keyframe.
"""

        try:
            response = model.generate_content(
                [img_file, prompt],
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json",
                    temperature=0.2
                )
            )

            resp_text = response.text.strip()

            try:
                state_data_list = json.loads(resp_text)
                if isinstance(state_data_list, list) and len(state_data_list) > 0:
                    state_data = state_data_list[0]
                else:
                    state_data = state_data_list

                state_id = f"STATE_{i+1:02d}"
                state_data["state_id"] = state_id
                state_data["timestamp_in_video"] = kf.get("timestamp_str", "00:00")

                if "expected_input_value" not in state_data:
                    state_data["expected_input_value"] = None

                raw_states.append(state_data)
                print(f"  [OK] Generated metadata for {state_id} (target: {state_data.get('ui_element_name')})")

            except json.JSONDecodeError:
                print(f"  [ERR] Failed to decode JSON for keyframe {i+1}: {resp_text}")

        except Exception as e:
            print(f"  [ERR] Gemini API error for keyframe {i+1}: {e}")

        finally:
            try:
                genai.delete_file(img_file.name)
            except Exception:
                pass

        time.sleep(1)

    print(f"[Stage 5] Successfully generated metadata for {len(raw_states)} states.")
    return raw_states
