"""Ground-plane calibration, speed estimation, lane analytics and physical convoy measurements.
A synthetic perspective camera stands in for real footage: metres are projected into frame coordinates with a
known homography, so every measured value has a ground truth to compare against."""
import json
from types import SimpleNamespace
import pytest
from backend.argus.analytics import AnalyticsEngine, validate_geometry
from backend.argus.convoy import context, measurements, LiveConvoy
from backend.argus.db import SessionLocal, Video, Job, Track, Camera
from backend.argus.physical import Calibration, SpeedEstimator
from backend.argus.schemas import GeometryInput

WIDTH_M=3.5; LENGTH_M=40

def project(x,y):
    """Synthetic camera: metres on the road plane to normalized frame coordinates."""
    den=.02*y+1
    return [(.03*x+.45)/den,(-.01*y+.9)/den]

ROAD=[project(0,0),project(WIDTH_M,0),project(WIDTH_M,LENGTH_M),project(0,LENGTH_M)]
CALIBRATION={'id':'c','kind':'calibration','name':'Road','points':ROAD,'width_m':WIDTH_M,'length_m':LENGTH_M}

def lane(**kwargs):
    return dict(id='lane',kind='zone',name='Lane 1',type='Lane',points=ROAD,object_class='vehicle',threshold=10,dwell_seconds=0,stop_seconds=10,**kwargs)

def vehicle(tid='V-0001',x=1.75,y=0,cls='car'):
    p=project(x,y)
    return dict(track_id=tid,position=p,box=[p[0]-.02,p[1]-.05,p[0]+.02,p[1]],object_class=cls,confidence=.9)

def test_calibration_inverts_the_projection_and_rejects_bad_quads():
    calibration=Calibration(CALIBRATION)
    for x,y in [(0,0),(1.75,20),(3.5,40),(2,5)]:
        measured=calibration.to_metres(project(x,y))
        assert measured==pytest.approx((x,y),abs=1e-6)
    assert calibration.covers(project(1.75,20))
    assert not calibration.covers(project(1.75,55))  # beyond the measured rectangle
    validate_geometry('calibration',ROAD)
    with pytest.raises(ValueError): validate_geometry('calibration',ROAD[:3])
    # A crossed quadrilateral cannot be a perspective view of a rectangle.
    with pytest.raises(ValueError): validate_geometry('calibration',[ROAD[0],ROAD[1],ROAD[3],ROAD[2]])
    with pytest.raises(ValueError): GeometryInput(name='Road',kind='calibration',points=ROAD)
    assert GeometryInput(name='Road',kind='calibration',points=ROAD,width_m=WIDTH_M,length_m=LENGTH_M).length_m==LENGTH_M

def test_speed_matches_known_ground_speed_despite_pixel_noise():
    estimator=SpeedEstimator(fps=10); calibration=Calibration(CALIBRATION); speeds=[]
    for i in range(30):
        t=i/10; y=2*t  # 2 m per second is 7.2 km/h
        jitter=.0008 if i%2 else -.0008
        point=[project(1.75,y)[0]+jitter,project(1.75,y)[1]+jitter]
        kmh=estimator.update('V-0001',calibration.to_metres(point),t)
        if kmh is not None: speeds.append(kmh)
    assert speeds and all(abs(s-7.2)<1.5 for s in speeds[3:])

def test_speed_history_restarts_after_an_identity_switch():
    estimator=SpeedEstimator(fps=10); calibration=Calibration(CALIBRATION)
    for i in range(8): estimator.update('V-0001',calibration.to_metres(project(1.75,2*i/10)),i/10)
    # The same track ID jumping 30 m in one sample is an identity switch, not a 1000 km/h vehicle.
    assert estimator.update('V-0001',calibration.to_metres(project(1.75,32)),.8) is None
    assert len(estimator.history['V-0001'])==1

def moving_lane_sequence(engine,speed_ms,samples=20,tid='V-0001',start=0):
    summaries=[]; events=[]
    for i in range(samples):
        t=start+i/10
        summary,step_events=engine.step([vehicle(tid,y=min(LENGTH_M-1,speed_ms*t))],t)
        summaries.append(summary); events+=step_events
    return summaries,events

