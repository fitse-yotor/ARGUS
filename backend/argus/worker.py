import json, logging, time, subprocess, hashlib
from pathlib import Path
import cv2
import imageio_ffmpeg
import supervision as sv
from sqlalchemy import select, update
from .config import settings
from .db import SessionLocal, Job, Video, Event, Track, Service, uid
from .vision import YOLODetector, ByteTracker, normalize, known, resolve_device, gpu_status, CLASSES, COCO_NAMES, ANNOTATE_MODE
from .analytics import AnalyticsEngine
from .render import AnnotatedVideo
from .heatmap import Heatmap
from . import visual

log=logging.getLogger('argus.worker')

def heartbeat(db, **data):
    service=db.scalar(select(Service).where(Service.name=='Vision Worker'))
    if not service: service=Service(name='Vision Worker',heartbeat=time.time(),data={}); db.add(service)
    service.heartbeat=time.time(); service.data={**service.data,**data}; db.commit()

def process(job_id, detector_factory=YOLODetector):
    cap=None; render=None
    with SessionLocal() as db:
        job=db.get(Job,job_id); video=db.get(Video,job.video_id); started=time.monotonic()
        folder=settings.storage_dir/'jobs'/job.id; folder.mkdir(parents=True,exist_ok=True)
        try:
            model_path=job.config.get('model',settings.model_path);device=job.config.get('device',settings.device)
            detector=detector_factory(model_path,device,job.mode,job.config['confidence'],job.config.get('imgsz',640),job.config.get('classes'),job.config.get('tiling',False),job.config.get('min_box',0))
            names=getattr(detector,'names',None) or (dict(enumerate(COCO_NAMES)) if job.mode==ANNOTATE_MODE else CLASSES)
            job.config={**job.config,'resolved_device':getattr(detector,'device',device)}
            if Path(model_path).exists(): job.config={**job.config,'model_sha256':hashlib.sha256(Path(model_path).read_bytes()).hexdigest()}
            tracker=ByteTracker(job.config['fps']); analytics=AnalyticsEngine(job.config['geometries'],job.config)
            cap=cv2.VideoCapture(video.path)
            if not cap.isOpened(): raise RuntimeError('Source video missing or unreadable')
            meta=video.metadata_json; stride=max(1,round(meta['fps']/job.config['fps'])); count=0; sampled=0; records={}
            observations=folder/'observations.jsonl'; job.observations=str(observations); db.commit()
            partial=folder/'annotated.partial.mp4'; render=AnnotatedVideo(partial,meta,job.config['geometries'])
            heat=Heatmap(); best={}; held=(sv.Detections.empty(),[]); summary={}
            with observations.open('w') as out:
                while True:
                    ok,frame=cap.read()
                    if not ok: break
                    index=count; count+=1
                    if frame.shape[1]!=meta['width'] or frame.shape[0]!=meta['height']: frame=cv2.resize(frame,(meta['width'],meta['height']))
                    if index%stride:
                        render.write(frame,*held,summary); continue
                    db.refresh(job)
                    if job.state=='CANCELLED': return
                    t=index/meta['fps']; detected=detector.detect(frame); tracked=known(tracker.update(detected,t),names)
                    objects=normalize(tracked,meta['width'],meta['height'],names); summary,events=analytics.step(objects,t)
                    held=(tracked,objects); annotated=render.write(frame,tracked,objects,summary)
                    heat.add(objects,stride/meta['fps']); visual.update_best(best,objects,tracked.xyxy,frame)
                    sampled+=1
                    out.write(json.dumps(dict(time=t,frame=index,objects=objects,analytics=summary))+'\n'); out.flush()
                    for event in events:
                        eid=uid(); snap=folder/f'{eid}.jpg'
                        if not cv2.imwrite(str(snap),annotated): raise RuntimeError('Could not save event snapshot')
                        db.add(Event(id=eid,job_id=job.id,video_id=video.id,video_time=t,frame=index,snapshot=str(snap),**event))
                    for tid,data in analytics.tracks.items():
                        if tid not in records:
                            records[tid]=Track(job_id=job.id,track_id=tid,object_class=data['object_class'],data={}); db.add(records[tid])
                        records[tid].data=dict(data)
                    job.summary=summary; job.frame=index; job.progress=min(99,100*count/meta['frame_count']); job.elapsed=time.monotonic()-started
                    job.processing_fps=sampled/max(.001,job.elapsed); job.heartbeat=time.time()
                    db.commit()
                    if sampled%10==0: heartbeat(db,detector='HEALTHY',tracker='HEALTHY',device=getattr(detector,'device',device),processing_fps=job.processing_fps,gpu=gpu_status())
            render.close()
            # Container frame counts can be approximate; only a substantial shortfall indicates a decode failure.
            if count<max(1,int(meta['frame_count']*.9)): raise RuntimeError(f'Decoding ended early at frame {count} of {meta["frame_count"]}')
            if not sampled: raise RuntimeError('No frames processed')
            if count!=meta['frame_count']: video.metadata_json={**meta,'frame_count':count,'duration':count/meta['fps']}
            for track in records.values(): track.data={**track.data,'state':'COMPLETED'}
            heat.save(folder/'heatmap.npz'); visual.save_crops(folder,best)
            if best:
                if visual.available():
                    try: job.config={**job.config,'visual_index':f'INDEXED {visual.index_folder(folder)} TRACKS'}
                    except Exception as exc:
                        log.exception('Visual indexing failed'); job.config={**job.config,'visual_index':f'FAILED: {exc}'[:200]}
                else: job.config={**job.config,'visual_index':'MODEL NOT INSTALLED'}
            # Uploads are normalized to H.264 already; older records without playback are converted here.
            if not (video.playback and Path(video.playback).is_file()):
                playback=folder/'playback.mp4'
                command=[imageio_ffmpeg.get_ffmpeg_exe(),'-nostdin','-y','-i',video.path,'-map','0:v:0','-an','-c:v','libx264','-pix_fmt','yuv420p','-preset','fast','-movflags','+faststart',str(playback)]
                error_log=(folder/'ffmpeg.log').open('w+')
                proc=subprocess.Popen(command,stdout=subprocess.DEVNULL,stderr=error_log)
                while proc.poll() is None:
                    time.sleep(.5); db.refresh(job)
                    if job.state=='CANCELLED': proc.terminate(); proc.wait(); return
                    heartbeat(db,detector='HEALTHY',tracker='HEALTHY'); job.heartbeat=time.time(); db.commit()
                error_log.seek(0); conversion_error=error_log.read()[-700:]; error_log.close()
                if proc.returncode: raise RuntimeError('Playback conversion failed: '+conversion_error)
                video.playback=str(playback)
            partial.replace(folder/'annotated.mp4')
            heartbeat(db,detector='HEALTHY',tracker='HEALTHY',device=getattr(detector,'device',device),processing_fps=job.processing_fps)
            job.state='COMPLETED'; job.progress=100; job.frame=count; job.elapsed=time.monotonic()-started
            db.commit()
        except Exception as exc:
            log.exception('Analysis failed')
            db.rollback(); job=db.get(Job,job_id)
            if job.state!='CANCELLED':
                job.state='FAILED'; job.error=f'{type(exc).__name__}: {exc}'[:2000]
                db.add(Event(job_id=job.id,video_id=job.video_id,type='Video Processing Failure',video_time=job.frame/max(1,video.metadata_json['fps']),frame=job.frame,priority='HIGH',rule={'stage':'vision pipeline'},analytics={'error':job.error}))
                db.commit()
            heartbeat(db,detector='DEGRADED',error=str(exc)[:500])
        finally:
            if cap is not None: cap.release()
            if render is not None:
                try: render.close()
                except Exception: pass

