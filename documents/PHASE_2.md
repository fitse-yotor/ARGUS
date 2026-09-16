# Remaining Phase 2 and deployment work

## Completed after the initial MVP delivery (2026-09-15)

- [x] PostgreSQL 16 / PostGIS 3.4 validated in a disposable container: Alembic migrations reach `0002` (15 tables plus the `postgis` extension), administrator/role/model seeding runs, and the full test suite — 22 tests including real YOLO inference — passes on PostgreSQL through `ARGUS_TEST_DATABASE_URL`.
- [x] Accelerated inference: `DEVICE=auto` selects CUDA, then Apple MPS, then CPU. MPS was verified on this Intel Mac (Radeon Pro 555X): detections match CPU output (maximum box difference 0.0001 px) and the smoke benchmark measures 18.1 FPS at 720p and 16.7 FPS at 1080p, against 7.1 / 7.5 FPS on CPU. See [BENCHMARK.json](BENCHMARK.json).
- [x] GPU health: the worker reports accelerator backend, device name, allocated memory and utilization where the platform exposes it (CUDA). System Health distinguishes GPU in use, available-but-unused, and unavailable.
- [x] Convoy route progress: operators draw a **Convoy Route** on the frame; ARGUS reports percent along the route in frame coordinates, flags vehicles outside route tolerance, and prefers the lead vehicle for overall progress.
- [x] Convoy operational timeline derived from recorded observations: designation, loss/reacquisition of designated vehicles, and debounced traffic-state changes. Entries seek the video.
- [x] Crowd level ratios (ELEVATED / CRITICAL multipliers of the threshold) are configurable per zone.
- [x] Zone, line and route vertices can be dragged after placement.
- [x] Track-only metadata search (Investigation → Track metadata) and paginated event/track results with `X-Total-Count`.
- [x] Any-format upload normalization and Supervision Detect & Annotate (all COCO classes, annotated MP4 for every analysis).
- [x] Per-class zone occupancy and line IN/OUT counting; zones visited and longest dwell stored per track.
- [x] Object-seconds heatmaps (all/person/vehicle/other) for recorded analyses and live sessions.
- [x] Lock tracking: recorded (dim others, trajectory, follow view, track summary) and live (server-side dimming, follow inset, in-view status).
- [x] Offline natural-language search over events and tracks, with local CLIP appearance ranking of per-track crops.
- [x] Live cameras over RTSP/HTTP/HLS (and EarthCam page links): newest-frame ingestion, reconnect with backoff, Camera Offline events, live zones/lines, MJPEG annotated view and 10 s event clips.
- [x] Still-image (snapshot) cameras, including trafficvision.live Georgia 511 links resolved to the official 511GA public image; a frame is analysed only when the image changes.
- [x] Blocked-provider handling: SkylineWebcams, YouTube and worldcams.tv URLs are refused with the reason rather than circumvented.
- [x] Detection filters shared by recorded analyses and cameras: class selection (`vehicle` expands to the four vehicle classes), tiled small-object inference merged with a full-frame pass, and a minimum box size.
- [x] Detections saved for every analysed frame of live sessions as well as recorded analyses; CSV/JSON export with class, confidence, time and track filters; operator-saved frames with drawn detections under Evidence.
- [x] Road calibration (four measured corners → homography) for uploaded video and live cameras: vehicle speed in km/h on tracks, annotations and exports, per-lane and per-line hourly flow and average speed, configurable per-zone speed limits with `Speeding` events, and traffic states that combine vehicle count with measured speed.
- [x] Physical convoy measurement: distance along the route, remaining distance, spacing between vehicles in metres, the time each needs to close its gap, convoy length and an arrival estimate, on recordings and live cameras.
- [x] Convoy mode for live cameras: designate lead and convoy vehicles in the running session, with session timeline, loss/reacquisition and delay events.

## Remaining

