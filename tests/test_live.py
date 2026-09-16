"""Live sources, rendering, heatmaps and an end-to-end camera session driven by a looped local file.
Fixture detections are test-only."""
import subprocess, time
import cv2, httpx, numpy as np, imageio_ffmpeg, pytest, supervision as sv
from backend.argus import sources, visual
from backend.argus.sources import validate_url, mask, earthcam_stream, input_args, probe, FrameReader, resolve
from backend.argus.render import Renderer
from backend.argus.heatmap import Heatmap, render
from backend.argus.db import SessionLocal, Camera, Event, Job, Track
from backend.argus.live import CameraRunner, LIVE_DIR
from backend.argus.vision import COCO_NAMES

FF=imageio_ffmpeg.get_ffmpeg_exe()
def clip(path,seconds=6):
    subprocess.run([FF,'-y','-loglevel','error','-f','lavfi','-i',f'testsrc=size=320x240:rate=25:duration={seconds}','-c:v','libx264','-pix_fmt','yuv420p',str(path)],check=True); return path

def test_url_validation_and_masking():
    assert validate_url(' rtsp://10.0.0.5:554/stream ')=='rtsp://10.0.0.5:554/stream'
    for bad in ['file:///etc/passwd','ftp://camera/x','rtsp:// space']:
        with pytest.raises(ValueError): validate_url(bad)
    assert mask('rtsp://admin:secret@10.0.0.5:554/live')=='rtsp://admin:***@10.0.0.5:554/live'
    assert input_args('rtsp://x/y',{})[:2]==['-rtsp_transport','tcp']

def test_earthcam_page_resolution(monkeypatch):
    html='{"cam_a":{"disableHofPosting":false,"stream":"https:\\/\\/videos.earthcam.com\\/a.flv\\/playlist.m3u8?t=1"},"cam_b":{"disableHofPosting":false,"stream":"https:\\/\\/videos.earthcam.com\\/b.flv\\/playlist.m3u8?t=2"}}'
    assert earthcam_stream(html,'cam_b')=='https://videos.earthcam.com/b.flv/playlist.m3u8?t=2'
    monkeypatch.setattr(sources.httpx,'get',lambda *a,**k:type('R',(),{'text':html})())
    url,headers=resolve('https://www.earthcam.com/usa/newyork/pulaski/?cam=cam_a')
    assert url.endswith('a.flv/playlist.m3u8?t=1') and headers['Referer']=='https://www.earthcam.com/'
    with pytest.raises(sources.SourceError): earthcam_stream('<html></html>')

def test_probe_and_reader_keep_latest_frame(tmp_path):
    path=str(clip(tmp_path/'cam.mp4')); assert probe(path,{}).shape==(240,320,3)
    reader=FrameReader(path,{},160,120,10,realtime=True)
    try:
        deadline=time.time()+15
        while reader.latest()[1]<5 and time.time()<deadline: time.sleep(.1)
        frame,seq=reader.latest(); assert seq>=5 and frame.shape==(120,160,3)
    finally: reader.close()

def test_heatmap_accumulates_and_renders_transparent_png(tmp_path):
    heat=Heatmap(); obj=dict(position=[.25,.5],object_class='person')
    for _ in range(10): heat.add([obj],.1)
    heat.add([dict(position=[.9,.9],object_class='car')],.1)
    heat.save(tmp_path/'heat.npz'); png,peak,seconds=render(tmp_path/'heat.npz','person',320,180)
    image=cv2.imdecode(np.frombuffer(png,np.uint8),cv2.IMREAD_UNCHANGED)
    assert image.shape==(180,320,4) and image[90,80,3]>100 and image[10,300,3]==0 and abs(peak-1)<1e-5 and abs(seconds-1.1)<1e-5
    vehicle=cv2.imdecode(np.frombuffer(render(tmp_path/'heat.npz','vehicle',320,180)[0],np.uint8),cv2.IMREAD_UNCHANGED)
    assert vehicle[90,80,3]==0

