"""Natural-language search over ARGUS metadata, with optional local CLIP appearance ranking.
Parsing is deterministic and offline. Words that are not metadata (colours, clothing, etc.) form the visual prompt."""
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from sqlalchemy import select, func, or_
from .analytics import VEHICLES
from .db import Event, Job, Track, Video, Geometry, Camera
from .vision import COCO_NAMES

UNITS={'s':1,'sec':1,'secs':1,'second':1,'seconds':1,'m':60,'min':60,'mins':60,'minute':60,'minutes':60,'h':3600,'hr':3600,'hrs':3600,'hour':3600,'hours':3600,'day':86400,'days':86400,'week':604800,'weeks':604800}
UNIT=r'(seconds?|secs?|minutes?|mins?|hours?|hrs?|days?|weeks?|s|m|h)'
ALIASES={n:n for n in COCO_NAMES if n!='orange'}
ALIASES.update({'people':'person','persons':'person','pedestrian':'person','pedestrians':'person','human':'person','humans':'person','man':'person','men':'person','woman':'person','women':'person','boy':'person','girl':'person','child':'person','children':'person','kid':'person','kids':'person','angler':'person','anglers':'person','fisherman':'person','fishermen':'person','motorbike':'motorcycle','motorbikes':'motorcycle','bike':'bicycle','bikes':'bicycle','cyclist':'bicycle','lorry':'truck','lorries':'truck','phone':'cell phone','mobile phone':'cell phone','television':'tv','sofa':'couch','puppy':'dog','oranges':'orange','vehicle':'vehicle','vehicles':'vehicle'})
EVENTS=[(r'restricted(?: zone)?(?: entr\w*)?','Restricted Zone Entry'),(r'overcrowd\w*|crowd(?:ed|ing|s)?|occupancy','Crowd Threshold'),(r'line crossings?|cross(?:ed|es|ing)?','Line Crossing'),
        (r'dwell\w*|stay(?:ed|ing|s)?|linger\w*|wait(?:ed|ing|s)?|remain(?:ed|ing|s)?','Dwell Threshold'),(r'stopped|parked|stationary','Stopped Vehicle'),(r'congest\w*|traffic jams?|heavy traffic','Traffic Congestion'),
        (r'convoy delays?|delayed convoy','Convoy Traffic Delay'),(r'corridor entr\w*','Corridor Entry'),(r'speed(?:ing|ers?)?|over the (?:speed )?limit|too fast','Speeding'),(r'processing failures?|failed analys\w*','Video Processing Failure'),(r'offline|disconnect\w*','Camera Offline')]
AGGREGATE={'Crowd Threshold','Traffic Congestion','Camera Offline','Video Processing Failure'}
STATUS=[(r'unreviewed|new (?:events?|alerts?)','NEW'),(r'verified|confirmed','VERIFIED'),(r'dismissed|false alarms?','DISMISSED'),(r'under review|further review','UNDER REVIEW'),(r'incidents?','CONVERTED TO INCIDENT')]
STOP=set('a an the show me find search for all any with of in on at near by from to that who which were was is are be been there and or video videos camera cameras footage clip clips event events alert alerts track tracks object objects please list get where when some their they it its this these those seen appear appeared appearing detected detect spotted zone area region inside within around than more less over under after before between during last first ago moving heading going walking driving display into'.split())
LEADING=set('show me find search for all any the a an list get display please'.split())

def local_to_utc(dt): return dt.astimezone(timezone.utc).isoformat()

def clock(h,m,ampm):
    h=int(h); m=int(m or 0)
    if ampm=='pm' and h<12: h+=12
    if ampm=='am' and h==12: h=0
    return (h,m) if 0<=h<24 and 0<=m<60 else None

