"""Local CLIP appearance index over per-track crops (open_clip ViT-B-32, LAION-2B weights).
Embeddings describe visible appearance for search ranking only; there is no face or identity recognition."""
import os, threading
from pathlib import Path
import cv2
import numpy as np
from .config import settings

MODEL='ViT-B-32'; PRETRAINED='laion2b_s34b_b79k'
CACHE=settings.storage_dir/'models'/'clip'
MEAN=np.array([0.48145466,0.4578275,0.40821073],np.float32); STD=np.array([0.26862954,0.26130258,0.27577711],np.float32)
MIN_CROP=16
_lock=threading.Lock(); _loaded=None; _cache={}

def available():
    return CACHE.is_dir() and any(p.name in ('open_clip_model.safetensors','open_clip_pytorch_model.bin') for p in CACHE.rglob('open_clip_*'))

def load():
    global _loaded
    with _lock:
        if _loaded is None:
            if not available(): raise RuntimeError('Visual search model not installed; run scripts/download_clip.py')
            # Runtime never downloads; weights come only from the explicit download script.
            os.environ.setdefault('HF_HUB_OFFLINE','1')
            import open_clip, torch
            from .vision import resolve_device
            model,_,_=open_clip.create_model_and_transforms(MODEL,pretrained=PRETRAINED,cache_dir=str(CACHE))
            model=model.eval(); tokenizer=open_clip.get_tokenizer(MODEL); device=resolve_device(settings.device)
            try:
                model=model.to(device)
                with torch.inference_mode(): model.encode_text(tokenizer(['warm up']).to(device))
            except Exception: device='cpu'; model=model.to('cpu')
            _loaded=(model,tokenizer,device)
        return _loaded

def _batch(crops):
    import torch
    items=[]
    for crop in crops:
        h,w=crop.shape[:2]; side=max(h,w); square=np.full((side,side,3),127,np.uint8)
        square[(side-h)//2:(side-h)//2+h,(side-w)//2:(side-w)//2+w]=crop
        rgb=cv2.cvtColor(cv2.resize(square,(224,224),interpolation=cv2.INTER_CUBIC),cv2.COLOR_BGR2RGB)
        items.append((rgb.astype(np.float32)/255-MEAN)/STD)
    arr=np.ascontiguousarray(np.stack(items).transpose(0,3,1,2),dtype=np.float32)
    # Buffer conversion avoids the torch.from_numpy bridge that is broken on Intel Mac PyTorch 2.2 with NumPy 2.
    return torch.frombuffer(bytearray(arr.tobytes()),dtype=torch.float32).reshape(arr.shape)

def _normalized(features):
    features=features/features.norm(dim=-1,keepdim=True)
    return np.asarray(features.float().cpu().tolist(),dtype=np.float32)

def embed_images(crops,batch=32):
    import torch
    model,_,device=load(); out=[]
    with torch.inference_mode():
        for i in range(0,len(crops),batch): out.append(_normalized(model.encode_image(_batch(crops[i:i+batch]).to(device))))
    return np.concatenate(out) if out else np.zeros((0,512),np.float32)

def embed_text(text):
    import torch
    model,tokenizer,device=load()
    with torch.inference_mode(): return _normalized(model.encode_text(tokenizer([text]).to(device)))[0]

def update_best(best,objects,xyxy,frame):
    """Keeps the most confident, largest view of each track for appearance indexing."""
    h,w=frame.shape[:2]
    for o,(x1,y1,x2,y2) in zip(objects,xyxy):
        bw,bh=x2-x1,y2-y1
        if min(bw,bh)<MIN_CROP: continue
        score=o['confidence']*float(np.sqrt(bw*bh))
        if score<=best.get(o['track_id'],(0,None))[0]: continue
        mx,my=bw*.08,bh*.08
        crop=frame[int(max(0,y1-my)):int(min(h,y2+my)),int(max(0,x1-mx)):int(min(w,x2+mx))]
        scale=256/max(crop.shape[:2])
        best[o['track_id']]=(score,cv2.resize(crop,None,fx=scale,fy=scale,interpolation=cv2.INTER_AREA) if scale<1 else crop.copy())

def save_crops(folder,best,track_ids=None):
    target=Path(folder)/'crops'; target.mkdir(parents=True,exist_ok=True)
    for tid in (best if track_ids is None else track_ids):
        if tid in best: cv2.imwrite(str(target/f'{tid}.jpg'),best[tid][1],[cv2.IMWRITE_JPEG_QUALITY,90])

def index_folder(folder,embedder=None):
    """Embeds every crops/*.jpg into visual.npz; returns the number of indexed tracks."""
    pairs=[(p.stem,img) for p in sorted((Path(folder)/'crops').glob('*.jpg')) if (img:=cv2.imread(str(p))) is not None]
    if not pairs: return 0
    save_vectors(folder,[i for i,_ in pairs],(embedder or embed_images)([img for _,img in pairs])); return len(pairs)

def save_vectors(folder,ids,vectors):
    path=Path(folder)/'visual.npz'; tmp=path.with_name('visual.tmp.npz')
    np.savez(tmp,ids=np.array(ids),vectors=np.asarray(vectors,np.float16)); tmp.replace(path); _cache.pop(str(path),None)

def vectors(folder):
    path=Path(folder)/'visual.npz'
    if not path.is_file(): return {}
    key=str(path); mtime=path.stat().st_mtime
    if key not in _cache or _cache[key][0]!=mtime:
        with np.load(path) as data: _cache[key]=(mtime,dict(zip(data['ids'].tolist(),data['vectors'].astype(np.float32))))
    return _cache[key][1]

def rank(prompt,candidates,embedder=None):
    """Cosine similarity between the prompt and each (job_id, track_id) that has a stored crop embedding."""
    text=(embedder or embed_text)(prompt); scores={}
    for job_id,track_id in candidates:
        vector=vectors(settings.storage_dir/'jobs'/job_id).get(track_id)
        if vector is not None: scores[(job_id,track_id)]=float(np.dot(vector,text))
    return scores
