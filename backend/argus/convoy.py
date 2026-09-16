"""Convoy context is derived only from observable vehicle tracks. Frame-relative progress needs no calibration;
distance, spacing and arrival estimates are reported only where an operator has drawn a road calibration."""
import json, math
from collections import deque
from shapely.geometry import LineString, Point
from .analytics import route_position, VEHICLES
from .physical import Calibration, SpeedEstimator

LOSS_SECONDS=1.5
ROUTE_TOLERANCE_M=8  # a vehicle further than this from the drawn route is not measured against it
MIN_MOVING_KMH=3  # below this, time gaps and arrival estimates divide by noise

def read_rows(job,start=0,end=float('inf')):
    if not job.observations: return
    with open(job.observations) as f:
        for line in f:
            try: row=json.loads(line)
            except json.JSONDecodeError: continue
            if row['time']>end: break
            if row['time']>=start: yield row

def measurements(vehicles,route=None,calibration=None):
    """Physical spacing, speed and arrival estimate for designated vehicles visible in one frame.
    Each vehicle carries track_id, role, position and an optional speed_kmh."""
    result=dict(calibrated=calibration is not None,route_metric=False,route_length_m=None,lead_track=None,lead_speed_kmh=None,
                average_speed_kmh=None,convoy_length_m=None,eta_seconds=None,largest_gap_m=None,vehicles=[],
                note='Draw a road calibration to measure distance, spacing and arrival time in metres')
    if calibration is None: return result
    result['note']=f'Estimated from calibration "{calibration.name}"; accuracy depends on the measured reference and a fixed camera'
    metric_route=None
    if route:
        corners=[calibration.to_metres(p) for p in route['points']]
        if all(c is not None for c in corners):
            metric_route=LineString(corners); result.update(route_metric=True,route_length_m=round(metric_route.length,1))
    rows=[]
    for v in vehicles:
        world=calibration.to_metres(v['position'])
        if world is None: continue
        item=dict(track_id=v['track_id'],role=v.get('role'),speed_kmh=v.get('speed_kmh'),extrapolated=not calibration.covers(v['position']),
                  gap_m=None,time_gap_s=None,distance_m=None,remaining_m=None,on_route=None)
        if metric_route:
            p=Point(world); along=metric_route.project(p); offset=metric_route.distance(p)
            item.update(distance_m=round(along,1),remaining_m=round(metric_route.length-along,1),offset_m=round(offset,1),on_route=offset<=ROUTE_TOLERANCE_M)
        rows.append((item,world,v.get('designated_at') or 0))
    if not rows: return result
    if metric_route:
        measured=sorted([r for r in rows if r[0]['on_route']],key=lambda r:-r[0]['distance_m'])
        ordered=measured+[r for r in rows if not r[0]['on_route']]
    else:
        anchor=next((r for r in rows if r[0]['role']=='Convoy Lead'),min(rows,key=lambda r:r[2]))
        measured=ordered=sorted(rows,key=lambda r:math.dist(r[1],anchor[1]))
    for ahead,behind in zip(measured,measured[1:]):
        gap=ahead[0]['distance_m']-behind[0]['distance_m'] if metric_route else math.dist(ahead[1],behind[1])
        behind[0]['gap_m']=round(gap,1)
        speed=behind[0]['speed_kmh']
        # A time gap is how long this vehicle needs to reach where the one ahead is now.
        if speed and speed>=MIN_MOVING_KMH: behind[0]['time_gap_s']=round(gap/(speed/3.6),1)
    lead=next((r for r in measured if r[0]['role']=='Convoy Lead'),measured[0] if measured else None)
    speeds=[r[0]['speed_kmh'] for r in measured if r[0]['speed_kmh'] is not None]
    gaps=[r[0]['gap_m'] for r in measured if r[0]['gap_m'] is not None]
    if lead:
        result['lead_track']=lead[0]['track_id']; result['lead_speed_kmh']=lead[0]['speed_kmh']
        if metric_route and lead[0]['speed_kmh'] and lead[0]['speed_kmh']>=MIN_MOVING_KMH:
            result['eta_seconds']=round(lead[0]['remaining_m']/(lead[0]['speed_kmh']/3.6),1)
    if len(measured)>1:
        result['convoy_length_m']=round(measured[0][0]['distance_m']-measured[-1][0]['distance_m'],1) if metric_route else round(math.dist(measured[0][1],measured[-1][1]),1)
    if speeds: result['average_speed_kmh']=round(sum(speeds)/len(speeds),1)
    if gaps: result['largest_gap_m']=max(gaps)
    result['vehicles']=[r[0] for r in ordered]
    return result

