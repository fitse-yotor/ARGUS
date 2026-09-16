"""Timestamp-based analytics on observed tracks. Coordinates are frame-relative; physical speed and distance
are measured only where an operator has drawn a road calibration."""
from collections import Counter, defaultdict, deque
import math, statistics
from shapely.geometry import Point, Polygon, LineString
from .physical import Calibration, SpeedEstimator

VEHICLES={'car','motorcycle','bus','truck'}
ZONE_TYPES=['Monitoring Zone','Restricted Zone','Crowd Zone','Traffic Zone','Lane','Entrance','Exit','Waiting Zone','No-Stopping Zone','Convoy Corridor']
ROAD_TYPES={'Traffic Zone','Lane'}
# Hourly flow is measured over the recent past, not the whole session, so it follows changing traffic.
FLOW_WINDOW=300; MIN_FLOW_SECONDS=10
TRAFFIC_STATES=['FREE FLOW','MODERATE','HEAVY','CONGESTED']
MIN_SPEED_SAMPLES=3

def validate_geometry(kind,points):
    if not all(len(p)==2 and all(math.isfinite(v) and 0<=v<=1 for v in p) for p in points): raise ValueError('Coordinates must be finite values between 0 and 1')
    if kind=='line':
        if len(points)!=2 or math.dist(*points)<.01: raise ValueError('Line needs two distinct points')
    elif kind=='route':
        if len(points)<2 or any(math.dist(a,b)<.005 for a,b in zip(points,points[1:])): raise ValueError('Route needs at least two distinct consecutive points')
        if LineString(points).length<.02: raise ValueError('Route is too short to measure progress')
    elif kind=='calibration':
        if len(points)!=4: raise ValueError('Calibration needs exactly four road corners')
        quad=Polygon(points)
        if not quad.is_valid or quad.area<.0001: raise ValueError('Calibration corners must form a simple quadrilateral with area')
        # A non-convex or self-crossing quad cannot be a perspective view of a road rectangle.
        if quad.convex_hull.area>quad.area*1.000001: raise ValueError('Click the four corners in order around the road rectangle')
    else:
        if len(points)<3: raise ValueError('Polygon needs at least three points')
        polygon=Polygon(points)
        if not polygon.is_valid or polygon.area<.0001: raise ValueError('Polygon must be simple, non-intersecting and have area')

def inside(point,points): return Polygon(points).covers(Point(point))
def side(point,line):
    a,b=line
    return (b[0]-a[0])*(point[1]-a[1])-(b[1]-a[1])*(point[0]-a[0])
def crossing(previous,current,line):
    a,b=side(previous,line),side(current,line)
    if a*b<0 and LineString([previous,current]).intersects(LineString(line)): return 'IN' if b>0 else 'OUT'
    return None

ROUTE_TOLERANCE=.08
def route_position(point,route):
    """Progress along an operator-drawn route in frame coordinates; not physical distance."""
    line=LineString(route['points']); p=Point(point); offset=line.distance(p); on_route=offset<=ROUTE_TOLERANCE
    return dict(route=route['name'],on_route=on_route,offset=round(offset,3),progress=round(100*line.project(p)/line.length,1) if on_route else None)

def direction(a,b):
    dx,dy=b[0]-a[0],b[1]-a[1]
    if math.hypot(dx,dy)<.003: return 'STATIONARY'
    return ('East' if dx>0 else 'West') if abs(dx)>abs(dy) else ('South' if dy>0 else 'North')