def test_lane_speed_limit_flow_and_speeding_events():
    engine=AnalyticsEngine([CALIBRATION,lane(speed_limit_kmh=50)],dict(fps=10,free_flow_kmh=50))
    summaries,events=moving_lane_sequence(engine,20)  # 20 m/s is 72 km/h
    measured=[s['zones'][0]['average_speed_kmh'] for s in summaries if s['zones'][0]['average_speed_kmh'] is not None]
    assert measured and all(abs(v-72)<3 for v in measured)
    speeding=[e for e in events if e['type']=='Speeding']
    assert len(speeding)==1 and speeding[0]['analytics']['speed_limit_kmh']==50
    assert speeding[0]['analytics']['speed_kmh']>50 and speeding[0]['analytics']['over_by_kmh']>0
    assert summaries[-1]['calibrated'] and summaries[-1]['speeding_vehicles']==1
    # The vehicle standing in the zone on the first sample is occupancy, not an arrival.
    assert summaries[-1]['zones'][0]['flow_per_hour']==0
    summary,_=engine.step([vehicle('V-0001',y=LENGTH_M-1),vehicle('V-0002',y=5)],2.0)
    assert summary['zones'][0]['flow_per_hour']>0 and summary['zones'][0]['occupancy']==2

def test_traffic_state_falls_when_measured_speed_is_low():
    engine=AnalyticsEngine([CALIBRATION,lane()],dict(fps=10,congestion_count=12,free_flow_kmh=50)); raised=[]
    for i in range(12):
        t=i/10; crawl=1*t  # 1 m/s is 3.6 km/h
        summary,events=engine.step([vehicle(f'V-000{n}',x=1.75,y=crawl+n*6) for n in range(3)],t)
        raised+=events
    assert summary['speed_samples']==3 and summary['median_speed_kmh']<10
    # Three vehicles are far below the count threshold, but the road is not flowing.
    assert summary['traffic_state']=='CONGESTED' and summary['traffic_basis']=='count and measured speed'
    # The state change is announced once, when measured speed first shows the road is not moving.
    congestion=[e for e in raised if e['type']=='Traffic Congestion']
    assert len(congestion)==1 and congestion[0]['analytics']['basis']=='count and measured speed'

def test_counting_line_reports_hourly_flow_and_crossing_speed():
    line=dict(id='l',kind='line',name='Cordon',points=[project(-1,20),project(5,20)],object_class='vehicle',events=True)
    engine=AnalyticsEngine([CALIBRATION,line],dict(fps=10,free_flow_kmh=50))
    summaries,events=moving_lane_sequence(engine,20,samples=20)
    crossing=[e for e in events if e['type']=='Line Crossing']
    assert len(crossing)==1 and abs(crossing[0]['analytics']['speed_kmh']-72)<4
    measured=summaries[-1]['zones'][0]
    assert measured['TOTAL']==1 and measured['flow_per_hour']>0 and abs(measured['average_speed_kmh']-72)<4

def convoy_vehicle(tid,role,y,speed):
    return {'track_id':tid,'role':role,'position':project(1.75,y),'speed_kmh':speed,'designated_at':0}

def test_convoy_measures_spacing_speed_and_arrival():
    calibration=Calibration(CALIBRATION)
    route={'name':'Main road','points':[project(1.75,0),project(1.75,LENGTH_M)]}
    lead=convoy_vehicle('V-0001','Convoy Lead',30,36)  # 36 km/h is 10 m/s
    follower=convoy_vehicle('V-0002','Convoy Vehicle',10,36)
    result=measurements([follower,lead],route,calibration)
    assert result['calibrated'] and result['route_metric']
    assert result['route_length_m']==pytest.approx(LENGTH_M,abs=.1)
    assert result['lead_track']=='V-0001' and result['eta_seconds']==pytest.approx(1,abs=.1)
    assert result['convoy_length_m']==pytest.approx(20,abs=.2)
    ordered=result['vehicles']
    assert [v['track_id'] for v in ordered]==['V-0001','V-0002']
    assert ordered[0]['distance_m']==pytest.approx(30,abs=.2) and ordered[0]['remaining_m']==pytest.approx(10,abs=.2)
    assert ordered[1]['gap_m']==pytest.approx(20,abs=.2) and ordered[1]['time_gap_s']==pytest.approx(2,abs=.1)
    # Without a calibration the same vehicles yield no physical measurement, only the reason why.
    plain=measurements([lead,follower],route,None)
    assert not plain['calibrated'] and plain['eta_seconds'] is None and 'calibration' in plain['note']

