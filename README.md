# ARGUS

<img src="frontend/public/argus-logo.png" alt="ARGUS logo" width="220">

**See. Sense. Understand. Respond.**

A functional local MVP for recorded-video detection, tracking, configurable zone/line analytics, human-reviewed events and incident coordination, plus an explicitly simulated WiFi CSI room.

**Central workflow:** upload → choose mode → draw zones/lines → background analysis → annotated playback → event timeline → verify → incident → assignment/status → search/audit.

## Quick start

Requirements: Python **3.11+**, Node **22.12+** with npm, approximately 3 GB free for dependencies/model, and additional media storage. CPU works; no RF hardware is needed. FFmpeg is provided by `imageio-ffmpeg`; a system install is optional. The initial model download is about 5.4 MB. No surveillance footage is downloaded.

From the repository root, use the single entry point:

```sh
python start.py
```

On Windows, `py -3.11 start.py` also works when `python` points to another version. On Linux/macOS, use `python3 start.py` if the `python` command is unavailable.

The first run creates `.venv` and `.env`, installs Python and frontend packages, migrates the database, downloads the YOLO model, and starts the API, vision worker, live camera service, and web app. Dependency installs are skipped on later runs unless `requirements.txt` or `frontend/package-lock.json` changes. The initializer asks for an administrator password (12+ characters) on first run unless `ADMIN_PASSWORD` is set in `.env`. Default username: `admin`. Keep `.env` private.

Open **http://127.0.0.1:5173**. Press **Ctrl+C** in the startup terminal to stop all four services. For a later run, use the same `python start.py` command.

Optional appearance search needs a separate ~600 MB CLIP download: `.venv/Scripts/python.exe scripts/download_clip.py` on Windows or `.venv/bin/python scripts/download_clip.py` on Linux/macOS.

### Run each process separately

For debugging, you can still run each process separately from the repository root with the virtual environment active. Run `python start.py` once first to complete setup.

```sh
# Terminal 1: API
uvicorn backend.argus.main:app --host 127.0.0.1 --port 8000
# Terminal 2: durable vision worker
python -m backend.argus.worker
# Terminal 3: live camera service
python -m backend.argus.live
# Terminal 4: React workspace
npm run dev --prefix frontend
```

The simulator is a lightweight provider hosted by the API; there is no additional daemon to start. Open **ARGUS Sense** for its controls. The `vision-service/` and `simulation-service/` directories document these service boundaries; shared Python contracts live under `backend/argus/`.

## Database and Docker

SQLite is the local fallback. Migrations run through `python scripts/init_db.py` or `alembic upgrade head`.

For PostgreSQL/PostGIS, set `DATABASE_URL=postgresql+psycopg://user:password@host:5432/argus` and run the initializer. The database user needs extension-creation permission for the initial PostGIS migration. Subsequent API requests use the same relational models. The basic map stores supplied coordinates; advanced spatial queries are deferred.

Docker Compose provisions PostgreSQL/PostGIS, migrations, API, worker and nginx/React:

1. Start Docker Desktop / Docker Engine.
2. Set unique `POSTGRES_PASSWORD` and `ADMIN_PASSWORD` values in `.env`. Prefer URL-safe passwords for the Compose database URL.
3. Ensure `storage/models/yolo11n.pt` exists by running the model download command above. On Linux, make `storage/` writable by container UID 1000.
4. Run:

```sh
docker compose up --build
```

Open **http://127.0.0.1:8080**. The API is also bound locally on port 8000. Local and Docker servers cannot both occupy that port. The provided Compose configuration defaults to CPU.

**Validation boundary:** PostgreSQL 16 / PostGIS 3.4 was validated in a disposable `postgis/postgis:16-3.4` container: migrations, seeding and the full test suite pass. The Compose application images (API, worker, nginx) were not built here. To rerun the suite on any disposable PostgreSQL database (tables are dropped):

```sh
ARGUS_TEST_DATABASE_URL=postgresql+psycopg://argus:PASSWORD@127.0.0.1:5432/argus_test python -m pytest -q
```

## GPU and CPU inference

`DEVICE=auto` selects CUDA, then Apple MPS, then CPU; `cpu`, `cuda:0` or `mps` force a device. The detector uses YOLO11 nano COCO weights and 640×640 letterboxed inference. Supported classes: person, car, motorcycle, bus, truck. Each job records the resolved device, and **Administration → System Health** shows whether a GPU is in use, available but unused, or unavailable.

