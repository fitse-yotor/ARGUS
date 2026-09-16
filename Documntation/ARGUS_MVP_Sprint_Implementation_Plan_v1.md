# ARGUS --- MVP Sprint Implementation Plan

**Product:** ARGUS --- Multi-Sensor AI Situational Awareness Platform\
**MVP Priority:** ARGUS Vision / Video Analysis\
**Plan Duration:** 12 Weeks\
**Sprint Length:** 2 Weeks\
**Number of Delivery Sprints:** 6 + Sprint 0 Foundation\
**Version:** 1.0\
**Motto:** *See. Sense. Understand. Respond.*

------------------------------------------------------------------------

# 1. MVP Implementation Strategy

The first ARGUS MVP shall present the complete product structure in the
user interface while prioritizing **ARGUS Vision / Video Analysis** as
the first fully functional product vertical.

The MVP shall implement the following complete operational chain:

``` text
Camera / Video
      ↓
Video Ingestion
      ↓
AI Object Detection
      ↓
Object Tracking
      ↓
Zone / Line Analytics
      ↓
Crowd / Vehicle / Dwell Analytics
      ↓
ARGUS Event Engine
      ↓
Human Verification
      ↓
Incident Management
      ↓
GIS / Search / Audit
```

Other product modules such as ARGUS Sense, advanced Fusion, advanced
GIS, advanced Evidence and advanced Analytics shall remain visible in
the overall product navigation, but they may initially use demonstration
data until activated in later phases.

------------------------------------------------------------------------

# 2. Sprint Summary

  -----------------------------------------------------------------------------
  Sprint                        Duration Primary Focus    Main Deliverable
  ---------------- --------------------- ---------------- ---------------------
  Sprint 0                    Foundation Architecture &   Running ARGUS
                                         Environment      engineering
                                                          environment

  Sprint 1                    Weeks 1--2 Video Ingestion  Real video analysis
                                         & Detection      with object detection

  Sprint 2                    Weeks 3--4 Tracking &       Tracked
                                         Vision Pipeline  persons/vehicles

  Sprint 3                    Weeks 5--6 Zones, Lines &   Configurable
                                         Counting         operational video
                                                          analytics

  Sprint 4                    Weeks 7--8 Crowd, Dwell &   Advanced operational
                                         Vehicle          Vision analytics
                                         Analytics        

  Sprint 5                   Weeks 9--10 Event Engine &   AI event and
                                         Verification     human-review workflow

  Sprint 6                  Weeks 11--12 Incidents,       Demonstration-ready
                                         Dashboard &      ARGUS Vision MVP
                                         Hardening        
  -----------------------------------------------------------------------------

------------------------------------------------------------------------

# 3. Sprint 0 --- Engineering Foundation

## Sprint Goal

Establish the development environment, architecture, repositories,
database and service structure required for all subsequent ARGUS
development.

## Backend Tasks

-   [ ] Create ARGUS backend repository/project structure.
-   [ ] Configure Python environment.
-   [ ] Create FastAPI backend.
-   [ ] Configure PostgreSQL.
-   [ ] Configure PostGIS extension.
-   [ ] Create database migration mechanism.
-   [ ] Create base API structure.
-   [ ] Create health-check endpoint.
-   [ ] Configure application logging.
-   [ ] Configure environment variables.
-   [ ] Configure secure secret handling for development.
-   [ ] Create Docker configuration.
-   [ ] Create Docker Compose development environment.
-   [ ] Define API response/error conventions.

## Vision Service Tasks

-   [ ] Create separate ARGUS Vision Worker service.
-   [ ] Install and pin Roboflow Supervision.
-   [ ] Install OpenCV.
-   [ ] Configure FFmpeg/GStreamer where required.
-   [ ] Select initial object-detection model.
-   [ ] Configure CPU inference.
-   [ ] Configure GPU inference.
-   [ ] Create `DetectorAdapter` interface.
-   [ ] Create `TrackerAdapter` interface.
-   [ ] Define normalized detection object.
-   [ ] Define normalized Vision Observation object.
-   [ ] Create Vision service health endpoint.

## Database Tasks

Create initial entities/tables:

-   [ ] User.
-   [ ] Role.
-   [ ] Permission.
-   [ ] Camera.
-   [ ] CameraGroup.
-   [ ] Site.
-   [ ] Zone.
-   [ ] VirtualLine.
-   [ ] AIModel.
-   [ ] ModelVersion.
-   [ ] Event.
-   [ ] Incident.
-   [ ] AuditLog.

