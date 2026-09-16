"""Explicit download of the CLIP model used for appearance search (~600 MB). Never downloads footage."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import open_clip
from backend.argus.visual import MODEL, PRETRAINED, CACHE, available
CACHE.mkdir(parents=True,exist_ok=True)
open_clip.create_model_and_transforms(MODEL,pretrained=PRETRAINED,cache_dir=str(CACHE))
print('CLIP model ready:' if available() else 'CLIP download did not produce weights in', CACHE)
