import asyncio, csv, hashlib, io, json, re, secrets, time, shutil
import cv2
from pathlib import Path
from collections import Counter, deque
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Response, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from sqlalchemy import select, delete, func, text
from sqlalchemy.exc import SQLAlchemyError
from .config import settings
from .db import *
from .security import current_user, permit, passwords, ROLES, permissions_for
from .schemas import *
from .media import metadata, prepare
from .analytics import VEHICLES

VIDEO_SUFFIXES={'.mp4','.m4v','.mov','.avi','.mkv','.webm','.mpg','.mpeg','.3gp','.wmv','.flv','.ts','.mts','.m2ts','.ogv'}
from .simulation import SimulatedCSIProvider, MODES
from . import search, visual
from .heatmap import render as render_heatmap, GROUPS
from .render import draw_objects
from .sources import validate_url, mask
from .live import LIVE_DIR

app=FastAPI(title='ARGUS API',version='0.1.0',description='See. Sense. Understand. Respond. Human-reviewed video analytics and explicitly simulated CSI.')

def require(db,model,id):
    item=db.get(model,id)
    if item is None: raise HTTPException(404,f'{model.__name__} not found')
    return item

def event_json(event):
    return {**serialize(event),'snapshot_url':f'/api/events/{event.id}/snapshot' if event.snapshot else None,'clip_url':f'/api/events/{event.id}/clip' if event.clip else None}

@app.exception_handler(SQLAlchemyError)
async def db_failure(request,exc): return JSONResponse(status_code=503,content={'detail':'Database unavailable; operation not completed'})

@app.post('/api/auth/login')
def login(data:LoginInput,response:Response,db=Depends(get_db)):
    recent=db.scalar(select(func.count()).select_from(Audit).where(Audit.actor==data.username,Audit.action=='login_failed',Audit.created_at>datetime.fromtimestamp(time.time()-300,timezone.utc).isoformat()))
    if recent>=10: raise HTTPException(429,'Too many attempts; retry in five minutes')
    user=db.scalar(select(User).where(User.username==data.username))
    valid=user and user.enabled and passwords.verify(data.password,user.password)
    if not valid:
        audit(db,data.username,'login_failed'); db.commit(); raise HTTPException(401,'Invalid credentials')
    token=secrets.token_urlsafe(40)
    db.add(Session(token_hash=hashlib.sha256(token.encode()).hexdigest(),user_id=user.id,expires=time.time()+settings.session_hours*3600))
    audit(db,user.username,'login'); db.commit()
    response.set_cookie('argus_session',token,httponly=True,samesite='strict',secure=settings.cookie_secure,max_age=settings.session_hours*3600)
    return {**serialize(user),'permissions':permissions_for(db,user)}

@app.get('/api/auth/me')
def me(user=Depends(current_user),db=Depends(get_db)): return {**serialize(user),'permissions':permissions_for(db,user)}

@app.post('/api/auth/logout')
def logout(request:Request,response:Response,user=Depends(current_user),db=Depends(get_db)):
    db.execute(delete(Session).where(Session.token_hash==hashlib.sha256(request.cookies.get('argus_session','').encode()).hexdigest()))
    audit(db,user.username,'logout'); db.commit(); response.delete_cookie('argus_session'); return {'ok':True}

@app.get('/api/videos')
def videos(user=Depends(current_user),db=Depends(get_db)):
    return [serialize(v) for v in db.scalars(select(Video).where(Video.archived==False,~Video.path.like('live://%')).order_by(Video.created_at.desc()))]

@app.post('/api/videos')
def upload(file:UploadFile=File(...),user=Depends(permit('operate')),db=Depends(get_db)):
    filename=Path((file.filename or '').replace('\\','/')).name
    suffix=Path(filename).suffix.lower(); ctype=file.content_type or ''
    # Browsers send inconsistent MIME types for MKV/TS/FLV; the decoder check below is the real validation.
    if suffix not in VIDEO_SUFFIXES or (ctype and not ctype.startswith('video/') and ctype!='application/octet-stream'):
        raise HTTPException(415,'Upload a video file: '+', '.join(sorted(s[1:].upper() for s in VIDEO_SUFFIXES)))
    folder=settings.storage_dir/'uploads'; folder.mkdir(exist_ok=True)
    vid=uid(); source=folder/f'{vid}.source{suffix}'; working=folder/f'{vid}.mp4'; size=0
    try:
        with source.open('wb') as out:
            while chunk:=file.file.read(1024*1024):
                size+=len(chunk)
                if size>settings.upload_limit_mb*1024**2: raise HTTPException(413,'Upload size limit exceeded')
                out.write(chunk)
        # The original is retained unchanged; analysis and playback use the normalized H.264 copy.
        prepare(source,working)
        meta={**metadata(working),'source_format':suffix[1:].upper(),'source_size':size}
        v=Video(id=vid,filename=filename[:255],path=str(working),playback=str(working),metadata_json=meta); db.add(v); db.flush()
        audit(db,user.username,'video_uploaded',v.id,meta); db.commit(); return serialize(v)
    except Exception as exc:
        source.unlink(missing_ok=True); working.unlink(missing_ok=True)
        if isinstance(exc,HTTPException): raise
        if isinstance(exc,ValueError): raise HTTPException(422,str(exc))
        raise
    finally: file.file.close()

@app.get('/api/videos/{id}/media')
def video_media(id:str,user=Depends(current_user),db=Depends(get_db)):
    v=require(db,Video,id); path=Path(v.playback or v.path)
    if not path.is_file(): raise HTTPException(404,'Video media missing')
    audit(db,user.username,'evidence_access',id); db.commit()
    return FileResponse(path,media_type='video/mp4' if path.suffix=='.mp4' else None)

@app.put('/api/videos/{id}/location')
def location(id:str,data:LocationInput,user=Depends(permit('configure')),db=Depends(get_db)):
    v=require(db,Video,id); v.location={**data.model_dump(),'source':'OPERATOR SUPPLIED'}; audit(db,user.username,'location_changed',id,v.location); db.commit(); return serialize(v)

@app.post('/api/videos/{id}/archive')
def archive(id:str,user=Depends(permit('admin')),db=Depends(get_db)):
    v=require(db,Video,id); v.archived=True; audit(db,user.username,'video_archived',id); db.commit(); return {'ok':True}