def test_recorded_convoy_context_measures_speed_from_saved_observations(tmp_path):
    rows=[]
    for i in range(40):
        t=i/10; y=10*t  # 10 m/s is 36 km/h
        rows.append(dict(time=round(t,2),frame=i,objects=[{**vehicle('V-0001',y=min(y,LENGTH_M-1)),'stopped_seconds':0}],analytics={'traffic_state':'FREE FLOW'}))
    path=tmp_path/'obs.jsonl'; path.write_text('\n'.join(json.dumps(r) for r in rows))
    job=SimpleNamespace(observations=str(path),config={'fps':10})
    track=SimpleNamespace(track_id='V-0001',convoy_role='Convoy Lead',designated_at=0)
    route={'name':'Main road','points':[project(1.75,0),project(1.75,LENGTH_M)]}
    result=context(job,[track],2.0,[route],Calibration(CALIBRATION))
    assert result['vehicles'][0]['speed_kmh']==pytest.approx(36,abs=2)
    physical=result['physical']
    assert physical['vehicles'][0]['distance_m']==pytest.approx(20,abs=1)
    assert physical['eta_seconds']==pytest.approx(2,abs=.3) and result['arrival_video_time']==pytest.approx(4,abs=.3)
    # The same analysis without a calibration keeps frame-relative progress only.
    assert context(job,[track],2.0,[route])['physical']['calibrated'] is False

def test_live_convoy_tracks_designation_loss_and_delay():
    monitor=LiveConvoy({'stop_seconds':10}); designations={'V-0001':('Convoy Lead',0.0)}
    events,status=monitor.step([{**vehicle('V-0001',y=10),'stopped_seconds':0}],{'traffic_state':'FREE FLOW'},0.,designations)
    assert not events and status['vehicles'][0]['observable']
    assert any('designated Convoy Lead' in e['text'] for e in status['timeline'])
    _,status=monitor.step([],{'traffic_state':'FREE FLOW'},2.,designations)
    assert any('no longer observable' in e['text'] for e in status['timeline'])
    events,status=monitor.step([{**vehicle('V-0001',y=10),'stopped_seconds':12}],{'traffic_state':'FREE FLOW'},3.,designations)
    assert any('observable again' in e['text'] for e in status['timeline'])
    assert [e['type'] for e in events]==['Convoy Traffic Delay']
    # A delay that is already active does not repeat every frame.
    repeat,_=monitor.step([{**vehicle('V-0001',y=10),'stopped_seconds':13}],{'traffic_state':'FREE FLOW'},4.,designations)
    assert not repeat

class MovingCarFixture:
    """Test-only detector: one car crossing the calibrated road at a known 36 km/h."""
    def __init__(self,*args,**kwargs): self.sample=0
    def detect(self,frame):
        import numpy as np, supervision as sv
        height,width=frame.shape[:2]
        t=self.sample/5; self.sample+=1  # the job samples five frames per second
        x,y=project(1.75,min(10*t,LENGTH_M-2))
        px,py=x*width,y*height
        box=[[px-8,max(0,py-20),px+8,py]]
        return sv.Detections(xyxy=np.array(box,float),confidence=np.array([.95]),class_id=np.array([2]))

