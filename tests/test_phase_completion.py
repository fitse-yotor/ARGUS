import json
from types import SimpleNamespace
import pytest
from backend.argus.analytics import AnalyticsEngine,validate_geometry,route_position
from backend.argus.convoy import context
from backend.argus.db import SessionLocal,Video,Job,Track,Event
from backend.argus.vision import resolve_device

def obj(tid='P-1',x=.5,y=.5,cls='person'):
    return dict(track_id=tid,position=[x,y],box=[x-.02,y-.1,x+.02,y],object_class=cls,confidence=.9)

def test_configurable_crowd_ratios():
    z=dict(id='z',kind='zone',name='Gate',points=[[.1,.1],[.9,.1],[.9,.9],[.1,.9]],type='Crowd Zone',threshold=10,elevated_ratio=.5,critical_ratio=2)
    a=AnalyticsEngine([z])
    s,_=a.step([obj(f'P-{i}') for i in range(5)],0);assert s['zones'][0]['status']=='ELEVATED'
    s,_=a.step([obj(f'P-{i}') for i in range(15)],1);assert s['zones'][0]['status']=='HIGH'
    s,e=a.step([obj(f'P-{i}') for i in range(20)],2);assert s['zones'][0]['status']=='CRITICAL' and e[0]['analytics']['previous_status']=='HIGH'
    with pytest.raises(ValueError): __import__('backend.argus.schemas',fromlist=['x']).GeometryInput(name='x',points=z['points'],elevated_ratio=1.2)

def test_route_geometry_progress_and_engine_ignores_routes():
    route=dict(id='r',kind='route',name='Main road',points=[[0,.5],[.5,.5],[1,.5]])
    validate_geometry('route',route['points'])
    with pytest.raises(ValueError): validate_geometry('route',[[.2,.2],[.2,.2]])
    assert route_position([.25,.52],route)['progress']==25.0
    off=route_position([.5,.9],route);assert not off['on_route'] and off['progress'] is None
    s,e=AnalyticsEngine([route]).step([obj('V-1',cls='car')],0);assert s['zones']==[] and not e

def test_convoy_route_progress_and_timeline(tmp_path):
    rows=[]
    for i in range(40):
        t=i/5; objects=[] if 10<=i<20 else [obj('V-1',x=min(1,i/40),cls='car')]
        rows.append(dict(time=t,frame=i,objects=objects,analytics={'traffic_state':'FREE FLOW' if i<25 else 'CONGESTED'}))
    path=tmp_path/'obs.jsonl';path.write_text('\n'.join(json.dumps(r) for r in rows))
    job=SimpleNamespace(observations=str(path))
    tr=SimpleNamespace(track_id='V-1',convoy_role='Convoy Lead',designated_at=0)
    c=context(job,[tr],7.8,[dict(name='Road',points=[[0,.5],[1,.5]])])
    assert c['route_progress']==pytest.approx(97.5,abs=.1) and c['route_progress_track']=='V-1'
    texts=[e['text'] for e in c['timeline']]
    assert any('no longer observable' in x for x in texts) and any('observable again' in x for x in texts)
    assert sum('FREE FLOW → CONGESTED' in x for x in texts)==1
    assert context(job,[tr],7.8)['route_progress'] is None

def test_resolve_device():
    assert resolve_device('cpu')=='cpu'
    assert resolve_device('auto') in ('cpu','cuda','mps')

def test_event_paging_and_track_search(client):
    with SessionLocal() as db:
        v=Video(filename='road.mp4',path='/x',metadata_json={'fps':10});db.add(v);db.flush()
        j=Job(video_id=v.id,mode='Convoy',state='COMPLETED',config={});db.add(j);db.flush()
        for i in range(3): db.add(Track(job_id=j.id,track_id=f'V-000{i}',object_class='car',data={'first_seen':i,'last_seen':i+5,'trajectory':[[0,0,0]]}))
        db.add(Track(job_id=j.id,track_id='P-0009',object_class='person',data={'first_seen':0,'last_seen':1}))
        for i in range(5): db.add(Event(job_id=j.id,video_id=v.id,type='Line Crossing',video_time=i,frame=i,rule={}))
        db.commit();vid=v.id
    r=client.get('/api/events?limit=2&offset=2');assert r.headers['x-total-count']=='5' and len(r.json())==2
    r=client.get(f'/api/track-search?video_id={vid}&object_class=vehicle&limit=2')
    assert r.headers['x-total-count']=='3' and len(r.json())==2
    item=r.json()[0];assert item['video']=='road.mp4' and 'trajectory' not in item and item['first_seen']==0
    assert client.get('/api/track-search?track_id=p-0009').json()[0]['object_class']=='person'
    assert client.post(f'/api/videos/{vid}/geometries',json={'kind':'route','name':'Route','points':[[0,.5],[1,.5]]}).status_code==200
    assert any(a['action']=='track_search' for a in client.get('/api/audit').json())