## Frontend Tasks

Create the complete ARGUS application shell.

Navigation:

-   [ ] Overview.
-   [ ] Live Operations.
-   [ ] GIS Command.
-   [ ] ARGUS Vision.
-   [ ] ARGUS Sense.
-   [ ] ARGUS Fusion.
-   [ ] Events & Alerts.
-   [ ] Incidents.
-   [ ] Investigation.
-   [ ] Evidence.
-   [ ] Analytics.
-   [ ] Administration.

## DevOps Tasks

-   [ ] Define Git branching strategy.
-   [ ] Create development configuration.
-   [ ] Create staging configuration.
-   [ ] Configure linting.
-   [ ] Configure automated tests.
-   [ ] Configure CI pipeline.
-   [ ] Define release/version convention.

## Sprint 0 Definition of Done

-   [ ] Frontend starts successfully.
-   [ ] Backend starts successfully.
-   [ ] Vision Worker starts successfully.
-   [ ] PostgreSQL/PostGIS is connected.
-   [ ] Frontend communicates with backend.
-   [ ] Backend communicates with Vision Worker.
-   [ ] Health endpoints work.
-   [ ] Development environment can be reproduced using documented setup
    steps.

------------------------------------------------------------------------

# 4. Sprint 1 --- Video Ingestion & Object Detection

## Sprint Goal

Allow ARGUS to receive real video and perform functional person and
vehicle detection.

## Camera Management Tasks

-   [ ] Create Camera entity.
-   [ ] Create camera registration API.
-   [ ] Create camera edit API.
-   [ ] Create camera disable API.
-   [ ] Create camera list API.
-   [ ] Create camera detail page.
-   [ ] Add camera name.
-   [ ] Add description.
-   [ ] Add location.
-   [ ] Add stream URL.
-   [ ] Add camera group.
-   [ ] Add operational status.
-   [ ] Add enabled analytics.

## Video Upload Tasks

-   [ ] Create video upload endpoint.
-   [ ] Validate supported file format.
-   [ ] Store uploaded video.
-   [ ] Create video metadata record.
-   [ ] Detect duration.
-   [ ] Detect resolution.
-   [ ] Detect source FPS.
-   [ ] Create uploaded-video list.
-   [ ] Create video playback UI.
-   [ ] Add delete/archive capability according to permissions.

## RTSP / Live Camera Tasks

-   [ ] Implement RTSP connection.
-   [ ] Validate stream.
-   [ ] Handle connection failure.
-   [ ] Implement reconnect logic.
-   [ ] Record stream health.
-   [ ] Display Online/Offline/Degraded state.

## Frame Processing Tasks

-   [ ] Decode video frames.
-   [ ] Implement configurable frame sampling.
-   [ ] Preserve source timestamps.
-   [ ] Send frames to inference worker.
-   [ ] Handle processing queue.
-   [ ] Handle processing failure.

## Detection Tasks

-   [ ] Integrate initial detector.
-   [ ] Implement person detection.
-   [ ] Implement vehicle detection.
-   [ ] Normalize detector results.
-   [ ] Capture object class.
-   [ ] Capture confidence.
-   [ ] Capture bounding box.
-   [ ] Capture timestamp.
-   [ ] Capture camera/video source.
-   [ ] Capture model/version.

## Supervision Tasks

-   [ ] Convert model output into Supervision detection representation.
-   [ ] Render bounding boxes.
-   [ ] Render object labels.
-   [ ] Render confidence.
-   [ ] Create annotated frame/video output.

## UI Tasks

Create:

**ARGUS Vision → Video Analysis**

-   [ ] Upload Video button.
-   [ ] Add Camera button.
-   [ ] Source selector.
-   [ ] Video player.
-   [ ] Detection overlay.
-   [ ] Object count.
-   [ ] Processing FPS.
-   [ ] Model information.
-   [ ] Start Analysis.
-   [ ] Stop Analysis.
-   [ ] Processing progress.
-   [ ] Error state.
-   [ ] Camera health.

## Sprint 1 Demo

``` text
Upload Video
      ↓
Start Analysis
      ↓
Person / Vehicle Detection
      ↓
Bounding Boxes + Labels
      ↓
Detection Metadata
```

## Sprint 1 Definition of Done

