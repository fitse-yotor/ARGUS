import cv2,numpy as np
from backend.argus.db import SessionLocal,Video,Job,Event,User,Audit
from backend.argus.media import metadata
from backend.argus.security import passwords
from sqlalchemy import select

def seed_event():
    with SessionLocal() as db:
        v=Video(filename='test.mp4',path='/missing',metadata_json={'duration':10,'fps':10});db.add(v);db.flush()
        j=Job(video_id=v.id,mode='Event / Crowd',config={},state='COMPLETED');db.add(j);db.flush()
        e=Event(video_id=v.id,job_id=j.id,type='Crowd Threshold',video_time=3,frame=30,rule={'threshold':2});db.add(e);db.commit();return e.id

def test_review_incident_audit(client):
    eid=seed_event();body={'title':'Gate occupancy','category':'Crowd','priority':'HIGH'}
    assert client.post(f'/api/events/{eid}/incident',json=body).status_code==409
    assert client.post(f'/api/events/{eid}/review',json={'action':'DISMISSED'}).status_code==422
    assert client.post(f'/api/events/{eid}/review',json={'action':'VERIFIED','note':'Reviewed the source frame'}).status_code==200
    r=client.post(f'/api/events/{eid}/incident',json=body);assert r.status_code==200;i=r.json()
    assert client.post(f'/api/events/{eid}/incident',json=body).status_code==409
    assert client.put(f'/api/incidents/{i["id"]}',json={'state':'CLOSED','note':'Skip'}).status_code==409
    for state in ['ASSIGNED','RESPONDING','MONITORING','RESOLVED','CLOSED']:
        assert client.put(f'/api/incidents/{i["id"]}',json={'state':state,'assignment':'admin','note':f'Human update {state}'}).status_code==200
    assert len(client.get('/api/search?event_type=Crowd%20Threshold').json())==1
    actions=[a['action'] for a in client.get('/api/audit').json()]
    assert 'event_review' in actions and 'incident_created' in actions and 'metadata_search' in actions

def test_auth_rbac_csrf(client):
    with SessionLocal() as db:
        db.add(User(username='auditor',password=passwords.hash('test-auditor-password'),role='Auditor'));db.commit()
    client.post('/api/auth/logout');assert client.get('/api/videos').status_code==401
    client.post('/api/auth/login',json={'username':'auditor','password':'test-auditor-password'})
    assert client.post('/api/demo/reset').status_code==403
    assert client.get('/api/audit').status_code==200
    client.headers.pop('X-Argus-Request');assert client.post('/api/auth/logout').status_code==403

def test_metadata_upload_and_bad_file(client,tmp_path):
    path=tmp_path/'video.avi';writer=cv2.VideoWriter(str(path),cv2.VideoWriter_fourcc(*'MJPG'),10,(160,120))
    for i in range(20):writer.write(np.zeros((120,160,3),dtype=np.uint8))
    writer.release();m=metadata(path);assert m['frame_count']==20 and m['duration']==2
    with path.open('rb') as f:r=client.post('/api/videos',files={'file':('../../unsafe.avi',f,'video/x-msvideo')})
    assert r.status_code==200;assert r.json()['filename']=='unsafe.avi'
    assert client.post('/api/videos',files={'file':('bad.mp4',b'not a video','video/mp4')}).status_code==422
    assert client.post('/api/videos',files={'file':('script.sh',b'echo unsafe','text/plain')}).status_code==415
    v=r.json()['id'];assert client.post(f'/api/videos/{v}/jobs',json={'mode':'Traffic','fps':5}).status_code==200
    assert client.post(f'/api/videos/{v}/jobs',json={'mode':'Traffic'}).status_code==409

def test_registry_and_role_enforcement(client,tmp_path):
    from backend.argus.config import settings
    folder=settings.storage_dir/'models';folder.mkdir(exist_ok=True)
    (folder/'approved.pt').write_bytes(b'not executed in registry test')
    r=client.post('/api/models',json={'name':'Test model','version':'test','filename':'approved.pt'});assert r.status_code==200
    mid=r.json()['id'];assert client.put(f'/api/models/{mid}/state',json={'state':'ACTIVE'}).status_code==200
    assert len(client.get('/api/models').json()[0]['sha256'])==64
    assert client.post('/api/models',json={'name':'Escape','version':'test','filename':'../escape.pt'}).status_code==422
    assert client.put('/api/roles/Administrator',json={'permissions':[]}).status_code==422
    assert client.put('/api/roles/Investigator',json={'permissions':[]}).status_code==200
    assert client.post('/api/users',json={'username':'investigator','password':'long-test-password','role':'Investigator'}).status_code==200
    client.post('/api/auth/logout');client.post('/api/auth/login',json={'username':'investigator','password':'long-test-password'})
    assert client.get('/api/videos').status_code==403
