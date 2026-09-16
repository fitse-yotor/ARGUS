"""Recorded-video heatmap, per-class zone counting, locked-track paths and the visual index (fake embedder)."""
import subprocess
import numpy as np, imageio_ffmpeg
from backend.argus import visual
from backend.argus.analytics import AnalyticsEngine
from backend.argus.db import SessionLocal, Job
from backend.argus.config import settings
from backend.argus.worker import process
from test_detect_annotate import AnnotateFixture

def test_zone_and_line_counts_per_class_and_zones_visited():
    zone=dict(id='z',kind='zone',name='Bank',type='Monitoring Zone',points=[[0,0],[.5,0],[.5,1],[0,1]],threshold=5)
    line=dict(id='l',kind='line',name='Gate',points=[[.5,0],[.5,1]])
    a=AnalyticsEngine([zone,line]);obj=lambda tid,x,cls:dict(track_id=tid,position=[x,.5],object_class=cls,confidence=.9)
    s,_=a.step([obj('P-0001',.2,'person'),obj('O-0001',.3,'dog')],0)
    assert s['zones'][0]['classes']=={'person':1,'dog':1}
    s,_=a.step([obj('P-0001',.2,'person'),obj('O-0001',.7,'dog')],1)
    assert s['zones'][1]['by_class']=={'dog':{'IN':0,'OUT':1}} and a.tracks['P-0001']['zones']=={'Bank':1}

def test_recorded_heatmap_track_path_crops_and_visual_index(client,tmp_path,monkeypatch):
    src=tmp_path/'clip.mp4'
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-loglevel','error','-f','lavfi','-i','testsrc=size=320x240:rate=25:duration=2','-c:v','libx264','-pix_fmt','yuv420p',str(src)],check=True)
    with src.open('rb') as f:video=client.post('/api/videos',files={'file':('clip.mp4',f,'video/mp4')}).json()
    j=client.post(f"/api/videos/{video['id']}/jobs",json={'mode':'Detect & Annotate','fps':10,'imgsz':960}).json()
    assert j['config']['imgsz']==960
    monkeypatch.setattr(visual,'available',lambda:False)
    with SessionLocal() as db:job=db.get(Job,j['id']);job.state='PROCESSING';db.commit()
    process(j['id'],AnnotateFixture)
    listed=next(x for x in client.get('/api/jobs').json() if x['id']==j['id'])
    assert listed['state']=='COMPLETED' and listed['heatmap_available'] and listed['config']['visual_index']=='MODEL NOT INSTALLED'
    heat=client.get(f"/api/jobs/{j['id']}/heatmap.png",params={'group':'person'})
    assert heat.headers['content-type']=='image/png' and float(heat.headers['x-heatmap-observed-seconds'])>1.5
    path=client.get(f"/api/jobs/{j['id']}/track-path",params={'track_id':'P-0000'}).json()
    assert len(path['path'])>=15 and path['object_class']=='person' and path['crop_url'] and 'trajectory' not in path['summary']
    assert client.get(path['crop_url']).headers['content-type']=='image/jpeg'
    assert client.get(f"/api/jobs/{j['id']}/track-path",params={'track_id':'X-1'}).status_code==422
    folder=settings.storage_dir/'jobs'/j['id']
    fake=lambda crops:np.eye(512,dtype=np.float32)[:len(crops)]
    assert visual.index_folder(folder,embedder=fake)==2
    scores=visual.rank('a photo of a chair',[(j['id'],'P-0000'),(j['id'],'O-0001'),(j['id'],'V-9999')],embedder=lambda text:np.eye(512,dtype=np.float32)[1])
    assert set(scores)=={(j['id'],'P-0000'),(j['id'],'O-0001')} and max(scores,key=scores.get)[1] in ('O-0001','P-0000')
