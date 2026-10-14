"""
SmartPath Simulation Authoring Engine — Stage 4: RapidOCR Text & Anchor Extraction

Runs RapidOCR (ONNX Runtime, CPU) on keyframe screenshots to extract all on-screen
text labels, headers, and buttons with exact machine-measured bounding boxes normalized
to 0-1000 scale. These serve as ground-truth spatial anchors for Gemini Vision (Stage 5).
"""

import os
from typing import Any, Optional
import cv2
from rapidocr_onnxruntime import RapidOCR

_DEFAULT_ENGINE: Optional[RapidOCR] = None


def get_ocr_engine() -> RapidOCR:
    """Singleton getter for the RapidOCR ONNX Runtime engine."""
    global _DEFAULT_ENGINE
    if _DEFAULT_ENGINE is None:
        _DEFAULT_ENGINE = RapidOCR()
    return _DEFAULT_ENGINE


def extract_text_anchors(
    image_path: str,
    engine: Optional[RapidOCR] = None,
    min_confidence: float = 0.50
) -> list[dict[str, Any]]:
    """
    Runs RapidOCR on an image and returns normalized [ymin, xmin, ymax, xmax] anchors.

    Args:
        image_path: Path to PNG/JPEG keyframe screenshot.
        engine: Optional RapidOCR engine instance.
        min_confidence: Confidence threshold (0.0 to 1.0) to filter spurious detections.

    Returns:
        List of dicts:
        {
            "anchor_id": int,
            "text": str,
            "bbox_1000": [ymin, xmin, ymax, xmax],
            "confidence": float
        }
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Keyframe image not found: {image_path}")

    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Unable to read image with OpenCV: {image_path}")

    h, w, _ = img.shape
    ocr = engine or get_ocr_engine()
    results, _ = ocr(image_path)

    if not results:
        return []

    anchors: list[dict[str, Any]] = []
    anchor_id = 0

    for item in results:
        box, text, score_val = item
        conf = float(score_val)
        if conf < min_confidence:
            continue

        clean_text = text.strip()
        if not clean_text:
            continue

        # box format: [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
        xs = [pt[0] for pt in box]
        ys = [pt[1] for pt in box]

        xmin = max(0, min(1000, round((min(xs) / w) * 1000)))
        xmax = max(0, min(1000, round((max(xs) / w) * 1000)))
        ymin = max(0, min(1000, round((min(ys) / h) * 1000)))
        ymax = max(0, min(1000, round((max(ys) / h) * 1000)))

        # Ensure non-zero width and height
        if xmax <= xmin:
            xmax = min(1000, xmin + 10)
        if ymax <= ymin:
            ymax = min(1000, ymin + 10)

        anchors.append({
            "anchor_id": anchor_id,
            "text": clean_text,
            "bbox_1000": [ymin, xmin, ymax, xmax],
            "confidence": round(conf, 3)
        })
        anchor_id += 1

    return anchors


def format_anchor_table_for_prompt(anchors: list[dict[str, Any]]) -> str:
    """
    Formats OCR anchors into a concise, structured prompt table that Gemini Vision
    uses as spatial ground-truth anchors.
    """
    if not anchors:
        return "No high-confidence text detected on screen."

    lines = ["GROUND-TRUTH ON-SCREEN TEXT ANCHORS (from OCR, scale 0-1000 [ymin, xmin, ymax, xmax]):"]
    for a in anchors:
        lines.append(
            f'- [ANCHOR {a["anchor_id"]}]: "{a["text"]}" at {a["bbox_1000"]} (conf: {a["confidence"]})'
        )
    return "\n".join(lines)


def process_keyframes_ocr(
    keyframes: list[dict[str, Any]],
    engine: Optional[RapidOCR] = None
) -> list[dict[str, Any]]:
    """
    Stage 4 pipeline entry point:
    Iterates over keyframes and enriches each with its OCR text anchors and formatted table.
    """
    print(f"\n[Stage 4] Running RapidOCR anchor extraction on {len(keyframes)} keyframes...")
    ocr = engine or get_ocr_engine()

    for idx, kf in enumerate(keyframes):
        img_path = kf.get("image_path")
        if not img_path or not os.path.exists(img_path):
            print(f"  [WARN] Keyframe #{idx} image missing, skipping OCR")
            kf["ocr_anchors"] = []
            kf["ocr_anchor_table"] = "No text detected (image missing)."
            continue

        anchors = extract_text_anchors(img_path, engine=ocr)
        kf["ocr_anchors"] = anchors
        kf["ocr_anchor_table"] = format_anchor_table_for_prompt(anchors)
        print(f"  [OK] Keyframe #{idx} ({os.path.basename(img_path)}): Detected {len(anchors)} text anchors")

    return keyframes
