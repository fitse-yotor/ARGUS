# API guide

Interactive OpenAPI: `http://127.0.0.1:8000/docs`; schema: `/openapi.json`.

All `/api` routes except login require a session cookie. Send `X-Argus-Request: 1` for mutations. Browser clients use same-origin fetch via Vite/nginx. Login takes `{username,password}`; logout revokes the server session. Swagger users can authenticate with login, then supply the custom header using an HTTP client for mutations.

| Domain | Endpoints |
|---|---|
| Authentication | POST `/api/auth/login`, GET `/api/auth/me`, POST `/api/auth/logout` |
| Video | GET/POST `/api/videos`, GET `/api/videos/{id}/media`, PUT `/api/videos/{id}/location`, POST `/api/videos/{id}/archive` |
| Configuration | GET/POST `/api/videos/{id}/geometries`, PUT/DELETE `/api/geometries/{id}` |
| Jobs | POST `/api/videos/{id}/jobs`, GET `/api/jobs?video_id=...` (includes `annotated_available`), POST `/api/jobs/{id}/cancel`, GET `/api/jobs/{id}/annotated[?download=true]` (Supervision-annotated MP4) |
| Playback metadata | GET `/api/jobs/{id}/observations?start=0&end=30`, GET `/api/jobs/{id}/tracks` |
| Convoy | POST `/api/tracks/{id}/convoy`, GET `/api/jobs/{id}/convoy?video_time=...`, POST `/api/cameras/{id}/convoy` (live sessions) |
| Events | GET `/api/events`, GET `/api/events/{id}`, GET `/api/events/{id}/snapshot`, POST `/api/events/{id}/review` |
| Incidents | POST `/api/events/{id}/incident`, GET `/api/incidents`, PUT `/api/incidents/{id}` |
| Search | GET `/api/search` with date_from, date_to, video_id, mode, object_class, track_id, event_type, zone, status, incident, offset, limit |
| Track search | GET `/api/track-search` with video_id, job_id, mode, object_class (`vehicle` matches all vehicle classes), track_id (substring), convoy_role, offset, limit |
| Administration | GET/POST `/api/users`, PUT `/api/users/{id}/role`, POST `/api/users/{id}/disable`, GET `/api/roles`, PUT `/api/roles/{name}` |
| Models | GET/POST `/api/models`, PUT `/api/models/{id}/state` |
| Health / analytics / audit | GET `/api/health`, GET `/api/analytics`, GET `/api/audit?q=...` |
| Simulation | GET/POST `/api/simulation` |
| Demo | POST `/api/demo/reset`, `/api/demo/clear-events`, `/api/demo/clear-incidents` |

## Job request

```json
{"mode":"Event / Crowd","fps":10,"confidence":0.3,"congestion_count":12,"stop_seconds":10,"stop_distance":0.015,"free_flow_kmh":50}
```

Valid modes: `Detect & Annotate` (all 80 COCO classes), `Event / Crowd`, `Traffic`, `Convoy`, `General`. Mode is operator selected. Uploads accept MP4, M4V, MOV, AVI, MKV, WEBM, MPG, MPEG, 3GP, WMV, FLV, TS, MTS, M2TS and OGV with a `video/*`, `application/octet-stream` or empty MIME type; decodability is verified by FFmpeg, and undecodable files return 422. Summaries include `classes`/`total_classes` per object class; `vehicles` counts only car, motorcycle, bus and truck. Configuration is copied into the queued job. Poll `/api/jobs`; QUEUED → PROCESSING → COMPLETED, FAILED or CANCELLED. Requesting cancellation is immediate in the API and honored between inference frames / during conversion by the worker.

## Geometry request

```json
{"kind":"zone","name":"Gate B","type":"Crowd Zone","object_class":"person","points":[[0.1,0.2],[0.6,0.2],[0.6,0.9],[0.1,0.9]],"threshold":250,"elevated_ratio":0.8,"critical_ratio":1.25,"dwell_seconds":300,"stop_seconds":10,"severity":"HIGH","enabled":true}
```

Coordinates are normalized to 0–1 of the video frame. `kind` is `zone` (simple polygon, ≥3 points), `line` (2 points), `route` (≥2 points, convoy progress reference) or `calibration` (exactly 4 convex corners with `width_m` and `length_m`). Crowd status is NORMAL below `elevated_ratio × threshold`, ELEVATED below the threshold, HIGH below `critical_ratio × threshold`, then CRITICAL. Zones and lines are copied into new jobs; routes and the calibration are read live by `/api/jobs/{id}/convoy`, which returns `route_progress` (percent along the first enabled route, frame coordinates), `route_progress_track`, a `physical` block and a `timeline` of designation, visibility and traffic-state changes.

## Road calibration and speed

```json
{"kind":"calibration","name":"Road","points":[[0.45,0.90],[0.55,0.90],[0.31,0.28],[0.25,0.28]],"width_m":3.5,"length_m":40}
```

Click the four corners in order — near-left, near-right, far-right, far-left — so that point 1→2 spans the measured width and point 2→3 the measured length. A second calibration on the same view returns 409; edit or delete the existing one. A crossed or non-convex quadrilateral returns 422.

With a calibration in place, observations and `/api/jobs/{id}/track-path` carry `speed_kmh` and `world` (metres) per vehicle, tracks gain `max_speed_kmh`, `mean_speed_kmh` and `speed_samples`, and summaries gain `calibrated`, `median_speed_kmh`, `average_speed_kmh`, `speed_samples`, `speeding_vehicles` and `traffic_basis`. Zone and line measurements gain `flow_per_hour`, `flow_window_seconds` and `average_speed_kmh`. A zone with `speed_limit_kmh` above zero raises `Speeding` events. Speed on tracks, lane flow and speed rules are computed during analysis, so a calibration drawn afterwards applies to the next run; convoy measurements are computed on request and apply immediately.

