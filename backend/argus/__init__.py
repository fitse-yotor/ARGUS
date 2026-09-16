"""ARGUS shared application contracts."""
import os
from pathlib import Path
_cache=Path(os.environ.get('STORAGE_DIR','storage'))/'cache'
_cache.mkdir(parents=True,exist_ok=True)
os.environ.setdefault('MPLCONFIGDIR',str(_cache/'matplotlib'))
os.environ.setdefault('YOLO_CONFIG_DIR',str(_cache/'ultralytics'))
os.environ.setdefault('XDG_CACHE_HOME',str(_cache))
