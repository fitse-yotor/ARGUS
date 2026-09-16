# ARGUS --- System Architecture Document

**Product:** ARGUS --- Multi-Sensor AI Situational Awareness Platform\
**Motto:** *See. Sense. Understand. Respond.*\
**Version:** 1.0

## 1. Architecture Goals

ARGUS shall be modular, model-agnostic, sensor-extensible, auditable and
suitable for controlled on-premises deployment. Computer-vision
processing, RF sensing, event correlation and operational workflow shall
be separate architectural concerns.

Key goals: - avoid lock-in to one detector or tracker; - use Roboflow
Supervision as a Vision application toolkit rather than the entire
product; - separate raw media processing from operational metadata; -
scale GPU inference independently; - allow edge/site processing; -
retain human verification; - protect evidence and operational data; -
make sensor-fusion decisions explainable.

## 2. Context Architecture

``` text
+----------------------- PHYSICAL / EXTERNAL SOURCES -----------------------+
| CCTV | Recorded Video | CSI Nodes | IoT Sensors | Access Control | GIS   |
+-------------------------------+-------------------------------------------+
                                |
                                v
+-------------------------- INGESTION LAYER --------------------------------+
| Video Gateway | Sensor Gateway | External Integration Adapters            |
+----------------------+------------------------------+---------------------+
                       |                              |
                       v                              v
              +----------------+              +----------------+
              | ARGUS VISION   |              | ARGUS SENSE    |
              | Inference      |              | CSI Processing |
              | Supervision    |              | Presence/Move  |
              | Tracking       |              | Pose POC       |
              | Zone Analytics |              +-------+--------+
              +--------+-------+                      |
                       +---------------+--------------+
                                       |
                                       v
                              +----------------+
                              | ARGUS FUSION   |
                              | Correlation    |
                              | Rules/Priority |
                              +-------+--------+
                                      |
                                      v
                              +----------------+
                              | EVENT PLATFORM |
                              +-------+--------+
                                      |
                +---------------------+----------------------+
                |                     |                      |
                v                     v                      v
             GIS SERVICE        INCIDENT SERVICE       SEARCH/EVIDENCE
                |                     |                      |
                +---------------------+----------------------+
                                      |
                                      v
                              +----------------+
                              | ARGUS COMMAND  |
                              +----------------+
```

## 3. Component Architecture

### 3.1 Video Gateway

Responsibilities: - connect to approved RTSP/video sources; - validate
source health; - sample/decode frames; - route frames to inference
workers; - expose stream metadata; - isolate camera network from
application services where required.

### 3.2 Inference Worker

Responsibilities: - load approved detection model; - perform GPU/CPU
inference; - return normalized detections; - expose
model/version/health; - support horizontal scaling.

### 3.3 Supervision Analytics Service

Supervision-based capabilities may include: - normalized detections; -
bounding-box/label annotation; - geometry helpers; - polygon zones; -
zone counts; - video processing helpers; - downstream tracking-oriented
analytics.

ARGUS shall wrap these capabilities behind internal services/interfaces
so upstream library changes do not directly define product architecture.

### 3.4 Tracking Adapter

A tracker adapter shall expose a stable ARGUS contract:

``` text
Input: detections + frame timestamp
Output: tracked detections + temporary track IDs
```

This permits tracker replacement without changing incident/event
services.

### 3.5 Vision Rules Engine

Consumes tracked detections and configured zones/lines to produce
observations such as: - restricted-zone entry; - occupancy threshold; -
line crossing; - dwell threshold; - stopped vehicle; - configured
traffic/crowd conditions.

### 3.6 Sensor Gateway

Normalizes supported non-video observations:

``` json
{
  "sensor_id": "RF-01",
  "site_id": "FAC-A",
  "zone_id": "ZONE-01",
  "type": "presence",
  "timestamp": "...",
  "confidence": 0.87,
  "validation_state": "POC_VALIDATED"
}
```

### 3.7 CSI Processing Service

For instrumented POC environments: 1. receive CSI measurements; 2. apply
calibration/preprocessing; 3. run approved signal/ML processing; 4. emit
presence/movement/experimental pose observation; 5. attach quality and
validation state.

The service shall not represent low-quality or unvalidated output as
certain.

### 3.8 Fusion Engine

Consumes observations from Vision, Sense and approved integrations.

Example rule:

``` text
IF
  vision.event = PERSON_IN_RESTRICTED_ZONE
AND
  rf.event = HUMAN_PRESENCE
AND
  same_site = TRUE
AND
  time_difference <= configured_window
THEN
  create FUSED_RESTRICTED_ZONE_EVENT
  priority = HIGH
  verification_required = TRUE
```

Fusion must retain all contributing observation IDs.

### 3.9 Event Service

Responsibilities: - create/update events; - assign priority; -
deduplicate repeated conditions; - maintain review state; - link
observations; - publish event updates.

