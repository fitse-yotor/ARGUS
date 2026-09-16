from typing import Literal
from pydantic import BaseModel, Field, model_validator, field_validator
from .analytics import validate_geometry, ZONE_TYPES
from .vision import COCO_NAMES

def class_filter(value):
    if value is None: return None
    unknown=[c for c in value if c not in COCO_NAMES and c!='vehicle']
    if unknown: raise ValueError(f'Unknown classes: {", ".join(unknown)}')
    return list(dict.fromkeys(value)) or None

class DetectionFilters(BaseModel):
    classes:list[str]|None=Field(default=None,max_length=81)
    tiling:bool=False
    min_box:int=Field(default=0,ge=0,le=500)
    _classes=field_validator('classes')(class_filter)
class LoginInput(BaseModel):
    username:str=Field(min_length=1,max_length=80)
    password:str=Field(min_length=1,max_length=200)
class UserInput(LoginInput):
    role:str='Operator'
class GeometryInput(BaseModel):
    kind:Literal['zone','line','route','calibration']='zone'
    name:str=Field(min_length=1,max_length=120)
    type:str='Crowd Zone'
    object_class:Literal['all','person','vehicle','car','bus','truck','motorcycle']='all'
    points:list[list[float]]=Field(max_length=64)
    # Measured ground dimensions of the calibration rectangle: point 1→2 is the width, point 2→3 the length.
    width_m:float|None=Field(default=None,ge=.5,le=5000)
    length_m:float|None=Field(default=None,ge=.5,le=5000)
    speed_limit_kmh:float=Field(default=0,ge=0,le=400)
    threshold:int=Field(default=10,ge=1,le=100000)
    elevated_ratio:float=Field(default=.8,gt=0,lt=1)
    critical_ratio:float=Field(default=1.25,gt=1,le=10)
    dwell_seconds:float=Field(default=30,ge=0,le=7200)
    stop_seconds:float=Field(default=10,gt=0,le=7200)
    severity:Literal['LOW','MEDIUM','HIGH','CRITICAL']='MEDIUM'
    enabled:bool=True
    events:bool=True
    @model_validator(mode='after')
    def valid(self):
        validate_geometry(self.kind,self.points)
        if self.kind=='zone' and self.type not in ZONE_TYPES: raise ValueError('Unknown zone type')
        if self.kind=='calibration':
            if not (self.width_m and self.length_m): raise ValueError('Calibration needs the measured road width and length in metres')
            # Rejects a homography that cannot be solved from these four corners.
            from .physical import Calibration
            Calibration(self.model_dump())
        return self
class JobInput(DetectionFilters):
    mode:Literal['Detect & Annotate','Event / Crowd','Traffic','Convoy','General']='General'
    fps:float=Field(default=10,ge=1,le=30)
    confidence:float=Field(default=.3,ge=.05,le=.95)
    congestion_count:int=Field(default=12,ge=1,le=10000)
    # Speed at which the calibrated road is considered to flow freely; states fall as measured speed drops below it.
    free_flow_kmh:float=Field(default=50,ge=5,le=200)
    stop_seconds:float=Field(default=10,gt=0,le=7200)
    stop_distance:float=Field(default=.015,gt=0,le=.2)
    imgsz:Literal[640,960,1280]=640
class ReviewInput(BaseModel):
    action:Literal['VERIFIED','DISMISSED','UNDER REVIEW']
    note:str=Field(default='',max_length=4000)
class IncidentInput(BaseModel):
    title:str=Field(min_length=1,max_length=200)
    category:str=Field(min_length=1,max_length=80)
    priority:Literal['LOW','MEDIUM','HIGH','CRITICAL']='MEDIUM'
class IncidentUpdate(BaseModel):
    state:Literal['VERIFIED','ASSIGNED','RESPONDING','MONITORING','RESOLVED','CLOSED']
    assignment:str|None=None
    note:str=Field(default='',max_length=4000)
    priority:Literal['LOW','MEDIUM','HIGH','CRITICAL']='MEDIUM'
class LocationInput(BaseModel):
    name:str=Field(max_length=120)
    latitude:float=Field(ge=-90,le=90)
    longitude:float=Field(ge=-180,le=180)
class ConvoyInput(BaseModel):
    role:Literal['Convoy Lead','Convoy Vehicle']
    video_time:float=Field(ge=0)
class SimInput(BaseModel):
    mode:str
    speed:float=Field(default=1,ge=.25,le=4)
class RoleUpdate(BaseModel):
    permissions:list[str]
class ModelInput(BaseModel):
    name:str=Field(min_length=1,max_length=100)
    version:str=Field(min_length=1,max_length=100)
    filename:str=Field(min_length=1,max_length=200)
class ModelState(BaseModel):
    state:Literal['TESTING','APPROVED','ACTIVE','DEPRECATED','DISABLED']
class UserRoleInput(BaseModel):
    role:str
LIVE_MODES=Literal['Detect & Annotate','Event / Crowd','Traffic','Convoy','General']
class CameraInput(DetectionFilters):
    name:str=Field(min_length=1,max_length=120)
    url:str=Field(min_length=8,max_length=2000)
    mode:LIVE_MODES='Detect & Annotate'
    fps:float=Field(default=5,ge=1,le=15)
    confidence:float=Field(default=.3,ge=.05,le=.95)
    imgsz:Literal[640,960,1280]=960
    width:Literal[640,960,1280,1920]=1280
    enabled:bool=True
class CameraUpdate(BaseModel):
    name:str|None=Field(default=None,min_length=1,max_length=120)
    url:str|None=Field(default=None,min_length=8,max_length=2000)
    mode:LIVE_MODES|None=None
    fps:float|None=Field(default=None,ge=1,le=15)
    confidence:float|None=Field(default=None,ge=.05,le=.95)
    imgsz:Literal[640,960,1280]|None=None
    width:Literal[640,960,1280,1920]|None=None
    enabled:bool|None=None
    classes:list[str]|None=Field(default=None,max_length=81)
    tiling:bool|None=None
    min_box:int|None=Field(default=None,ge=0,le=500)
    _classes=field_validator('classes')(class_filter)
class LockInput(BaseModel):
    track_id:str|None=Field(default=None,pattern=r'^[POV]-\d{4}$')
class LiveConvoyInput(BaseModel):
    """Designates a vehicle visible in the running camera session; a null role clears the designation."""
    track_id:str=Field(pattern=r'^V-\d{4}$')
    role:Literal['Convoy Lead','Convoy Vehicle']|None=None
class SaveDetectionInput(BaseModel):
    job_id:str|None=None
    camera_id:str|None=None
    video_time:float=Field(default=0,ge=0)
    note:str=Field(default='',max_length=1000)
    classes:list[str]|None=Field(default=None,max_length=81)
    min_confidence:float=Field(default=0,ge=0,le=1)
    _classes=field_validator('classes')(class_filter)
    @model_validator(mode='after')
    def one_source(self):
        if bool(self.job_id)==bool(self.camera_id): raise ValueError('Provide either job_id (recorded video) or camera_id (live camera)')
        return self
