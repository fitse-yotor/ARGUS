"""Supervision frame rendering shared by recorded analysis and live cameras."""
import cv2
import numpy as np
import imageio_ffmpeg
import supervision as sv

ZONE_COLOR=sv.Color.from_hex('#86BDC7'); LINE_COLOR=sv.Color.from_hex('#F2BB62'); LOCK_COLOR=sv.Color.from_hex('#F2BB62'); DIM_COLOR=sv.Color.from_hex('#6B7B88'); CALIBRATION_COLOR=sv.Color.from_hex('#9FD98C')

def label_for(o):
    """Track label; measured ground speed is appended wherever the calibration covers the vehicle."""
    text=f"{o['track_id']} {o['object_class']} {o['confidence']:.0%}"
    return text+f" {o['speed_kmh']:.0f} km/h" if o.get('speed_kmh') is not None else text
H264=['-vf','pad=ceil(iw/2)*2:ceil(ih/2)*2','-preset','veryfast','-movflags','+faststart']

class Renderer:
    """Boxes, labels and traces per track, configured geometry with live counts, and an optional locked track."""
    def __init__(self,width,height,fps,geometries):
        self.size=(width,height)
        self.scale=sv.calculate_optimal_text_scale((width,height)); self.thickness=sv.calculate_optimal_line_thickness((width,height))
        self.boxes=sv.BoxAnnotator(thickness=self.thickness,color_lookup=sv.ColorLookup.TRACK)
        self.dim_boxes=sv.BoxAnnotator(color=DIM_COLOR,thickness=1)
        self.labels=sv.LabelAnnotator(text_scale=self.scale,text_thickness=max(1,self.thickness//2),color_lookup=sv.ColorLookup.TRACK,smart_position=True)
        self.traces=sv.TraceAnnotator(thickness=self.thickness,trace_length=max(10,int(fps*2)),color_lookup=sv.ColorLookup.TRACK)
        self.set_geometries(geometries)
    def set_geometries(self,geometries): self.geometries=[g for g in geometries if g.get('enabled',True)]
    def draw(self,frame,tracked,objects,summary,locked=None):
        scene=frame.copy(); w,h=self.size; measured={z['id']:z for z in summary.get('zones',[])}
        for g in self.geometries:
            points=(np.array(g['points'])*[w,h]).astype(int)
            color=ZONE_COLOR if g['kind']=='zone' else CALIBRATION_COLOR if g['kind']=='calibration' else LINE_COLOR
            if g['kind'] in ('zone','calibration'): scene=sv.draw_polygon(scene,points,color,self.thickness)
            else:
                for a,b in zip(points,points[1:]): scene=sv.draw_line(scene,sv.Point(*a),sv.Point(*b),color,self.thickness)
            z=measured.get(g['id'])
            speed=f" {z['average_speed_kmh']:.0f} km/h" if z and z.get('average_speed_kmh') is not None else ''
            text=g['name']+(f" {g.get('width_m')}×{g.get('length_m')} m" if g['kind']=='calibration' else
                            f" IN {z['IN']} OUT {z['OUT']}{speed}" if z and z['kind']=='line' else f" {z['occupancy']}/{z['threshold']} {z['status']}{speed}" if z else '')
            scene=sv.draw_text(scene,text,sv.Point(*points[0]),text_color=sv.Color.BLACK,text_scale=self.scale,background_color=color)
        ids=[o['track_id'] for o in objects]
        if locked and locked in ids:
            index=ids.index(locked); x1,y1,x2,y2=[int(v) for v in tracked.xyxy[index]]
            # Everything except the locked track is dimmed so the operator's selection stays unambiguous.
            clean=scene.copy(); scene=cv2.convertScaleAbs(scene,alpha=.45); scene[y1:y2,x1:x2]=clean[y1:y2,x1:x2]
            others=tracked[np.arange(len(ids))!=index]
            if len(others): scene=self.dim_boxes.annotate(scene,others)
            cv2.rectangle(scene,(x1,y1),(x2,y2),LOCK_COLOR.as_bgr(),self.thickness+2)
            o=objects[index]; offset=int(24*self.scale)
            scene=sv.draw_text(scene,f'LOCKED {label_for(o)}',sv.Point((x1+x2)//2,max(offset,y1-offset)),text_color=sv.Color.BLACK,text_scale=self.scale,background_color=LOCK_COLOR)
            scene=self.inset(scene,frame,(x1,y1,x2,y2))
        else:
            if len(tracked):
                scene=self.traces.annotate(scene,tracked); scene=self.boxes.annotate(scene,tracked)
                scene=self.labels.annotate(scene,tracked,labels=[label_for(o) for o in objects])
            if locked: scene=sv.draw_text(scene,f'LOCKED {locked} · NOT VISIBLE',sv.Point(w//2,int(40*self.scale)),text_color=sv.Color.BLACK,text_scale=self.scale,background_color=LOCK_COLOR)
        return scene
    def inset(self,scene,frame,box):
        """Zoomed follow view of the locked track in the top-right corner."""
        w,h=self.size; x1,y1,x2,y2=box; cx,cy=(x1+x2)/2,(y1+y2)/2
        ch=min(h,max(x2-x1,y2-y1,16)*1.6); cw=min(w,ch*4/3); iw=int(w*.26); ih=int(iw*.75); margin=int(16*self.scale)
        sx=int(max(0,min(w-cw,cx-cw/2))); sy=int(max(0,min(h-ch,cy-ch/2))); crop=frame[sy:int(sy+ch),sx:int(sx+cw)]
        if crop.size==0 or margin+ih>h: return scene
        scene[margin:margin+ih,w-iw-margin:w-margin]=cv2.resize(crop,(iw,ih),interpolation=cv2.INTER_LINEAR)
        cv2.rectangle(scene,(w-iw-margin,margin),(w-margin,margin+ih),LOCK_COLOR.as_bgr(),2)
        return scene

class AnnotatedVideo(Renderer):
    """Writes every rendered frame to H.264. Between inference samples the latest detections are held,
    so boxes can trail fast motion slightly."""
    def __init__(self,path,meta,geometries):
        super().__init__(meta['width'],meta['height'],meta['fps'],geometries)
        self.writer=imageio_ffmpeg.write_frames(str(path),self.size,pix_fmt_in='bgr24',fps=meta['fps'],codec='libx264',macro_block_size=1,ffmpeg_log_level='error',output_params=H264+['-crf','23'])
        self.writer.send(None)
    def write(self,frame,tracked,objects,summary):
        scene=self.draw(frame,tracked,objects,summary); self.writer.send(np.ascontiguousarray(scene)); return scene
    def close(self): self.writer.close()

def draw_objects(frame,objects):
    """Boxes and labels for a saved set of normalized detections."""
    scene=frame.copy()
    if not objects: return scene
    h,w=frame.shape[:2]; n=len(objects)
    detections=sv.Detections(xyxy=np.array([[o['box'][0]*w,o['box'][1]*h,o['box'][2]*w,o['box'][3]*h] for o in objects],float),confidence=np.array([o['confidence'] for o in objects]),class_id=np.arange(n),tracker_id=np.arange(n))
    scale=sv.calculate_optimal_text_scale((w,h)); thickness=sv.calculate_optimal_line_thickness((w,h))
    scene=sv.BoxAnnotator(thickness=thickness,color_lookup=sv.ColorLookup.INDEX).annotate(scene,detections)
    return sv.LabelAnnotator(text_scale=scale,color_lookup=sv.ColorLookup.INDEX,smart_position=True).annotate(scene,detections,labels=[f"{o['track_id']} {o['object_class']} {o['confidence']:.0%}" for o in objects])

def write_clip(path,jpegs,fps):
    """Encodes buffered annotated JPEG frames into an MP4 event clip."""
    frames=[f for f in (cv2.imdecode(np.frombuffer(j,np.uint8),cv2.IMREAD_COLOR) for j in jpegs) if f is not None]
    if not frames: return False
    h,w=frames[0].shape[:2]
    writer=imageio_ffmpeg.write_frames(str(path),(w,h),pix_fmt_in='bgr24',fps=fps,codec='libx264',macro_block_size=1,ffmpeg_log_level='error',output_params=H264+['-crf','26'])
    writer.send(None)
    for f in frames: writer.send(np.ascontiguousarray(f if f.shape[:2]==(h,w) else cv2.resize(f,(w,h))))
    writer.close(); return True
