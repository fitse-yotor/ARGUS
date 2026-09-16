"""Format normalization and Supervision Detect & Annotate rendering. Fixture detections are test-only."""
import subprocess
import cv2, numpy as np, imageio_ffmpeg, pytest, supervision as sv
from backend.argus.media import prepare, metadata
from backend.argus.analytics import AnalyticsEngine
from backend.argus.db import SessionLocal, Job
from backend.argus.vision import COCO_NAMES
from backend.argus.worker import process

FF=imageio_ffmpeg.get_ffmpeg_exe()
def encode(path,*args,src='testsrc=size=320x240:rate=25:duration=2'):
    subprocess.run([FF,'-y','-loglevel','error','-f','lavfi','-i',src,*args,str(path)],check=True)

@pytest.mark.parametrize('ext,codec',[('mkv',['-c:v','libx264','-pix_fmt','yuv420p']),('webm',['-c:v','libvpx-vp9','-deadline','realtime']),('wmv',['-c:v','wmv2']),('mov',['-c:v','libx265','-tag:v','hvc1'])])
def test_prepare_normalizes_common_formats(tmp_path,ext,codec):
    src=tmp_path/f'in.{ext}';encode(src,*codec);out=tmp_path/'out.mp4';prepare(src,out);m=metadata(out)
    assert (m['width'],m['height'])==(320,240) and m['fps']==pytest.approx(25) and abs(m['frame_count']-50)<=1

def test_prepare_applies_phone_rotation(tmp_path):
    src=tmp_path/'a.mp4';encode(src,'-c:v','libx264','-pix_fmt','yuv420p')
    rotated=tmp_path/'rotated.mp4';subprocess.run([FF,'-y','-loglevel','error','-display_rotation','90','-i',str(src),'-c','copy',str(rotated)],check=True)
    out=tmp_path/'out.mp4';prepare(rotated,out);m=metadata(out)
    assert (m['width'],m['height'])==(240,320)

def test_prepare_caps_frame_rate_and_rejects_garbage(tmp_path):
    src=tmp_path/'fast.mp4';encode(src,'-c:v','libx264','-pix_fmt','yuv420p',src='testsrc=size=320x240:rate=120:duration=1')
    out=tmp_path/'out.mp4';prepare(src,out);m=metadata(out)
    assert m['fps']==pytest.approx(60) and abs(m['duration']-1)<.1
    bad=tmp_path/'bad.mkv';bad.write_bytes(b'not a video')
    with pytest.raises(ValueError): prepare(bad,tmp_path/'bad.mp4')
    assert not (tmp_path/'bad.mp4').exists()

def test_other_objects_are_not_vehicles():
    s,_=AnalyticsEngine([]).step([dict(track_id='O-0001',position=[.5,.5],box=[.4,.4,.6,.5],object_class='chair',confidence=.9)],0)
    assert s['vehicles']==0 and s['total_vehicles']==0 and s['total_classes']=={'chair':1} and s['total_objects']==1

class AnnotateFixture:
    names=dict(enumerate(COCO_NAMES))
    def __init__(self,*args): pass
    def detect(self,frame):
        return sv.Detections(xyxy=np.array([[40,20,120,200],[180,60,260,220]],dtype=float),confidence=np.array([.9,.8]),class_id=np.array([0,56]))

def test_upload_any_format_then_detect_and_annotate(client,tmp_path):
    src=tmp_path/'phone clip.mkv';encode(src,'-c:v','libx264','-pix_fmt','yuv420p')
    with src.open('rb') as f:r=client.post('/api/videos',files={'file':('phone clip.mkv',f,'video/x-matroska')})
    assert r.status_code==200,r.text;video=r.json();assert video['metadata_json']['source_format']=='MKV'
    assert client.get(f"/api/videos/{video['id']}/media").headers['content-type']=='video/mp4'
    assert client.post('/api/videos',files={'file':('clip.webm',b'garbage','video/webm')}).status_code==422
    assert client.post('/api/videos',files={'file':('notes.txt',b'text','text/plain')}).status_code==415
    j=client.post(f"/api/videos/{video['id']}/jobs",json={'mode':'Detect & Annotate','fps':25}).json()
    assert client.get(f"/api/jobs/{j['id']}/annotated").status_code==404
    with SessionLocal() as db:job=db.get(Job,j['id']);job.state='PROCESSING';db.commit()
    process(j['id'],AnnotateFixture)
    job=next(x for x in client.get('/api/jobs').json() if x['id']==j['id'])
    assert job['state']=='COMPLETED',job['error'];assert job['annotated_available']
    assert job['summary']['total_classes']=={'person':1,'chair':1} and job['summary']['total_vehicles']==0
    assert {t['track_id'][0] for t in client.get(f"/api/jobs/{j['id']}/tracks").json()}=={'P','O'}
    r=client.get(f"/api/jobs/{j['id']}/annotated?download=true")
    assert r.status_code==200 and r.headers['content-type']=='video/mp4' and 'attachment' in r.headers['content-disposition']
    out=tmp_path/'annotated.mp4';out.write_bytes(r.content)
    annotated=cv2.VideoCapture(str(out));original=cv2.VideoCapture(str(src));frames=0;changed=0
    while True:
        ok,a=annotated.read();ok2,b=original.read()
        if not ok or not ok2: break
        frames+=1;changed+=float(np.abs(a[20:200,40:120].astype(int)-b[20:200,40:120].astype(int)).mean())>5
    assert frames==50 and changed>=45
