import math
from typing import Protocol
MODES=['No Person','Enter Room','Walk','Stand','Sit','Fall','Exit Room','Random Movement','Moving Left','Moving Right']
LABEL='SIMULATED RF/CSI DATA — MVP DEMONSTRATION'
class SensorProvider(Protocol):
    def observe(self,mode:str,elapsed:float,speed:float=1)->dict: ...
class RealCSIProvider:
    def observe(self,mode,elapsed,speed=1):
        raise NotImplementedError('Real CSI requires a calibrated hardware service implementing SensorProvider')
class SimulatedCSIProvider:
    def observe(self,mode,elapsed,speed=1):
        if mode not in MODES: raise ValueError('Unknown simulation mode')
        t=max(0,elapsed)*speed; x,y=4.,3.; presence=mode!='No Person'; movement='STATIONARY'
        if mode in ['Walk','Random Movement']:
            x=4+2.4*math.sin(t*.35); y=3+1.5*math.sin(t*.22); movement='WALKING'
        if mode=='Moving Left': x=6-(t*.5)%4; movement='WEST'
        if mode=='Moving Right': x=2+(t*.5)%4; movement='EAST'
        if mode=='Enter Room': x=min(4,t*.6); movement='EAST' if x<4 else 'STATIONARY'
        if mode=='Exit Room': x=max(0,4-t*.6); presence=x>0; movement='WEST'
        pose='SITTING' if mode=='Sit' else 'FALLING' if mode=='Fall' else 'STANDING'
        swing=math.sin(t*4)*.13 if movement!='STATIONARY' else 0
        joints=[[0,-.45],[0,-.25],[-.2,-.18],[.2,-.18],[-.3,.03+swing],[.3,.03-swing],[0,.08],[-.15,.35+swing],[.15,.35-swing]]
        if pose=='SITTING': joints[7:]=[[-.3,.16],[.3,.16]]
        if pose=='FALLING':
            angle=min(1,t/1.5)*math.pi/2
            joints=[[a*math.cos(angle)-b*math.sin(angle),a*math.sin(angle)+b*math.cos(angle)] for a,b in joints]
        return dict(sensor='RF-ROOM-01',timestamp=t,presence=presence,x=x,y=y,pose=pose if presence else 'NONE',movement=movement if presence else 'NONE',confidence=round(.88+.035*math.sin(t),3) if presence else .96,validation='SIMULATED',source='SIMULATED CSI',label=LABEL,joints=joints if presence else [],nodes=[dict(id='RF-01',x=1,y=1,quality=round(.92+.02*math.sin(t),3)),dict(id='RF-02',x=7,y=5,quality=round(.87+.03*math.cos(t),3))],csi_amplitude=[round(1+.12*math.sin(i*.3+t)+(0.1*math.cos(i+t*2) if presence else 0),3) for i in range(32)])