### 3.10 Incident Service

Responsibilities: - create incident from verified event; - assignment; -
status lifecycle; - notes; - escalation; - resolution/closure; -
timeline.

### 3.11 GIS Service

Stores/serves: - camera coordinates; - sensor coordinates; - operational
sites; - zones; - event/incident positions; - permitted GIS layers.

PostgreSQL/PostGIS is recommended for geospatial metadata.

### 3.12 Search Service

Indexes operational metadata for filters such as: - time; - camera; -
zone; - object class; - event category; - incident.

Raw video search is not the first-stage architecture; ARGUS first
indexes structured metadata and links results to authorized
evidence/video references.

### 3.13 Evidence Service

Controls references to: - clips; - snapshots; - metadata; - documents.

It shall enforce authorization, retention and access audit.

### 3.14 Identity/RBAC Service

Provides authentication integration, role permissions and resource
scope.

### 3.15 Audit Service

Receives immutable/append-oriented records for security and operational
actions.

## 4. Suggested Technology Stack

  Layer             Candidate Technology
  ----------------- ------------------------------------------------------------
  Vision language   Python
  Vision toolkit    Roboflow Supervision
  Detection         Replaceable approved detector
  Tracking          Replaceable tracker adapter
  Video             FFmpeg / GStreamer / OpenCV as appropriate
  Backend API       FastAPI
  Frontend          React / Next.js or equivalent
  Operational DB    PostgreSQL
  GIS DB            PostGIS
  Cache             Redis
  Event messaging   Kafka or RabbitMQ depending scale
  Object storage    MinIO or approved S3-compatible on-prem storage
  GIS UI            MapLibre with approved map data/service
  Containers        Docker
  Orchestration     Kubernetes when deployment scale justifies it
  GPU               NVIDIA CUDA-capable infrastructure where model supports it
  Monitoring        Prometheus/Grafana or approved equivalent
  Logs              Centralized logging stack

Technology choices remain subject to client infrastructure, licensing
and benchmark validation.

## 5. Vision Processing Sequence

``` text
Camera
  |
  v
Video Gateway
  |
  v
Frame Sampler/Decoder
  |
  v
Inference Worker (GPU)
  |
  v
Detection Adapter
  |
  v
Supervision Representation
  |
  v
Tracking Adapter
  |
  +--> Polygon Zones
  +--> Virtual Lines
  +--> Dwell/Occupancy
  |
  v
Vision Observation
  |
  v
Event/Fusion Platform
```

## 6. Event Verification Sequence

``` text
Vision/Sense
    |
Observation
    |
    v
Fusion / Rule Engine
    |
    v
Event Service
    |
    v
ARGUS Command
    |
    v
Operator Review
   / \
Dismiss Verify
         |
         v
    Incident Service
         |
         v
 Assignment / Response / Closure
```

## 7. Data Architecture

### 7.1 Transactional Data

PostgreSQL: - users/roles; - cameras/sensors; - zones/lines; - rules; -
events; - incidents; - assignments; - timelines; - configuration.

### 7.2 Geospatial Data

PostGIS: - camera/sensor coordinates; - sites; - geographic operational
zones; - event/incident locations.

### 7.3 Media/Evidence

Object storage: - approved clips; - snapshots; - generated incident
attachments.

Database stores metadata/reference, not large binary media where
avoidable.

### 7.4 Search Index

Initial POC may use PostgreSQL indexes. At larger scale, a dedicated
search engine may be introduced after measured requirements justify it.

## 8. Core Data Relationships

``` text
Camera 1---* Zone
Camera 1---* VirtualLine
Camera 1---* Detection
Detection *---1 Track

Sensor 1---* SensorObservation

Detection/Track ----\
                     > Observation ----\
SensorObservation --/                  \
                                         > Event ----* Incident
Fusion Observation --------------------/

Incident 1---* Timeline
Incident 1---* Assignment
Incident 1---* Evidence
User 1---* AuditLog
```

## 9. API Domains

Suggested internal/external API groups:

``` text
/api/auth
/api/users
/api/roles
/api/cameras
/api/camera-groups
/api/sensors
/api/zones
/api/lines
/api/models
/api/rules
/api/events
/api/incidents
/api/evidence
/api/search
/api/gis
/api/analytics
/api/health
/api/audit
```

### Example Event API

``` json
POST /api/events
{
  "type": "crowd_threshold",
  "source": "vision",
  "camera_id": "CAM-002",
  "zone_id": "GATE-B",
  "priority": "medium",
  "observation_ids": ["OBS-1002"],
  "verification_required": true
}
```

## 10. Deployment Architecture --- POC