@app.get('/api/videos/{id}/geometries')
def geometries(id:str,user=Depends(current_user),db=Depends(get_db)):
    require(db,Video,id)
    return [{**g.config,'id':g.id,'kind':g.kind} for g in db.scalars(select(Geometry).where(Geometry.video_id==id))]

@app.post('/api/videos/{id}/geometries')
def add_geometry(id:str,data:GeometryInput,user=Depends(permit('configure')),db=Depends(get_db)):
    require(db,Video,id)
    # One ground plane per camera view: a second calibration would make speeds ambiguous.
    if data.kind=='calibration' and db.scalar(select(Geometry).where(Geometry.video_id==id,Geometry.kind=='calibration')): raise HTTPException(409,'This view already has a road calibration; edit or delete it first')
    g=Geometry(video_id=id,kind=data.kind,config=data.model_dump()); db.add(g); db.flush(); audit(db,user.username,'geometry_created',g.id,g.config); db.commit(); return {**g.config,'id':g.id}

@app.put('/api/geometries/{id}')
def edit_geometry(id:str,data:GeometryInput,user=Depends(permit('configure')),db=Depends(get_db)):
    g=require(db,Geometry,id); g.kind=data.kind; g.config=data.model_dump(); audit(db,user.username,'geometry_changed',id,g.config); db.commit(); return {**g.config,'id':g.id}

@app.delete('/api/geometries/{id}')
def delete_geometry(id:str,user=Depends(permit('configure')),db=Depends(get_db)):
    g=require(db,Geometry,id); db.delete(g); audit(db,user.username,'geometry_deleted',id); db.commit(); return {'ok':True}

@app.post('/api/videos/{id}/jobs')
def enqueue(id:str,data:JobInput,user=Depends(permit('operate')),db=Depends(get_db)):
    require(db,Video,id)
    if db.scalar(select(Job).where(Job.video_id==id,Job.state.in_(['QUEUED','PROCESSING']))): raise HTTPException(409,'This video already has an active job')
    config=data.model_dump(); config['geometries']=[{**g.config,'id':g.id,'kind':g.kind} for g in db.scalars(select(Geometry).where(Geometry.video_id==id))]
    active=db.scalar(select(AIModel).where(AIModel.state=='ACTIVE'))
    if not active and db.scalar(select(AIModel)): raise HTTPException(409,'No active approved model; activate one in Administration')
    config['model']=str(settings.storage_dir/'models'/active.filename) if active else settings.model_path; config['device']=settings.device
    config['model_version']=active.version if active else 'Configured local model'
    j=Job(video_id=id,mode=data.mode,config=config); db.add(j); db.flush(); audit(db,user.username,'analysis_started',j.id,config); db.commit(); return serialize(j)

@app.get('/api/jobs')
def jobs(video_id:str|None=None,user=Depends(current_user),db=Depends(get_db)):
    q=select(Job).order_by(Job.created_at.desc())
    if video_id: q=q.where(Job.video_id==video_id)
    return [{**serialize(j),'annotated_available':annotated_path(j).is_file(),'heatmap_available':(job_folder(j)/'heatmap.npz').is_file()} for j in db.scalars(q)]

def annotated_path(job): return settings.storage_dir/'jobs'/job.id/'annotated.mp4'

@app.get('/api/jobs/{id}/annotated')
def annotated_video(id:str,download:bool=False,user=Depends(current_user),db=Depends(get_db)):
    j=require(db,Job,id); path=annotated_path(j)
    if not path.is_file(): raise HTTPException(404,'Annotated video is available after analysis completes')
    audit(db,user.username,'evidence_access',id,{'artifact':'annotated_video','download':download}); db.commit()
    name=Path(require(db,Video,j.video_id).filename).stem+'-argus-annotated.mp4'
    return FileResponse(path,media_type='video/mp4',filename=name,content_disposition_type='attachment' if download else 'inline')

@app.post('/api/jobs/{id}/cancel')
def cancel(id:str,user=Depends(permit('operate')),db=Depends(get_db)):
    j=require(db,Job,id)
    if j.state not in ['QUEUED','PROCESSING']: raise HTTPException(409,'Job is already terminal')
    j.state='CANCELLED'; audit(db,user.username,'analysis_cancelled',id); db.commit(); return serialize(j)

@app.get('/api/jobs/{id}/observations')
def observations(id:str,start:float=0,end:float=30,user=Depends(current_user),db=Depends(get_db)):
    j=require(db,Job,id)
    if end<start or end-start>120: raise HTTPException(422,'Request a time window of at most 120 seconds')
    result=[]
    if j.observations and Path(j.observations).exists():
        with open(j.observations) as f:
            for line in f:
                try: row=json.loads(line)
                except json.JSONDecodeError: continue
                if row['time']>end: break
                if row['time']>=start: result.append(row)
    return result

@app.get('/api/jobs/{id}/tracks')
def tracks(id:str,user=Depends(current_user),db=Depends(get_db)):
    require(db,Job,id); return [serialize(t) for t in db.scalars(select(Track).where(Track.job_id==id))]

