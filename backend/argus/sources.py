"""Live source validation, EarthCam page resolution and FFmpeg frame reading (RTSP, HTTP(S), HLS)."""
import hashlib, json, re, subprocess, threading, time
from urllib.parse import urlparse, parse_qs, urlunparse
import cv2
import httpx
import numpy as np
import imageio_ffmpeg

UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36'
EARTHCAM_HEADERS={'User-Agent':UA,'Referer':'https://www.earthcam.com/'}
SCHEMES={'rtsp','rtsps','http','https'}

GA511='https://511ga.org'
# Providers that deny access outside their own players. ARGUS reports why instead of working around it.
BLOCKED={
    'skylinewebcams.com':'SkylineWebcams only licenses its streams for its own player and sends other clients a copyright-violation placeholder.',
    'youtube.com':'YouTube requires a signed-in browser session (bot check) to read this live stream; ARGUS does not reuse browser cookies to get around it.',
    'youtu.be':'YouTube requires a signed-in browser session (bot check) to read this live stream; ARGUS does not reuse browser cookies to get around it.',
    'worldcams.tv':'worldcams.tv re-embeds YouTube or SkylineWebcams players, which do not allow access outside those players.',
}

class SourceError(Exception): pass

def unsupported(url):
    host=(urlparse(url).hostname or '').lower()
    return next((reason for domain,reason in BLOCKED.items() if host==domain or host.endswith('.'+domain)),None)

def validate_url(url):
    url=url.strip(); p=urlparse(url)
    if p.scheme not in SCHEMES or not p.hostname or any(c.isspace() for c in url): raise ValueError('Use an rtsp://, rtsps://, http:// or https:// camera or stream URL')
    if reason:=unsupported(url): raise ValueError(reason+' Use a camera you are authorized to access, or a provider that publishes an open stream.')
    return url

def is_snapshot(url):
    """Still-image cameras: direct .jpg/.png URLs, 'snapshot' endpoints and 511GA public camera images."""
    path=urlparse(url).path
    return bool(re.search(r'\.(jpe?g|png)$',path,re.I)) or '/map/Cctv/' in path or 'snapshot' in path.lower()

def fetch_image(url,headers,timeout=20):
    try: response=httpx.get(url,headers={'User-Agent':UA,**headers},timeout=timeout,follow_redirects=True)
    except httpx.HTTPError as exc: raise SourceError(f'Snapshot unavailable: {exc}') from exc
    frame=cv2.imdecode(np.frombuffer(response.content,np.uint8),cv2.IMREAD_COLOR) if response.status_code==200 and response.content else None
    if frame is None: raise SourceError(f'Snapshot unavailable: HTTP {response.status_code}')
    return frame,response.content

def ga511_snapshot(url):
    """trafficvision.live Georgia 511 links resolve to the official 511GA public camera image.
    GDOT marks the video feeds as authentication-required, so only the public snapshot is used."""
    camera=parse_qs(urlparse(url).query).get('camera',[''])[0].lower()
    m=re.fullmatch(r'511ga-([a-z]+)-cctv-(\d+)',camera)
    if not m: raise SourceError('Only Georgia 511 cameras (camera=511ga-…) are supported from trafficvision.live; use the agency feed for others')
    term=f'{m.group(1).upper()}-{m.group(2)}'
    query={'columns':[{'data':None,'name':''},{'name':'sortOrder','s':True}],'order':[{'column':1,'dir':'asc'}],'start':0,'length':100,'search':{'value':term}}
    try:
        rows=httpx.get(f'{GA511}/List/GetData/Cameras',params={'query':json.dumps(query),'lang':'en-US'},headers={'User-Agent':UA,'X-Requested-With':'XMLHttpRequest'},timeout=20).json()['data']
    except (httpx.HTTPError,ValueError,KeyError) as exc: raise SourceError(f'Georgia 511 camera list unavailable: {exc}') from exc
    for row in rows:
        for image in row.get('images',[]):
            if image.get('description','').upper().startswith(term+':') and not image.get('disabled') and not image.get('blocked'):
                return GA511+image['imageUrl']
    raise SourceError(f'Georgia 511 camera {term} was not found or is disabled')

def mask(url):
    """Hides embedded camera passwords in API responses and logs."""
    p=urlparse(url)
    if p.password is None: return url
    return urlunparse(p._replace(netloc=f"{p.username}:***@{p.hostname}"+(f":{p.port}" if p.port else '')))

def is_earthcam(url): host=urlparse(url).hostname or ''; return host=='earthcam.com' or host.endswith('.earthcam.com')

def earthcam_stream(html,cam=None):
    block=html
    if cam and (m:=re.search(r'"%s":\{"'%re.escape(cam),html)): block=html[m.start():m.start()+20000]
    streams=re.findall(r'"stream":"(https:[^"]+?\.m3u8[^"]*)"',block)
    if not streams: raise SourceError('No live HLS stream found on the EarthCam page')
    return streams[0].replace('\\/','/')

