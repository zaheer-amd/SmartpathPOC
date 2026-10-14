import cv2
import os
import time
from skimage.metrics import structural_similarity as ssim

def ms_to_str(ms: int) -> str:
    """Converts milliseconds to MM:SS string."""
    s = ms // 1000
    m = s // 60
    s = s % 60
    return f"{m:02d}:{s:02d}"

def detect_keyframes(
    video_path: str,
    output_dir: str,
    sample_fps: float = 2.0,
    change_threshold: float = 0.92,
    stable_threshold: float = 0.97,
    min_gap_seconds: float = 2.0
) -> list[dict]:
    """
    Detects keyframes based on structural similarity (SSIM).
    Returns a list of dicts with keyframe metadata.
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video not found: {video_path}")
        
    # Clear output directory if it exists to prevent mixing old and new keyframes
    if os.path.exists(output_dir):
        import shutil
        shutil.rmtree(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"OpenCV failed to open video: {video_path}")
        
    native_fps = cap.get(cv2.CAP_PROP_FPS)
    if native_fps <= 0:
        native_fps = 30.0
        
    frame_step = max(1, int(native_fps / sample_fps))
    
    keyframes = []
    
    state = "WAITING_FOR_CHANGE"
    
    prev_gray = None
    last_capture_time_ms = - (min_gap_seconds * 1000)
    
    frame_idx = 0
    keyframe_count = 0
    
    print(f"Detecting keyframes in {video_path}...")
    start_time = time.time()
    
    while True:
        # Fast-forward to next sample
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        success, frame = cap.read()
        
        if not success:
            break
            
        current_time_ms = int(cap.get(cv2.CAP_PROP_POS_MSEC))
        
        # Determine appropriate window size for SSIM
        # SSIM requires the window size to be less than or equal to the smallest dimension of the image
        # and it must be odd. default is 7.
        min_dim = min(frame.shape[0], frame.shape[1])
        win_size = 7
        if min_dim < 7:
             win_size = min_dim if min_dim % 2 != 0 else min_dim - 1
             if win_size < 3: # Too small for SSIM
                 break
        
        curr_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        if prev_gray is not None:
            score, _ = ssim(prev_gray, curr_gray, full=True, win_size=win_size)
            
            if state == "WAITING_FOR_CHANGE":
                if score < change_threshold:
                    state = "WAITING_FOR_STABLE"
            
            elif state == "WAITING_FOR_STABLE":
                if score >= stable_threshold:
                    # It became stable!
                    if (current_time_ms - last_capture_time_ms) >= (min_gap_seconds * 1000):
                        # Capture this frame
                        kf_name = f"KF_{keyframe_count:02d}.png"
                        kf_path = os.path.join(output_dir, kf_name)
                        
                        # Use a slightly better quality
                        cv2.imwrite(kf_path, frame, [cv2.IMWRITE_PNG_COMPRESSION, 3])
                        
                        ts_str = ms_to_str(current_time_ms)
                        print(f"  [+] Keyframe {keyframe_count:02d} at {ts_str} (SSIM {score:.3f})")
                        
                        keyframes.append({
                            "keyframe_index": keyframe_count,
                            "timestamp_ms": current_time_ms,
                            "timestamp_str": ts_str,
                            "path": kf_path
                        })
                        
                        last_capture_time_ms = current_time_ms
                        keyframe_count += 1
                        
                    state = "WAITING_FOR_CHANGE"
                    
        prev_gray = curr_gray
        frame_idx += frame_step
        
    cap.release()
    print(f"Detected {len(keyframes)} keyframes in {time.time() - start_time:.2f}s.")
    return keyframes

if __name__ == "__main__":
    # Test script if run directly
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True)
    parser.add_argument("--out", default="outputs/keyframes")
    args = parser.parse_args()
    detect_keyframes(args.video, args.out)
