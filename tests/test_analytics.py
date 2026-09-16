import pytest
from backend.argus.analytics import AnalyticsEngine,inside,crossing,validate_geometry

def obj(tid='P-1',x=.5,y=.5,cls='person'):
    return dict(track_id=tid,position=[x,y],box=[x-.02,y-.1,x+.02,y],object_class=cls,confidence=.9)
def zone(**kwargs):
    return dict(id='z',kind='zone',name='Gate',points=[[.2,.2],[.8,.2],[.8,.8],[.2,.8]],type='Crowd Zone',threshold=2,dwell_seconds=3,**kwargs)

def test_polygon():
    assert inside([.5,.5],zone()['points'])
    assert not inside([.9,.5],zone()['points'])
    with pytest.raises(ValueError): validate_geometry('zone',[[0,0],[1,1],[0,1],[1,0]])

def test_crossing_segment():
    line=[[.5,.2],[.5,.8]]
    assert crossing([.4,.5],[.6,.5],line)=='OUT'
    assert crossing([.6,.5],[.4,.5],line)=='IN'
    assert crossing([.4,.9],[.6,.9],line) is None

def test_crowd_transitions_and_dedup():
    a=AnalyticsEngine([zone()]);s,e=a.step([obj()],0);assert s['zones'][0]['occupancy']==1 and not e
    s,e=a.step([obj(),obj('P-2')],1);assert any(x['type']=='Crowd Threshold' for x in e)
    s,e=a.step([obj(),obj('P-2')],2);assert not e
    s,e=a.step([],3);assert any(x['analytics']['status']=='NORMAL' for x in e)

def test_dwell_and_reentry():
    a=AnalyticsEngine([zone()]);a.step([obj()],0)
    for t in [1,2]: a.step([obj()],t)
    _,e=a.step([obj()],3);assert sum(x['type']=='Dwell Threshold' for x in e)==1
    _,e=a.step([obj()],4);assert not e
    a.step([],5);a.step([obj()],6);a.step([obj()],7);a.step([obj()],8)
    _,e=a.step([obj()],9);assert any(x['type']=='Dwell Threshold' for x in e)

def test_stopped_is_motion_not_dwell():
    z=zone();z.update(type='No-Stopping Zone',dwell_seconds=0,stop_seconds=2)
    a=AnalyticsEngine([z]);a.step([obj('V-1',cls='car')],0);a.step([obj('V-1',cls='car')],1)
    _,e=a.step([obj('V-1',cls='car')],2);assert any(x['type']=='Stopped Vehicle' for x in e)
    b=AnalyticsEngine([z]);b.step([obj('V-1',x=.3,cls='car')],0);b.step([obj('V-1',x=.4,cls='car')],1)
    _,e=b.step([obj('V-1',x=.5,cls='car')],2);assert not e

def test_restricted_and_line():
    z=zone();z['type']='Restricted Zone';z['dwell_seconds']=0
    line=dict(id='l',kind='line',name='Road',points=[[.5,.1],[.5,.9]])
    a=AnalyticsEngine([z,line]);_,e=a.step([obj(x=.3)],0);assert e[0]['type']=='Restricted Zone Entry'
    s,e=a.step([obj(x=.7)],1);assert any(x['type']=='Line Crossing' for x in e);assert s['zones'][1]['TOTAL']==1

def test_line_counts_when_sample_lands_exactly_on_line():
    a=AnalyticsEngine([dict(id='l',kind='line',name='Gate',points=[[.5,.1],[.5,.9]])])
    a.step([obj(x=.4)],0);a.step([obj(x=.5)],.1)
    summary,events=a.step([obj(x=.6)],.2)
    assert summary['zones'][0]['OUT']==1
    assert len(events)==1