def parse(query,zones=(),videos=(),cameras=(),now=None):
    """Returns filters, human-readable interpretation chips and an optional visual prompt."""
    now=now or datetime.now().astimezone(); midnight=now.replace(hour=0,minute=0,second=0,microsecond=0)
    state={'rest':' '+re.sub(r'\s+',' ',query.lower()).strip()+' '}; state['visual']=state['rest']
    f={}; chips=[]
    def take(pattern,handler,keep_visual=False):
        regex=re.compile(r'(?<![\w-])(?:'+pattern+r')(?![\w-])')
        for m in list(regex.finditer(state['rest'])): handler(m)
        state['rest']=regex.sub(' ',state['rest'])
        if not keep_visual: state['visual']=regex.sub(' ',state['visual'])
    def add(key,value,chip):
        if isinstance(value,list): f.setdefault(key,[]); [f[key].append(v) for v in value if v not in f[key]]
        else: f[key]=value
        if chip not in chips: chips.append(chip)

    take(r'([pvo])-?(\d{1,4})',lambda m:add('track_id',f"{m.group(1).upper()}-{int(m.group(2)):04d}",f"Track {m.group(1).upper()}-{int(m.group(2)):04d}"))
    take(r'(?:in )?(?:the )?first (\d+(?:\.\d+)?) ?'+UNIT+r'(?: of (?:the )?video)?',lambda m:add('video_max',float(m.group(1))*UNITS[m.group(2)],f"Video time ≤ {m.group(1)} {m.group(2)}"))
    take(r'(after|past|from|before|until) (\d{1,2}):(\d{2}) (?:in|into|of) (?:the )?video',lambda m:add('video_min' if m.group(1) in ('after','past','from') else 'video_max',int(m.group(2))*60+int(m.group(3)),f"Video time {'≥' if m.group(1) in ('after','past','from') else '≤'} {m.group(2)}:{m.group(3)}"))
    def relative(m):
        n=float(m.group(1) or 1); since=now-timedelta(seconds=n*UNITS[m.group(2)]); add('since',local_to_utc(since),f"Since {since:%Y-%m-%d %H:%M}")
    take(r'(?:in )?(?:the )?(?:last|past) (\d+(?:\.\d+)?)? ?(minutes?|mins?|hours?|hrs?|days?|weeks?)',relative)
    take(r'(\d+(?:\.\d+)?) (minutes?|mins?|hours?|hrs?|days?|weeks?) ago',relative)
    day=[None]
    def one_day(start,label):
        day[0]=start; add('since',local_to_utc(start),label); add('until',local_to_utc(start+timedelta(days=1)),label)
    take(r'today',lambda m:one_day(midnight,'Today'))
    take(r'yesterday',lambda m:one_day(midnight-timedelta(days=1),'Yesterday'))
    take(r'this week',lambda m:add('since',local_to_utc(midnight-timedelta(days=now.weekday())),'This week'))
    take(r'(?:on )?(20\d\d)-(\d\d)-(\d\d)',lambda m:one_day(midnight.replace(year=int(m.group(1)),month=int(m.group(2)),day=int(m.group(3))),f"On {m.group(0).strip().removeprefix('on ').strip()}"))
    def at(t): base=day[0] or midnight; return base.replace(hour=t[0],minute=t[1])
    def between(m):
        a,b=clock(m.group(1),m.group(2),m.group(3) or m.group(6)),clock(m.group(4),m.group(5),m.group(6))
        if a and b: add('since',local_to_utc(at(a)),f"From {at(a):%H:%M}"); add('until',local_to_utc(at(b)),f"Until {at(b):%H:%M}")
    take(r'between (\d{1,2})(?::(\d{2}))? ?(am|pm)? and (\d{1,2})(?::(\d{2}))? ?(am|pm)?',between)
    def boundary(m):
        if not (m.group(3) or m.group(4)): return
        t=clock(m.group(2),m.group(3),m.group(4))
        if t: add('since' if m.group(1) in ('after','since') else 'until',local_to_utc(at(t)),f"{m.group(1).title()} {at(t):%H:%M}")
    take(r'(after|since|before) (\d{1,2})(?::(\d{2}))? ?(am|pm)?(?= )',boundary)
    def count(m):
        n=int(m.group(2)); word=m.group(3); add('min_count' if m.group(1) in ('more than','over','at least','above') else 'max_count',n,f"Count {'≥' if m.group(1) in ('more than','over','at least','above') else '≤'} {n}")
        if word!='objects': add('object_class',ALIASES.get(word,ALIASES.get(word.rstrip('s'),'vehicle')),f"Class: {ALIASES.get(word,ALIASES.get(word.rstrip('s'),'vehicle'))}")
    take(r'(more than|over|at least|above|fewer than|less than|under) (\d+) (people|persons|vehicles|cars|trucks|buses|objects)',count)
    take(r'confidence (?:above |over |at least |>=? ?)?(\d{1,3}) ?%?',lambda m:add('min_confidence',min(100,int(m.group(1)))/100,f"Confidence ≥ {m.group(1)}%"))
    def duration(m):
        seconds=float(m.group(2))*UNITS[m.group(3)]; low=m.group(1) in ('less than','under','shorter than','within')
        add('max_duration' if low else 'min_duration',seconds,f"Duration {'≤' if low else '≥'} {m.group(2)} {m.group(3)}")
    take(r'(more than|over|longer than|at least|above|for|less than|under|shorter than|within) (\d+(?:\.\d+)?) ?'+UNIT,duration)
    for names,key,label in ((cameras,'cameras','Camera'),(videos,'videos','Video'),(zones,'zones','Zone')):
        for name in sorted({n for n in names if n},key=len,reverse=True):
            take(re.escape(name.lower()),lambda m,name=name,key=key,label=label:add(key,[name],f"{label}: {name}"))
    for pattern,event in EVENTS: take(pattern,lambda m,event=event:add('event_types',[event],f"Event: {event}"))
    for pattern,status in STATUS: take(pattern,lambda m,status=status:add('status',[status],f"Status: {status}"))
    directions={'left':'West','right':'East','up':'North','down':'South'}
    take(r'(?:moving |heading |going |travell?ing |walking |driving )?(north|south|east|west)(?:bound|wards?)?',lambda m:add('direction',m.group(1).title(),f"Direction: {m.group(1).title()}"))
    take(r'moving (left|right|up|down)',lambda m:add('direction',directions[m.group(1)],f"Direction: {directions[m.group(1)]}"))
    take(r'live',lambda m:add('live',True,'Source: live cameras'))
    take(r'uploaded|recorded',lambda m:add('live',False,'Source: uploaded videos'))
    for alias in sorted(ALIASES,key=len,reverse=True):
        take(re.escape(alias)+r'(?:e?s)?',lambda m,alias=alias:add('object_class',ALIASES[alias],f"Class: {ALIASES[alias]}"),keep_visual=True)
    descriptive=[w for w in re.findall(r'[a-z]+',state['rest']) if w not in STOP and len(w)>1]
    visual=None
    if descriptive:
        words=re.findall(r"[a-z0-9']+",state['visual'])
        while words and words[0] in LEADING: words.pop(0)
        while words and words[-1] in STOP: words.pop()
        phrase=' '.join(words)
        if f.get('object_class') and f['object_class']!='vehicle' and f['object_class'] not in phrase and not any(a in phrase for a,c in ALIASES.items() if c==f['object_class']): phrase+=' '+f['object_class']
        visual='a photo of '+phrase.replace('vehicles','vehicle'); chips.append(f"Appearance: {phrase}")
    return {'filters':f,'understood':chips,'visual':visual}