-   [ ] User can upload a video.
-   [ ] User can register a demo/live camera.
-   [ ] ARGUS can process video.
-   [ ] Persons are detected.
-   [ ] Vehicles are detected.
-   [ ] Bounding boxes are displayed.
-   [ ] Confidence values are available.
-   [ ] Model/version is traceable.
-   [ ] Processing health is visible.

------------------------------------------------------------------------

# 5. Sprint 2 --- Object Tracking & Supervision Pipeline

## Sprint Goal

Transform independent frame detections into persistent temporary tracks
that support movement analytics.

## Tracking Tasks

-   [ ] Select initial tracking implementation.
-   [ ] Implement `TrackerAdapter`.
-   [ ] Feed normalized detections to tracker.
-   [ ] Generate temporary Track IDs.
-   [ ] Maintain track across frames.
-   [ ] Handle track creation.
-   [ ] Handle track update.
-   [ ] Handle lost tracks.
-   [ ] Handle completed tracks.
-   [ ] Configure tracking parameters.

## Track Metadata Tasks

Store:

-   [ ] Track ID.
-   [ ] Camera ID.
-   [ ] Object class.
-   [ ] First seen.
-   [ ] Last seen.
-   [ ] Confidence.
-   [ ] Current position.
-   [ ] Historical positions.
-   [ ] Duration.
-   [ ] Movement direction.

## Trajectory Tasks

-   [ ] Store track center points.
-   [ ] Calculate movement trajectory.
-   [ ] Calculate basic direction.
-   [ ] Render trajectory line.
-   [ ] Configure trajectory history length.

## Vision Pipeline Tasks

Implement:

``` text
Video
  ↓
Frame Decoder
  ↓
Detector
  ↓
Supervision
  ↓
Tracker Adapter
  ↓
Tracked Detections
  ↓
Analytics
```

## UI Tasks

-   [ ] Display Track ID.
-   [ ] Display object class.
-   [ ] Display confidence.
-   [ ] Display tracking duration.
-   [ ] Optional trajectory overlay.
-   [ ] Show active track count.
-   [ ] Add overlay enable/disable controls.

## Performance Tasks

-   [ ] Measure detection FPS.
-   [ ] Measure tracking FPS.
-   [ ] Measure GPU utilization.
-   [ ] Measure CPU utilization.
-   [ ] Record end-to-end processing latency.
-   [ ] Test representative 720p video.
-   [ ] Test representative 1080p video.

## Sprint 2 Definition of Done

-   [ ] Person tracks persist across multiple frames.
-   [ ] Vehicle tracks persist across multiple frames.
-   [ ] Temporary Track IDs are visible.
-   [ ] Track history is available.
-   [ ] Movement direction can be calculated.
-   [ ] Tracking service can be replaced through the adapter interface.

------------------------------------------------------------------------

# 6. Sprint 3 --- Polygon Zones, Virtual Lines & Counting

## Sprint Goal

Allow authorized users to configure operational areas directly over
video and use tracking data for entry, exit and counting analytics.

## Polygon Zone Tasks

-   [ ] Create Zone database model.
-   [ ] Create zone API.
-   [ ] Create zone list API.
-   [ ] Create zone edit API.
-   [ ] Create zone delete/disable API.
-   [ ] Build polygon drawing tool.
-   [ ] Build polygon editing tool.
-   [ ] Save polygon coordinates.
-   [ ] Render saved polygon over video.

## Zone Configuration Tasks

Support:

-   [ ] Zone name.
-   [ ] Zone description.
-   [ ] Zone type.
-   [ ] Applicable object class.
-   [ ] Severity.
-   [ ] Active/inactive state.
-   [ ] Schedule.
-   [ ] Occupancy threshold.
-   [ ] Dwell threshold.

Zone types:

-   [ ] Monitoring Zone.
-   [ ] Restricted Zone.
-   [ ] Crowd Zone.
-   [ ] Vehicle Zone.
-   [ ] Entrance Zone.
-   [ ] Exit Zone.
-   [ ] Waiting Zone.
-   [ ] No-Stopping Zone.

## Zone Analytics Tasks

-   [ ] Determine track inside/outside polygon.
-   [ ] Detect zone entry.
-   [ ] Detect zone exit.
-   [ ] Calculate current occupancy.
-   [ ] Calculate maximum occupancy.
-   [ ] Associate tracks with zone.

## Virtual Line Tasks

-   [ ] Create VirtualLine model.
-   [ ] Create line drawing UI.
-   [ ] Save line coordinates.
-   [ ] Configure object classes.
-   [ ] Configure allowed direction.
-   [ ] Detect crossing.
-   [ ] Calculate crossing direction.
-   [ ] Maintain IN count.
-   [ ] Maintain OUT count.
-   [ ] Maintain total count.

