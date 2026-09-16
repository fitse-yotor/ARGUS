import numpy as np
import supervision as sv
from backend.argus.vision import normalize,ByteTracker
from backend.argus.simulation import SimulatedCSIProvider,RealCSIProvider,MODES
import pytest

def test_detection_normalization():
    d=sv.Detections(xyxy=np.array([[10,20,30,60]],dtype=float),confidence=np.array([.8]),class_id=np.array([0]),tracker_id=np.array([7]))
    o=normalize(d,100,100)[0];assert o['track_id']=='P-0007';assert o['position']==[.2,.6]

def test_tracker_contract():
    tracker=ByteTracker();ids=[]
    for frame in range(8):
        d=sv.Detections(xyxy=np.array([[10+frame,20,40+frame,80]],dtype=float),confidence=np.array([.95]),class_id=np.array([0]))
        tracked=tracker.update(d,frame/10)
        if len(tracked):ids.append(int(tracked.tracker_id[0]))
    assert len(ids)>=4 and len(set(ids))==1
    with pytest.raises(ValueError):tracker.update(d,.1)

def test_simulation():
    p=SimulatedCSIProvider()
    for mode in MODES:
        a=p.observe(mode,3);assert a==p.observe(mode,3);assert a['validation']=='SIMULATED';assert len(a['nodes'])==2
    assert not p.observe('No Person',1)['presence']
    assert p.observe('Walk',1)['x']!=p.observe('Walk',2)['x']
    assert p.observe('Sit',1)['pose']=='SITTING'
    assert not p.observe('Exit Room',10)['presence']
    with pytest.raises(NotImplementedError):RealCSIProvider().observe('Walk',0)