def context(job,tracks,t,routes=(),calibration=None):
    designated=[tr for tr in tracks if tr.convoy_role and tr.designated_at<=t]
    nearest=None; visible_samples={tr.track_id:0 for tr in designated}; total_samples={tr.track_id:0 for tr in designated}
    timeline=[dict(time=tr.designated_at,text=f'{tr.track_id} designated {tr.convoy_role}; convoy tracking started') for tr in designated]
    start=min((tr.designated_at for tr in designated),default=None)
    lost={}; last_seen={tr.track_id:tr.designated_at for tr in designated}; state=None; candidate=None; streak=0
    # Speed is recomputed from saved positions so a calibration drawn after processing still measures the convoy.
    estimator=SpeedEstimator(getattr(job,'config',{}).get('fps',10) if calibration else 10); speeds={}
    for row in read_rows(job,0,t+.03):
        nearest=row
        for tr in designated:
            observed=next((o for o in row['objects'] if o['track_id']==tr.track_id),None)
            if calibration and observed and row['time']>=tr.designated_at-2:
                metres=calibration.to_metres(observed['position']) if calibration.covers(observed['position']) else None
                if metres is None: estimator.forget(tr.track_id); speeds.pop(tr.track_id,None)
                else: speeds[tr.track_id]=(row['time'],estimator.update(tr.track_id,metres,row['time']))
            if row['time']<tr.designated_at: continue
            seen=observed is not None
            total_samples[tr.track_id]+=1; visible_samples[tr.track_id]+=seen
            if seen:
                if lost.get(tr.track_id): timeline.append(dict(time=row['time'],text=f'{tr.track_id} observable again'))
                lost[tr.track_id]=False; last_seen[tr.track_id]=row['time']
            elif not lost.get(tr.track_id) and row['time']-last_seen[tr.track_id]>LOSS_SECONDS:
                lost[tr.track_id]=True; timeline.append(dict(time=row['time'],text=f'{tr.track_id} no longer observable in frame'))
        if start is None or row['time']<start: continue
        observed_state=row['analytics'].get('traffic_state')
        if state is None: state=observed_state; continue
        # Two consecutive samples are required so a single noisy count does not become a timeline entry.
        streak=streak+1 if observed_state==candidate else 1; candidate=observed_state
        if candidate!=state and streak>=2: timeline.append(dict(time=row['time'],text=f'Traffic {state} → {candidate}')); state=candidate
    objects=nearest['objects'] if nearest and t-nearest['time']<1.5 else []
    vehicles=[o for o in objects if o['object_class'] in VEHICLES]; visible=[]; nearby=set(); present=[]
    route=routes[0] if routes else None
    for tr in designated:
        o=next((o for o in vehicles if o['track_id']==tr.track_id),None)
        item={'track_id':tr.track_id,'role':tr.convoy_role,'observable':bool(o),'continuity':round(100*visible_samples[tr.track_id]/max(1,total_samples[tr.track_id]),1),'designated_at':tr.designated_at}
        if o:
            neighbors=[v for v in vehicles if v['track_id']!=tr.track_id and math.dist(v['position'],o['position'])<=.25]
            nearby.update(v['track_id'] for v in neighbors)
            measured=speeds.get(tr.track_id)
            speed=measured[1] if measured and nearest and abs(measured[0]-nearest['time'])<1e-6 else None
            item.update(position=o['position'],direction=o.get('direction'),tracking_duration=t-tr.designated_at,nearby_tracks=[v['track_id'] for v in neighbors],stopped_seconds=o.get('stopped_seconds',0),speed_kmh=speed)
            if route: item['route']=route_position(o['position'],route)
            present.append({'track_id':tr.track_id,'role':tr.convoy_role,'position':o['position'],'speed_kmh':speed,'designated_at':tr.designated_at})
        visible.append(item)
    measured=[v for v in visible if v.get('route',{}).get('on_route')]
    lead=next((v for v in measured if v['role']=='Convoy Lead'),None) or max(measured,key=lambda v:v['route']['progress'],default=None)
    note=('Percent along operator-drawn route in frame coordinates; not physical distance' if route else 'Draw a Convoy Route on the frame to measure progress; physical distance requires calibration')
    physical=measurements(present,route,calibration)
    return {'video_time':t,'vehicles':visible,'nearby_tracks':sorted(nearby),'traffic':nearest['analytics'] if nearest else {},'proximity_rule':'Within 0.25 normalized frame units; not physical distance','route':route['name'] if route else None,'route_progress':lead['route']['progress'] if lead else None,'route_progress_track':lead['track_id'] if lead else None,'route_progress_note':note,
            'physical':physical,'arrival_video_time':round(t+physical['eta_seconds'],1) if physical['eta_seconds'] is not None else None,
            'timeline':sorted(timeline,key=lambda e:e['time'])[-50:]}