## UI Tasks

Create:

**ARGUS Vision → Analytics Configuration**

-   [ ] Camera selector.
-   [ ] Add Zone.
-   [ ] Add Line.
-   [ ] Edit Zone.
-   [ ] Edit Line.
-   [ ] Enable/Disable.
-   [ ] Zone list.
-   [ ] Line list.
-   [ ] Real-time counters.

## Sprint 3 Definition of Done

-   [ ] User can draw polygon over video.
-   [ ] Zone can be saved.
-   [ ] Track entry is detected.
-   [ ] Track exit is detected.
-   [ ] Current occupancy is calculated.
-   [ ] User can draw virtual line.
-   [ ] Person crossing is counted.
-   [ ] Vehicle crossing is counted.
-   [ ] Directional counts work where tracking permits.

------------------------------------------------------------------------

# 7. Sprint 4 --- Crowd, Dwell & Vehicle Analytics

## Sprint Goal

Convert tracked object movement into operational crowd, dwell and
traffic conditions.

## Crowd Analytics Tasks

-   [ ] Calculate zone person occupancy.
-   [ ] Calculate current occupancy.
-   [ ] Calculate maximum occupancy.
-   [ ] Calculate entry count.
-   [ ] Calculate exit count.
-   [ ] Calculate approximate entry rate.
-   [ ] Calculate approximate exit rate.
-   [ ] Store occupancy history.
-   [ ] Calculate trend.
-   [ ] Configure occupancy thresholds.

Threshold levels:

-   [ ] Normal.
-   [ ] Elevated.
-   [ ] High.
-   [ ] Critical.

## Crowd Dashboard Tasks

Display:

-   [ ] Zone name.
-   [ ] Current occupancy.
-   [ ] Threshold.
-   [ ] Current state.
-   [ ] Entry rate.
-   [ ] Exit rate.
-   [ ] Trend.
-   [ ] Associated camera.

## Dwell Analytics Tasks

-   [ ] Start timer when track enters zone.
-   [ ] Stop timer when track exits.
-   [ ] Calculate current dwell duration.
-   [ ] Configure dwell threshold.
-   [ ] Generate dwell observation.
-   [ ] Prevent duplicate dwell events for same continuing condition.
-   [ ] Display dwell duration.

## Vehicle Analytics Tasks

-   [ ] Vehicle tracking by supported class.
-   [ ] Vehicle line count.
-   [ ] Vehicle zone occupancy.
-   [ ] Vehicle direction.
-   [ ] No-stopping zone.
-   [ ] Stopped vehicle timer.
-   [ ] Stopped vehicle observation.
-   [ ] Traffic count dashboard.

## Testing Tasks

-   [ ] Test low-density crowd.
-   [ ] Test threshold crossing.
-   [ ] Test repeated threshold behavior.
-   [ ] Test person dwell.
-   [ ] Test vehicle dwell.
-   [ ] Test multiple vehicles.
-   [ ] Test line crossing with occlusion cases.
-   [ ] Document known limitations.

## Sprint 4 Definition of Done

-   [ ] Crowd occupancy is functional.
-   [ ] Threshold state changes correctly.
-   [ ] Crowd threshold observation is generated.
-   [ ] Dwell time is calculated.
-   [ ] Dwell observation is generated.
-   [ ] Vehicle counts work.
-   [ ] Stopped vehicle condition works.
-   [ ] Analytics operate on real/prerecorded test video.

------------------------------------------------------------------------

# 8. Sprint 5 --- Event Engine & Human Verification

## Sprint Goal

Convert Vision observations into manageable ARGUS events and introduce
the human-verification workflow.

## Event Service Tasks

-   [ ] Create Event database model.
-   [ ] Create event API.
-   [ ] Create event list API.
-   [ ] Create event detail API.
-   [ ] Create event status API.
-   [ ] Create event priority logic.
-   [ ] Link event to camera.
-   [ ] Link event to zone.
-   [ ] Link event to track.
-   [ ] Link event to observation.
-   [ ] Store model/version where applicable.

## Event Types

Implement:

-   [ ] Restricted Zone Entry.
-   [ ] Crowd Threshold.
-   [ ] Line Crossing event where configured.
-   [ ] Dwell Threshold.
-   [ ] Stopped Vehicle.
-   [ ] Camera Offline.