@app.post('/api/tracks/{id}/convoy')
def convoy(id:str,data:ConvoyInput,user=Depends(permit('operate')),db=Depends(get_db)):
    tr=require(db,Track,id); j=require(db,Job,tr.job_id)
    if j.mode!='Convoy' or tr.object_class not in VEHICLES: raise HTTPException(422,'Select a vehicle from a Convoy analysis')
    if not tr.data['first_seen']<=data.video_time<=tr.data['last_seen']: raise HTTPException(422,'Track is not observable at this video time')
    # Confirm an actual observation at the selected time, including gaps in a track.
    visible=False
    if j.observations:
        with open(j.observations) as f:
            for line in f:
                row=json.loads(line)
                if abs(row['time']-data.video_time)<=1/max(1,j.config['fps'])+.1 and any(o['track_id']==tr.track_id for o in row['objects']): visible=True; break
    if not visible: raise HTTPException(422,'Vehicle is not visible at the selected time')
    if data.role=='Convoy Lead':
        for lead in db.scalars(select(Track).where(Track.job_id==j.id,Track.convoy_role=='Convoy Lead')): lead.convoy_role='Convoy Vehicle'
    tr.convoy_role=data.role; tr.designated_at=data.video_time
    # Retrospective rule evaluation on persisted observations, never synthetic events.
    from .convoy import read_rows
    import cv2
    already=db.scalar(select(Event).where(Event.job_id==j.id,Event.track_id==tr.track_id,Event.type=='Convoy Traffic Delay'))
    if not already:
        cap=None
        try:
            active=False
            for row in read_rows(j,data.video_time):
                observed=next((o for o in row['objects'] if o['track_id']==tr.track_id),None)
                delayed=bool(observed and (observed.get('stopped_seconds',0)>=j.config.get('stop_seconds',10) or row['analytics']['traffic_state']=='CONGESTED'))
                if delayed and not active:
                    if cap is None: cap=cv2.VideoCapture(require(db,Video,j.video_id).path)
                    cap.set(cv2.CAP_PROP_POS_MSEC,row['time']*1000); ok,frame=cap.read()
                    snapshot_path=None
                    if ok:
                        target=settings.storage_dir/'jobs'/j.id/(uid()+'.jpg')
                        if cv2.imwrite(str(target),frame): snapshot_path=str(target)
                    db.add(Event(job_id=j.id,video_id=j.video_id,type='Convoy Traffic Delay',video_time=row['time'],frame=row['frame'],track_id=tr.track_id,object_class=tr.object_class,confidence=observed['confidence'],priority='MEDIUM',snapshot=snapshot_path,rule={'name':'Designated convoy vehicle stopped or configured congestion','designation_time':data.video_time,'stop_seconds':j.config.get('stop_seconds',10),'congestion_count':j.config.get('congestion_count',12)},analytics=row['analytics']))
                active=delayed
        finally:
            if cap is not None: cap.release()
    audit(db,user.username,'convoy_designated',id,data.model_dump()); db.commit()
    return serialize(tr)

@app.get('/api/events')
@app.get('/api/search')
def events(request:Request,response:Response,video_id:str|None=None,job_id:str|None=None,mode:str|None=None,object_class:str|None=None,track_id:str|None=None,event_type:str|None=None,zone:str|None=None,status:str|None=None,date_from:str|None=None,date_to:str|None=None,incident:str|None=None,offset:int=0,limit:int=1000,user=Depends(current_user),db=Depends(get_db)):
    q=select(Event).join(Job,Event.job_id==Job.id)
    for column,value in [(Event.video_id,video_id),(Event.job_id,job_id),(Job.mode,mode),(Event.object_class,object_class),(Event.track_id,track_id),(Event.type,event_type),(Event.zone,zone),(Event.status,status)]:
        if value: q=q.where(column==value)
    if date_from: q=q.where(Event.created_at>=date_from)
    if date_to: q=q.where(Event.created_at<=date_to+'T23:59:59.999999+00:00' if len(date_to)==10 else Event.created_at<=date_to)
    if incident: q=q.join(Incident,Incident.event_id==Event.id).where(Incident.number==incident)
    if request.url.path=='/api/search': audit(db,user.username,'metadata_search',detail=dict(request.query_params)); db.commit()
    response.headers['X-Total-Count']=str(db.scalar(select(func.count()).select_from(q.subquery())))
    return [event_json(e) for e in db.scalars(q.order_by(Event.created_at.desc()).offset(max(0,offset)).limit(max(1,min(limit,1000))))]

@app.get('/api/track-search')
def track_search(request:Request,response:Response,video_id:str|None=None,job_id:str|None=None,mode:str|None=None,object_class:str|None=None,track_id:str|None=None,convoy_role:str|None=None,offset:int=0,limit:int=50,user=Depends(current_user),db=Depends(get_db)):
    """Track metadata search independent of events; trajectories are omitted from results."""
    filters=[column==value for column,value in [(Job.video_id,video_id),(Track.job_id,job_id),(Job.mode,mode),(Track.convoy_role,convoy_role)] if value]
    if object_class: filters.append(Track.object_class.in_(VEHICLES) if object_class=='vehicle' else Track.object_class==object_class)
    if track_id: filters.append(Track.track_id.contains(track_id.strip().upper()))
    response.headers['X-Total-Count']=str(db.scalar(select(func.count(Track.id)).join(Job,Track.job_id==Job.id).where(*filters)))
    rows=db.execute(select(Track,Job).join(Job,Track.job_id==Job.id).where(*filters).order_by(Job.created_at.desc(),Track.track_id).offset(max(0,offset)).limit(max(1,min(limit,200)))).all()
    names={v.id:v.filename for v in db.scalars(select(Video).where(Video.id.in_({j.video_id for _,j in rows})))}
    audit(db,user.username,'track_search',detail=dict(request.query_params)); db.commit()
    return [{**{k:v for k,v in tr.data.items() if k!='trajectory'},**{k:v for k,v in serialize(tr).items() if k!='data'},'mode':j.mode,'video_id':j.video_id,'video':names.get(j.video_id)} for tr,j in rows]

@app.get('/api/events/{id}')
def event_detail(id:str,user=Depends(current_user),db=Depends(get_db)):
    e=require(db,Event,id); audit(db,user.username,'event_opened',id); db.commit()
    camera=db.scalar(select(Camera).where(Camera.video_id==e.video_id))
    return {**event_json(e),'camera':{'id':camera.id,'name':camera.name} if camera else None,'video':serialize(require(db,Video,e.video_id)),'related':[event_json(r) for r in db.scalars(select(Event).where(Event.job_id==e.job_id,Event.id!=e.id,Event.zone==e.zone).limit(20))]}

@app.get('/api/events/{id}/snapshot')
def snapshot(id:str,user=Depends(current_user),db=Depends(get_db)):
    e=require(db,Event,id)
    if not e.snapshot or not Path(e.snapshot).is_file(): raise HTTPException(404,'Snapshot unavailable')
    audit(db,user.username,'evidence_access',id); db.commit(); return FileResponse(e.snapshot,media_type='image/jpeg')

@app.post('/api/events/{id}/review')
def review(id:str,data:ReviewInput,user=Depends(permit('review')),db=Depends(get_db)):
    e=db.scalar(select(Event).where(Event.id==id).with_for_update())
    if not e: raise HTTPException(404,'Event not found')
    if e.status=='CONVERTED TO INCIDENT': raise HTTPException(409,'Incident-linked review is finalized')
    if not data.note.strip(): raise HTTPException(422,'A review note is required')
    e.status=data.action; record={'actor':user.username,'timestamp':now(),**data.model_dump()}; e.reviews=[*e.reviews,record]
    audit(db,user.username,'event_review',id,record); db.commit(); return event_json(e)