class LiveConvoy:
    """Convoy state for a running camera: designations come from Track rows, measurements from the current frame.
    Session time is seconds since the camera session started."""
    def __init__(self,settings=None):
        self.settings=settings or {}; self.roles={}; self.lost={}; self.last_seen={}; self.delayed={}; self.timeline=deque(maxlen=50)
    def step(self,objects,summary,t,designations,routes=(),calibration=None):
        events=[]
        for tid,(role,at) in designations.items():
            if self.roles.get(tid)!=role:
                self.timeline.append(dict(time=t,text=f'{tid} designated {role}; convoy tracking started')); self.roles[tid]=role; self.last_seen.setdefault(tid,t)
        for tid in [tid for tid in self.roles if tid not in designations]:
            self.timeline.append(dict(time=t,text=f'{tid} designation cleared')); self.roles.pop(tid); self.lost.pop(tid,None); self.delayed.pop(tid,None)
        present=[]; designated=[]
        for tid,(role,at) in designations.items():
            o=next((o for o in objects if o['track_id']==tid),None)
            if o:
                if self.lost.get(tid): self.timeline.append(dict(time=t,text=f'{tid} observable again'))
                self.lost[tid]=False; self.last_seen[tid]=t
                present.append({'track_id':tid,'role':role,'position':o['position'],'speed_kmh':o.get('speed_kmh'),'designated_at':at})
                delayed=o.get('stopped_seconds',0)>=self.settings.get('stop_seconds',10) or summary.get('traffic_state')=='CONGESTED'
                if delayed and not self.delayed.get(tid):
                    events.append(dict(type='Convoy Traffic Delay',zone=None,track_id=tid,object_class=o['object_class'],confidence=o['confidence'],priority='MEDIUM',
                                       rule={'name':'Designated convoy vehicle stopped or configured congestion','stop_seconds':self.settings.get('stop_seconds',10),'congestion_count':self.settings.get('congestion_count',12)},
                                       analytics={'traffic_state':summary.get('traffic_state'),'stopped_seconds':o.get('stopped_seconds',0),'speed_kmh':o.get('speed_kmh'),'role':role}))
                self.delayed[tid]=delayed
            elif not self.lost.get(tid) and t-self.last_seen.get(tid,t)>LOSS_SECONDS:
                self.lost[tid]=True; self.timeline.append(dict(time=t,text=f'{tid} no longer observable in frame'))
            designated.append({'track_id':tid,'role':role,'designated_at':at,'observable':bool(o),'tracking_duration':round(t-at,1),
                              'speed_kmh':o.get('speed_kmh') if o else None,'position':o['position'] if o else None,
                              'route':route_position(o['position'],routes[0]) if o and routes else None})
        physical=measurements(present,routes[0] if routes else None,calibration)
        status=dict(session_time=round(t,1),vehicles=designated,physical=physical,route=routes[0]['name'] if routes else None,
                    eta_seconds=physical['eta_seconds'],timeline=list(self.timeline)[-20:])
        return events,status