- [ ] Validate on user-supplied crowd, traffic and convoy videos with ground-truth counts; measure ID switches, missed crossings and false events.
- [ ] Build and run the complete `docker compose up --build` stack (API, worker, nginx images) on the target host and test backup/restore. The PostGIS database and migrations were validated; the application images were not built here.
- [ ] Benchmark CUDA hardware, representative 720p/1080p field media, four/eight concurrent streams and end-to-end event latency including decode/storage/encode.
- [ ] Camera groups, multi-camera stream wall, continuous recording with retention, WebRTC low-latency output, ONVIF discovery and PTZ, and distributing live sessions across GPU hosts. Validate live analytics on the target cameras.
- [ ] Re-identification across occlusions and cameras for lock tracking; a temporary ID currently ends when the tracker loses the object.
- [ ] Add organization/site/camera-group authorization scopes, federation/SSO, MFA, account recovery and policy-based retention.
- [ ] Implement real CSI sensor registry, acquisition, calibration, health, uncertainty and hardware-specific inference; validate pose locally. Requires physical CSI hardware.
- [ ] Implement Vision + RF correlation with real synchronized sources and provenance. No simulated RF is fused into genuine video incidents.
- [ ] Validate calibrated speed against ground truth (a vehicle driven at a known speed, or GPS logs) and publish the measured error; the current accuracy claim rests on synthetic projection tests only.
- [ ] Map the calibrated ground plane to GIS coordinates so convoy position and arrival can be shown on the map, and support moving or PTZ cameras through re-calibration or stabilization.
- [ ] Add editable rule schedules.
- [ ] Add dwell distributions and advanced reporting; speed and lane flow are not yet in the CSV/JSON export columns.
- [ ] Add indexed long-video observation chunks (playback windows and convoy context still scan JSONL sequentially), a large-site search index and configurable evidence retention.
- [ ] Add independent RF service deployment, durable event bus, distributed worker leases, horizontal scale and crash-safe media finalization.
- [ ] Add map status/area filters, approved offline basemap, PostGIS spatial queries and facility/site layers.
- [ ] Add advanced incident escalation policy, teams, manual incidents, attachments, response-duration reporting and evidence integrity signatures.
- [ ] Harden TLS, host/process isolation, decoder resource limits, secrets management, deployment dependency/container scans and least-privilege database roles.
- [ ] Provide production monitoring, alerting, high availability and disaster recovery. macOS does not expose GPU utilization to PyTorch; utilization is reported only on CUDA.

## Known limitations

The functional loop was validated using deterministic business-logic fixtures and actual YOLO inference on a bundled photograph encoded as test video. There is no representative operational footage in this repository, so detection accuracy and real convoy continuity are unvalidated. Temporary IDs may fragment or switch under occlusion or camera movement. Dwell conservatively resets when observations disappear. Without a road calibration, traffic state remains an image-count heuristic and no velocity is claimed.

Calibrated speed is an estimate, not a metrological measurement, and must not be used for enforcement. It assumes a fixed camera and a flat road, and is only computed inside the drawn rectangle; each pixel covers more ground further from the camera, so error grows with distance. It inherits the accuracy of the operator's tape measure and corner clicks, and of the detector's box bottom as a ground-contact point — a box clipped at the frame edge or a partly occluded vehicle biases the anchor. Speed is suppressed rather than guessed after a tracking gap or an implausible jump, so a vehicle whose ID switches simply reports no speed. Convoy spacing along a route assumes vehicles travel on the drawn line; the gap is measured along that line, not along each vehicle's own path. No ground-truth validation against a known-speed vehicle has been performed in this repository.

Convoy designations are scoped to existing saved tracks; they do not rerun re-identification. Delay evaluation uses observations available when the vehicle is marked, so designate after processing completes for a complete timeline. Re-marking an already evaluated track does not regenerate its historical delay events. Route progress is a projection onto an operator-drawn line in frame coordinates, so it is only meaningful for a fixed camera and is not a physical distance. Only the first enabled route per video is measured.

Uploads are normalized at upload time to constant-frame-rate H.264 MP4, so any decodable format is playable and drawable before analysis; the upload request waits for this preparation, which is slow for very long or 4K files. Frame rates above 60 FPS are reduced to 60. Audio is not retained in the working copy (the original file is kept). The annotated video holds the latest detections between inference samples. Custom models with non-COCO class names work in Detect & Annotate, but ARGUS rules recognize only person, car, motorcycle, bus and truck.

SQLite remains the default local backend; PostgreSQL/PostGIS is validated but the Compose application images were not built. The default topology is one API and one worker. MPS acceleration on this Intel Mac uses PyTorch 2.2.2; non-maximum suppression runs on CPU because torchvision has no MPS kernel for it. CUDA paths are implemented but untested on NVIDIA hardware. Intel Mac PyTorch emits a known NumPy bridge warning; the adapter avoids the bridge and passes real inference tests.

Audit rows are immutable through the API and retained by demo reset, but not protected against direct privileged database modification. Event search pages up to 1,000 rows per request and track search up to 200; audit returns the latest 500. Large exports, site-based RBAC, production TLS and retention automation are not implemented.