@app.post('/api/events/{id}/incident')
def create_incident(id:str,data:IncidentInput,user=Depends(permit('incident')),db=Depends(get_db)):
    e=db.scalar(select(Event).where(Event.id==id).with_for_update())
    if not e: raise HTTPException(404,'Event not found')
    if e.status!='VERIFIED': raise HTTPException(409,'Human verification is required before incident creation')
    iid=uid(); record={'actor':user.username,'timestamp':now(),'state':'VERIFIED','note':'Created from verified event'}
    i=Incident(id=iid,event_id=e.id,number='AG-INC-'+iid[:8].upper(),**data.model_dump(),timeline=[record]); db.add(i); e.status='CONVERTED TO INCIDENT'
    audit(db,user.username,'incident_created',iid,{'event_id':e.id}); db.commit(); return serialize(i)

@app.get('/api/incidents')
def incidents(user=Depends(current_user),db=Depends(get_db)):
    return [{**serialize(i),'event':event_json(db.get(Event,i.event_id)),'location':db.get(Video,db.get(Event,i.event_id).video_id).location} for i in db.scalars(select(Incident).order_by(Incident.created_at.desc()))]

@app.put('/api/incidents/{id}')
def update_incident(id:str,data:IncidentUpdate,user=Depends(permit('incident')),db=Depends(get_db)):
    i=require(db,Incident,id)
    allowed={'VERIFIED':['ASSIGNED'],'ASSIGNED':['RESPONDING'],'RESPONDING':['MONITORING','RESOLVED'],'MONITORING':['RESPONDING','RESOLVED'],'RESOLVED':['CLOSED'],'CLOSED':[]}
    if i.state=='CLOSED' or (data.state!=i.state and data.state not in allowed[i.state]): raise HTTPException(409,'Invalid lifecycle transition')
    if not data.note.strip(): raise HTTPException(422,'An update/resolution note is required')
    if data.state=='ASSIGNED' and not data.assignment: raise HTTPException(422,'Assignment is required')
    if data.assignment and not db.scalar(select(User).where(User.username==data.assignment,User.enabled==True,User.role.in_(['Operator','Incident Controller','Supervisor','Administrator']))): raise HTTPException(422,'Select an enabled operational user')
    for key,value in data.model_dump().items():
        if key!='note': setattr(i,key,value)
    record={**data.model_dump(),'actor':user.username,'timestamp':now()}; i.timeline=[*i.timeline,record]
    audit(db,user.username,'incident_updated',id,record); db.commit(); return serialize(i)

@app.get('/api/users')
def users(user=Depends(current_user),db=Depends(get_db)): return [serialize(u) for u in db.scalars(select(User))]
@app.get('/api/roles')
def roles(user=Depends(current_user),db=Depends(get_db)):
    saved=list(db.scalars(select(Role)))
    return {r.name:r.permissions for r in saved} if saved else ROLES
@app.post('/api/users')
def add_user(data:UserInput,user=Depends(permit('admin')),db=Depends(get_db)):
    if data.role not in ROLES or len(data.password)<12: raise HTTPException(422,'Valid role and at least 12 password characters required')
    if db.scalar(select(User).where(User.username==data.username)): raise HTTPException(409,'Username exists')
    u=User(username=data.username,password=passwords.hash(data.password),role=data.role); db.add(u); audit(db,user.username,'user_created',data.username,{'role':data.role}); db.commit(); return serialize(u)
@app.post('/api/users/{id}/disable')
def disable_user(id:str,user=Depends(permit('admin')),db=Depends(get_db)):
    u=require(db,User,id)
    if u.id==user.id: raise HTTPException(422,'Cannot disable your own session')
    u.enabled=False; db.execute(delete(Session).where(Session.user_id==id)); audit(db,user.username,'user_disabled',id); db.commit(); return serialize(u)

@app.get('/api/audit')
def audits(q:str='',user=Depends(permit('audit')),db=Depends(get_db)):
    query=select(Audit).order_by(Audit.created_at.desc())
    if q: query=query.where(Audit.action.contains(q)|Audit.resource.contains(q)|Audit.actor.contains(q))
    return [serialize(a) for a in db.scalars(query.limit(500))]

@app.get('/api/health')
def health(user=Depends(current_user),db=Depends(get_db)):
    db.execute(text('SELECT 1')); worker=db.scalar(select(Service).where(Service.name=='Vision Worker')); fresh=worker and time.time()-worker.heartbeat<30
    gpu=(worker.data.get('gpu') or {}) if fresh else {}; device=worker.data.get('device') if fresh else None
    gpu_state=('OFFLINE — WORKER NOT REPORTING' if not fresh else f"HEALTHY — {gpu.get('backend',device.upper())} IN USE" if device in ('cuda','mps') else f"AVAILABLE — {gpu['backend']} NOT USED (DEVICE=cpu)" if gpu.get('backend') not in (None,'NONE') else 'NOT AVAILABLE — CPU INFERENCE')
    return {'Backend':'HEALTHY','Database':'HEALTHY','Storage':'HEALTHY' if shutil.disk_usage(settings.storage_dir).free>100*1024**2 else 'DEGRADED','Vision Worker':'HEALTHY' if fresh else 'OFFLINE','Detector':worker.data.get('detector','OFFLINE') if fresh else 'OFFLINE','Tracker':worker.data.get('tracker','OFFLINE') if fresh else 'OFFLINE','GPU':gpu_state,'Simulation Service':'HEALTHY — SIMULATED','Live Service':live_state(db),'Visual Search':'HEALTHY — CLIP ViT-B-32 (local)' if visual.available() else 'NOT INSTALLED','live_cameras':db.scalar(select(func.count()).select_from(Camera).where(Camera.enabled==True)),'database_backend':engine.dialect.name,'inference_device':device or 'UNKNOWN','processing_fps':round(worker.data.get('processing_fps',0),2) if fresh else 0,'queue_size':db.scalar(select(func.count()).select_from(Job).where(Job.state=='QUEUED')),'active_jobs':db.scalar(select(func.count()).select_from(Job).where(Job.state=='PROCESSING')),'gpu':gpu,'worker':worker.data if worker else {}}

