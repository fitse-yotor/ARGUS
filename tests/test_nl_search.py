from datetime import datetime, timezone, timedelta
from backend.argus.search import parse, run
from backend.argus.db import SessionLocal, Video, Job, Track, Event, Geometry

NOW=datetime(2026,9,16,15,30,tzinfo=timezone(timedelta(hours=3)))

def test_parse_zone_dwell_duration_and_day():
    p=parse('people who stayed in Gate B for more than 2 minutes yesterday',zones=['Gate B'],now=NOW);f=p['filters']
    assert f['object_class']=='person' and f['zones']==['Gate B'] and f['event_types']==['Dwell Threshold'] and f['min_duration']==120
    assert f['since']=='2026-09-14T21:00:00+00:00' and f['until']=='2026-09-15T21:00:00+00:00' and p['visual'] is None

def test_parse_appearance_zone_and_time_of_day():
    p=parse('red car near the entrance after 10:30 am today',zones=['Entrance'],now=NOW);f=p['filters']
    assert f['object_class']=='car' and f['zones']==['Entrance'] and f['since']=='2026-09-16T07:30:00+00:00'
    assert p['visual']=='a photo of red car'

def test_parse_track_direction_video_time_counts_status():
    f=parse('show P-3 moving north in the first 90 seconds',now=NOW)['filters']
    assert f['track_id']=='P-0003' and f['direction']=='North' and f['video_max']==90
    f=parse('verified crowd events with more than 20 people',now=NOW)['filters']
    assert f['min_count']==20 and f['object_class']=='person' and f['event_types']==['Crowd Threshold'] and f['status']==['VERIFIED']
    f=parse('vehicles stopped over 30 seconds on Pulaski River in the last hour',cameras=['Pulaski River'],now=NOW)['filters']
    assert f['cameras']==['Pulaski River'] and f['object_class']=='vehicle' and f['event_types']==['Stopped Vehicle'] and f['min_duration']==30
    assert f['since']=='2026-09-16T11:30:00+00:00'

def seed():
    with SessionLocal() as db:
        v=Video(filename='river.mp4',path='/x',metadata_json={'fps':10});db.add(v);db.flush()
        j=Job(video_id=v.id,mode='Detect & Annotate',state='COMPLETED',config={});db.add(j);db.flush()
        db.add(Geometry(video_id=v.id,kind='zone',config={'name':'Gate B'}))
        db.add(Track(job_id=j.id,track_id='P-0001',object_class='person',data={'duration':200,'zones':{'Gate B':150},'direction':'North','first_seen':1,'last_seen':201}))
        db.add(Track(job_id=j.id,track_id='P-0002',object_class='person',data={'duration':10,'zones':{'Gate B':5},'first_seen':3,'last_seen':13}))
        db.add(Track(job_id=j.id,track_id='V-0001',object_class='car',data={'duration':50,'first_seen':0,'last_seen':50}))
        db.add(Event(job_id=j.id,video_id=v.id,type='Dwell Threshold',zone='Gate B',track_id='P-0001',object_class='person',video_time=121,frame=1210,rule={},analytics={'dwell_seconds':150}))
        db.add(Event(job_id=j.id,video_id=v.id,type='Crowd Threshold',zone='Gate B',video_time=30,frame=300,status='VERIFIED',rule={},analytics={'occupancy':25}))
        db.commit();return j.id

def test_run_filters_events_tracks_and_visual_ranking(client):
    jid=seed()
    with SessionLocal() as db:
        r=run(db,'people who stayed in Gate B for more than 2 minutes')
        assert [t[0].track_id for t in r['tracks']]==['P-0001'] and [e.type for e in r['events']]==['Dwell Threshold']
        r=run(db,'verified crowd events with more than 20 people')
        assert [e.type for e in r['events']]==['Crowd Threshold'] and r['tracks']==[] and not r['searched']['tracks']
        r=run(db,'person in a white coat')
        assert r['visual']['note'] and len(r['tracks'])==2
        fake=lambda prompt,keys:{k:{'P-0001':.31,'P-0002':.12}[k[1]] for k in keys if k[1] in ('P-0001','P-0002')}
        r=run(db,'person in a white coat',rank=fake)
        assert r['visual']['applied'] and [t[0].track_id for t in r['tracks']]==['P-0001'] and r['tracks'][0][2]==.31
    body=client.get('/api/nl-search',params={'q':'cars in river'}).json()
    assert body['understood'][:2]==['Video: river','Class: car'] and [t['track_id'] for t in body['tracks']]==['V-0001']
    assert client.get('/api/nl-search',params={'q':' '}).status_code==422
    assert any(a['action']=='natural_language_search' for a in client.get('/api/audit').json())