On macOS, MPS runs the network on the GPU and non-maximum suppression on CPU (torchvision has no MPS kernel for it). This was verified on this Intel Mac with a Radeon Pro 555X: detections match CPU output and inference is roughly 2.4× faster. macOS does not expose GPU utilization to PyTorch, so that field reads "Not exposed by platform".

For NVIDIA hardware, install a PyTorch build matching the host CUDA driver, keep `DEVICE=auto` or set `cuda:0`, and restart the worker. Docker GPU use additionally requires NVIDIA Container Toolkit and GPU device reservation in a Compose override. An invalid device produces a failed analysis; switch back to `cpu` to retry. CUDA is implemented but untested here.

Intel macOS resolves to PyTorch 2.2.2, which warns about its NumPy 2 bridge. ARGUS's detector uses buffer-based tensor conversion and list-based output normalization instead of that bridge; real inference passed on this machine. Modern Linux/Apple Silicon PyTorch builds are preferable for future deployment. OpenCV is pinned to 4.11 because the newer Intel Mac wheel lacked FFmpeg support.

Models are replaceable through `DetectorAdapter`. Administration → Models registers approved local `.pt` files, computes checksums on activation, and selects the active model for new jobs. Existing jobs retain their configuration. Only use trusted approved model weights. Ultralytics is AGPL-3.0/commercial; review its distribution terms before proprietary deployment.

## Using video analysis

1. Open **Operations** and upload a video: MP4, MOV, AVI, MKV, WEBM, M4V, MPG/MPEG, 3GP, WMV, FLV, TS/MTS/M2TS or OGV, including HEVC phone recordings. ARGUS keeps the original unchanged and prepares a normalized H.264 MP4 with the bundled FFmpeg: phone rotation is applied, variable frame rate becomes constant (capped at 60 FPS), and the video plays in the browser immediately. Filename, duration, resolution, FPS, frame count, size and source format are recorded. Preparation takes roughly real time or less for 1080p on CPU.
2. Select **Detect & Annotate** (default), **Event / Crowd**, **Traffic**, **Convoy** or **General**. Set processing FPS and confidence. Start with 5–10 FPS on CPU.
   - **Detect & Annotate** follows the Supervision "Detect and Annotate" example: all 80 COCO classes, ByteTrack IDs, `BoxAnnotator`, `LabelAnnotator` and `TraceAnnotator`. Every analysis — in any mode — also renders an annotated MP4 with configured zones, lines and live counts drawn in. Toggle **Supervision annotated** on the player, or use **Download annotated**. Between inference samples the latest boxes are held, so raise processing FPS for fast motion.
3. Pause on a useful frame. Select **Draw zone**, click polygon corners, name it, choose its type/class, occupancy/dwell/stop thresholds, speed limit, ELEVATED/CRITICAL ratios and severity, then Save. **Draw line** takes two endpoints; **Calibrate road** takes four measured corners. Drag any placed point to adjust it; **Edit** reopens a saved geometry for dragging.
4. Start analysis. Leave the page if needed; the worker continues. Progress, elapsed time, frame count, measured processing FPS and failure state persist.
5. When complete, play the video with normalized detection boxes, temporary IDs and confidence. The timeline markers seek to event time. Toggle overlays when needed.
6. Changing rules after analysis requires a **new analysis run**. Earlier rules/events remain tied to their original job. Select the desired run in the analysis panel.
7. Review an event, inspect its snapshot/video/rule, enter a note and **Verify**, **Dismiss** or request **Further review**.
8. A verified event can become an incident. Open **Incidents**, assign an enabled operational user and record response, monitoring, resolution and closure notes.
9. **Investigation** filters event metadata by date, source video, mode, class, Track ID, event type, zone and incident number. The **Track metadata** tab searches tracks independently of events and opens the video at the track's first observation. Results are paged 50 at a time.

Track IDs are temporary and job-scoped. Counts are observed tracks, not unique real-world identities. Dwell does not imply intent. Without a road calibration, stopped/congestion measurements are configurable image-based heuristics, not speed or road-capacity estimates.

### Vehicle speed and lane flow

ARGUS measures speed only after you give it one real distance. Pause on a clear frame, select **Calibrate road**, and click the four corners of a rectangle on the road surface in order — near-left, near-right, far-right, far-left — then enter the measured width (point 1 → 2) and length (point 2 → 3) in metres. A lane width or the spacing between road markings is usually enough. ARGUS solves the perspective mapping from that rectangle, so any point on the road plane can be expressed in metres.