@app.get('/api/analytics')
def dashboard(user=Depends(current_user),db=Depends(get_db)):
    jobs=list(db.scalars(select(Job).order_by(Job.created_at.desc()))); ev=list(db.scalars(select(Event))); inc=list(db.scalars(select(Incident)))
    latest={}
    for j in jobs:
        if j.state=='COMPLETED' and j.video_id not in latest: latest[j.video_id]=j
    return dict(videos_analyzed=len(latest),people_observed=sum(j.summary.get('total_people',0) for j in latest.values()),vehicles_observed=sum(j.summary.get('total_vehicles',0) for j in latest.values()),active_events=sum(e.status in ['NEW','UNDER REVIEW'] for e in ev),open_incidents=sum(i.state!='CLOSED' for i in inc),processing_jobs=sum(j.state in ['QUEUED','PROCESSING'] for j in jobs),event_count=len(ev),events_by_type=dict(Counter(e.type for e in ev)),events_over_time=dict(sorted(Counter(e.created_at[:10] for e in ev).items())),average_processing_time=sum(j.elapsed for j in latest.values())/max(1,len(latest)),recent_events=[event_json(e) for e in sorted(ev,key=lambda e:e.created_at,reverse=True)[:8]],recent_analysis=[serialize(j) for j in jobs[:8]])

@app.get('/api/simulation')
def simulation(user=Depends(current_user),db=Depends(get_db)):
    sim=db.scalar(select(Simulation).order_by(Simulation.created_at.desc()))
    if not sim: return {'mode':'No Person','speed':1,'timeline':[],'observation':SimulatedCSIProvider().observe('No Person',0)}
    return {**serialize(sim),'observation':SimulatedCSIProvider().observe(sim.mode,time.time()-sim.started,sim.speed)}
@app.post('/api/simulation')
def control_sim(data:SimInput,user=Depends(permit('operate')),db=Depends(get_db)):
    if data.mode not in MODES: raise HTTPException(422,'Unknown demo mode')
    sim=db.scalar(select(Simulation).order_by(Simulation.created_at.desc()))
    if not sim: sim=Simulation(started=time.time(),timeline=[]); db.add(sim)
    sim.mode=data.mode; sim.speed=data.speed; sim.started=time.time(); sim.timeline=[*sim.timeline,{'timestamp':now(),'mode':data.mode,'actor':user.username}][-100:]
    audit(db,user.username,'simulation_control',detail=data.model_dump()); db.commit(); return serialize(sim)

@app.post('/api/demo/{action}')
def demo(action:str,user=Depends(permit('admin')),db=Depends(get_db)):
    if not settings.demo_enabled: raise HTTPException(403,'Demo controls disabled')
    if action not in ['reset','clear-events','clear-incidents']: raise HTTPException(422,'Unknown demo action')
    if db.scalar(select(Job).where(Job.state.in_(['PROCESSING','QUEUED']))): raise HTTPException(409,'Cancel active jobs before clearing demo records')
    if action in ['reset','clear-incidents','clear-events']:
        for i in db.scalars(select(Incident)):
            e=db.get(Event,i.event_id)
            if e: e.status='VERIFIED'
            db.delete(i)
        db.flush()
    if action in ['reset','clear-events']: db.execute(delete(Event))
    if action=='reset': db.execute(delete(Simulation))
    audit(db,user.username,'demo_'+action,detail={'scope':'workflow records; videos and audit retained'}); db.commit(); return {'ok':True}

@app.get('/api/jobs/{id}/convoy')
def convoy_context(id:str,video_time:float=0,user=Depends(current_user),db=Depends(get_db)):
    from .convoy import context
    from .physical import Calibration
    j=require(db,Job,id)
    # Routes and the calibration are read live so an operator can draw them after processing; they never alter detections.
    measures=[{**g.config,'kind':g.kind} for g in db.scalars(select(Geometry).where(Geometry.video_id==j.video_id,Geometry.kind.in_(['route','calibration'])).order_by(Geometry.created_at)) if g.config.get('enabled',True)]
    routes=[g for g in measures if g['kind']=='route']
    return context(j,list(db.scalars(select(Track).where(Track.job_id==id))),video_time,routes,Calibration.find(measures))

@app.put('/api/roles/{name}')
def update_role(name:str,data:RoleUpdate,user=Depends(permit('admin')),db=Depends(get_db)):
    if name=='Administrator': raise HTTPException(422,'Administrator recovery permissions are fixed')
    if name not in ROLES or not set(data.permissions)<=set(ROLES['Administrator']): raise HTTPException(422,'Unknown role or permissions')
    r=db.scalar(select(Role).where(Role.name==name))
    if not r: r=Role(name=name,permissions=[]);db.add(r)
    r.permissions=data.permissions;audit(db,user.username,'role_updated',name,data.model_dump());db.commit();return {'name':name,'permissions':r.permissions}

@app.put('/api/users/{id}/role')
def user_role(id:str,data:UserRoleInput,user=Depends(permit('admin')),db=Depends(get_db)):
    u=require(db,User,id)
    if u.id==user.id or data.role not in ROLES: raise HTTPException(422,'Select another user and a known role')
    u.role=data.role;db.execute(delete(Session).where(Session.user_id==id));audit(db,user.username,'user_role_changed',id,data.model_dump());db.commit();return serialize(u)

@app.get('/api/models')
def models(user=Depends(current_user),db=Depends(get_db)):
    return [{**serialize(m),'available':(settings.storage_dir/'models'/m.filename).is_file()} for m in db.scalars(select(AIModel))]

@app.post('/api/models')
def register_model(data:ModelInput,user=Depends(permit('admin')),db=Depends(get_db)):
    if Path(data.filename).name!=data.filename or not data.filename.endswith('.pt'): raise HTTPException(422,'Use the basename of an approved local .pt file')
    path=settings.storage_dir/'models'/data.filename
    if not path.is_file(): raise HTTPException(422,'Place approved model weights in storage/models first')
    if db.scalar(select(AIModel).where(AIModel.filename==data.filename)): raise HTTPException(409,'Model is already registered')
    m=AIModel(**data.model_dump(),sha256=hashlib.sha256(path.read_bytes()).hexdigest());db.add(m);audit(db,user.username,'model_registered',data.filename);db.commit();return serialize(m)

