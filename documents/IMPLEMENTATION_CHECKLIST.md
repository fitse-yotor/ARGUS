# MVP implementation checklist

Sources read: all five v1 documents in `../Documntation/`. Priority: sprint plan, SRS, architecture, stories, use cases. The master implementation prompt overrides live-camera priority and Sense placeholders: upload-first, real video analytics, simulated CSI only. No downloaded surveillance footage; no identity recognition or threat inference.

## Build sequence
- [x] Foundation: FastAPI, React, PostgreSQL/PostGIS target (validated) / SQLite local, migrations, service boundaries.
- [x] Upload validation, metadata, durable background jobs, sampled inference, failure/cancellation.
- [x] DetectorAdapter (YOLO11n, CUDA/MPS/CPU), Supervision representation/annotations, independent maintained TrackerAdapter (ByteTrack).
- [x] Playback, normalized editable zones/lines/routes with vertex dragging, counts, crowd (configurable ratios)/dwell/traffic rules.
- [x] Convoy designations bound to real temporary tracks and video time; route progress and operational timeline.
- [x] Events, snapshots, timeline seeking, deduplication, human review.
- [x] Verified-event incidents, assignment/lifecycle/notes, event and track search with paging, evidence audit.
- [x] Real-data overview, analytics, operational map with supplied locations.
- [x] Deterministic CSI provider, normalized schema, floor plan, controls, sessions.
- [x] Administration, RBAC, sessions, audit, demo reset, truthful health including GPU.
- [x] Business tests (SQLite and PostgreSQL), integration checks, build, CPU/MPS benchmarks.
- [x] Installation, API/architecture/demo instructions, limitations and Phase 2 ledger.

## Master prompt section status

| § | Requirement | Status |
|---|---|---|
| 1 | Read product documents | Done |
| 2 | Supervision foundation; CSI research-informed simulation | Done |
| 3 / 43 | Crowd, traffic, convoy, RF scenarios | Implemented; field footage validation pending |
| 4 / 35 | Modular architecture; persisted state; PostgreSQL target | Done; PostGIS validated |
| 5 / 6 / 34 | Upload, metadata, mode selection, async jobs with progress/ETA | Done |
| 7–9 | Person/vehicle detection, genuine tracking | Done |
| 10–14 | Zones (10 types), lines, crowd, dwell, traffic analytics | Done; speed, lane flow and speed limits with a road calibration |
| 15 | Convoy mode, status panel, route progress, timeline | Done; metres, spacing and arrival estimate with a road calibration |
| 16–20 | Event engine, video timeline, snapshots, review, incidents | Done |
| 21–24 | RF room, simulation modes, controls, SensorProvider | Done (simulated by design) |
| 25 / 26 | Dashboard, Operations | Done |
| 27 | Addis Ababa GIS with operator-supplied locations | Done |
| 28 | Investigation search (events and tracks) | Done |
| 29 / 30 | Analytics, Administration | Done |
| 31 | Operational UI direction | Done |
| 32 | Demo Control | Done |
| 33 | System health incl. GPU | Done; utilization only where exposed (CUDA) |
| 36 | Configurable processing FPS; 720p/1080p benchmark | Done on CPU and MPS; CUDA/field media pending |
| 37 / 38 | Error handling, security | Done for MVP scope |
| 39 | Automated tests | Done (60 tests) |
| 40 / 41 / 45 | Demo data guidance, README, delivery documents | Done |

### Extensions after MVP delivery

| Feature | Status |
|---|---|
| Any-format upload, Supervision Detect & Annotate | Done |
| Zone and line counting per class | Done |
| Heatmaps (recorded and live) | Done |
| Lock tracking (recorded and live) | Done |
| Natural language search with local CLIP appearance ranking | Done |
| Live RTSP/HTTP/HLS cameras with all of the above, event clips | Done; target-camera validation pending |
| Snapshot (still-image) cameras, including official 511 agency images | Done |
| Detection filters: classes, minimum box size, tiled small-object inference | Done |
| Saved detections and CSV/JSON detection export (recorded and live) | Done |
| Road calibration, vehicle speed, lane flow, speed limits (recorded and live) | Done; ground-truth speed validation pending |
| Physical convoy distance, spacing and arrival estimate | Done; ground-truth validation pending |
| Convoy mode on live cameras with in-session designation | Done; target-camera validation pending |

Remaining work is tracked in [PHASE_2.md](PHASE_2.md).

## Architecture decisions
Separate Python worker consumes durable database jobs; API never performs inference in a request. Media and sampled observation JSONL live on disk; relational records hold tracks, configuration, events and workflow. Jobs snapshot rule configuration. Reanalysis creates a new job to preserve review evidence. Convoy routes are read live because they only measure progress and never alter detections or events. PostgreSQL migrations and SQLite share SQLAlchemy models. Browser playback uses authenticated same-origin media routes and normalized overlays. No camera infrastructure or fusion observations are fabricated.