Start a new analysis and each vehicle inside the calibrated area carries a speed in km/h, on the boxes, in the annotated video, in the track summary (current, fastest and average) and in the saved observations. **Lane** zones and counting lines report vehicles per hour and average speed; a Lane or Traffic Zone with a **speed limit** raises a `Speeding` event once per vehicle per visit. Traffic state then combines vehicle count with measured speed, so a full road that has stopped moving reads CONGESTED even below the count threshold; set **Free-flow speed** to the speed this road runs at when clear.

Speed is an estimate for situational awareness, not enforcement. It assumes a fixed camera and a flat road, is computed only inside the rectangle you drew, and loses accuracy with distance from the camera, where each pixel covers more ground. ARGUS reports no speed at all — rather than a wrong one — after a tracking gap or a jump that implies over 250 km/h, which is what an identity switch looks like. Live cameras work the same way: draw the calibration under **Zones & lines**, and it takes effect within about five seconds without restarting the session.

### Convoy

Analyze in Convoy mode. Pause playback and click an observed vehicle box; mark **Convoy Lead** or **Convoy Vehicle**. The designation starts at the selected video time. The panel shows visible status, frame-relative position, direction, duration, observation continuity and nearby tracks. Saved observations are evaluated for convoy traffic delay from that time onward. Events and corridor entries appear in the operational timeline. Vehicles are not classified as threats.

Select **Draw route** and click points along the convoy path. The panel then reports route progress as a percent along that line for the lead vehicle (or the furthest designated vehicle), and marks vehicles more than 0.08 frame units from the route as outside tolerance. This percentage is measured in frame coordinates for a fixed camera.

Add a road calibration and the same panel reports physical values: each vehicle's speed, how far it has travelled along the route and how far remains, the spacing to the vehicle ahead in metres, how long it needs to close that gap at its current speed, the length of the convoy, and an estimated time of arrival at the end of the route. Convoy measurements are computed when you ask for them, so a calibration or route drawn after processing applies immediately — no new analysis run. Vehicles outside the calibrated rectangle are marked as such rather than silently extrapolated.

Convoy mode also runs on live cameras. Set the camera's mode to **Convoy**, then designate vehicles from the visible list in the Convoy status panel; times are counted from the start of the camera session. A vehicle that has just appeared may need a second or two before it can be designated, because live tracks are saved periodically.

The **Operational timeline** lists designations, vehicles leaving and re-entering view, and traffic-state changes that persist for two samples; click an entry to seek. Track identity is not recovered across long occlusions or camera cuts.

### Zone counting, heatmaps and lock tracking

- **Zone counting:** every zone reports current occupancy per object class; every line reports IN/OUT per class. Counts are drawn into the annotated video and live view, and listed under the player.
- **Heatmap:** each analysis and live session accumulates object-seconds on a 160×90 frame grid (all, person, vehicle, other). Tick **Heatmap** on the player or live view; the overlay uses square-root scaling so brief paths stay visible. It is frame-relative, not a map projection.
- **Lock tracking:** click any box (or pick a visible ID, or type one such as `P-0003`). ARGUS dims everything else, draws the locked object's trajectory up to the playhead, shows a zoomed follow view, its best crop, first/last seen, direction and longest dwell per zone, with jump buttons. On live cameras the lock is applied server-side: other objects are dimmed in the stream and a follow inset appears top-right; the panel shows whether the ID is currently in view. A temporary ID can change after long occlusion; lock the new ID if that happens.
- **Detection input size:** 640 px by default; choose 960 or 1280 for small or distant objects (slower).

### Live cameras

Open **Live Cameras → Add camera** and paste one of:

| Source | Example | Notes |
|---|---|---|
| RTSP / RTSPS camera | `rtsp://user:password@192.168.1.20:554/stream1` | Read over TCP; the usual choice for CCTV and IP cameras |
| HTTP(S) or HLS stream | `https://host/live/playlist.m3u8` | Any stream FFmpeg can open |
| EarthCam page | `https://www.earthcam.com/usa/newyork/timessquare/?cam=tsrobo1` | Re-resolved on every reconnect because the stream token expires |
| Still-image camera | `http://10.0.0.9/snapshot.jpg` | Polled every 15 s; a frame is analysed only when the image changes |
| trafficvision.live Georgia 511 link | `https://trafficvision.live/?camera=511ga-cobb-cctv-0820` | Resolves to the official 511GA public snapshot; GDOT marks its video feeds authentication-required, so only the public image is used |

