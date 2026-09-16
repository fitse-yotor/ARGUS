from functools import cache
from typing import Protocol
from pathlib import Path
import numpy as np
import supervision as sv

from .analytics import VEHICLES

CLASSES={0:'person',2:'car',3:'motorcycle',5:'bus',7:'truck'}
COCO_NAMES=['person','bicycle','car','motorcycle','airplane','bus','train','truck','boat','traffic light','fire hydrant','stop sign','parking meter','bench','bird','cat','dog','horse','sheep','cow','elephant','bear','zebra','giraffe','backpack','umbrella','handbag','tie','suitcase','frisbee','skis','snowboard','sports ball','kite','baseball bat','baseball glove','skateboard','surfboard','tennis racket','bottle','wine glass','cup','fork','knife','spoon','bowl','banana','apple','sandwich','orange','broccoli','carrot','hot dog','pizza','donut','cake','chair','couch','potted plant','bed','dining table','toilet','tv','laptop','mouse','remote','keyboard','cell phone','microwave','oven','toaster','sink','refrigerator','book','clock','vase','scissors','teddy bear','hair drier','toothbrush']
ANNOTATE_MODE='Detect & Annotate'
TILE=640; TILE_OVERLAP=128

def classes_for(mode):
    """Detect & Annotate keeps every model class, as in the Supervision README example."""
    return None if mode==ANNOTATE_MODE else [0] if mode=='Event / Crowd' else [2,3,5,7] if mode in ['Traffic','Convoy'] else list(CLASSES)

def class_ids(names,selected):
    """Model class indices for the operator's class filter; 'vehicle' expands to car, motorcycle, bus and truck."""
    if not selected: return None
    wanted={s.lower() for s in selected}
    return [i for i,n in names.items() if n.lower() in wanted or ('vehicle' in wanted and n in VEHICLES)]

def filter_detections(detections,min_box=0):
    """Drops boxes whose shorter side is below min_box pixels (noise, distant clutter)."""
    if not min_box or not len(detections): return detections
    sides=np.minimum(detections.xyxy[:,2]-detections.xyxy[:,0],detections.xyxy[:,3]-detections.xyxy[:,1])
    return detections[sides>=min_box]

def known(detections,names):
    return detections[np.isin(detections.class_id,list(names))] if len(detections) else detections
class DetectorAdapter(Protocol):
    def detect(self, frame: np.ndarray) -> sv.Detections: ...
class TrackerAdapter(Protocol):
    def update(self, detections: sv.Detections, timestamp: float) -> sv.Detections: ...

@cache
def resolve_device(requested='cpu'):
    """'auto' prefers CUDA, then Apple MPS, then CPU; explicit devices are respected."""
    if requested!='auto': return requested
    import torch
    if torch.cuda.is_available(): return 'cuda'
    if torch.backends.mps.is_available(): return 'mps'
    return 'cpu'

def gpu_status():
    """Measured accelerator facts only; utilization is None where the platform does not expose it."""
    import torch
    if torch.cuda.is_available():
        try: utilization=torch.cuda.utilization(0)
        except Exception: utilization=None
        return dict(backend='CUDA',name=torch.cuda.get_device_name(0),memory_allocated_mb=round(torch.cuda.memory_allocated(0)/1048576,1),utilization_percent=utilization)
    if torch.backends.mps.is_available():
        return dict(backend='MPS',name='Apple Metal Performance Shaders',memory_allocated_mb=round(torch.mps.current_allocated_memory()/1048576,1),utilization_percent=None,note='macOS does not expose GPU utilization to PyTorch')
    return dict(backend='NONE',name=None,memory_allocated_mb=None,utilization_percent=None)