def main():
    logging.basicConfig(level=logging.INFO)
    with SessionLocal() as db:
        heartbeat(db,detector='DEGRADED — AWAITING INFERENCE' if Path(settings.model_path).exists() else 'OFFLINE',tracker='HEALTHY',device=resolve_device(settings.device),gpu=gpu_status())
    while True:
        try:
            with SessionLocal() as db:
                heartbeat(db,device=resolve_device(settings.device))
                stale=db.scalars(select(Job).where(Job.state=='PROCESSING',Job.heartbeat<time.time()-300)).all()
                for j in stale:
                    j.state='FAILED'; j.error='Worker heartbeat expired; start a new analysis to retry'
                    db.add(Event(job_id=j.id,video_id=j.video_id,type='Video Processing Failure',video_time=0,frame=j.frame,priority='HIGH',rule={'stage':'worker recovery'},analytics={'error':j.error}))
                db.commit()
                candidate=db.scalar(select(Job).where(Job.state=='QUEUED').order_by(Job.created_at).limit(1))
                if candidate:
                    claimed=db.execute(update(Job).where(Job.id==candidate.id,Job.state=='QUEUED').values(state='PROCESSING',heartbeat=time.time())).rowcount
                    db.commit()
                    if claimed: process(candidate.id)
            time.sleep(1)
        except KeyboardInterrupt: break
        except Exception: log.exception('Worker unavailable'); time.sleep(3)

if __name__=='__main__': main()