def test_renderer_lock_dims_others_and_adds_follow_view():
    frame=np.full((360,640,3),200,np.uint8); r=Renderer(640,360,10,[])
    tracked=sv.Detections(xyxy=np.array([[50,100,110,300],[400,120,460,320]],float),confidence=np.array([.9,.8]),class_id=np.array([0,0]),tracker_id=np.array([1,2]))
    objects=[dict(track_id='P-0001',object_class='person',confidence=.9),dict(track_id='P-0002',object_class='person',confidence=.8)]
    normal=r.draw(frame,tracked,objects,{}); locked=r.draw(frame,tracked,objects,{},locked='P-0001')
    assert locked[340,300].mean()<normal[340,300].mean()-60
    assert np.abs(locked[20:150,460:620].astype(int)-normal[20:150,460:620].astype(int)).mean()>10
    missing=r.draw(frame,tracked,objects,{},locked='P-0099'); assert missing[340,300].mean()>150

class LiveFixture:
    names=dict(enumerate(COCO_NAMES))
    def __init__(self,*args): pass
    def detect(self,frame):
        return sv.Detections(xyxy=np.array([[40,20,120,200]],float),confidence=np.array([.9]),class_id=np.array([0]))

def test_live_camera_session_end_to_end(client,tmp_path,monkeypatch):
    monkeypatch.setattr(visual,'available',lambda:False)
    cam=client.post('/api/cameras',json={'name':'River cam','url':'rtsp://viewer:secret@camera.local/stream','fps':10,'width':640}).json()
    assert cam['url']=='rtsp://viewer:***@camera.local/stream' and cam['state']=='WAITING FOR LIVE SERVICE'
    assert all(v['id']!=cam['video_id'] for v in client.get('/api/videos').json())
    assert client.post('/api/cameras',json={'name':'Bad','url':'file:///etc/passwd'}).status_code==422
    assert client.post(f"/api/videos/{cam['video_id']}/geometries",json={'name':'Bank','kind':'zone','type':'Crowd Zone','points':[[0,0],[1,0],[1,1],[0,1]],'threshold':1}).status_code==200
    assert client.post(f"/api/cameras/{cam['id']}/lock",json={'track_id':'P-0000'}).json()['lock_track_id']=='P-0000'
    assert client.post(f"/api/cameras/{cam['id']}/lock",json={'track_id':'bad'}).status_code==422
    with SessionLocal() as db: version=db.get(Camera,cam['id']).updated_at
    runner=CameraRunner(cam['id'],version,detector_factory=LiveFixture,source=str(clip(tmp_path/'loop.mp4')),realtime=True,max_ticks=30)
    runner.run(); assert not runner.failed
    with SessionLocal() as db:
        job=db.query(Job).filter(Job.video_id==cam['video_id']).one(); status=db.get(Camera,cam['id']).status
        events=db.query(Event).filter(Event.job_id==job.id).all(); tracks=db.query(Track).filter(Track.job_id==job.id).all()
        assert job.state=='COMPLETED' and job.summary['total_classes']=={'person':1} and [t.track_id for t in tracks]==['P-0000']
        crowd=next(e for e in events if e.type=='Crowd Threshold'); assert crowd.clip and cv2.VideoCapture(crowd.clip).read()[0]
        assert status['state']=='STOPPED' and status['locked']['track_id']=='P-0000' and status['width']==320
    assert (LIVE_DIR/cam['id']/'latest.jpg').is_file() and (LIVE_DIR/cam['id']/'raw.jpg').is_file()
    exported=client.get(f"/api/jobs/{job.id}/detections").text.strip().splitlines()
    assert len(exported)>=20 and ',P-0000,person,' in exported[1] and len(exported[1].split(',')[2])>0
    stream=client.get(f"/api/cameras/{cam['id']}/stream",params={'frames':1})
    assert stream.headers['content-type'].startswith('multipart/x-mixed-replace') and stream.content.startswith(b'--frame\r\nContent-Type: image/jpeg')
    assert client.get(f"/api/jobs/{job.id}/heatmap.png").headers['content-type']=='image/png'
    assert client.get(f"/api/events/{crowd.id}/clip").status_code==200
    detail=client.get(f"/api/events/{crowd.id}").json(); assert detail['camera']['name']=='River cam' and detail['clip_url']
    assert client.put(f"/api/cameras/{cam['id']}",json={'url':cam['url'],'enabled':False}).json()['state']=='STOPPED'
    with SessionLocal() as db: assert db.get(Camera,cam['id']).url=='rtsp://viewer:secret@camera.local/stream'
