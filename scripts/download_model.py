"""Explicit model download only. Never downloads videos or other demonstration footage."""
import sys, urllib.request
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.argus.config import settings
path=Path(settings.model_path);path.parent.mkdir(parents=True,exist_ok=True)
if path.exists(): print('Model already exists:',path)
else:
    url='https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11n.pt'
    temporary=path.with_suffix('.download')
    try:
        urllib.request.urlretrieve(url,temporary)
        temporary.replace(path)
        print('Downloaded official YOLO11n COCO weights:',path)
    finally: temporary.unlink(missing_ok=True)
