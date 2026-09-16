"""Provider rules, snapshot cameras, class/size filters, tiled detection, detection export and saved detections."""
import subprocess, time
import cv2, numpy as np, imageio_ffmpeg, pytest, supervision as sv
from backend.argus import sources
from backend.argus.sources import validate_url, is_snapshot, resolve, SnapshotReader
from backend.argus.vision import YOLODetector, class_ids, filter_detections, COCO_NAMES
from backend.argus.db import SessionLocal, Job
from backend.argus.worker import process
from test_detect_annotate import AnnotateFixture

def test_blocked_providers_are_rejected_with_reason(client):
    for url,word in [('https://www.skylinewebcams.com/en/webcam/italia/lazio/roma/fontana-di-trevi.html','copyright'),('https://www.youtube.com/watch?v=abc','signed-in'),('https://worldcams.tv/united-states/new-york/bryant-park','re-embeds')]:
        with pytest.raises(ValueError,match=word): validate_url(url)
    r=client.post('/api/cameras',json={'name':'Trevi','url':'https://www.skylinewebcams.com/en/webcam/x.html'})
    assert r.status_code==422 and 'copyright' in r.text
    assert is_snapshot('https://511ga.org/map/Cctv/22609') and is_snapshot('http://10.0.0.9/snapshot.cgi') and not is_snapshot('rtsp://cam/stream')

def test_trafficvision_ga511_resolves_to_official_snapshot(monkeypatch):
    rows={'data':[{'images':[{'description':'COBB-0820: Johnson Ferry Rd at Princeton Lakes Dr (COBB)','imageUrl':'/map/Cctv/22609','disabled':False,'blocked':False}]}]}
    calls=[]
    def fake_get(url,**kw): calls.append((url,kw['params']['query'])); return type('R',(),{'json':lambda self:rows})()
    monkeypatch.setattr(sources.httpx,'get',fake_get)
    url,headers=resolve('https://trafficvision.live/?camera=511ga-cobb-cctv-0820')
    assert url=='https://511ga.org/map/Cctv/22609' and headers['Referer']=='https://511ga.org/' and 'COBB-0820' in calls[0][1]
    with pytest.raises(sources.SourceError): resolve('https://trafficvision.live/?camera=txdot-123')

def test_snapshot_reader_publishes_only_changed_images(monkeypatch):
    a=np.zeros((20,30,3),np.uint8); b=np.full((20,30,3),255,np.uint8); feed=iter([(a,b'a'),(a,b'a'),(b,b'b')]+[(b,b'b')]*50)
    monkeypatch.setattr(sources,'fetch_image',lambda url,headers:next(feed))
    reader=SnapshotReader('https://cam/snap.jpg',{},16,10,1,interval=.02)
    try:
        time.sleep(.5); frame,seq=reader.latest()
        assert seq==2 and frame.shape==(10,16,3) and frame.mean()==255 and not reader.ended
    finally: reader.close()

def test_class_and_size_filters():
    names=dict(enumerate(COCO_NAMES))
    assert class_ids(names,['person','vehicle'])==[0,2,3,5,7] and class_ids(names,None) is None
    d=sv.Detections(xyxy=np.array([[0,0,10,40],[0,0,30,30]],float),confidence=np.array([.9,.8]),class_id=np.array([0,0]))
    assert len(filter_detections(d,20))==1 and len(filter_detections(d,0))==2

def test_tiled_detection_merges_tiles_with_full_frame():
    detector=object.__new__(YOLODetector); detector.imgsz=640; detector.tiling=True; detector.min_box=0; detector.slicer=None
    def fake_predict(frames,size):
        if len(frames)==1 and frames[0].shape[1]==1280: return [sv.Detections(xyxy=np.array([[100,100,900,600]],float),confidence=np.array([.9]),class_id=np.array([5]))]
        return [sv.Detections(xyxy=np.array([[20,20,40,60]],float),confidence=np.array([.6]),class_id=np.array([0])) for _ in frames]
    detector._predict=fake_predict
    result=detector.detect(np.zeros((720,1280,3),np.uint8))
    assert 5 in result.class_id and (result.class_id==0).sum()>=4 and result.xyxy[result.class_id==0][:,0].max()>500

def test_export_and_saved_detections(client,tmp_path):
    src=tmp_path/'clip.mp4'
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-loglevel','error','-f','lavfi','-i','testsrc=size=320x240:rate=25:duration=2','-c:v','libx264','-pix_fmt','yuv420p',str(src)],check=True)
    with src.open('rb') as f:video=client.post('/api/videos',files={'file':('clip.mp4',f,'video/mp4')}).json()
    j=client.post(f"/api/videos/{video['id']}/jobs",json={'mode':'Detect & Annotate','fps':10,'classes':['person','chair'],'tiling':True,'min_box':8}).json()
    assert j['config']['classes']==['person','chair'] and j['config']['tiling'] and j['config']['min_box']==8
    assert client.post(f"/api/videos/{video['id']}/jobs",json={'classes':['spaceship']}).status_code==422
    with SessionLocal() as db:job=db.get(Job,j['id']);job.state='PROCESSING';db.commit()
    process(j['id'],AnnotateFixture)
    rows=client.get(f"/api/jobs/{j['id']}/detections",params={'classes':'chair'}).text.strip().splitlines()
    assert rows[0].startswith('video_time,frame') and len(rows)>10 and all(',chair,' in r for r in rows[1:])
    data=client.get(f"/api/jobs/{j['id']}/detections",params={'format':'json','min_confidence':.85,'end':1}).json()
    assert data and {d['object_class'] for d in data}=={'person'} and max(d['video_time'] for d in data)<=1
    saved=client.post('/api/saved-detections',json={'job_id':j['id'],'video_time':1.0,'classes':['person'],'note':'Gate check'}).json()
    assert [o['object_class'] for o in saved['detections']]==['person'] and saved['source']=='clip.mp4'
    assert client.get(saved['image_url']).headers['content-type']=='image/jpeg'
    assert client.get('/api/saved-detections').json()[0]['id']==saved['id']
    assert client.post('/api/saved-detections',json={'job_id':j['id'],'camera_id':'x'}).status_code==422
    assert client.delete(f"/api/saved-detections/{saved['id']}").status_code==200 and client.get('/api/saved-detections').json()==[]