@app.put('/api/models/{id}/state')
def model_state(id:str,data:ModelState,user=Depends(permit('admin')),db=Depends(get_db)):
    m=require(db,AIModel,id)
    if data.state=='ACTIVE':
        path=settings.storage_dir/'models'/m.filename
        if not path.is_file(): raise HTTPException(422,'Model weights are missing')
        for other in db.scalars(select(AIModel).where(AIModel.state=='ACTIVE')): other.state='APPROVED'
        m.sha256=hashlib.sha256(path.read_bytes()).hexdigest()
    m.state=data.state;audit(db,user.username,'model_state_changed',id,data.model_dump());db.commit();return serialize(m)

def job_folder(job): return settings.storage_dir/'jobs'/job.id

def live_state(db):
    service=db.scalar(select(Service).where(Service.name=='Live Service'))
    return 'HEALTHY' if service and time.time()-service.heartbeat<30 else 'OFFLINE'

TRACK_ID=re.compile(r'^[POV]-\d{4}$')

@app.get('/api/jobs/{id}/heatmap.png')
def heatmap_png(id:str,group:str='all',user=Depends(current_user),db=Depends(get_db)):
    j=require(db,Job,id); path=job_folder(j)/'heatmap.npz'
    if not path.is_file(): raise HTTPException(404,'Heatmap is available once analysis has observed objects')
    meta=require(db,Video,j.video_id).metadata_json; width=640; height=max(2,round(width*(meta.get('height') or 360)/max(1,meta.get('width') or 640)))
    png,peak,seconds=render_heatmap(path,group if group in GROUPS else 'all',width,height)
    return Response(png,media_type='image/png',headers={'Cache-Control':'no-store','X-Heatmap-Peak-Seconds':f'{peak:.2f}','X-Heatmap-Observed-Seconds':f'{seconds:.1f}'})

@app.get('/api/jobs/{id}/track-path')
def track_path(id:str,track_id:str,user=Depends(current_user),db=Depends(get_db)):
    """Every sampled observation of one track, for locked-track follow views and trajectory review."""
    j=require(db,Job,id)
    if not TRACK_ID.match(track_id): raise HTTPException(422,'Track IDs look like P-0003, V-0012 or O-0007')
    rows=[]
    if j.observations and Path(j.observations).is_file():
        with open(j.observations) as f:
            for line in f:
                try: row=json.loads(line)
                except json.JSONDecodeError: continue
                o=next((o for o in row['objects'] if o['track_id']==track_id),None)
                if o: rows.append({'time':row['time'],'box':o['box'],'position':o['position'],'confidence':o['confidence'],'direction':o.get('direction'),'zones':o.get('zones',[]),'speed_kmh':o.get('speed_kmh'),'world':o.get('world')})
    track=db.scalar(select(Track).where(Track.job_id==id,Track.track_id==track_id))
    if not rows and track is None: raise HTTPException(404,'Track not found in this analysis')
    audit(db,user.username,'track_locked',id,{'track_id':track_id}); db.commit()
    return {'track_id':track_id,'object_class':track.object_class if track else None,'summary':{k:v for k,v in (track.data if track else {}).items() if k!='trajectory'},'path':rows,
            'crop_url':f'/api/jobs/{id}/crops/{track_id}.jpg' if (job_folder(j)/'crops'/f'{track_id}.jpg').is_file() else None}

@app.get('/api/jobs/{id}/crops/{track_id}.jpg')
def track_crop(id:str,track_id:str,user=Depends(current_user),db=Depends(get_db)):
    j=require(db,Job,id); path=job_folder(j)/'crops'/f'{track_id}.jpg'
    if not TRACK_ID.match(track_id) or not path.is_file(): raise HTTPException(404,'Object crop unavailable')
    return FileResponse(path,media_type='image/jpeg')

@app.get('/api/events/{id}/clip')
def event_clip(id:str,user=Depends(current_user),db=Depends(get_db)):
    e=require(db,Event,id)
    if not e.clip or not Path(e.clip).is_file(): raise HTTPException(404,'Event clip unavailable')
    audit(db,user.username,'evidence_access',id,{'artifact':'event_clip'}); db.commit()
    return FileResponse(e.clip,media_type='video/mp4')

@app.get('/api/nl-search')
def natural_language_search(q:str,limit:int=100,user=Depends(current_user),db=Depends(get_db)):
    q=q.strip()
    if not q or len(q)>300: raise HTTPException(422,'Enter a search of up to 300 characters')
    limit=max(1,min(limit,200)); rank=visual.rank if visual.available() else None
    try: result=search.run(db,q,rank=rank,limit=limit)
    except Exception as exc:
        if rank is None: raise
        db.rollback(); result=search.run(db,q,rank=None,limit=limit); result['visual']['note']=f'Visual ranking failed: {type(exc).__name__}: {exc}'[:300]
    cameras={c.video_id:c for c in db.scalars(select(Camera))}; names={v.id:v.filename for v in db.scalars(select(Video))}
    audit(db,user.username,'natural_language_search',detail={'q':q,'filters':result['filters']}); db.commit()
    def track_json(tr,j,score):
        camera=cameras.get(j.video_id); crop=job_folder(j)/'crops'/f'{tr.track_id}.jpg'
        return {**{k:v for k,v in tr.data.items() if k!='trajectory'},**{k:v for k,v in serialize(tr).items() if k!='data'},'mode':j.mode,'video_id':j.video_id,'video':names.get(j.video_id),
                'camera_id':camera.id if camera else None,'score':score,'crop_url':f'/api/jobs/{j.id}/crops/{tr.track_id}.jpg' if crop.is_file() else None}
    return {'query':q,'understood':result['understood'],'visual':result['visual'],'searched':result['searched'],
            'events':[{**event_json(e),'score':result['event_scores'].get(e.id),'camera_id':cameras[e.video_id].id if e.video_id in cameras else None} for e in result['events']],
            'tracks':[track_json(*t) for t in result['tracks']]}

def camera_json(c):
    fresh=time.time()-(c.heartbeat or 0)<15; status=c.status or {}
    state='STOPPED' if not c.enabled else status.get('state','STARTING') if fresh else 'WAITING FOR LIVE SERVICE'
    return {**{k:v for k,v in serialize(c).items() if k not in ('url','status')},'url':mask(c.url),'status':status,'state':state}