## Event Evidence Tasks

-   [ ] Generate event snapshot.
-   [ ] Store event timestamp.
-   [ ] Create video time reference.
-   [ ] Link source camera.
-   [ ] Link zone.
-   [ ] Link object/Track ID.

## Deduplication Tasks

-   [ ] Define event deduplication window.
-   [ ] Prevent excessive duplicate events.
-   [ ] Reopen/update continuing condition where appropriate.
-   [ ] Test alert volume.

## Event Queue UI

Display:

-   [ ] Priority.
-   [ ] Event type.
-   [ ] Source.
-   [ ] Location.
-   [ ] Camera.
-   [ ] Zone.
-   [ ] Time.
-   [ ] Status.
-   [ ] Review action.

## Event Detail UI

Display:

-   [ ] Snapshot/video.
-   [ ] Event metadata.
-   [ ] Detection confidence.
-   [ ] Track ID.
-   [ ] Zone.
-   [ ] Rule.
-   [ ] Timeline.
-   [ ] Related events.

## Verification Tasks

Implement:

-   [ ] Verify.
-   [ ] Dismiss.
-   [ ] Further Review.
-   [ ] Verification note.
-   [ ] Dismissal reason.
-   [ ] Operator ID.
-   [ ] Verification timestamp.
-   [ ] Audit record.

## Sprint 5 Definition of Done

-   [ ] Vision analytics generate real events.
-   [ ] Events appear in queue.
-   [ ] Operator can open an event.
-   [ ] Supporting evidence is visible.
-   [ ] Operator can verify.
-   [ ] Operator can dismiss.
-   [ ] Operator decision is audited.
-   [ ] Duplicate event volume is controlled.

------------------------------------------------------------------------

# 9. Sprint 6 --- Incident Workflow, GIS, Search & MVP Hardening

## Sprint Goal

Complete the end-to-end ARGUS Vision operational workflow and prepare a
stable demonstration MVP.

## Incident Management Tasks

-   [ ] Create Incident model.
-   [ ] Create incident API.
-   [ ] Create incident list.
-   [ ] Create incident detail.
-   [ ] Create incident from verified event.
-   [ ] Support manual incident where permitted.
-   [ ] Generate incident number.
-   [ ] Configure category.
-   [ ] Configure priority.
-   [ ] Link originating event.
-   [ ] Link camera.
-   [ ] Link zone/location.
-   [ ] Link snapshot/video reference.

## Incident Lifecycle Tasks

Implement:

``` text
Verified
   ↓
Assigned
   ↓
Responding
   ↓
Monitoring
   ↓
Resolved
   ↓
Closed
```

Tasks:

-   [ ] Assignment.
-   [ ] Reassignment.
-   [ ] Status update.
-   [ ] Notes.
-   [ ] Escalation.
-   [ ] Resolution.
-   [ ] Closure.
-   [ ] Incident timeline.
-   [ ] Audit.

## Dashboard Integration Tasks

Connect dashboard to real APIs.

KPI cards:

-   [ ] Active cameras.
-   [ ] People observed.
-   [ ] Vehicles observed.
-   [ ] Active events.
-   [ ] Open incidents.
-   [ ] Camera health.

## GIS MVP Tasks

-   [ ] Integrate map.
-   [ ] Display camera markers.
-   [ ] Display camera health.
-   [ ] Display event markers.
-   [ ] Display incident markers.
-   [ ] Click marker for details.
-   [ ] Filter by type/status.

## Investigation Search Tasks

Implement filters:

-   [ ] Date/time.
-   [ ] Camera.
-   [ ] Zone.
-   [ ] Object class.
-   [ ] Event type.
-   [ ] Incident ID.

Results:

-   [ ] Timestamp.
-   [ ] Source.
-   [ ] Location.
-   [ ] Event.
-   [ ] Snapshot/reference.
-   [ ] Incident link.

## Evidence MVP Tasks

-   [ ] Event snapshots.
-   [ ] Video timestamp/reference.
-   [ ] Incident evidence links.
-   [ ] Evidence authorization.
-   [ ] Evidence access audit.

## RBAC Tasks

-   [ ] Operator role.
-   [ ] Incident Controller role.
-   [ ] Supervisor role.
-   [ ] Investigator role.
-   [ ] Administrator role.
-   [ ] Auditor role.

## Audit Tasks

Audit:

