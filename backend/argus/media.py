import math, subprocess
from pathlib import Path
import cv2
import imageio_ffmpeg

MAX_FPS=60

def source_fps(source):
    cap=cv2.VideoCapture(str(source))
    try: fps=cap.get(cv2.CAP_PROP_FPS) if cap.isOpened() else 0
    finally: cap.release()
    if not math.isfinite(fps) or not 1<=fps<=240:
        # Containers such as browser-recorded WebM often report no or bogus rates; measure instead.
        try:
            frames,seconds=imageio_ffmpeg.count_frames_and_secs(str(source)); fps=frames/seconds if seconds>0 else 0
        except Exception: fps=0
    if not math.isfinite(fps) or fps<=0: raise ValueError('Unsupported or corrupt video: no measurable frame rate')
    return min(MAX_FPS,fps)

def prepare(source,target,timeout=3600):
    """Normalize any decodable upload to constant-frame-rate H.264 MP4 with rotation applied.
    Browsers can play the result before analysis, and frame index maps exactly to video time."""
    fps=source_fps(source)
    command=[imageio_ffmpeg.get_ffmpeg_exe(),'-nostdin','-y','-loglevel','error','-i',str(source),'-map','0:v:0','-an','-sn','-dn',
             '-vf','scale=trunc(iw/2)*2:trunc(ih/2)*2,setsar=1','-r',f'{fps:.3f}','-fps_mode','cfr',
             '-c:v','libx264','-preset','veryfast','-crf','20','-pix_fmt','yuv420p','-movflags','+faststart',str(target)]
    try: result=subprocess.run(command,capture_output=True,text=True,timeout=timeout)
    except subprocess.TimeoutExpired:
        Path(target).unlink(missing_ok=True); raise ValueError('Video preparation timed out')
    if result.returncode or not Path(target).is_file() or Path(target).stat().st_size==0:
        Path(target).unlink(missing_ok=True)
        detail=(result.stderr.strip().splitlines() or ['decoder could not read a video stream'])[-1]
        raise ValueError('Unsupported or corrupt video: '+detail[:300])

def metadata(path):
    cap=cv2.VideoCapture(str(path))
    try:
        if not cap.isOpened(): raise ValueError('Unsupported or corrupt video: decoder could not open it')
        fps=cap.get(cv2.CAP_PROP_FPS); frames=int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        ok,frame=cap.read()
        if not ok: raise ValueError('Video has no valid decodable frames or timing')
        h,w=frame.shape[:2]
        if not math.isfinite(fps) or fps<=0 or frames<=0:
            frames,seconds=imageio_ffmpeg.count_frames_and_secs(str(path)); fps=frames/seconds if seconds>0 else 0
        if not math.isfinite(fps) or fps<=0 or frames<=0 or min(w,h)<=0: raise ValueError('Video has no valid decodable frames or timing')
        if w*h>3840*2160 or frames/fps>7200: raise ValueError('MVP supports up to 4K and two hours per video')
        return dict(duration=frames/fps,width=w,height=h,fps=fps,frame_count=frames,file_size=Path(path).stat().st_size)
    finally: cap.release()