class AnalyticsEngine:
    def __init__(self,geometries,settings=None):
        # Routes and the road calibration are measurement references, not counting rules.
        enabled=[g for g in geometries if g.get('enabled',True)]
        self.geometries=[g for g in enabled if g.get('kind') not in ('route','calibration')]
        self.routes=[g for g in enabled if g.get('kind')=='route']
        self.calibration=Calibration.find(enabled)
        self.settings=settings or {}; self.previous={}; self.tracks={}; self.members={}; self.entered={}; self.fired=set()
        self.maxima=defaultdict(int); self.counts=defaultdict(lambda:{'IN':0,'OUT':0,'TOTAL':0})
        self.class_counts=defaultdict(lambda:defaultdict(lambda:{'IN':0,'OUT':0})); self.flows=defaultdict(deque); self.levels={}; self.stationary={}; self.last_congested=False; self.line_previous={}; self.line_cross_times={}
        self.speed=SpeedEstimator(self.settings.get('fps',10)); self.passages=defaultdict(deque); self.over_limit={}; self.started=None
    def elapsed(self,t):
        """Seconds of observation behind the current sample, used as the flow-rate denominator."""
        return max(MIN_FLOW_SECONDS,min(FLOW_WINDOW,t-self.started)) if self.started is not None else MIN_FLOW_SECONDS
    def per_hour(self,key,t): return round(len(self.passages[key])*3600/self.elapsed(t))
    def measure_speed(self,o,t):
        """Ground speed in km/h for a vehicle inside the calibrated road area."""
        tid=o['track_id']; metres=self.calibration.to_metres(o['position']) if self.calibration.covers(o['position']) else None
        if metres is None: self.speed.forget(tid); return
        o['world']=[round(metres[0],2),round(metres[1],2)]
        kmh=self.speed.update(tid,metres,t)
        if kmh is None: return
        o['speed_kmh']=kmh; tr=self.tracks[tid]
        tr['speed_kmh']=kmh; tr['max_speed_kmh']=round(max(tr.get('max_speed_kmh',0),kmh),1)
        samples=tr.get('speed_samples',0)+1
        tr['speed_samples']=samples; tr['mean_speed_kmh']=round(tr.get('mean_speed_kmh',kmh)+(kmh-tr.get('mean_speed_kmh',kmh))/samples,1)
    def step(self,objects,t):
        events=[]; zones=[]; speeding=set()
        first_step=self.started is None
        if first_step: self.started=t
        def emit(typ,g=None,o=None,metrics=None):
            events.append(dict(type=typ,zone=g.get('name') if g else None,track_id=o.get('track_id') if o else None,object_class=o.get('object_class') if o else None,confidence=o.get('confidence') if o else None,priority=(g or {}).get('severity','MEDIUM'),rule=g or self.settings,analytics=metrics or {}))
        seen={o['track_id'] for o in objects}
        for o in objects:
            tid=o['track_id']; p=o['position']; old=self.previous.get(tid)
            continuous=old and t-old[1]<=self.settings.get('max_gap',1.5)
            if tid not in self.tracks: self.tracks[tid]=dict(first_seen=t,trajectory=[],observations=0,object_class=o['object_class'])
            tr=self.tracks[tid]
            sample=1/max(1,self.settings.get('fps',10))
            previous_seen=tr.get('last_seen')
            increment=sample
            if previous_seen is not None and t-previous_seen<=self.settings.get('max_gap',1.5):
                increment=min(sample*1.5,max(0,t-previous_seen))
            tr['observed_seconds']=round(tr.get('observed_seconds',0)+increment,3)
            tr.update(last_seen=t,position=p,confidence=o['confidence'],state='ACTIVE',duration=t-tr['first_seen'])
            tr['observations']+=1; tr['trajectory']=(tr['trajectory']+[[t,*p]])[-600:]
            tr['direction']=direction(tr['trajectory'][max(0,len(tr['trajectory'])-11)][1:],p)
            o.update(direction=tr['direction'],duration=tr['duration'],observed_seconds=tr['observed_seconds'])
            anchor=self.stationary.get(tid)
            if not continuous or not anchor or math.dist(anchor[0],p)>self.settings.get('stop_distance',.015): self.stationary[tid]=(p,t)
            o['stopped_seconds']=t-self.stationary[tid][1]
            if self.calibration and o['object_class'] in VEHICLES: self.measure_speed(o,t)
        for tid,tr in self.tracks.items():
            if tid not in seen: tr['state']='LOST' if t-tr['last_seen']<2 else 'COMPLETED'
        for g in self.geometries:
            key=g['id']; eligible=[o for o in objects if g.get('object_class','all') in ['all',o['object_class']] or (g.get('object_class')=='vehicle' and o['object_class'] in VEHICLES)]
            if g['kind']=='line':
                for o in eligible:
                    lk=(key,o['track_id']); old=self.line_previous.get(lk)
                    d=crossing(old[0],o['position'],g['points']) if old and t-old[1]<=1.5 else None
                    if abs(side(o['position'],g['points']))>1e-7: self.line_previous[lk]=(o['position'],t)
                    if d and t-self.line_cross_times.get(lk,-100)>0.5:
                        self.line_cross_times[lk]=t
                        self.counts[key][d]+=1; self.counts[key]['TOTAL']+=1; self.class_counts[key][o['object_class']][d]+=1
                        self.passages[key].append((t,o.get('speed_kmh')))
                        if g.get('events',True): emit('Line Crossing',g,o,{'direction':d,'speed_kmh':o.get('speed_kmh'),**self.counts[key]})
                while self.passages[key] and self.passages[key][0][0]<t-FLOW_WINDOW: self.passages[key].popleft()
                crossing_speeds=[s for _,s in self.passages[key] if s is not None]
                zones.append(dict(id=key,name=g['name'],kind='line',type='Counting line',by_class={c:dict(v) for c,v in self.class_counts[key].items()},
                                  flow_per_hour=self.per_hour(key,t),flow_window_seconds=round(self.elapsed(t)),
                                  average_speed_kmh=round(statistics.fmean(crossing_speeds),1) if crossing_speeds else None,**self.counts[key])); continue
            members={o['track_id']:o for o in eligible if inside(o['position'],g['points'])}
            previous=self.members.get(key,set()); current=set(members)
            entered=current-previous; exited=previous-current
            for tid in entered:
                self.entered[(key,tid)]=t; self.flows[key].append((t,'IN')); self.counts[key]['IN']+=1
                # Objects already inside on the first sample are standing occupancy, not arrivals.
                if not first_step: self.passages[key].append((t,members[tid].get('speed_kmh')))
                if g['type']=='Restricted Zone': emit('Restricted Zone Entry',g,members[tid])
                if g['type']=='Convoy Corridor' and members[tid]['object_class'] in VEHICLES: emit('Corridor Entry',g,members[tid])
            for tid in exited:
                self.entered.pop((key,tid),None); self.fired.discard((key,tid,'dwell')); self.fired.discard((key,tid,'stop')); self.fired.discard((key,tid,'speed'))
                self.over_limit.pop((key,tid),None)
                self.flows[key].append((t,'OUT')); self.counts[key]['OUT']+=1
            while self.flows[key] and self.flows[key][0][0]<t-60: self.flows[key].popleft()
            while self.passages[key] and self.passages[key][0][0]<t-FLOW_WINDOW: self.passages[key].popleft()
            occupancy=len(current); self.maxima[key]=max(self.maxima[key],occupancy)
            threshold=g.get('threshold',10); ratio=occupancy/max(1,threshold)
            elevated,critical=g.get('elevated_ratio',.8),g.get('critical_ratio',1.25)
            level='CRITICAL' if ratio>=critical else 'HIGH' if ratio>=1 else 'ELEVATED' if ratio>=elevated else 'NORMAL'
            zone_speeds=[o['speed_kmh'] for o in members.values() if o.get('speed_kmh') is not None]
            speed_limit=g.get('speed_limit_kmh') or 0
            metrics=dict(id=key,name=g['name'],kind='zone',type=g['type'],occupancy=occupancy,maximum=self.maxima[key],threshold=threshold,elevated_ratio=elevated,critical_ratio=critical,status=level,entry_rate=sum(d=='IN' for _,d in self.flows[key]),exit_rate=sum(d=='OUT' for _,d in self.flows[key]),trend=len(entered)-len(exited),classes=dict(Counter(o['object_class'] for o in members.values())),
                         flow_per_hour=self.per_hour(key,t),flow_window_seconds=round(self.elapsed(t)),speed_limit_kmh=speed_limit or None,
                         average_speed_kmh=round(statistics.fmean(zone_speeds),1) if zone_speeds else None,
                         stopped_vehicles=sum(o['object_class'] in VEHICLES and o['stopped_seconds']>=g.get('stop_seconds',self.settings.get('stop_seconds',10)) for o in members.values()),**self.counts[key])
            if g['type']=='Crowd Zone' and level!=self.levels.get(key,'NORMAL'): emit('Crowd Threshold',g,metrics={**metrics,'previous_status':self.levels.get(key,'NORMAL')})
            self.levels[key]=level
            for tid,o in members.items():
                dwell=t-self.entered[(key,tid)]; o.setdefault('zones',[]).append(dict(name=g['name'],dwell=dwell))
                # Longest continuous dwell per zone is kept on the track for locked-track review and search.
                visited=self.tracks[tid].setdefault('zones',{}); visited[g['name']]=round(max(visited.get(g['name'],0),dwell),2)
                if g.get('dwell_seconds',0)>0 and dwell>=g['dwell_seconds'] and (key,tid,'dwell') not in self.fired:
                    emit('Dwell Threshold',g,o,{'dwell_seconds':dwell}); self.fired.add((key,tid,'dwell'))
                if speed_limit and o['object_class'] in VEHICLES and o.get('speed_kmh') is not None:
                    if o['speed_kmh']>speed_limit:
                        speeding.add(tid)
                        # Two consecutive over-limit estimates are required so one noisy sample is not an event.
                        self.over_limit[(key,tid)]=self.over_limit.get((key,tid),0)+1
                        if self.over_limit[(key,tid)]>=2 and (key,tid,'speed') not in self.fired:
                            emit('Speeding',g,o,{'speed_kmh':o['speed_kmh'],'speed_limit_kmh':speed_limit,'over_by_kmh':round(o['speed_kmh']-speed_limit,1),'calibration':self.calibration.name,'estimated':True}); self.fired.add((key,tid,'speed'))
                    else: self.over_limit[(key,tid)]=0
                if g['type']=='No-Stopping Zone' and o['object_class'] in VEHICLES:
                    if o['stopped_seconds']>=g.get('stop_seconds',10) and (key,tid,'stop') not in self.fired:
                        emit('Stopped Vehicle',g,o,{'stopped_seconds':o['stopped_seconds']}); self.fired.add((key,tid,'stop'))
                    elif o['stopped_seconds']==0: self.fired.discard((key,tid,'stop'))
            zones.append(metrics); self.members[key]=current
        road_zones=[g for g in self.geometries if g['kind']=='zone' and g['type'] in ROAD_TYPES]
        vehicles=[o for o in objects if o['object_class'] in VEHICLES and (not road_zones or any(inside(o['position'],g['points']) for g in road_zones))]; n=len(vehicles)
        stopped=sum(o['stopped_seconds']>=self.settings.get('stop_seconds',10) for o in vehicles)
        limit=self.settings.get('congestion_count',12)
        state='CONGESTED' if n>=limit else 'HEAVY' if n>=limit*.75 else 'MODERATE' if n>=limit*.4 else 'FREE FLOW'
        speeds=[o['speed_kmh'] for o in vehicles if o.get('speed_kmh') is not None]; basis='count'
        free_flow=self.settings.get('free_flow_kmh',50); median=statistics.median(speeds) if speeds else None
        if len(speeds)>=MIN_SPEED_SAMPLES:
            # Measured speed and vehicle count are combined pessimistically: a slow-moving full road is congested
            # even below the count threshold, and a crowded road is congested even while it still moves.
            ratio=median/max(free_flow,1)
            by_speed='FREE FLOW' if ratio>=.7 else 'MODERATE' if ratio>=.45 else 'HEAVY' if ratio>=.25 else 'CONGESTED'
            state=max(state,by_speed,key=TRAFFIC_STATES.index); basis='count and measured speed'
        if state=='CONGESTED' and not self.last_congested: emit('Traffic Congestion',metrics={'vehicles':n,'threshold':limit,'median_speed_kmh':round(median,1) if median is not None else None,'basis':basis})
        self.last_congested=state=='CONGESTED'
        new_vehicles=sum(tr['object_class'] in VEHICLES and tr['first_seen']>=t-60 for tr in self.tracks.values())
        self.previous={o['track_id']:(o['position'],t) for o in objects}
        return {'people':sum(o['object_class']=='person' for o in objects),'vehicles':n,'total_people':sum(tr['object_class']=='person' for tr in self.tracks.values()),'total_vehicles':sum(tr['object_class'] in VEHICLES for tr in self.tracks.values()),'objects':len(objects),'classes':dict(Counter(o['object_class'] for o in objects)),'total_objects':len(self.tracks),'total_classes':dict(Counter(tr['object_class'] for tr in self.tracks.values())),'zones':zones,'traffic_state':state,'stopped_vehicles':stopped,'vehicles_per_minute':new_vehicles*60/max(1,min(60,t)),
                'calibrated':self.calibration is not None,'calibration':self.calibration.name if self.calibration else None,'traffic_basis':basis,'free_flow_kmh':free_flow,'speed_samples':len(speeds),
                'median_speed_kmh':round(median,1) if median is not None else None,'average_speed_kmh':round(statistics.fmean(speeds),1) if speeds else None,'speeding_vehicles':len(speeding)},events