`/api/jobs/{id}/convoy` and the live camera status both return `physical`: `calibrated`, `route_metric`, `route_length_m`, `lead_track`, `lead_speed_kmh`, `average_speed_kmh`, `convoy_length_m`, `largest_gap_m`, `eta_seconds` and a `vehicles` list ordered lead first, each with `speed_kmh`, `distance_m`, `remaining_m`, `gap_m`, `time_gap_s` and `extrapolated` (outside the calibrated area). Recorded contexts add `arrival_video_time`.

Live designation: `POST /api/cameras/{id}/convoy` `{"track_id":"V-0003","role":"Convoy Lead"}` — the camera must be in Convoy mode with a running session, and the track must already be saved (409 while it is not, retry within a couple of seconds). A null role clears the designation. The live service picks up changes within a second and reports convoy state in the camera `status.convoy` payload, with times measured in seconds since the session started.

## Review and incident

```json
{"action":"VERIFIED","note":"Reviewed source video and occupancy measurement."}
```

Review actions: VERIFIED, DISMISSED, UNDER REVIEW. A note is required. Only VERIFIED events can be converted. Converted event reviews are finalized. Incidents follow VERIFIED → ASSIGNED → RESPONDING → MONITORING → RESOLVED → CLOSED, with RESPONDING → RESOLVED and MONITORING → RESPONDING also allowed. Each change requires a note; ASSIGNED requires an enabled operational username. Closed incidents cannot be edited.

## Errors

400/422: invalid input or geometry; 401: missing/expired session; 403: insufficient permission or request protection; 404: missing record/media; 409: conflict or invalid state transition; 413: upload size; 415: unsupported format; 429: login throttle; 503: database unavailable. Failed analysis is visible in job state and produces a Video Processing Failure event.

Dates filter processing/event creation time because uploaded media has no trusted capture date. `video_time` is the source offset in seconds. Event lists and search accept `offset` and `limit` (maximum 1,000; default 1,000); track search accepts up to 200 (default 50). Both return the unpaged match count in the `X-Total-Count` response header. Audit returns the latest 500 matches.

`/api/health` returns component states plus `database_backend`, `inference_device`, `processing_fps`, `queue_size`, `active_jobs` and a `gpu` object (`backend`, `name`, `memory_allocated_mb`, `utilization_percent` — null where the platform does not expose it), plus `Live Service`, `Visual Search` and `live_cameras`.

## Live cameras, heatmaps, lock tracking and search

| Domain | Endpoints |
|---|---|
| Cameras | GET/POST `/api/cameras`, PUT/DELETE `/api/cameras/{id}`, POST `/api/cameras/{id}/lock` `{"track_id":"P-0003"}` (null unlocks) |
| Live media | GET `/api/cameras/{id}/stream` (MJPEG), GET `/api/cameras/{id}/frame.jpg[?raw=true]` |
| Detection export | GET `/api/jobs/{id}/detections?format=csv\|json&classes=person,vehicle&min_confidence=0.4&start=0&end=60&track_id=P-0003` (streamed, one row per detection) |
| Saved detections | POST `/api/saved-detections` `{"job_id"\|"camera_id", "video_time", "classes", "min_confidence", "note"}`, GET `/api/saved-detections`, GET `/api/saved-detections/{id}/image`, DELETE `/api/saved-detections/{id}` (admin) |
| Heatmap | GET `/api/jobs/{id}/heatmap.png?group=all|person|vehicle|other` (transparent PNG; `X-Heatmap-Peak-Seconds`, `X-Heatmap-Observed-Seconds`) |
| Lock tracking | GET `/api/jobs/{id}/track-path?track_id=P-0003` (sampled boxes, summary, zones visited, crop URL), GET `/api/jobs/{id}/crops/{track_id}.jpg` |
| Event clips | GET `/api/events/{id}/clip` (live events) |
| Natural language | GET `/api/nl-search?q=...&limit=100` → `understood`, `visual`, `searched`, `events`, `tracks` |

Camera body: `{"name":"River","url":"rtsp://user:pass@host/stream","mode":"Detect & Annotate","fps":5,"confidence":0.3,"imgsz":960,"width":1280,"enabled":true}`. Camera modes match job modes, including `Convoy`. Accepted schemes: rtsp, rtsps, http, https; EarthCam page URLs are resolved to their current HLS stream. URLs are returned with passwords masked; sending the masked URL back in an update keeps the stored one. Each camera owns a placeholder video (`video_id`), so its zones use `/api/videos/{video_id}/geometries` and its events filter with `video_id`. Live sessions appear as jobs in state `LIVE`, then `COMPLETED`. Job requests also accept `imgsz` (640, 960, 1280).

Jobs and cameras share the detection filters `classes` (COCO names plus `vehicle`; unknown names return 422), `tiling` (tiled small-object inference) and `min_box` (minimum shorter side in pixels). Camera URLs may be RTSP/RTSPS, HTTP(S)/HLS, a still-image endpoint (polled every 15 s, analysed only when the image changes), an EarthCam page or a trafficvision.live Georgia 511 link. Providers that block access outside their own player (SkylineWebcams, YouTube, worldcams.tv) are rejected at creation with 422 and the reason.