Some providers refuse access outside their own player, and ARGUS reports that instead of working around it: **SkylineWebcams** returns a copyright-violation placeholder to other clients, **YouTube** (and **worldcams.tv**, which re-embeds it) requires a signed-in browser session to pass its bot check. Those URLs are rejected when the camera is added.

The live service (`python -m backend.argus.live`, started by `start.py`) reads each camera through FFmpeg (RTSP over TCP), keeps only the newest frame so there is no backlog, and runs detection, ByteTrack, zone/line rules, heatmap, lock tracking and appearance crops at the configured analysis FPS. EarthCam pages are re-resolved on every reconnect because their stream tokens expire.

- The annotated live view is an MJPEG stream (`/api/cameras/{id}/stream`), typically 1–3 s behind real time for HLS sources.
- **Zones & lines** are drawn on the latest raw frame and applied within about five seconds.
- Events are recorded like video events, with a snapshot and a ~10 s annotated **event clip** (5 s before, 5 s after). Continuous footage is not recorded.
- Streams reconnect automatically with backoff; a **Camera Offline** event is raised after 30 s without a connection.
- Changing mode, FPS, input size or processing width restarts the session (new track IDs, counts reset).
- Passwords in URLs are stored in the local database and masked in the UI and API.

Use only cameras you are authorized to monitor. Public webcams and public agency cameras (EarthCam, state 511 systems) are published under their own terms of use; check those terms before any use beyond local personal evaluation, and do not redistribute their footage.

Camera viewpoint decides what can be detected. A high aerial view (EarthCam `tsnorth4k` over Times Square at night) renders people a few pixels tall and yields nothing, while the street-level `tsrobo1` view on the same site gives steady person and vehicle detections. Prefer street-level or mid-height views, and remember that agency snapshot cameras are sometimes offline ("No live camera feed at this time"), which appears as a live camera with no detections.

### Detection filters, small objects and saving detections

Analysis controls (recorded videos) and the camera form/settings (live cameras) share three detection settings:

- **Detect only** — restrict detection to chosen classes; `vehicle` expands to car, motorcycle, bus and truck. The filter narrows the mode's classes and is applied during inference, so tracks, counts, events, heatmaps and exports all follow it. Filtering to `person` removes most false boxes on rocks, signage and street furniture.
- **Detect small objects (tiled)** — Supervision `InferenceSlicer` runs 640 px tiles with 128 px overlap as one GPU batch and merges them with a full-frame pass, so small distant objects are seen at native resolution while large objects stay whole. On a real 1280×720 river scene this raised detections from 10 to 21 (people 5 → 7) at about 4× the compute; use it with a lower analysis FPS.
- **Ignore boxes smaller than (px)** — drops boxes whose shorter side is under the given pixel count.

Detections are saved for every analysed frame of both recorded analyses and live sessions (roughly 1 MB per camera-hour at 5 FPS with few objects), which is what lock tracking, search and these exports read:

- **Export CSV / JSON** on the player and the live view stream every saved detection, filtered by class, confidence, time window and track. CSV columns cover video time, frame, wall-clock time, track ID, class, confidence, normalized and pixel box coordinates, direction and zones.
- **Save detections** stores the current frame with the detections drawn on it, the filters used and your username. Saved frames are listed under **Evidence → Saved detections**, where they can be opened at their source, downloaded or deleted (administrators).

### Natural language and appearance search

**Investigation → Natural language search** understands, offline: object classes and synonyms (people, anglers, vehicles, bikes…), zone, video and camera names, event types (crowd, dwell/stayed/waited, stopped, congestion, line crossing, restricted, offline), review status, counts ("more than 20 people"), durations ("over 2 minutes"), direction ("moving north"), track IDs, confidence, video time ("first 90 seconds", "after 1:30 in the video"), wall-clock time ("today", "yesterday", "last hour", "after 10:30 am", "between 2 pm and 4 pm") and source ("live", "uploaded"). The recognized filters are shown as chips.