def test_worker_measures_speed_end_to_end(client,tmp_path):
    import cv2, numpy as np
    from backend.argus.worker import process
    path=tmp_path/'road.avi'; writer=cv2.VideoWriter(str(path),cv2.VideoWriter_fourcc(*'MJPG'),10,(160,120))
    for _ in range(30): writer.write(np.zeros((120,160,3),np.uint8))
    writer.release()
    with path.open('rb') as f: video=client.post('/api/videos',files={'file':('road.avi',f,'video/x-msvideo')}).json()
    assert client.post(f"/api/videos/{video['id']}/geometries",json={'name':'Road','kind':'calibration','points':ROAD,'width_m':WIDTH_M,'length_m':LENGTH_M}).status_code==200
    assert client.post(f"/api/videos/{video['id']}/geometries",json={'name':'Lane 1','kind':'zone','type':'Lane','points':ROAD,'object_class':'vehicle','speed_limit_kmh':20,'dwell_seconds':0}).status_code==200
    job=client.post(f"/api/videos/{video['id']}/jobs",json={'mode':'Traffic','fps':5}).json()
    with SessionLocal() as db: db.get(Job,job['id']).state='PROCESSING'; db.commit()
    process(job['id'],MovingCarFixture)
    state=client.get(f"/api/jobs?video_id={video['id']}").json()[0]
    assert state['state']=='COMPLETED',state['error']
    assert state['summary']['calibrated'] and state['summary']['calibration']=='Road'
    rows=client.get(f"/api/jobs/{job['id']}/observations?start=0&end=10").json()
    measured=[o['speed_kmh'] for r in rows for o in r['objects'] if o.get('speed_kmh') is not None]
    assert measured and all(abs(v-36)<4 for v in measured)
    track=client.get(f"/api/jobs/{job['id']}/tracks").json()[0]
    assert abs(track['data']['max_speed_kmh']-36)<4 and track['data']['speed_samples']>3
    speeding=[e for e in client.get(f"/api/events?job_id={job['id']}").json() if e['type']=='Speeding']
    assert len(speeding)==1 and speeding[0]['analytics']['speed_limit_kmh']==20 and speeding[0]['zone']=='Lane 1'
    path_rows=client.get(f"/api/jobs/{job['id']}/track-path?track_id={track['track_id']}").json()['path']
    assert any(r['speed_kmh'] is not None and r['world'] for r in path_rows)

class LiveCarFixture:
    """Test-only detector: a car driving up and down the calibrated road at a steady 10 m/s.
    Position follows the wall clock, so the measured speed is independent of frame pacing."""
    def __init__(self,*args,**kwargs):
        import time
        self.start=time.monotonic()
    def detect(self,frame):
        import time, numpy as np, supervision as sv
        height,width=frame.shape[:2]
        travelled=10*(time.monotonic()-self.start)
        y=2+abs((travelled%66)-33)  # a fold keeps the car moving without ever jumping position
        x,py=project(1.75,y)
        px,py=x*width,py*height
        return sv.Detections(xyxy=np.array([[px-8,max(0,py-20),px+8,py]],float),confidence=np.array([.95]),class_id=np.array([2]))

def test_live_camera_measures_speed_and_convoy(client,tmp_path,monkeypatch):
    import subprocess, threading, time
    import imageio_ffmpeg
    from backend.argus import visual
    from backend.argus.live import CameraRunner
    monkeypatch.setattr(visual,'available',lambda:False)
    source=tmp_path/'road.mp4'
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-loglevel','error','-f','lavfi','-i','testsrc=size=320x240:rate=25:duration=30','-c:v','libx264','-pix_fmt','yuv420p',str(source)],check=True)
    created=client.post('/api/cameras',json={'name':'Convoy cam','url':'rtsp://camera.local/stream','mode':'Convoy','fps':10,'width':640})
    assert created.status_code==200,created.text
    cam=created.json()
    assert client.post(f"/api/videos/{cam['video_id']}/geometries",json={'name':'Road','kind':'calibration','points':ROAD,'width_m':WIDTH_M,'length_m':LENGTH_M}).status_code==200
    assert client.post(f"/api/videos/{cam['video_id']}/geometries",json={'name':'Main road','kind':'route','points':[project(1.75,2),project(1.75,LENGTH_M-2)]}).status_code==200
    with SessionLocal() as db: version=db.get(Camera,cam['id']).updated_at
    runner=CameraRunner(cam['id'],version,detector_factory=LiveCarFixture,source=str(source),realtime=True,max_ticks=400)
    thread=threading.Thread(target=runner.run,daemon=True); thread.start()

    def wait_for(check,timeout=40):
        deadline=time.time()+timeout
        while time.time()<deadline:
            value=check()
            if value: return value
            time.sleep(.5)
        return None
    try:
        status=wait_for(lambda:(client.get('/api/cameras').json()[0]['status'] or {}).get('job_id') and client.get('/api/cameras').json()[0]['status'])
        assert status and not runner.failed
        job_id=status['job_id']
        track=wait_for(lambda:next((t for t in client.get(f'/api/jobs/{job_id}/tracks').json() if t['track_id'].startswith('V-')),None))
        assert track,'live session never saved a vehicle track'
        designated=client.post(f"/api/cameras/{cam['id']}/convoy",json={'track_id':track['track_id'],'role':'Convoy Lead'})
        assert designated.status_code==200
        convoy=wait_for(lambda:(lambda s:s.get('convoy') if s.get('convoy',{}).get('physical',{}).get('vehicles') else None)(client.get('/api/cameras').json()[0]['status'] or {}))
        assert convoy,'convoy measurements never appeared in the camera status'
        measured=convoy['physical']['vehicles'][0]
        assert convoy['physical']['calibrated'] and convoy['physical']['route_metric']
        assert 0<=measured['distance_m']<=LENGTH_M
        assert abs(measured['speed_kmh']-36)<12  # 10 m/s, with slack for the fold and frame pacing
        assert any('designated Convoy Lead' in e['text'] for e in convoy['timeline'])
        live=client.get('/api/cameras').json()[0]['status']
        assert live['summary']['calibrated'] and live['visible'][0]['speed_kmh'] is not None
    finally:
        runner.stop(); thread.join(timeout=30)