``` text
                 CONTROLLED LAN
                      |
      +---------------+---------------+
      |                               |
Demo Cameras                     CSI Test Nodes
      |                               |
      v                               v
Video Gateway                    Sensor Gateway
      |                               |
      v                               v
GPU Inference                    CSI Processor
      |                               |
      +---------------+---------------+
                      |
                 ARGUS Backend
                      |
          +-----------+-----------+
          |           |           |
      PostgreSQL    Redis      Object Store
          |
        PostGIS
          |
          v
      ARGUS Command
   Operator Workstation
```

## 11. Production Scaling Concept

Production shall separate: - camera/site ingestion; - GPU inference
pool; - sensor ingestion; - event/fusion services; - operational DB; -
evidence storage; - command UI; - monitoring/security services.

Inference workers scale independently according to measured per-stream
cost.

## 12. GPU Sizing Principle

GPU capacity shall be benchmark-driven.

``` text
Required GPU Capacity =
  Concurrent Streams
  x Processed FPS per Stream
  x Model Cost at Selected Resolution
  + Safety/Redundancy Margin
```

Supervision itself is not the primary GPU consumer; neural inference is.

POC should benchmark: - 720p vs 1080p; - target FPS; - selected
detector; - 4/8/16 streams; - tracking/zone overhead; - GPU
utilization; - end-to-end event latency.

## 13. Network Zones

Recommended segmentation:

``` text
[Camera / Sensor Network]
          |
     Video/Sensor Gateways
          |
        Firewall
          |
[AI / Processing Network]
          |
        Firewall
          |
[Application / Data Network]
          |
        Firewall
          |
[Operator / Command Network]

[Administrative Network] -> tightly controlled management access
```

## 14. Security Architecture

Controls: - TLS for sensitive service communication; - least-privilege
service identities; - RBAC; - network segmentation; - secrets manager or
protected secret storage; - protected evidence; - configuration audit; -
centralized logs; - time synchronization; - backup/recovery; -
dependency and container scanning in development pipeline.

## 15. Responsible-Use Architecture

Architectural controls shall reinforce: - human verification; - explicit
event provenance; - model/version traceability; - source
confidence/quality; - experimental labels for CSI pose; - no facial
recognition in V1; - no autonomous enforcement; - configurable
retention; - evidence access audit.

## 16. Failure Handling

  -----------------------------------------------------------------------
  Failure                             Expected Behavior
  ----------------------------------- -----------------------------------
  Camera offline                      Health becomes Offline; other
                                      cameras continue

  Detector unavailable                Vision processing marked Degraded;
                                      no fabricated detections

  Tracker failure                     Detection may continue;
                                      tracking-dependent analytics marked
                                      unavailable

  CSI sensor offline                  Sense health shows Offline; fusion
                                      does not assume negative presence

  Fusion service unavailable          Raw observations/events remain
                                      available where architecture
                                      permits

  Database unavailable                Services fail safely; recovery
                                      procedures invoked

  Evidence storage unavailable        Incident metadata remains
                                      protected; evidence operation
                                      reports failure

  GIS unavailable                     Non-GIS incident/event functions
                                      continue where feasible
  -----------------------------------------------------------------------

## 17. Observability

Metrics should include: - stream health; - decoded FPS; - inference
FPS; - GPU utilization; - inference latency; - event latency; - event
volume; - fusion volume; - queue depth; - database latency; - API
errors; - sensor health; - storage capacity.

## 18. POC Architecture Deliverables

1.  Four demo video sources.
2.  GPU inference worker.
3.  Supervision analytics pipeline.
4.  Tracking adapter.
5.  Polygon/line configuration.
6.  Vision event generation.
7.  CSI sensor gateway and test zone.
8.  Fusion rule.
9.  FastAPI backend.
10. PostgreSQL/PostGIS.
11. ARGUS Command web UI.
12. Event/incident workflow.
13. Search/evidence reference.
14. Audit and health dashboard.

## 19. Architecture Decision Summary

  -----------------------------------------------------------------------
  Decision                            Rationale
  ----------------------------------- -----------------------------------
  Modular detector                    Avoid model lock-in

  Supervision as toolkit              Reuse strong CV primitives without
                                      making it the entire product

  Replaceable tracker                 Upstream tracking libraries evolve

  Metadata-first search               More scalable/structured than
                                      manually scanning raw video

  Human verification                  Operational accountability

  CSI as separate service             Different hardware/calibration
                                      lifecycle from cameras

  Fusion retains provenance           Explainability and audit

  Benchmark GPU before procurement    Stream/model performance varies
                                      materially

  On-prem capable                     Appropriate for controlled
                                      public-safety environments
  -----------------------------------------------------------------------

## 20. Final Architecture Principle

``` text
SEE -> Vision Pipeline
SENSE -> CSI / Sensor Pipeline
UNDERSTAND -> Analytics + Fusion
VERIFY -> Human Review
RESPOND -> Incident + GIS + Evidence + Analytics
```

ARGUS shall remain a human-centered operational platform in which sensor
and AI systems improve awareness while authorized personnel retain
responsibility for operational decisions.