@app.get('/api/cameras')
def cameras(user=Depends(current_user),db=Depends(get_db)):
    return [camera_json(c) for c in db.scalars(select(Camera).order_by(Camera.created_at))]

@app.post('/api/cameras')
def add_camera(data:CameraInput,user=Depends(permit('configure')),db=Depends(get_db)):
    try: url=validate_url(data.url)
    except ValueError as exc: raise HTTPException(422,str(exc))
    if db.scalar(select(Camera).where(Camera.name==data.name)): raise HTTPException(409,'A camera with this name exists')
    cid=uid(); v=Video(filename=data.name,path=f'live://{cid}',metadata_json={'live':True,'width':0,'height':0,'fps':data.fps,'duration':0,'frame_count':0,'file_size':0}); db.add(v); db.flush()
    c=Camera(id=cid,video_id=v.id,url=url,status={},**data.model_dump(exclude={'url'})); db.add(c)
    audit(db,user.username,'camera_added',cid,{'name':data.name,'url':mask(url),'mode':data.mode}); db.commit(); return camera_json(c)

@app.put('/api/cameras/{id}')
def update_camera(id:str,data:CameraUpdate,user=Depends(permit('configure')),db=Depends(get_db)):
    c=require(db,Camera,id); changes=data.model_dump(exclude_unset=True)
    # A masked URL sent back unchanged keeps the stored credentials.
    if 'url' in changes and changes['url']==mask(c.url): changes.pop('url')
    if 'url' in changes:
        try: changes['url']=validate_url(changes['url'])
        except ValueError as exc: raise HTTPException(422,str(exc))
    for key,value in changes.items(): setattr(c,key,value)
    c.updated_at=now(); db.get(Video,c.video_id).filename=c.name
    audit(db,user.username,'camera_updated',id,{**changes,'url':mask(changes['url'])} if 'url' in changes else changes); db.commit(); return camera_json(c)

@app.delete('/api/cameras/{id}')
def delete_camera(id:str,user=Depends(permit('admin')),db=Depends(get_db)):
    c=require(db,Camera,id); db.delete(c); audit(db,user.username,'camera_deleted',id,{'name':c.name}); db.commit()
    return {'ok':True,'note':'Recorded events, tracks and clips are retained'}

@app.post('/api/cameras/{id}/lock')
def lock_track(id:str,data:LockInput,user=Depends(permit('operate')),db=Depends(get_db)):
    c=require(db,Camera,id); c.lock_track_id=data.track_id
    audit(db,user.username,'track_locked' if data.track_id else 'track_unlocked',id,{'track_id':data.track_id}); db.commit(); return camera_json(c)

@app.post('/api/cameras/{id}/convoy')
def live_convoy(id:str,data:LiveConvoyInput,user=Depends(permit('operate')),db=Depends(get_db)):
    """Designates a vehicle in the running camera session. The live service picks the change up within a second."""
    c=require(db,Camera,id)
    if c.mode!='Convoy': raise HTTPException(422,'Set the camera to Convoy mode before designating vehicles')
    job=db.scalar(select(Job).where(Job.video_id==c.video_id,Job.state=='LIVE').order_by(Job.created_at.desc()))
    if not job: raise HTTPException(409,'No running session for this camera')
    tr=db.scalar(select(Track).where(Track.job_id==job.id,Track.track_id==data.track_id))
    # Live tracks are written every two seconds, so a vehicle seen right now may not be saved yet.
    if not tr: raise HTTPException(409,'This track is still being saved; try again in a few seconds')
    if tr.object_class not in VEHICLES: raise HTTPException(422,'Designate a vehicle track')
    if data.role=='Convoy Lead':
        for lead in db.scalars(select(Track).where(Track.job_id==job.id,Track.convoy_role=='Convoy Lead')): lead.convoy_role='Convoy Vehicle'
    tr.convoy_role=data.role; tr.designated_at=tr.data.get('last_seen',0) if data.role else None
    audit(db,user.username,'convoy_designated' if data.role else 'convoy_cleared',id,data.model_dump()); db.commit()
    return serialize(tr)

@app.get('/api/cameras/{id}/frame.jpg')
def camera_frame(id:str,raw:bool=False,user=Depends(current_user),db=Depends(get_db)):
    require(db,Camera,id); path=LIVE_DIR/id/('raw.jpg' if raw else 'latest.jpg')
    if not path.is_file(): raise HTTPException(404,'No frame received from this camera yet')
    return FileResponse(path,media_type='image/jpeg',headers={'Cache-Control':'no-store'})

@app.get('/api/cameras/{id}/stream')
async def camera_stream(id:str,request:Request,frames:int=0,user=Depends(current_user),db=Depends(get_db)):
    """MJPEG of the annotated live view; `frames` limits the stream length (used by tests)."""
    require(db,Camera,id); audit(db,user.username,'live_view',id); db.commit()
    path=LIVE_DIR/id/'latest.jpg'
    async def generate():
        last=None; sent=0
        while not await request.is_disconnected():
            try: stamp=path.stat().st_mtime_ns; data=path.read_bytes()
            except FileNotFoundError: await asyncio.sleep(.25); continue
            if stamp!=last:
                last=stamp; sent+=1
                yield b'--frame\r\nContent-Type: image/jpeg\r\nContent-Length: '+str(len(data)).encode()+b'\r\n\r\n'+data+b'\r\n'
                if frames and sent>=frames: break
            await asyncio.sleep(.04)
    return StreamingResponse(generate(),media_type='multipart/x-mixed-replace; boundary=frame',headers={'Cache-Control':'no-store'})

def observation_rows(job,start=0,end=None):
    if not job.observations or not Path(job.observations).is_file(): return
    with open(job.observations) as f:
        for line in f:
            try: row=json.loads(line)
            except json.JSONDecodeError: continue
            if row['time']<start: continue
            if end is not None and row['time']>end: break
            yield row

def matches(o,classes,min_confidence,track_id=''):
    return (not classes or o['object_class'] in classes or ('vehicle' in classes and o['object_class'] in VEHICLES)) and o['confidence']>=min_confidence and (not track_id or o['track_id']==track_id)