class YOLODetector:
    def __init__(self,path,device='cpu',mode='General',confidence=.3,imgsz=640,classes=None,tiling=False,min_box=0):
        if not Path(path).is_file(): raise RuntimeError(f'Model unavailable: place approved weights at {path}; run scripts/download_model.py')
        from ultralytics import YOLO
        import torch
        torch.set_num_threads(4)
        device=resolve_device(device)
        yolo=YOLO(path); self.names=dict(yolo.names)
        self.model=yolo.model.to(device).float().eval(); self.device=device; self.confidence=confidence
        base=classes_for(mode); selected=class_ids(self.names,classes)
        # The operator filter narrows the mode's classes; it never adds classes a mode excludes.
        self.classes=base if selected is None else selected if base is None else [c for c in selected if c in base]
        self.imgsz=int(imgsz)//32*32; self.tiling=bool(tiling); self.min_box=int(min_box or 0); self.slicer=None
    def _predict(self,frames,size):
        # Buffer conversion supports Intel Mac PyTorch 2.2 with NumPy 2 without
        # using the incompatible torch.from_numpy / Tensor.numpy bridge.
        import cv2, torch
        from ultralytics.utils.ops import non_max_suppression
        canvases=[]; geometry=[]
        for frame in frames:
            h,w=frame.shape[:2]; scale=min(size/w,size/h)
            nw,nh=round(w*scale),round(h*scale); left=(size-nw)//2; top=(size-nh)//2
            canvas=np.full((size,size,3),114,dtype=np.uint8); canvas[top:top+nh,left:left+nw]=cv2.resize(frame,(nw,nh))
            canvases.append(cv2.cvtColor(canvas,cv2.COLOR_BGR2RGB)); geometry.append((w,h,scale,left,top))
        batch=np.ascontiguousarray(np.stack(canvases))
        tensor=torch.frombuffer(bytearray(batch.tobytes()),dtype=torch.uint8).reshape(len(frames),size,size,3).permute(0,3,1,2).to(self.device).float()/255
        with torch.inference_mode():
            prediction=self.model(tensor)
            if isinstance(prediction,(list,tuple)): prediction=prediction[0]
            # torchvision NMS has no MPS kernel, so suppression runs on CPU after accelerated inference.
            results=non_max_suppression(prediction.cpu(),conf_thres=self.confidence,iou_thres=.5,classes=self.classes)
        out=[]
        for rows,(w,h,scale,left,top) in zip(results,geometry):
            rows=rows.tolist()
            if not rows: out.append(sv.Detections.empty()); continue
            arr=np.asarray(rows); boxes=arr[:,:4]
            boxes[:,[0,2]]=((boxes[:,[0,2]]-left)/scale).clip(0,w)
            boxes[:,[1,3]]=((boxes[:,[1,3]]-top)/scale).clip(0,h)
            out.append(sv.Detections(xyxy=boxes,confidence=arr[:,4],class_id=arr[:,5].astype(int)))
        return out
    def detect(self,frame):
        # Larger input sizes (960/1280) find small, distant objects at proportionally higher compute cost.
        detections=self._predict([frame],self.imgsz)[0]
        if self.tiling:
            # Tiled inference sees small objects at native resolution; the full-frame pass keeps large objects whole.
            if self.slicer is None: self.slicer=sv.InferenceSlicer(callback=lambda tiles:self._predict(tiles,TILE),slice_wh=TILE,overlap_wh=TILE_OVERLAP,iou_threshold=.5,batch_size=8)
            parts=[d for d in (detections,self.slicer(frame)) if len(d)]
            detections=sv.Detections.merge(parts).with_nms(threshold=.5) if parts else sv.Detections.empty()
        return filter_detections(detections,self.min_box)

class ByteTracker:
    def __init__(self,fps=10):
        from trackers import ByteTrackTracker
        self.tracker=ByteTrackTracker(frame_rate=fps)
        self.last_time=-1
    def update(self,detections,timestamp):
        if timestamp<=self.last_time: raise ValueError('Tracker timestamps must increase')
        self.last_time=timestamp
        tracked = self.tracker.update(detections, timestamp=timestamp)
        return tracked[tracked.tracker_id >= 0]

def normalize(detections,width,height,names=None):
    names=names or CLASSES; results=[]
    if detections.tracker_id is None: return results
    for box,confidence,cls,tid in zip(detections.xyxy,detections.confidence,detections.class_id,detections.tracker_id):
        if int(cls) not in names: continue
        box=np.clip(box/np.array([width,height,width,height]),0,1).tolist()
        name=names[int(cls)]; prefix='P' if name=='person' else 'V' if name in VEHICLES else 'O'
        results.append(dict(track_id=f"{prefix}-{int(tid):04d}",object_class=name,confidence=float(confidence),box=box,position=[(box[0]+box[2])/2,box[3]]))
    return results
