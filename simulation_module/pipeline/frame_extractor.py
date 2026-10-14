import cv2
import os

def parse_timestamp_to_ms(timestamp_str: str) -> int:
    """
    Converts "MM:SS" string to milliseconds.
    
    Args:
        timestamp_str: Time string in "MM:SS" format. Example: "01:42"
    
    Returns:
        Integer milliseconds. Example: 102000
    
    Raises:
        ValueError: If format is invalid.
    """
    parts = timestamp_str.strip().split(":")
    if len(parts) != 2:
        raise ValueError(f"Expected MM:SS format, got: '{timestamp_str}'")
    
    minutes = int(parts[0])
    seconds = int(parts[1])
    
    return (minutes * 60 + seconds) * 1000

def extract_frame(video_path: str, timestamp_ms: int, output_path: str) -> str:
    """
    Extracts a single frame from a video at the given timestamp.
    
    Args:
        video_path:   Absolute path to the MP4 file.
        timestamp_ms: Position in the video in milliseconds.
        output_path:  Absolute path for the output PNG file.
    
    Returns:
        The output_path on success.
    
    Raises:
        FileNotFoundError: If video file doesn't exist.
        RuntimeError: If OpenCV cannot open the video or seek fails.
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video not found: {video_path}")
    
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        raise RuntimeError(f"OpenCV failed to open video: {video_path}")
    
    try:
        # Seek to the exact millisecond position
        cap.set(cv2.CAP_PROP_POS_MSEC, timestamp_ms)
        
        success, frame = cap.read()
        
        if not success or frame is None:
            raise RuntimeError(
                f"Failed to read frame at {timestamp_ms}ms from {video_path}"
            )
        
        # Save as high-quality PNG (lossless)
        # cv2.IMWRITE_PNG_COMPRESSION: 0 = no compression (fastest),
        #                               9 = max compression (smallest)
        # Use 3 as a balance between size and speed.
        cv2.imwrite(output_path, frame, [cv2.IMWRITE_PNG_COMPRESSION, 3])
        
        return output_path
    finally:
        cap.release()


def extract_all_frames(video_path: str, states: list[dict], output_dir: str) -> dict:
    """
    Extracts frames for all states in the metadata.
    
    Args:
        video_path: Path to the MP4 file.
        states:     List of state dicts from raw_metadata.json.
        output_dir: Directory to write PNG files to.
    
    Returns:
        Dict mapping state_id -> output PNG path.
        Example: {"STATE_01": "outputs/frames/STATE_01.png", ...}
    """
    os.makedirs(output_dir, exist_ok=True)
    
    frame_map = {}
    for state in states:
        state_id = state["state_id"]
        timestamp_ms = parse_timestamp_to_ms(state["timestamp_in_video"])
        output_path = os.path.join(output_dir, f"{state_id}.png")
        
        extract_frame(video_path, timestamp_ms, output_path)
        frame_map[state_id] = output_path
        print(f"  [OK] Extracted {state_id} at {state['timestamp_in_video']} -> {output_path}")
    
    return frame_map