-   [ ] Login.
-   [ ] Zone changes.
-   [ ] Threshold changes.
-   [ ] Event verification.
-   [ ] Event dismissal.
-   [ ] Incident creation.
-   [ ] Assignment.
-   [ ] Status changes.
-   [ ] Evidence access.
-   [ ] Administrative changes.

## Performance & Hardening Tasks

-   [ ] GPU benchmark.
-   [ ] CPU benchmark.
-   [ ] 720p benchmark.
-   [ ] 1080p benchmark.
-   [ ] 4-stream test.
-   [ ] 8-stream test where hardware permits.
-   [ ] API performance test.
-   [ ] Database indexing.
-   [ ] Error handling review.
-   [ ] Camera reconnection testing.
-   [ ] Permission testing.
-   [ ] Security review.
-   [ ] Dependency review.
-   [ ] Logging review.
-   [ ] Demo reset mechanism.
-   [ ] Deployment documentation.
-   [ ] User demonstration guide.

## Sprint 6 Definition of Done

The following complete scenario must work:

``` text
Video / Camera
      ↓
Person Detection
      ↓
Tracking
      ↓
Restricted Polygon Entry
      ↓
Vision Event
      ↓
Event Queue
      ↓
Operator Review
      ↓
Human Verification
      ↓
Incident
      ↓
Assignment
      ↓
GIS
      ↓
Response Status
      ↓
Resolution
      ↓
Historical Search
      ↓
Audit Trail
```

A second scenario shall demonstrate:

``` text
Crowd Increase
      ↓
Zone Occupancy
      ↓
Threshold Crossed
      ↓
Crowd Event
      ↓
Human Verification
      ↓
Incident
      ↓
Occupancy Normalizes
      ↓
Resolution
```

------------------------------------------------------------------------

# 10. MVP Functional Scope by Module

  Module            MVP Status
  ----------------- --------------------------------------------
  Overview          Functional
  Live Operations   Functional
  GIS Command       Basic Functional
  ARGUS Vision      **Fully Functional MVP**
  ARGUS Sense       UI / Demonstration placeholder
  ARGUS Fusion      UI / Demonstration data
  Events & Alerts   Functional
  Incidents         Functional
  Investigation     Basic Functional
  Evidence          Basic Functional
  Analytics         Basic Functional
  Administration    Users, cameras, zones and rules functional

------------------------------------------------------------------------

# 11. MVP Definition of Done

ARGUS Vision MVP is complete only when the platform demonstrates a
reliable end-to-end operational workflow rather than isolated AI
features.

Required capabilities:

-   [ ] Video upload.
-   [ ] Live/RTSP source integration.
-   [ ] Person detection.
-   [ ] Vehicle detection.
-   [ ] Object tracking.
-   [ ] Track IDs.
-   [ ] Polygon zones.
-   [ ] Restricted zones.
-   [ ] Crowd zones.
-   [ ] Virtual lines.
-   [ ] Directional counting.
-   [ ] Occupancy.
-   [ ] Crowd thresholds.
-   [ ] Dwell analytics.
-   [ ] Stopped vehicle analytics.
-   [ ] Event generation.
-   [ ] Event snapshots.
-   [ ] Human verification.
-   [ ] Event dismissal.
-   [ ] Incident creation.
-   [ ] Assignment.
-   [ ] Incident lifecycle.
-   [ ] GIS markers.
-   [ ] Metadata search.
-   [ ] Evidence reference.
-   [ ] RBAC.
-   [ ] Audit trail.
-   [ ] Camera/system health.
-   [ ] GPU benchmark.
-   [ ] Deployment documentation.

------------------------------------------------------------------------

# 12. Post-MVP Roadmap

After the Vision MVP is accepted, development shall continue with:

## Phase 2 --- ARGUS Sense

-   CSI hardware setup.
-   Sensor registration.
-   CSI ingestion.
-   Calibration.
-   Human presence.
-   Movement sensing.
-   Experimental pose evaluation.

## Phase 3 --- ARGUS Fusion

-   Vision + RF correlation.
-   Multi-source event rules.
-   Fusion confidence/priority.
-   Explainability.
-   Sensor health-aware correlation.

## Phase 4 --- Advanced Command

-   Advanced GIS.
-   Multi-site management.
-   Advanced evidence workflow.
-   Advanced investigation.
-   Advanced analytics.
-   Operational reporting.

## Phase 5 --- Pilot Hardening

-   Production sizing.
-   High availability.
-   Security hardening.
-   Backup/disaster recovery.
-   Monitoring.
-   User acceptance testing.
-   Operational training.
