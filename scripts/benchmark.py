"""Measured local inference smoke benchmark, not a scene-accuracy benchmark."""
import sys,time,json,platform,statistics
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.argus.vision import YOLODetector,ByteTracker,normalize,resolve_device,gpu_status
from backend.argus.analytics import AnalyticsEngine
from backend.argus.config import settings
import cv2,ultralytics
image=cv2.imread(str(Path(ultralytics.__file__).parent/'assets'/'bus.jpg'))
accelerator=resolve_device('auto')
devices=['cpu']+([accelerator] if accelerator!='cpu' else [])
results=[]
for device in devices:
    detector=YOLODetector(settings.model_path,device)
    for w,h in [(1280,720),(1920,1080)]:
        frame=cv2.resize(image,(w,h))
        for _ in range(3): detector.detect(frame)
        tracker=ByteTracker(10);engine=AnalyticsEngine([]);samples=[];count=0
        for i in range(30):
            start=time.perf_counter();d=detector.detect(frame);tracked=tracker.update(d,i/10);o=normalize(tracked,w,h);summary,events=engine.step(o,i/10)
            samples.append(time.perf_counter()-start);count=len(d)
        results.append({'device':device,'source_resolution':f'{w}x{h}','model_input':'640x640 letterbox','frames':30,'mean_latency_seconds':statistics.mean(samples),'p95_latency_seconds':sorted(samples)[int(len(samples)*.95)-1],'processing_fps':1/statistics.mean(samples),'detections_final_frame':count})
report={'hardware':platform.platform()+' '+platform.machine(),'gpu':gpu_status(),'devices':devices,'threads':4,'fixture':'Ultralytics bundled bus.jpg resized to each resolution; repeated static image after 3 warm-up frames. Not representative field footage. Decode, database writes and encoding excluded; includes detection, NMS, tracking and analytics.','results':results}
Path('documents/BENCHMARK.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
