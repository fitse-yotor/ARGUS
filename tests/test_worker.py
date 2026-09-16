"""Integration fixture detector is test-only; production never fabricates detections."""
import cv2,numpy as np,supervision as sv
from sqlalchemy import select
from backend.argus.db import SessionLocal,Video,Job,Event,Track
from backend.argus.media import metadata
from backend.argus.worker import process

class FixtureDetector:
    def __init__(self,*args): pass
    def detect(self,frame):
        return sv.Detections(xyxy=np.array([[40,20,80,110]],dtype=float),confidence=np.array([.95]),class_id=np.array([0]))

def test_worker_to_incident(client,tmp_path):
    path=tmp_path/'source.avi';w=cv2.VideoWriter(str(path),cv2.VideoWriter_fourcc(*'MJPG'),10,(160,120))
    for i in range(30):w.write(np.zeros((120,160,3),np.uint8))
    w.release()
    with path.open('rb') as f:r=client.post('/api/videos',files={'file':('source.avi',f,'video/x-msvideo')})
    assert r.status_code==200;vid=r.json()['id']
    g=client.post(f'/api/videos/{vid}/geometries',json={'name':'Gate','kind':'zone','type':'Crowd Zone','points':[[0,0],[1,0],[1,1],[0,1]],'threshold':1,'dwell_seconds':1})
    assert g.status_code==200
    j=client.post(f'/api/videos/{vid}/jobs',json={'mode':'Event / Crowd','fps':5}).json()
    with SessionLocal() as db:job=db.get(Job,j['id']);job.state='PROCESSING';db.commit()
    process(j['id'],FixtureDetector)
    jobs=client.get('/api/jobs').json();assert jobs[0]['state']=='COMPLETED',jobs[0]['error']
    events=client.get('/api/events').json();crowd=next(e for e in events if e['type']=='Crowd Threshold')
    assert client.get(crowd['snapshot_url']).status_code==200
    media=client.get(f'/api/videos/{vid}/media',headers={'Range':'bytes=0-99'})
    assert media.status_code==206
    observations=client.get(f'/api/jobs/{j["id"]}/observations').json();assert len(observations)>5
    assert len(client.get(f'/api/jobs/{j["id"]}/tracks').json())==1
    assert client.post(f'/api/events/{crowd["id"]}/review',json={'action':'VERIFIED','note':'Fixture integration review'}).status_code==200
    assert client.post(f'/api/events/{crowd["id"]}/incident',json={'title':'Gate','category':'Crowd'}).status_code==200

def test_worker_failure_is_not_success(client):
    with SessionLocal() as db:
        v=Video(filename='missing.mp4',path='/not-present',metadata_json={'fps':10});db.add(v);db.flush()
        j=Job(video_id=v.id,mode='Traffic',config={'confidence':.3,'fps':5,'geometries':[]});db.add(j);db.commit();jid=j.id
    process(jid,FixtureDetector)
    with SessionLocal() as db:
        assert db.get(Job,jid).state=='FAILED'
        assert db.scalar(select(Event).where(Event.job_id==jid)).type=='Video Processing Failure'
