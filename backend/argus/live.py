"""Live camera service: FFmpeg ingestion, detection, tracking, zone analytics, heatmaps, locked-track rendering,
event clips and appearance crops. Run with `python -m backend.argus.live`.
Each enabled camera gets one thread; frames that arrive while a frame is being analysed are dropped, never queued."""
import hashlib, json, logging, os, threading, time
from collections import deque
import cv2
from sqlalchemy import select, update
from .config import settings
from .db import SessionLocal, Camera, Video, Job, Event, Track, Geometry, Service, AIModel, uid
from .vision import YOLODetector, ByteTracker, normalize, known, resolve_device, CLASSES, COCO_NAMES, ANNOTATE_MODE
from .analytics import AnalyticsEngine, VEHICLES
from .convoy import LiveConvoy
from .render import Renderer, write_clip
from .heatmap import Heatmap
from .sources import resolve, probe, open_reader, mask, SourceError
from . import visual

log=logging.getLogger('argus.live')
LIVE_DIR=settings.storage_dir/'live'
PRE_SECONDS=5; POST_SECONDS=5; OFFLINE_AFTER=30; STALL_SECONDS=20; PRUNE_AFTER=120; MAX_OPEN_CLIPS=4

def write_atomic(path,data):
    tmp=path.with_name(path.name+'.tmp'); tmp.write_bytes(data); os.replace(tmp,path)

def service_heartbeat(db,**data):
    service=db.scalar(select(Service).where(Service.name=='Live Service'))
    if not service: service=Service(name='Live Service',heartbeat=time.time(),data={}); db.add(service)
    service.heartbeat=time.time(); service.data={**service.data,**data}; db.commit()

def geometries_for(db,video_id):
    return [{**g.config,'id':g.id,'kind':g.kind} for g in db.scalars(select(Geometry).where(Geometry.video_id==video_id).order_by(Geometry.created_at))]

def digest(value): return hashlib.sha1(json.dumps(value,sort_keys=True).encode()).hexdigest()

def finish_clip(clip,fps):
    try:
        if write_clip(clip['path'],clip['frames'],fps):
            with SessionLocal() as db:
                event=db.get(Event,clip['event_id'])
                if event: event.clip=str(clip['path']); db.commit()
    except Exception: log.exception('Event clip failed')