def test_calibration_api_allows_one_per_view(client):
    with SessionLocal() as db:
        v=Video(filename='road.mp4',path='/x',metadata_json={'fps':10,'width':640,'height':360}); db.add(v); db.commit(); vid=v.id
    body={'name':'Road','kind':'calibration','points':ROAD,'width_m':WIDTH_M,'length_m':LENGTH_M}
    saved=client.post(f'/api/videos/{vid}/geometries',json=body)
    assert saved.status_code==200 and saved.json()['width_m']==WIDTH_M
    assert client.post(f'/api/videos/{vid}/geometries',json=body).status_code==409
    assert client.post(f'/api/videos/{vid}/geometries',json={**body,'width_m':None}).status_code==422
    assert client.put(f"/api/geometries/{saved.json()['id']}",json={**body,'length_m':45}).json()['length_m']==45
    lane_zone={'name':'Lane 1','kind':'zone','type':'Lane','points':ROAD,'object_class':'vehicle','speed_limit_kmh':50}
    assert client.post(f'/api/videos/{vid}/geometries',json=lane_zone).json()['speed_limit_kmh']==50
    assert client.post(f'/api/videos/{vid}/jobs',json={'mode':'Traffic','free_flow_kmh':60}).json()['config']['free_flow_kmh']==60

def test_live_camera_convoy_designation(client):
    cam=client.post('/api/cameras',json={'name':'Road cam','url':'rtsp://camera.local/stream','mode':'Convoy'}).json()
    assert cam['mode']=='Convoy'
    designate={'track_id':'V-0001','role':'Convoy Lead'}
    assert client.post(f"/api/cameras/{cam['id']}/convoy",json=designate).status_code==409  # no running session
    with SessionLocal() as db:
        job=Job(video_id=cam['video_id'],mode='Convoy',state='LIVE',config={}); db.add(job); db.flush()
        db.add(Track(job_id=job.id,track_id='V-0001',object_class='car',data={'first_seen':1,'last_seen':7.5}))
        db.add(Track(job_id=job.id,track_id='P-0001',object_class='person',data={'first_seen':1,'last_seen':7.5}))
        db.commit()
    result=client.post(f"/api/cameras/{cam['id']}/convoy",json=designate)
    assert result.status_code==200 and result.json()['convoy_role']=='Convoy Lead' and result.json()['designated_at']==7.5
    assert client.post(f"/api/cameras/{cam['id']}/convoy",json={'track_id':'P-0001','role':'Convoy Vehicle'}).status_code==422
    assert client.post(f"/api/cameras/{cam['id']}/convoy",json={'track_id':'V-0009','role':'Convoy Vehicle'}).status_code==409
    assert client.post(f"/api/cameras/{cam['id']}/convoy",json={'track_id':'V-0001'}).json()['convoy_role'] is None
