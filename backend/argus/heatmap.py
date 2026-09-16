"""Occupancy heatmaps: seconds of observed presence per cell of a frame-relative grid."""
import cv2
import numpy as np
from .analytics import VEHICLES

GROUPS=('all','person','vehicle','other')

class Heatmap:
    def __init__(self,cols=160,rows=90):
        self.cols,self.rows=cols,rows; self.seconds=0.
        self.grid={g:np.zeros((rows,cols),np.float32) for g in GROUPS}
    def add(self,objects,seconds):
        """Each observed anchor adds the sampling interval, so cells accumulate object-seconds."""
        self.seconds+=seconds
        for o in objects:
            x=min(self.cols-1,max(0,int(o['position'][0]*self.cols))); y=min(self.rows-1,max(0,int(o['position'][1]*self.rows)))
            group='person' if o['object_class']=='person' else 'vehicle' if o['object_class'] in VEHICLES else 'other'
            self.grid['all'][y,x]+=seconds; self.grid[group][y,x]+=seconds
    def save(self,path):
        tmp=path.with_name(path.stem+'.tmp.npz'); np.savez_compressed(tmp,seconds=np.float32(self.seconds),**self.grid); tmp.replace(path)

def render(path,group='all',width=640,height=360):
    """Transparent PNG overlay. Colour is square-root normalized so brief paths stay visible beside busy areas."""
    with np.load(path) as data:
        grid=data[group] if group in data.files else data['all']; seconds=float(data['seconds'])
    peak=float(grid.max()); rgba=np.zeros((height,width,4),np.uint8)
    if peak>0:
        smooth=cv2.GaussianBlur(cv2.resize(grid,(width,height),interpolation=cv2.INTER_LINEAR),(0,0),sigmaX=max(2.,width/120))
        level=(np.sqrt(np.clip(smooth/max(1e-6,float(smooth.max())),0,1))*255).astype(np.uint8)
        rgba[...,:3]=cv2.applyColorMap(level,cv2.COLORMAP_TURBO)
        rgba[...,3]=np.where(level>12,np.clip(level.astype(np.int32)*.85+40,0,215),0).astype(np.uint8)
    return cv2.imencode('.png',rgba)[1].tobytes(),peak,seconds