class CameraRunner(threading.Thread):
    """`source`, `realtime` and `max_ticks` let tests drive a runner from a local file."""
    def __init__(self,camera_id,version,detector_factory=YOLODetector,source=None,realtime=False,max_ticks=None):
        super().__init__(daemon=True,name=f'camera-{camera_id[:8]}')
        self.camera_id=camera_id; self.version=version; self.detector_factory=detector_factory
        self.source=source; self.realtime=realtime; self.max_ticks=max_ticks
        self.stopping=threading.Event(); self.locked=None; self.clips=[]; self.failed=False
    def stop(self): self.stopping.set()
    def run(self):
        try: self.session()
        except Exception: self.failed=True; log.exception('Camera runner failed')

    def session(self):
        live_dir=LIVE_DIR/self.camera_id; live_dir.mkdir(parents=True,exist_ok=True)
        with SessionLocal() as db:
            cam=db.get(Camera,self.camera_id)
            if cam is None: return
            video_id,fps,name=cam.video_id,cam.fps,cam.name; self.locked=cam.lock_track_id
            geometries=geometries_for(db,video_id); geo_digest=digest(geometries)
            active=db.scalar(select(AIModel).where(AIModel.state=='ACTIVE'))
            model=str(settings.storage_dir/'models'/active.filename) if active else settings.model_path
            config=dict(fps=fps,confidence=cam.confidence,imgsz=cam.imgsz,width=cam.width,geometries=geometries,live=True,camera_id=cam.id,camera=name,source=mask(cam.url),stop_seconds=10,congestion_count=12,free_flow_kmh=50,model=model,device=settings.device,classes=cam.classes,tiling=cam.tiling,min_box=cam.min_box)
            job=Job(video_id=video_id,mode=cam.mode,state='LIVE',config=config,heartbeat=time.time()); db.add(job); db.commit()
            folder=settings.storage_dir/'jobs'/job.id; folder.mkdir(parents=True,exist_ok=True)
            # Every analysed live frame's detections are saved (roughly 1 MB per camera-hour at 5 FPS with few objects).
            observations=(folder/'observations.jsonl').open('a'); job.observations=str(folder/'observations.jsonl')
            detector=self.detector_factory(model,settings.device,cam.mode,cam.confidence,cam.imgsz,cam.classes,cam.tiling,cam.min_box)
            names=getattr(detector,'names',None) or (dict(enumerate(COCO_NAMES)) if cam.mode==ANNOTATE_MODE else CLASSES)
            job.config={**job.config,'resolved_device':getattr(detector,'device',settings.device)}; db.commit()
            tracker=ByteTracker(fps); analytics=AnalyticsEngine(geometries,config); heat=Heatmap()
            reader=None; renderer=None; width=height=0; t0=time.monotonic(); last_seq=0; last_t=-1.; tick=0
            outage=None; offline_sent=False; attempts=0; connected=False; error=None
            ring=deque(); best={}; records={}; persisted={}; to_index=set(); recent=deque(maxlen=50)
            summary={}; objects=[]; timers=dict(control=0,tracks=0,geometry=0,heat=0,prune=0,index=0,raw=0)
            convoy=LiveConvoy(config) if cam.mode=='Convoy' else None; designations={}; convoy_status=None

            def status(state):
                lock=None
                if self.locked:
                    tr=analytics.tracks.get(self.locked); visible=any(o['track_id']==self.locked for o in objects)
                    lock={'track_id':self.locked,'visible':visible and state=='LIVE','known':tr is not None}
                    if tr: lock.update(object_class=tr['object_class'],first_seen=tr['first_seen'],last_seen=tr['last_seen'],duration=tr['duration'],direction=tr.get('direction'),zones=tr.get('zones',{}),seconds_since_seen=round(time.monotonic()-t0-tr['last_seen'],1),speed_kmh=tr.get('speed_kmh'),max_speed_kmh=tr.get('max_speed_kmh'))
                rate=(len(recent)-1)/(recent[-1]-recent[0]) if len(recent)>1 and recent[-1]>recent[0] else 0
                payload=dict(state=state,error=error,job_id=job.id,width=width,height=height,fps=round(rate,2),target_fps=fps,ticks=tick,uptime=round(time.monotonic()-t0),
                             summary={k:summary.get(k) for k in ('people','vehicles','objects','classes','total_classes','total_objects','zones','traffic_state','stopped_vehicles',
                                                                 'calibrated','calibration','traffic_basis','free_flow_kmh','speed_samples','median_speed_kmh','average_speed_kmh','speeding_vehicles','vehicles_per_minute')},
                             visible=[{'track_id':o['track_id'],'object_class':o['object_class'],'confidence':round(o['confidence'],3),'speed_kmh':o.get('speed_kmh')} for o in objects],
                             locked=lock,convoy=convoy_status,device=job.config.get('resolved_device'))
                db.execute(update(Camera).where(Camera.id==self.camera_id).values(status=payload,heartbeat=time.time())); db.commit()

            def housekeeping(t):
                nonlocal analytics,geo_digest
                now=time.time()
                if now>=timers['control']:
                    timers['control']=now+1
                    row=db.execute(select(Camera.enabled,Camera.lock_track_id,Camera.updated_at).where(Camera.id==self.camera_id)).first()
                    if row is None or not row.enabled or row.updated_at!=self.version: self.stopping.set()
                    else: self.locked=row.lock_track_id
                    if convoy is not None:
                        # Operators designate convoy vehicles through the API, which writes the role onto the Track row.
                        current_roles={r.track_id:(r.convoy_role,r.designated_at or 0) for r in db.execute(select(Track.track_id,Track.convoy_role,Track.designated_at).where(Track.job_id==job.id,Track.convoy_role.is_not(None))).all()}
                        designations.clear(); designations.update(current_roles)
                    observations.flush(); job.summary=summary; job.heartbeat=now; job.frame=tick; job.elapsed=time.monotonic()-t0; db.commit()
                    status('LIVE')
                if now>=timers['tracks']:
                    timers['tracks']=now+2
                    for tid,data in analytics.tracks.items():
                        if persisted.get(tid)==data['last_seen']: continue
                        if tid not in records: records[tid]=Track(job_id=job.id,track_id=tid,object_class=data['object_class'],data={}); db.add(records[tid])
                        records[tid].data=dict(data); persisted[tid]=data['last_seen']
                    db.commit()
                if now>=timers['geometry']:
                    timers['geometry']=now+5; current=geometries_for(db,video_id)
                    if digest(current)!=geo_digest:
                        # Counts restart with the new rules; existing tracks and their history are kept.
                        replacement=AnalyticsEngine(current,{**config,'geometries':current}); replacement.tracks=analytics.tracks; analytics=replacement
                        renderer.set_geometries(current); geo_digest=digest(current); job.config={**job.config,'geometries':current}; db.commit()
                if now>=timers['heat']: timers['heat']=now+15; heat.save(folder/'heatmap.npz')
                if now>=timers['prune']:
                    timers['prune']=now+30
                    for tid,tr in list(analytics.tracks.items()):
                        if t-tr['last_seen']<PRUNE_AFTER: continue
                        if tid in records: records[tid].data={**tr,'state':'COMPLETED'}
                        visual.save_crops(folder,best,[tid]); best.pop(tid,None); to_index.add(tid)
                        for store in (analytics.tracks,records,persisted,analytics.stationary,analytics.speed.history): store.pop(tid,None)
                    db.commit()
                if now>=timers['index']:
                    timers['index']=now+60
                    if to_index and visual.available():
                        try:
                            crops=[(tid,cv2.imread(str(folder/'crops'/f'{tid}.jpg'))) for tid in to_index]; crops=[(i,c) for i,c in crops if c is not None]
                            if crops:
                                merged=dict(visual.vectors(folder)); merged.update(zip([i for i,_ in crops],visual.embed_images([c for _,c in crops])))
                                visual.save_vectors(folder,list(merged),list(merged.values()))
                            to_index.clear()
                        except Exception: log.exception('Live visual indexing failed')

            try:
                while not self.stopping.is_set():
                    now=time.time()
                    if reader is None or reader.ended or now-reader.last>STALL_SECONDS:
                        if reader is not None:
                            error=(reader.error.decode(errors='ignore').strip().splitlines() or ['Stream stalled'])[-1][:300]
                            reader.close(); reader=None; outage=outage or now
                        status('RECONNECTING' if connected else 'CONNECTING')
                        try:
                            url,headers=(self.source,{}) if self.source else resolve(cam.url)
                            frame=probe(url,headers)
                            width=min(cam.width,frame.shape[1]); width-=width%2; height=int(round(width*frame.shape[0]/frame.shape[1]/2)*2)
                            reader=open_reader(url,headers,width,height,fps,self.realtime)
                            if renderer is None: renderer=Renderer(width,height,fps,geometries)
                            else: renderer.__init__(width,height,fps,renderer.geometries)
                            write_atomic(live_dir/'raw.jpg',cv2.imencode('.jpg',cv2.resize(frame,(width,height)))[1].tobytes())
                            video=db.get(Video,video_id); video.metadata_json={**video.metadata_json,'width':width,'height':height,'fps':fps}; db.commit()
                            connected=True; outage=None; offline_sent=False; attempts=0; error=None; last_seq=0
                            status('LIVE')
                        except (SourceError,OSError,ValueError) as exc:
                            error=str(exc)[:300]; outage=outage or now; attempts+=1
                            if not offline_sent and now-outage>=OFFLINE_AFTER:
                                db.add(Event(job_id=job.id,video_id=video_id,type='Camera Offline',video_time=time.monotonic()-t0,frame=tick,priority='HIGH',rule={'offline_after_seconds':OFFLINE_AFTER,'camera':name},analytics={'error':error}))
                                offline_sent=True; db.commit()
                            status('RECONNECTING' if connected else 'CONNECTING')
                            self.stopping.wait(min(30,2**min(attempts,5))); continue
                    frame,seq=reader.latest(); t=time.monotonic()-t0
                    if frame is None or seq==last_seq or t-last_t<.9/fps:
                        housekeeping(t); self.stopping.wait(.01); continue
                    last_seq=seq; last_t=t; tick+=1; recent.append(time.monotonic())
                    tracked=known(tracker.update(detector.detect(frame),t),names)
                    objects=normalize(tracked,width,height,names); summary,events=analytics.step(objects,t)
                    if convoy is not None:
                        convoy_events,convoy_status=convoy.step(objects,summary,t,designations,analytics.routes,analytics.calibration)
                        events=events+convoy_events
                    observations.write(json.dumps(dict(time=t,frame=tick,wall=round(time.time(),3),objects=objects,analytics=summary))+'\n')
                    heat.add(objects,1/fps); visual.update_best(best,objects,tracked.xyxy,frame)
                    scene=renderer.draw(frame,tracked,objects,summary,self.locked)
                    jpeg=cv2.imencode('.jpg',scene,[cv2.IMWRITE_JPEG_QUALITY,80])[1].tobytes(); write_atomic(live_dir/'latest.jpg',jpeg)
                    ring.append((t,jpeg))
                    while ring and ring[0][0]<t-PRE_SECONDS: ring.popleft()
                    for clip in self.clips: clip['frames'].append(jpeg)
                    for event in events:
                        eid=uid(); snap=folder/f'{eid}.jpg'; cv2.imwrite(str(snap),scene)
                        db.add(Event(id=eid,job_id=job.id,video_id=video_id,video_time=t,frame=tick,snapshot=str(snap),**event))
                        if len(self.clips)<MAX_OPEN_CLIPS: self.clips.append({'event_id':eid,'frames':[j for _,j in ring],'until':t+POST_SECONDS,'path':folder/f'{eid}.mp4'})
                    if events: db.commit()
                    for clip in [c for c in self.clips if t>=c['until']]:
                        self.clips.remove(clip); threading.Thread(target=finish_clip,args=(clip,fps),daemon=True).start()
                    if now>=timers['raw']: timers['raw']=now+1; write_atomic(live_dir/'raw.jpg',cv2.imencode('.jpg',frame,[cv2.IMWRITE_JPEG_QUALITY,75])[1].tobytes())
                    housekeeping(t)
                    if self.max_ticks and tick>=self.max_ticks: break
            finally:
                if reader is not None: reader.close()
                observations.close(); db.rollback()
                for clip in self.clips: finish_clip(clip,fps)
                self.clips=[]
                try:
                    for tid,data in analytics.tracks.items():
                        if tid not in records: records[tid]=Track(job_id=job.id,track_id=tid,object_class=data['object_class'],data={}); db.add(records[tid])
                        records[tid].data={**data,'state':'COMPLETED'}
                    heat.save(folder/'heatmap.npz'); visual.save_crops(folder,best)
                    if visual.available(): job.config={**job.config,'visual_index':f'INDEXED {visual.index_folder(folder)} TRACKS'}
                except Exception: log.exception('Live session finalization failed')
                job.state='COMPLETED'; job.summary=summary; job.frame=tick; job.elapsed=time.monotonic()-t0; db.commit()
                objects=[]; status('STOPPED')

def main():
    logging.basicConfig(level=logging.INFO); LIVE_DIR.mkdir(parents=True,exist_ok=True)
    runners={}; cooldown={}
    try:
        while True:
            try:
                with SessionLocal() as db:
                    cameras={c.id:(c.enabled,c.updated_at) for c in db.scalars(select(Camera))}
                    service_heartbeat(db,cameras=len(cameras),running=len(runners),device=resolve_device(settings.device))
                for cid,runner in list(runners.items()):
                    enabled,version=cameras.get(cid,(False,None))
                    if enabled and version==runner.version and runner.is_alive(): continue
                    runner.stop(); runner.join(timeout=30); del runners[cid]
                    if enabled and version==runner.version: cooldown[cid]=time.time()+10
                for cid,(enabled,version) in cameras.items():
                    if enabled and cid not in runners and time.time()>=cooldown.get(cid,0):
                        runners[cid]=CameraRunner(cid,version); runners[cid].start()
                time.sleep(2)
            except KeyboardInterrupt: raise
            except Exception: log.exception('Live service loop failed'); time.sleep(3)
    except KeyboardInterrupt: pass
    finally:
        for runner in runners.values(): runner.stop()
        for runner in runners.values(): runner.join(timeout=30)

if __name__=='__main__': main()