def resolve(url):
    """Media URL and request headers. EarthCam pages are re-resolved on each connection because stream tokens expire."""
    if is_earthcam(url) and '.m3u8' not in urlparse(url).path:
        try: html=httpx.get(url,headers={'User-Agent':UA},timeout=20,follow_redirects=True).text
        except httpx.HTTPError as exc: raise SourceError(f'EarthCam page unavailable: {exc}') from exc
        return earthcam_stream(html,parse_qs(urlparse(url).query).get('cam',[None])[0]),EARTHCAM_HEADERS
    host=urlparse(url).hostname or ''
    if host=='trafficvision.live' or host.endswith('.trafficvision.live'): return ga511_snapshot(url),{'Referer':GA511+'/'}
    return url,(EARTHCAM_HEADERS if is_earthcam(url) else {})

def input_args(url,headers,realtime=False):
    args=['-rtsp_transport','tcp','-timeout','10000000'] if url.startswith(('rtsp://','rtsps://')) else []
    if headers.get('User-Agent'): args+=['-user_agent',headers['User-Agent']]
    extra=''.join(f'{k}: {v}\r\n' for k,v in headers.items() if k!='User-Agent')
    if extra: args+=['-headers',extra]
    # Local files (tests, recorded demos) are paced at native speed and looped to behave like a camera.
    if realtime: args+=['-re','-stream_loop','-1']
    return args

def probe(url,headers,timeout=45):
    """One decoded frame, used for dimensions and the configuration snapshot."""
    if is_snapshot(url): return fetch_image(url,headers,timeout)[0]
    cmd=[imageio_ffmpeg.get_ffmpeg_exe(),'-nostdin','-hide_banner','-loglevel','error',*input_args(url,headers),'-i',url,'-map','0:v:0','-frames:v','1','-f','image2pipe','-c:v','png','-']
    try: result=subprocess.run(cmd,capture_output=True,timeout=timeout)
    except subprocess.TimeoutExpired as exc: raise SourceError('Timed out connecting to the camera') from exc
    frame=cv2.imdecode(np.frombuffer(result.stdout,np.uint8),cv2.IMREAD_COLOR) if result.stdout else None
    if result.returncode or frame is None:
        raise SourceError('Camera stream unavailable: '+(result.stderr.decode(errors='ignore').strip().splitlines() or ['no video frame'])[-1][:300])
    return frame

class FrameReader:
    """FFmpeg decoder that keeps only the newest frame, so buffered HLS/RTSP backlog never delays analysis."""
    def __init__(self,url,headers,width,height,fps,realtime=False):
        self.width,self.height=width,height; self.frame=None; self.seq=0; self.last=time.time(); self.ended=False; self.error=b''; self.lock=threading.Lock()
        cmd=[imageio_ffmpeg.get_ffmpeg_exe(),'-nostdin','-hide_banner','-loglevel','error',*input_args(url,headers,realtime),'-i',url,
             '-map','0:v:0','-an','-sn','-vf',f'fps={fps},scale={width}:{height}','-f','rawvideo','-pix_fmt','bgr24','-']
        self.proc=subprocess.Popen(cmd,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,bufsize=0)
        threading.Thread(target=self._read,daemon=True).start(); threading.Thread(target=self._errors,daemon=True).start()
    def _read(self):
        size=self.width*self.height*3
        try:
            while True:
                chunks=[]; remaining=size
                while remaining:
                    chunk=self.proc.stdout.read(remaining)
                    if not chunk: return
                    chunks.append(chunk); remaining-=len(chunk)
                frame=np.frombuffer(b''.join(chunks),np.uint8).reshape(self.height,self.width,3)
                with self.lock: self.frame=frame; self.seq+=1; self.last=time.time()
        finally: self.ended=True
    def _errors(self):
        for line in self.proc.stderr: self.error=(self.error+line)[-2000:]
    def latest(self):
        with self.lock: return self.frame,self.seq
    def close(self):
        if self.proc.poll() is None:
            self.proc.terminate()
            try: self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired: self.proc.kill()

class SnapshotReader:
    """Polls a still-image camera. A frame is published only when the image content changes, so a camera
    that refreshes once a minute is not analysed as many identical frames. Tracking across such gaps is not continuous."""
    def __init__(self,url,headers,width,height,fps,interval=None):
        # Still-image cameras typically refresh about once a minute, so polling faster only wastes their bandwidth.
        self.url,self.headers,self.width,self.height=url,headers,width,height; self.interval=interval or max(15.,1/fps)
        self.frame=None; self.seq=0; self.last=time.time(); self.ended=False; self.error=b''; self.digest=None
        self.lock=threading.Lock(); self.stopped=threading.Event()
        threading.Thread(target=self._poll,daemon=True).start()
    def _poll(self):
        failures=0
        while not self.stopped.is_set():
            try:
                frame,data=fetch_image(self.url,self.headers); failures=0; self.last=time.time()
                digest=hashlib.sha1(data).hexdigest()
                if digest!=self.digest:
                    self.digest=digest; frame=cv2.resize(frame,(self.width,self.height))
                    with self.lock: self.frame=frame; self.seq+=1
            except SourceError as exc:
                failures+=1; self.error=str(exc).encode()
                if failures>=5: self.ended=True; return
            self.stopped.wait(self.interval)
    def latest(self):
        with self.lock: return self.frame,self.seq
    def close(self): self.stopped.set()

def open_reader(url,headers,width,height,fps,realtime=False):
    return SnapshotReader(url,headers,width,height,fps) if is_snapshot(url) else FrameReader(url,headers,width,height,fps,realtime)