@app.get('/api/jobs/{id}/detections')
def export_detections(id:str,format:str='csv',classes:str='',min_confidence:float=0,start:float=0,end:float|None=None,track_id:str='',user=Depends(current_user),db=Depends(get_db)):
    """Streams every saved detection of an analysis or live session, filtered by class, confidence, time and track."""
    j=require(db,Job,id)
    if not j.observations or not Path(j.observations).is_file(): raise HTTPException(404,'No saved detections for this analysis')
    if format not in ('csv','json'): raise HTTPException(422,'format must be csv or json')
    wanted={c.strip() for c in classes.split(',') if c.strip()}; video=require(db,Video,j.video_id)
    w,h=video.metadata_json.get('width') or 0,video.metadata_json.get('height') or 0
    audit(db,user.username,'detections_exported',id,{'format':format,'classes':sorted(wanted),'min_confidence':min_confidence,'start':start,'end':end,'track_id':track_id}); db.commit()
    name=re.sub(r'[^A-Za-z0-9._-]','_',Path(video.filename).stem)+f'-{j.id[:8]}-detections.{format}'
    def items():
        for row in observation_rows(j,start,end):
            for o in row['objects']:
                if matches(o,wanted,min_confidence,track_id): yield row,o
    def as_json():
        yield '['
        for n,(row,o) in enumerate(items()):
            yield (',' if n else '')+json.dumps({'video_time':row['time'],'frame':row['frame'],'wall_time':row.get('wall'),**{k:o.get(k) for k in ('track_id','object_class','confidence','box','direction')},'zones':[z['name'] for z in o.get('zones',[])]})
        yield ']'
    def as_csv():
        buffer=io.StringIO(); writer=csv.writer(buffer)
        writer.writerow(['video_time','frame','wall_time','track_id','object_class','confidence','x1','y1','x2','y2','x1_px','y1_px','x2_px','y2_px','direction','zones'])
        for row,o in items():
            b=o['box']; writer.writerow([round(row['time'],3),row['frame'],row.get('wall',''),o['track_id'],o['object_class'],round(o['confidence'],4),*[round(v,5) for v in b],*[round(v*s) for v,s in zip(b,(w,h,w,h))],o.get('direction',''),'|'.join(z['name'] for z in o.get('zones',[]))])
            if buffer.tell()>65536: yield buffer.getvalue(); buffer.seek(0); buffer.truncate()
        yield buffer.getvalue()
    return StreamingResponse(as_json() if format=='json' else as_csv(),media_type='application/json' if format=='json' else 'text/csv',headers={'Content-Disposition':f'attachment; filename="{name}"'})

def saved_json(s,db):
    camera=db.get(Camera,s.camera_id) if s.camera_id else None; video=db.get(Video,s.video_id)
    return {**serialize(s),'image_url':f'/api/saved-detections/{s.id}/image','source':camera.name if camera else video.filename if video else 'Deleted source'}

@app.post('/api/saved-detections')
def save_detections(data:SaveDetectionInput,user=Depends(permit('operate')),db=Depends(get_db)):
    folder=settings.storage_dir/'saved'; folder.mkdir(parents=True,exist_ok=True); sid=uid(); target=folder/f'{sid}.jpg'; wanted=set(data.classes or [])
    if data.camera_id:
        cam=require(db,Camera,data.camera_id); status=cam.status or {}
        if status.get('state')!='LIVE' or not status.get('job_id'): raise HTTPException(409,'Camera is not live')
        job=require(db,Job,status['job_id']); rows=deque(observation_rows(job),maxlen=200)
        # Prefer the newest recent frame that actually has matching detections; otherwise keep the latest frame.
        row=next((r for r in reversed(rows) if any(matches(o,wanted,data.min_confidence) for o in r['objects'])),rows[-1] if rows else None)
        image=cv2.imread(str(LIVE_DIR/cam.id/'raw.jpg'))
        if row is None or image is None: raise HTTPException(409,'No detections received from this camera yet')
        video_id=cam.video_id
    else:
        job=require(db,Job,data.job_id); rows=[r for r in observation_rows(job,max(0,data.video_time-1.5),data.video_time+1.5)]
        if not rows: raise HTTPException(404,'No detections were recorded near this video time')
        matching=[r for r in rows if any(matches(o,wanted,data.min_confidence) for o in r['objects'])]
        row=min(matching or rows,key=lambda r:abs(r['time']-data.video_time)); video=require(db,Video,job.video_id)
        capture=cv2.VideoCapture(str(video.playback or video.path)); capture.set(cv2.CAP_PROP_POS_MSEC,row['time']*1000); ok,image=capture.read(); capture.release()
        if not ok: raise HTTPException(422,'Could not read the video frame')
        video_id=job.video_id
    objects=[o for o in row['objects'] if matches(o,wanted,data.min_confidence)]
    if not cv2.imwrite(str(target),draw_objects(image,objects)): raise HTTPException(500,'Could not store the saved frame')
    s=SavedDetection(id=sid,actor=user.username,job_id=job.id,video_id=video_id,camera_id=data.camera_id,video_time=row['time'],note=data.note,snapshot=str(target),detections=objects,filters={'classes':sorted(wanted),'min_confidence':data.min_confidence})
    db.add(s); audit(db,user.username,'detections_saved',sid,{'job_id':job.id,'camera_id':data.camera_id,'count':len(objects)}); db.commit()
    return saved_json(s,db)

@app.get('/api/saved-detections')
def saved_detections(user=Depends(current_user),db=Depends(get_db)):
    return [saved_json(s,db) for s in db.scalars(select(SavedDetection).order_by(SavedDetection.created_at.desc()).limit(200))]

@app.get('/api/saved-detections/{id}/image')
def saved_detection_image(id:str,user=Depends(current_user),db=Depends(get_db)):
    s=require(db,SavedDetection,id)
    if not Path(s.snapshot).is_file(): raise HTTPException(404,'Saved image missing')
    return FileResponse(s.snapshot,media_type='image/jpeg')

@app.delete('/api/saved-detections/{id}')
def delete_saved_detection(id:str,user=Depends(permit('admin')),db=Depends(get_db)):
    s=require(db,SavedDetection,id); Path(s.snapshot).unlink(missing_ok=True); db.delete(s)
    audit(db,user.username,'saved_detection_deleted',id); db.commit(); return {'ok':True}
