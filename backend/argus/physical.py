"""Ground-plane calibration: four operator-clicked road points with measured width and length map
frame coordinates to metres through a homography. Speeds and distances are estimates; accuracy depends on
the reference measurements, a fixed camera and a flat road inside the calibrated area."""
import math
from collections import deque
import numpy as np
from shapely.geometry import Point, Polygon

MAX_SPEED_KMH=250  # larger implied speeds come from ID switches or calibration error, never from road traffic

def homography(src,dst):
    rows=[]; rhs=[]
    for (x,y),(u,v) in zip(src,dst):
        rows+=[[x,y,1,0,0,0,-u*x,-u*y],[0,0,0,x,y,1,-v*x,-v*y]]; rhs+=[u,v]
    try: h=np.linalg.solve(np.array(rows,float),np.array(rhs,float))
    except np.linalg.LinAlgError: raise ValueError('Calibration points are degenerate; click four distinct road corners')
    return np.append(h,1).reshape(3,3)

class Calibration:
    """Point 1→2 spans the measured width and point 2→3 the measured length of a road rectangle."""
    def __init__(self,geometry):
        self.name=geometry.get('name','Calibration'); self.points=[list(p) for p in geometry['points']]
        self.width_m=float(geometry['width_m']); self.length_m=float(geometry['length_m'])
        self.matrix=homography(self.points,[[0,0],[self.width_m,0],[self.width_m,self.length_m],[0,self.length_m]])
        # Buffered once: `covers` runs for every vehicle in every analysed frame.
        self.area=Polygon(self.points).buffer(1e-6)
        # Points beyond the horizon project with the opposite homogeneous sign and have no ground position.
        self.sign=math.copysign(1,(self.matrix@[*self.area.centroid.coords[0],1])[2])
    @staticmethod
    def find(geometries):
        g=next((g for g in geometries if g.get('kind')=='calibration' and g.get('enabled',True)),None)
        return Calibration(g) if g else None
    def to_metres(self,point):
        x,y,w=self.matrix@[point[0],point[1],1]
        return None if w*self.sign<=1e-9 else (x/w,y/w)
    def covers(self,point): return self.area.covers(Point(point))

class SpeedEstimator:
    """Least-squares ground velocity per track over a short sliding window. History restarts after a sampling
    gap or an implausible jump, so an ID switch yields no speed rather than a spike."""
    def __init__(self,fps=10,max_gap=1.5,max_speed_kmh=MAX_SPEED_KMH):
        self.window=max(1.,2/max(fps,.1)); self.min_span=min(.4,self.window/2); self.max_gap=max_gap; self.max_speed=max_speed_kmh; self.history={}
    def update(self,track_id,metres,t):
        h=self.history.setdefault(track_id,deque())
        if h and (t-h[-1][0]>self.max_gap or t<=h[-1][0] or math.dist(h[-1][1:],metres)/(t-h[-1][0])*3.6>self.max_speed): h.clear()
        h.append((t,*metres))
        while h[0][0]<t-self.window: h.popleft()
        if len(h)<3 or h[-1][0]-h[0][0]<self.min_span: return None
        samples=np.array(h); times=samples[:,0]-samples[0,0]
        vx=np.polyfit(times,samples[:,1],1)[0]; vy=np.polyfit(times,samples[:,2],1)[0]
        kmh=math.hypot(vx,vy)*3.6
        return round(kmh,1) if kmh<=self.max_speed else None
    def forget(self,track_id): self.history.pop(track_id,None)