Remaining descriptive words ("red", "white coat", "backpack") become an appearance prompt ranked with a local CLIP model (open_clip ViT-B-32, LAION-2B) against the best crop saved for each track. Install it once with `python scripts/download_clip.py`; without it, metadata search still works and the page says appearance terms were ignored. Indexing runs after each analysis and every minute for live sessions. Similarity is a search aid for human review, not identification; there is no face recognition.

### RF room

Open **ARGUS Sense**. Use No Person, Enter Room, Walk, Stand, Sit, Fall, Exit Room, Random Movement, Moving Left or Moving Right. Change simulation speed for repeatable presentations. The floor plan displays room boundaries, entry, two nodes, coverage, synthetic human skeleton, movement trail, node quality, subcarrier amplitudes and session history.

**SIMULATED RF/CSI DATA — MVP DEMONSTRATION** is shown on the page and in the observation schema. This is not real sensing. `SensorProvider` permits a future real calibrated service; `RealCSIProvider` explicitly reports unimplemented operation.

### GIS and demo control

In **GIS Command**, select a video and supply a location name/latitude/longitude. Map markers can show analyses, events and incidents. The initial viewport is Addis Ababa; uploaded video GPS is never inferred. OpenStreetMap tiles require internet; other workflows work locally.

**Demo Control** loads a user-uploaded sample and creates broad scene presets before running real inference. It cannot guarantee an event if the video does not contain the configured condition. Adjust zones/thresholds to fit the footage. RF scenario controls remain explicitly synthetic. Clear incidents, clear events and incidents, or reset workflow after cancelling active jobs. Videos, analysis outputs and audit are retained.

## Tests and verification

```sh
python -m pytest -q
ARGUS_REAL_MODEL_TEST=1 python -m pytest tests/test_real_model.py -q
npm run build --prefix frontend
python scripts/benchmark.py
```

Unit/integration coverage includes metadata extraction, bad uploads, geometry validity, exact-on-line crossing, occupancy transitions, dwell/stop rules, deduplication, detector normalization, real ByteTrack continuity, authentication/RBAC, verification, incident transitions, evidence range requests, model registry, persisted roles, worker success/failure and deterministic simulation. Speed and convoy measurement are tested against a synthetic perspective camera: metres are projected into frame coordinates with a known mapping, so measured speed, spacing and arrival estimates have a ground truth — including a recorded analysis and a live camera session driven end to end. This proves the mathematics and the plumbing, not accuracy on real footage. The opt-in test uses the photograph already bundled by Ultralytics, encoded as a labeled test video. It performs actual inference for crowd, traffic and convoy. It is not field footage or an accuracy evaluation.

Browser checks in `frontend/browser-check.mjs` and `frontend/browser-video-check.mjs` use local Chrome and the generated `.env` credentials. They require running servers; the full video check also requires the labeled fixture at `storage/validation/TEST-bundled-image-fixture.avi`. It creates test operational records; do not run it on a production database. Browser executables may need adjustment outside this Mac.

Measured smoke benchmark (detection, NMS, tracking and analytics; 30 frames after warm-up; 640×640 model input):

| Device | 720p | 1080p |
|---|---|---|
| CPU (i7-9750H, 4 threads) | 7.1 FPS | 7.5 FPS |
| MPS (Radeon Pro 555X) | 18.1 FPS | 16.7 FPS |

See [raw benchmark results](documents/BENCHMARK.json). The fixture is one repeated still image; decode, persistence and output encoding are excluded. Field-video, CUDA and concurrent-stream benchmarks remain pending suitable assets/hardware.

## Source and delivery documents

- [Architecture, rule semantics and research foundations](documents/ARCHITECTURE.md)
- [API guide](documents/API.md) and generated `/docs`
- [Demonstration guide](documents/DEMO_GUIDE.md)
- [Requirements implementation checklist](documents/IMPLEMENTATION_CHECKLIST.md)
- [Phase 2 and known limitations](documents/PHASE_2.md)
- [Original product documentation](Documntation/)

## Known local MVP limits

One worker process is the supported local topology. Tracking can fragment with occlusion, camera motion, low confidence or frame sampling. There is no facial recognition, identity matching, autonomous enforcement or intent inference. Real CSI, fusion, cross-camera tracking, continuous live recording, retention automation, multi-site authorization and production redundancy remain outside this upload-first implementation. Long-video observation files currently scan sequentially. Search is paged, but not backed by a dedicated search index. TLS termination and production backup/monitoring must be configured before network deployment.
