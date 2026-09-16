"""Opt-in real inference regression using the photograph bundled by Ultralytics.
This generated fixture is not surveillance footage or a field accuracy benchmark.
"""
import os
from pathlib import Path
import pytest
import cv2,numpy as np
from backend.argus.config import settings
from backend.argus.worker import process
from backend.argus.db import SessionLocal,Job

@pytest.mark.skipif(os.environ.get('ARGUS_REAL_MODEL_TEST')!='1',reason='Opt-in real model test requires downloaded weights')
def test_actual_model_upload_crowd_traffic_convoy(client,tmp_path):
    import ultralytics
    settings.model_path=str(Path('storage/models/yolo11n.pt').resolve())
    source=Path(ultralytics.__file__).parent/'assets'/'bus.jpg'
    image=cv2.imread(str(source));image=cv2.resize(image,(480,640))
    path=tmp_path/'bundled-image-fixture.avi';w=cv2.VideoWriter(str(path),cv2.VideoWriter_fourcc(*'MJPG'),4,(480,640))
    for _ in range(12):w.write(image)
    w.release()
    with path.open('rb') as f:v=client.post('/api/videos',files={'file':('bundled-image-fixture.avi',f,'video/x-msvideo')}).json()
    for mode,kind,cls in [('Event / Crowd','Crowd Zone','person'),('Traffic','No-Stopping Zone','vehicle'),('Convoy','Convoy Corridor','vehicle')]:
        client.post(f'/api/videos/{v["id"]}/geometries',json={'name':mode,'kind':'zone','type':kind,'object_class':cls,'points':[[0,0],[1,0],[1,1],[0,1]],'threshold':1,'dwell_seconds':.5,'stop_seconds':.5})
        j=client.post(f'/api/videos/{v["id"]}/jobs',json={'mode':mode,'fps':2,'stop_seconds':.5,'congestion_count':1}).json()
        with SessionLocal() as db:job=db.get(Job,j['id']);job.state='PROCESSING';db.commit()
        process(j['id'])
        finished=next(x for x in client.get('/api/jobs').json() if x['id']==j['id'])
        assert finished['state']=='COMPLETED',finished['error']
        tracks=client.get(f'/api/jobs/{j["id"]}/tracks').json();assert tracks
        events=client.get('/api/events?job_id='+j['id']).json()
        if mode=='Event / Crowd':
            assert finished['summary']['total_people']>=2
            e=next(e for e in events if e['type']=='Crowd Threshold')
            assert client.post(f'/api/events/{e["id"]}/review',json={'action':'VERIFIED','note':'Actual inference fixture reviewed'}).status_code==200
            assert client.post(f'/api/events/{e["id"]}/incident',json={'title':'Real model regression','category':'Crowd'}).status_code==200
        if mode=='Traffic': assert any(e['type']=='Stopped Vehicle' for e in events)
        if mode=='Convoy':
            tr=tracks[0]
            response=client.post(f'/api/tracks/{tr["id"]}/convoy',json={'role':'Convoy Lead','video_time':tr['data']['first_seen']})
            assert response.status_code==200,response.text
            assert any(e['type']=='Convoy Traffic Delay' for e in client.get('/api/events?job_id='+j['id']).json())
            ctx=client.get(f'/api/jobs/{j["id"]}/convoy?video_time=2').json();assert ctx['vehicles'][0]['observable']