def run(db,query,rank=None,limit=100,now=None):
    """Executes a parsed query against events and tracks. `rank` is the CLIP scorer, or None when unavailable."""
    zones={g.config.get('name','') for g in db.scalars(select(Geometry))}
    cameras={c.name:c.video_id for c in db.scalars(select(Camera))}
    videos={Path(v.filename).stem:v.id for v in db.scalars(select(Video).where(~Video.path.like('live://%')))}
    parsed=parse(query,zones,list(videos),list(cameras),now); f=parsed['filters']
    source_ids=[videos[n] for n in f.get('videos',[])]+[cameras[n] for n in f.get('cameras',[])]; live_ids=list(cameras.values())
    # Re-analysing a video repeats its tracks and events, so recorded results come from the latest run only; every live session counts.
    latest={}
    for j in db.scalars(select(Job).where(Job.state.in_(['COMPLETED','PROCESSING','LIVE'])).order_by(Job.created_at)):
        if j.video_id not in live_ids: latest[j.video_id]=j.id
    current_jobs=list(latest.values())
    event_types=set(f.get('event_types',[])); zone_names={z.lower() for z in f.get('zones',[])}
    want_events=not f.get('direction') and not (parsed['visual'] and not event_types and not f.get('status'))
    want_tracks=not f.get('status') and 'min_count' not in f and 'max_count' not in f and event_types<={'Dwell Threshold'}
    def scoped(q,class_column,video_column,created_column,aggregate=False):
        cls=f.get('object_class')
        if cls:
            match=class_column.in_(VEHICLES) if cls=='vehicle' else class_column==cls
            # Area-wide events (crowd, congestion, offline) have no single object class; their counts carry the class.
            q=q.where(or_(match,class_column.is_(None)) if aggregate else match)
        if f.get('since'): q=q.where(created_column>=f['since'])
        if f.get('until'): q=q.where(created_column<=f['until'])
        if source_ids: q=q.where(video_column.in_(source_ids))
        if f.get('live') is True: q=q.where(video_column.in_(live_ids or ['']))
        if f.get('live') is False and live_ids: q=q.where(video_column.not_in(live_ids))
        return q.where(or_(Job.id.in_(current_jobs or ['']),Job.video_id.in_(live_ids or [''])))
    events=[]; tracks=[]
    if want_events:
        aggregate=bool(event_types&AGGREGATE) or 'min_count' in f or 'max_count' in f
        q=scoped(select(Event).join(Job,Event.job_id==Job.id),Event.object_class,Event.video_id,Event.created_at,aggregate)
        if event_types: q=q.where(Event.type.in_(event_types))
        if zone_names: q=q.where(func.lower(Event.zone).in_(zone_names))
        if f.get('track_id'): q=q.where(Event.track_id==f['track_id'])
        if f.get('status'): q=q.where(Event.status.in_(f['status']))
        if 'video_min' in f: q=q.where(Event.video_time>=f['video_min'])
        if 'video_max' in f: q=q.where(Event.video_time<=f['video_max'])
        if 'min_confidence' in f: q=q.where(Event.confidence>=f['min_confidence'])
        for e in db.scalars(q.order_by(Event.created_at.desc()).limit(2000)):
            a=e.analytics or {}; n=a.get('occupancy',a.get('vehicles')); measured=a.get('dwell_seconds',a.get('stopped_seconds'))
            if ('min_count' in f and (n is None or n<f['min_count'])) or ('max_count' in f and (n is None or n>f['max_count'])): continue
            if measured is not None and ('min_duration' in f and measured<f['min_duration'] or 'max_duration' in f and measured>f['max_duration']): continue
            events.append(e)
    if want_tracks:
        q=scoped(select(Track,Job).join(Job,Track.job_id==Job.id),Track.object_class,Job.video_id,Track.created_at)
        if f.get('track_id'): q=q.where(Track.track_id==f['track_id'])
        for tr,j in db.execute(q.order_by(Track.created_at.desc()).limit(5000)):
            d=tr.data or {}; visited={k.lower():v for k,v in (d.get('zones') or {}).items()}
            if zone_names and not zone_names&set(visited): continue
            # With a zone, duration means dwell inside that zone; otherwise the observed track duration.
            measured=max(visited[z] for z in zone_names&set(visited)) if zone_names else d.get('duration',0)
            if 'min_duration' in f and measured<f['min_duration'] or 'max_duration' in f and measured>f['max_duration']: continue
            if f.get('direction') and d.get('direction')!=f['direction']: continue
            if 'video_min' in f and d.get('last_seen',0)<f['video_min'] or 'video_max' in f and d.get('first_seen',0)>f['video_max']: continue
            tracks.append([tr,j,None])
    visual={'prompt':parsed['visual'],'applied':False,'note':None}; event_scores={}
    if parsed['visual']:
        if rank is None: visual['note']='Appearance terms were not applied: the visual search model is not installed (python scripts/download_clip.py).'
        else:
            scores=rank(parsed['visual'],[(j.id,tr.track_id) for tr,j,_ in tracks]+[(e.job_id,e.track_id) for e in events if e.track_id])
            if not scores: visual['note']='No indexed object crops match the other filters yet.'; tracks=[]; events=[]
            else:
                top=max(scores.values()); cutoff=max(.15,top-.04)
                for item in tracks: item[2]=scores.get((item[1].id,item[0].track_id))
                tracks=sorted([t for t in tracks if (t[2] or -1)>=cutoff],key=lambda t:-t[2])
                event_scores={e.id:scores[(e.job_id,e.track_id)] for e in events if scores.get((e.job_id,e.track_id),-1)>=cutoff}
                events=sorted([e for e in events if e.id in event_scores],key=lambda e:-event_scores[e.id])
                visual.update(applied=True,top=round(top,3),cutoff=round(cutoff,3))
    return {'understood':parsed['understood'],'filters':f,'visual':visual,'events':events[:limit],'tracks':tracks[:limit],'event_scores':event_scores,'searched':{'events':want_events,'tracks':want_tracks}}
