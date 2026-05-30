import cv2
import numpy as np
from scipy.ndimage import gaussian_filter1d
import os

def read_video(video_path):
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    ret, frame = cap.read()
    if not ret:
        raise ValueError("Error reading the video file.")
    
    return cap, fps, total_frames, frame

def calculate_optical_flow(prev_gray, gray):
    use_gpu = True if cv2.cuda.getCudaEnabledDeviceCount() > 0 else False
    if use_gpu:
        gpu_prev = cv2.cuda_GpuMat()
        gpu_prev.upload(prev_gray)
        gpu_gray = cv2.cuda_GpuMat()
        gpu_gray.upload(gray)
        flow_gpu = cv2.cuda_FarnebackOpticalFlow_create().calc(gpu_prev, gpu_gray, None)
        flow = flow_gpu.download()
    else:
        flow = cv2.calcOpticalFlowFarneback(prev_gray, gray, None, 0.5, 3, 15, 3, 5, 1.2, 0)
    
    magnitude, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
    return magnitude

def calculate_stable_windows(video_path, min_duration_sec=5.0, motion_threshold=2.0, max_width=320):
    cap, fps, total_frames, prev_frame = read_video(video_path)
    h, w = prev_frame.shape[:2]
    scale = max_width / w if w > max_width else 1.0
    new_size = (int(w * scale), int(h * scale))
    
    prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
    if scale < 1.0:
        prev_gray = cv2.resize(prev_gray, new_size, interpolation=cv2.INTER_AREA)
    
    effective_threshold = motion_threshold * scale
    frame_motion = []
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if scale < 1.0:
            gray = cv2.resize(gray, new_size, interpolation=cv2.INTER_AREA)
        
        magnitude = calculate_optical_flow(prev_gray, gray)
        smoothed_magnitude = gaussian_filter1d(magnitude, sigma=5)
        
        frame_motion.append(np.mean(smoothed_magnitude))
        
        prev_gray = gray
    
    cap.release()
    
    min_frames = int(min_duration_sec * fps)
    stable_windows = []
    start_frame = None

    for idx, motion in enumerate(frame_motion):
        if motion < effective_threshold:
            if start_frame is None:
                start_frame = idx
        else:
            if start_frame is not None:
                end_frame = idx
                if (end_frame - start_frame) >= min_frames:
                    stable_windows.append((start_frame / fps, end_frame / fps))
                start_frame = None

    # Handle case where video ends while stable
    if start_frame is not None and (total_frames - start_frame) >= min_frames:
        stable_windows.append((start_frame / fps, total_frames / fps))

    return stable_windows

def slice_video(video_path, stable_windows):
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    base_name = os.path.splitext(os.path.basename(video_path))[0]
    output_folder = f"{base_name}_sliced"
    os.makedirs(output_folder, exist_ok=True)
    
    for idx, (start_sec, end_sec) in enumerate(stable_windows):
        start_frame = int(start_sec * fps)
        end_frame = int(end_sec * fps)
        
        out = cv2.VideoWriter(os.path.join(output_folder, f"{base_name}_{idx+1}.mp4"), 
                              cv2.VideoWriter_fourcc(*'mp4v'), fps, (int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))))
        
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        for _ in range(end_frame - start_frame):
            ret, frame = cap.read()
            if not ret:
                break
            out.write(frame)
        
        out.release()

def main(video_path="sample.MP4", min_duration_sec=5.0, motion_threshold=2.0, max_width=320):
    print(f"Processing {video_path} (downscaled to {max_width}px for motion analysis)...")
    stable_windows = calculate_stable_windows(video_path, min_duration_sec, motion_threshold, max_width)
    print(f"Found {len(stable_windows)} stable window(s): {stable_windows}")
    slice_video(video_path, stable_windows)
    print("Done.")

if __name__ == "__main__":
    main()