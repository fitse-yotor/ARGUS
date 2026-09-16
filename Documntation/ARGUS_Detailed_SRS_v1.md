# ARGUS --- Detailed Software Requirements Specification (SRS)

**Product:** ARGUS\
**Type:** Multi-Sensor AI Situational Awareness Platform\
**Motto:** *See. Sense. Understand. Respond.*\
**Version:** 1.0\
**Date:** September 2026\
**Initial POC Context:** Addis Ababa Police controlled demonstration

------------------------------------------------------------------------

## 1. Introduction

### 1.1 Purpose

This SRS defines the functional, non-functional, security, data,
integration, user-interface, infrastructure, demonstration and
acceptance requirements for ARGUS. It is intended to guide product
design, development, testing, demonstration and future controlled
deployment.

ARGUS transforms authorized video and instrumented sensor observations
into structured operational events. It supports computer-vision
analytics, sensor fusion, GIS visualization, human verification,
incident management, investigation search, evidence references,
reporting and audit.

### 1.2 Product Principle

ARGUS follows four stages:

**See** --- authorized CCTV/video.\
**Sense** --- WiFi CSI and approved physical sensors.\
**Understand** --- detection, tracking, zones, rules and sensor fusion.\
**Respond** --- human verification, incidents, assignment, GIS and
reporting.

AI/sensor output is decision support. An observation is not
automatically a confirmed incident or enforcement decision.

### 1.3 Scope

V1 includes ARGUS Vision, ARGUS Sense, ARGUS Fusion, ARGUS Command,
ARGUS Insight and Administration. Facial recognition, autonomous
identity matching, autonomous enforcement, criminal-intent inference and
unvalidated through-wall pose claims are outside V1.

------------------------------------------------------------------------

## 2. Product Modules

  -----------------------------------------------------------------------
  Module                              Description
  ----------------------------------- -----------------------------------
  ARGUS Vision                        Video ingestion, detector
                                      integration, Supervision-based
                                      analytics, tracking, zones, lines,
                                      crowd and vehicle analytics

  ARGUS Sense                         WiFi CSI and approved sensor
                                      ingestion, presence/movement
                                      sensing and experimental pose POC

  ARGUS Fusion                        Time/location/source correlation,
                                      rules, confidence and priority

  ARGUS Command                       Live operations, GIS, events,
                                      verification, incidents and command
                                      workflow

  ARGUS Insight                       Historical metadata search,
                                      evidence references, analytics and
                                      reporting

  Administration                      Users, roles, cameras, sensors,
                                      models, zones, thresholds, health
                                      and audit
  -----------------------------------------------------------------------

Roboflow Supervision is a core application-layer toolkit inside ARGUS
Vision. Detector, tracker and sensor adapters shall remain replaceable
so ARGUS is not locked to one model or implementation.

------------------------------------------------------------------------

## 3. Actors

### 3.1 Command Center Operator

Views assigned cameras/sensors, reviews events, verifies or dismisses
observations, creates incidents where authorized and records notes.

### 3.2 Incident Controller

Assigns verified incidents, changes status, escalates, monitors response
and closes incidents.

### 3.3 Supervisor / Commander

Views operational map, priorities, unresolved incidents, trends, system
health and response metrics.

### 3.4 Investigator / Analyst

Searches authorized historical metadata and opens permitted evidence
references.

### 3.5 System Administrator

Manages users, roles, cameras, sensors, zones, thresholds, integrations
and configuration.

### 3.6 AI / Technical Administrator

Manages approved models, inference endpoints, versions, calibration,
health and benchmarking.

### 3.7 Auditor

Reviews audit trails, incident histories, evidence access and
configuration changes without modifying operational records.

------------------------------------------------------------------------

# 4. Functional Requirements

## 4.1 Authentication and Authorization

**FR-AUTH-001 --- Authentication:** The system shall authenticate users
before protected functionality is available.

**FR-AUTH-002 --- RBAC:** The system shall enforce role-based access to
cameras, sensors, events, incidents, evidence, analytics and
administration.

**FR-AUTH-003 --- Operational Scope:** Permissions shall support
restriction by organization, site, camera group, sensor group or
operational area.

**FR-AUTH-004 --- Session Control:** Sessions shall support secure
expiration, logout and invalidation.

**FR-AUTH-005 --- Login Audit:** Failed and successful authentication
events shall be auditable according to policy.

## 4.2 Camera Management

**FR-CAM-001 --- Registration:** Administrators shall register a camera
with ID, name, description, location, stream endpoint, group,
operational area, status and enabled analytics.

**FR-CAM-002 --- Grouping:** Cameras shall be groupable by site,
district, event, road corridor, facility or organizational ownership.

**FR-CAM-003 --- Health:** Camera state shall include Online, Degraded,
Offline, Maintenance and Disabled.

**FR-CAM-004 --- Video Wall:** Operators shall display authorized
cameras in configurable command-center layouts.

**FR-CAM-005 --- Recorded Input:** ARGUS shall accept approved
prerecorded video for testing, demonstration and investigation.

## 4.3 ARGUS Vision --- Detection

**FR-VIS-001 --- Detector Adapter:** ARGUS shall integrate approved
detection inference through a replaceable interface.

**FR-VIS-002 --- Normalization:** Model output shall be converted to a
consistent internal detection representation.

**FR-VIS-003 --- Detection Metadata:** Supported detections shall
contain timestamp, camera, object class, confidence, geometry, tracking
ID when available, zone membership and model/version reference.

**FR-VIS-004 --- Object Classes:** Administrators shall enable supported
object classes per analytic rule or camera.

**FR-VIS-005 --- Annotation:** The UI may overlay boxes, labels,
tracking IDs, zones, lines, counts and trajectories.

## 4.4 Tracking

**FR-TRK-001:** ARGUS shall support multi-object tracking within
individual streams.

**FR-TRK-002:** Active tracks shall receive temporary tracking
identifiers.

**FR-TRK-003:** Tracking metadata shall support direction, dwell,
trajectory, line crossing and zone entry/exit.

**FR-TRK-004:** Tracking shall use a replaceable adapter to permit
future tracker upgrades.

## 4.5 Polygon Zones

**FR-ZON-001:** Authorized administrators shall draw polygon zones over
camera views.

**FR-ZON-002:** A zone shall store ID, name, camera, coordinates, type,
applicable classes, threshold, dwell duration, active schedule and
severity.

**FR-ZON-003:** Supported types shall include monitoring, restricted,
crowd, vehicle, entrance/exit, waiting and no-stopping zones.

**FR-ZON-004:** ARGUS shall generate configured zone-entry
observations/events.

**FR-ZON-005:** ARGUS shall support configured zone-exit events.

**FR-ZON-006:** ARGUS shall calculate supported occupancy within a zone.

**FR-ZON-007:** ARGUS shall create an event when a configured occupancy
threshold is met.

## 4.6 Line Crossing

**FR-LIN-001:** Administrators shall configure virtual lines.

**FR-LIN-002:** ARGUS shall record crossing direction where tracking
quality permits.

**FR-LIN-003:** ARGUS shall maintain crossing counts by supported object
class.

**FR-LIN-004:** A configured crossing may create an operational event.

## 4.7 Dwell Analytics

**FR-DWL-001:** ARGUS shall calculate how long a supported tracked
object remains in a configured zone.

**FR-DWL-002:** Administrators shall configure dwell thresholds.

**FR-DWL-003:** ARGUS shall create an observation when the threshold is
exceeded. Dwell shall describe observed behavior and shall not
automatically infer intent.

## 4.8 Crowd Analytics

**FR-CRD-001:** ARGUS shall calculate supported person counts in
configured zones.

**FR-CRD-002:** Administrators shall configure Normal, Elevated, High
and Critical occupancy thresholds or equivalent client-defined levels.

**FR-CRD-003:** Threshold transitions shall be recorded.

**FR-CRD-004:** Supported line/zone analytics shall estimate entry and
exit flow.

**FR-CRD-005:** The dashboard shall show current occupancy, threshold
state, trend, associated camera and recent events.

**FR-CRD-006:** Crowd events shall require human operational
interpretation.

## 4.9 Vehicle Analytics

**FR-VEH-001:** ARGUS shall support approved vehicle classes.

**FR-VEH-002:** Vehicles shall be trackable within supported camera
streams.

**FR-VEH-003:** ARGUS shall count vehicles using configured lines/zones.

**FR-VEH-004:** Direction shall be recorded where supported.

**FR-VEH-005:** A stopped-vehicle event may be generated when a vehicle
remains in a configured zone beyond a threshold.

**FR-VEH-006:** Traffic dashboards shall expose supported flow and
occupancy indicators.

## 4.10 ARGUS Sense

**FR-SEN-001:** Sensors shall be registered with ID, type, site, zone,
endpoint, status and calibration information.

**FR-SEN-002:** Sensor health shall be visible.

**FR-SEN-003:** Observations shall contain source, time, zone/location,
observation type, quality/confidence where available and processing
version.

## 4.11 WiFi CSI

**FR-CSI-001:** Advanced WiFi sensing shall use approved CSI-capable
hardware where channel-state information is required.

**FR-CSI-002:** ARGUS Sense shall support locally validated
human-presence observations.

**FR-CSI-003:** ARGUS Sense shall support locally validated movement
observations.

**FR-CSI-004:** Experimental CSI-derived pose visualization may be
included in a controlled POC.

**FR-CSI-005:** Each CSI analytic shall display a validation state:
Experimental, Under Calibration, Validated for POC or Operationally
Approved.

**FR-CSI-006:** CSI sensing shall support site-specific calibration
because room geometry, walls, furniture, interference, device placement
and occupancy can affect results.

**FR-CSI-007:** The product shall not claim validated pose sensing from
ordinary WiFi hardware when the required CSI hardware and calibration
are absent.

## 4.12 ARGUS Fusion

**FR-FUS-001:** ARGUS shall correlate observations using configurable
rules.

**FR-FUS-002:** Correlation may use time window, location, zone, source,
event category, confidence and sensor health.

**FR-FUS-003:** Fused events shall reference all contributing
observations.

**FR-FUS-004:** ARGUS may calculate a fusion confidence/priority
indicator.

**FR-FUS-005:** Operators shall see why a fused event was generated.

Example:

``` text
Restricted Zone Event
Vision Person Detection: 0.91
RF Presence Observation: 0.87
Rule: Restricted Area / Multi-Sensor
Fusion Priority: HIGH
State: Awaiting Human Verification
```

**FR-FUS-006:** Fusion results shall not automatically initiate
enforcement action.

## 4.13 Event Management

**FR-EVT-001:** A configured analytic or fusion rule may create an
event.

**FR-EVT-002:** Events shall include ID, type, source, location, zone,
time, priority, confidence where applicable, state, rule and supporting
references.

**FR-EVT-003:** Event states shall include New, Under Review, Verified,
Dismissed and Converted to Incident.

**FR-EVT-004:** The event queue shall support sorting/filtering by
priority, time, location, source, category and state.

**FR-EVT-005:** ARGUS should support deduplication/suppression for
repeated observations representing one continuing condition.

**FR-EVT-006:** Dismissal shall require a reason or note.

## 4.14 Human Verification

**FR-VER-001:** Configured event categories shall require human
verification before incident creation.

**FR-VER-002:** The review workspace shall display available video,
sensor observations, rule, location, time, confidence, fusion
contributors and related events.

**FR-VER-003:** Authorized actions shall include Verify, Dismiss and
Request Further Review.

**FR-VER-004:** Verification shall record actor, action, timestamp and
note/reason.

## 4.15 Incident Management

**FR-INC-001:** Authorized users shall create incidents from verified
events.

**FR-INC-002:** Manual incident creation may be enabled according to
policy.

**FR-INC-003:** Incidents shall include ID, title, category, priority,
location, originating events, description, state, assignment,
timestamps, notes and evidence references.

**FR-INC-004:** Default lifecycle shall be:

``` text
Detected -> Under Review -> Verified -> Assigned ->
Responding -> Monitoring -> Resolved -> Closed
```

**FR-INC-005:** Incident Controllers shall assign incidents to
authorized teams/users.

**FR-INC-006:** Authorized users shall escalate incidents.

**FR-INC-007:** Significant actions shall appear in a chronological
timeline.

**FR-INC-008:** Closure shall require appropriate permission and a
resolution note.

## 4.16 GIS Command

**FR-GIS-001:** ARGUS shall provide an operational GIS map.

**FR-GIS-002:** Layers may include cameras, sensors, events, incidents,
facilities and operational zones.

**FR-GIS-003:** Marker appearance shall communicate operational status.

**FR-GIS-004:** Selecting a map item shall open authorized details.

**FR-GIS-005:** Users shall filter map objects by type, status and area.

## 4.17 Investigation Search

**FR-SRC-001:** ARGUS shall index selected event/detection metadata.

**FR-SRC-002:** Search filters shall include date/time, camera,
location, zone, object class, event category and incident ID.

**FR-SRC-003:** Results shall show timestamp, source, category, location
and available preview/reference.

**FR-SRC-004:** Authorized users shall open linked evidence.

**FR-SRC-005:** Sensitive searches/evidence access shall be auditable.

## 4.18 Evidence

**FR-EVD-001:** Events/incidents shall support associated video clips,
snapshots, metadata and documents where authorized.

**FR-EVD-002:** Evidence metadata shall include ID, source, capture
time, associated event/incident, storage reference and access
classification.

**FR-EVD-003:** Evidence shall be protected by role and operational
scope.

**FR-EVD-004:** Protected evidence access shall be logged.

**FR-EVD-005:** Retention shall be configurable according to approved
policy.

## 4.19 Analytics

**FR-ANA-001:** Dashboards shall show active events, open incidents,
source health and configured counts.

**FR-ANA-002:** Event trends shall be filterable by category, location,
time, priority and source.

**FR-ANA-003:** Incident metrics shall include time to verification,
assignment and resolution where data is available.

**FR-ANA-004:** Camera/sensor availability metrics shall be available.

**FR-ANA-005:** Authorized users shall generate approved operational
reports.

## 4.20 Administration and AI Models

**FR-ADM-001:** Administrators shall manage users.

**FR-ADM-002:** Administrators shall manage roles/permissions.

**FR-ADM-003:** Authorized administrators shall configure occupancy,
dwell, vehicle and sensor thresholds.

**FR-ADM-004:** Rules shall be configurable and enable/disable capable.

**FR-ADM-005:** Security/operational configuration changes shall be
audited.

**FR-AIM-001:** ARGUS shall maintain an approved model registry.

**FR-AIM-002:** Model-generated events should be traceable to
model/version.

**FR-AIM-003:** Model states shall include Testing, Approved, Active,
Deprecated and Disabled.

**FR-AIM-004:** Representative benchmark records shall be maintained.

**FR-AIM-005:** Deployment processes shall support rollback to a
previously approved model/configuration.

------------------------------------------------------------------------

# 5. User Stories and Acceptance Criteria

  -----------------------------------------------------------------------------
  ID                      User Story              Key Acceptance Criteria
  ----------------------- ----------------------- -----------------------------
  US-001                  As an operator, I want  Camera identity/status
                          to monitor authorized   visible; permissions
                          cameras from one        enforced; unavailable streams
                          interface so I can      clearly marked.
                          maintain situational    
                          awareness.              

  US-002                  As an administrator, I  Polygon editable;
                          want to draw a          name/rule/schedule/severity
                          restricted polygon so   saved; change audited.
                          ARGUS can evaluate      
                          detections against it.  

  US-003                  As an operator, I want  Camera, zone, time and
                          a restricted-zone event supporting reference
                          so I can review         displayed; verify/dismiss
                          possible presence       available.
                          quickly.                

  US-004                  As an event commander,  Count, threshold state and
                          I want crowd occupancy  event transition visible.
                          by zone so congestion   
                          can be identified.      

  US-005                  As a traffic operator,  Line configurable;
                          I want vehicle line     counts/direction visible.
                          counts so I can         
                          understand flow.        

  US-006                  As a traffic operator,  Dwell threshold configurable;
                          I want stopped-vehicle  event linked to camera; no
                          events so I can review  intent inference.
                          possible obstruction.   

  US-007                  As a facility operator, Sensor health, time, zone and
                          I want CSI presence     validation status shown.
                          observations so I have  
                          an additional sensing   
                          signal.                 

  US-008                  As an operator, I want  Both sources and fusion rule
                          Vision + RF correlation visible; human verification
                          so I can prioritize     required.
                          multi-source events.    

  US-009                  As an operator, I want  Supporting information
                          to verify an event so   visible; actor/time recorded.
                          an incident can be      
                          created appropriately.  

  US-010                  As an incident          Team/user selectable;
                          controller, I want to   assignment audited.
                          assign incidents so     
                          responsibility is       
                          clear.                  

  US-011                  As a commander, I want  Layers, status, filters and
                          cameras, sensors and    detail selection available.
                          incidents on GIS so I   
                          understand geographic   
                          context.                

  US-012                  As an investigator, I   Time/source/event filters;
                          want historical         authorized evidence links;
                          metadata search so I    access audited.
                          can find relevant       
                          footage faster.         

  US-013                  As an auditor, I want   Verification, assignment,
                          complete incident       status changes and closure
                          history so              show actor/time.
                          accountability can be   
                          verified.               
  -----------------------------------------------------------------------------

------------------------------------------------------------------------

# 6. Detailed Use Cases

## UC-001 --- Public Event Crowd Congestion

**Primary Actor:** Command Center Operator\
**Supporting Actors:** Event Commander, Incident Controller

**Preconditions:** Authorized camera online; person detection enabled;
crowd zone and thresholds configured.

**Trigger:** Supported person occupancy crosses a configured threshold.

**Main Flow:** 1. Camera stream enters ARGUS Vision. 2. Detector
generates person detections. 3. Detections are normalized and evaluated
by tracking/zone analytics. 4. Zone occupancy exceeds threshold. 5.
ARGUS creates a crowd event. 6. Event enters operator queue. 7. Operator
reviews associated video and analytics. 8. Operator verifies or
dismisses the event. 9. If verified, ARGUS creates an incident. 10.
Incident Controller assigns a response team. 11. ARGUS continues
monitoring. 12. Occupancy returns below threshold. 13. Authorized
personnel resolve and close the incident. 14. Timeline and audit remain
available.

**Alternative:** If the event is not actionable, the operator dismisses
it with a reason.

## UC-002 --- Restricted Facility Vision + RF

**Preconditions:** Restricted video zone, CSI zone and fusion rule
configured.

**Main Flow:** 1. Vision observes a supported person detection. 2.
Tracking places it inside the restricted polygon. 3. ARGUS Vision
creates an observation. 4. ARGUS Sense receives an RF presence/movement
observation. 5. Fusion correlates both within configured time/location
constraints. 6. A fused high-priority event is created. 7. Operator sees
contributing sources. 8. Operator verifies or dismisses. 9. A verified
event may become an incident.

**Constraint:** The system shall not identify the individual or infer
intent solely from these observations.

## UC-003 --- Vehicle Flow / Stopped Vehicle

1.  Vehicle detections enter tracking.
2.  Vehicles cross configured lines.
3.  Directional counts update.
4.  Traffic dashboard shows flow.
5.  If a vehicle remains in a configured no-stopping zone beyond
    threshold, an event is created.
6.  Operator reviews associated video.
7.  Operational handling remains a human decision.

## UC-004 --- Investigation Search

1.  Investigator selects a time range.
2.  Investigator selects camera/zone/location.
3.  Investigator selects object/event category.
4.  ARGUS searches indexed metadata.
5.  Matching event references are returned.
6.  Permission is checked before evidence opens.
7.  Evidence access is audited.

------------------------------------------------------------------------

# 7. Addis Ababa Police Demonstration --- Operation Meskel

The demonstration shall use authorized, synthetic or prerecorded media
and a controlled sensor lab.

## 7.1 Stage 1 --- Normal Operations

ARGUS Command displays four demo cameras, operational map, source
health, current counts and event queue.

## 7.2 Stage 2 --- Crowd Increase

A demo gate shows increasing occupancy:

``` text
09:55  143
10:02  186
10:09  231
10:15  287
```

ARGUS creates:

``` text
Event: AG-EVT-0042
Category: Crowd Threshold
Location: Demo Gate B
Priority: Medium
State: New
```

## 7.3 Stage 3 --- Human Verification

The operator opens the event and reviews the feed, polygon, count,
threshold and trend. Selecting **Verify** records operator and time.

## 7.4 Stage 4 --- Incident

A verified event becomes:

``` text
Incident: AG-INC-0017
Category: Crowd Congestion
Priority: Medium
Status: Verified
```

The controller assigns the demo response team and updates the lifecycle.

## 7.5 Stage 5 --- Vision + RF Fusion

Vision:

``` text
Person in Restricted Zone
Confidence: 0.91
```

ARGUS Sense:

``` text
RF Presence
Quality/Confidence: 0.87
```

Fusion:

``` text
Sources: Vision + RF
Rule: Restricted Zone Multi-Sensor
Priority: High
State: Awaiting Human Verification
```

## 7.6 Stage 6 --- Investigation and Audit

The presenter searches Facility A + restricted-zone events, opens the
linked reference, then shows:

``` text
Detected -> Correlated -> Reviewed -> Verified ->
Assigned -> Responding -> Resolved -> Closed
```

------------------------------------------------------------------------

# 8. UI Requirements

## 8.1 Navigation

Overview; Live Operations; GIS Command; ARGUS Vision; ARGUS Sense; ARGUS
Fusion; Events & Alerts; Incidents; Investigation; Evidence; Analytics;
Administration.

## 8.2 Main Dashboard

The dashboard shall include live operations, GIS, KPI cards, active
events, Vision/Sense/Fusion status, incident workflow, investigation
search and system health.

## 8.3 Event Detail

Shall show event ID, priority, source, camera/sensor, location, map,
time, supporting reference, rule, confidence, fusion contributors and
verification actions.

## 8.4 Incident Workspace

Shall show summary, priority, status, map, observations, evidence,
assignment, notes, timeline, escalation, resolution and closure.

## 8.5 ARGUS Sense UI

Shall show sensor health, CSI quality, presence, movement, calibration
and validation status. Pose visualization shall be labeled experimental
where applicable.

------------------------------------------------------------------------

# 9. Data Model

Core entities:

`User`, `Role`, `Permission`, `Organization`, `Camera`, `CameraGroup`,
`Sensor`, `Site`, `Zone`, `VirtualLine`, `AIModel`, `ModelVersion`,
`Detection`, `Track`, `SensorObservation`, `FusionRule`, `Event`,
`EventObservation`, `Incident`, `IncidentAssignment`,
`IncidentTimeline`, `Evidence`, `AuditLog`, `SystemHealth`.

Example event:

``` json
{
  "event_id": "AG-EVT-0042",
  "event_type": "restricted_zone_presence",
  "priority": "high",
  "status": "under_review",
  "site": "Facility A",
  "zone": "Restricted Area 01",
  "sources": ["vision", "rf"],
  "human_verification_required": true
}
```

------------------------------------------------------------------------

# 10. Integration Requirements

ARGUS shall support modular adapters for video streams, inference
services, GIS, CSI sensors, approved IoT devices and future external
systems.

The Supervision integration shall focus on computer-vision primitives
such as detection representation, annotation, video processing, polygon
zones, counting and related analytics. ARGUS event management, fusion,
GIS, evidence, RBAC and incident workflows shall remain product-owned
application components.

Future controlled integrations may include access control, dispatch,
notification gateways, existing command-center systems and approved GIS
layers.

------------------------------------------------------------------------

# 11. Non-Functional Requirements

## 11.1 Security

-   Encrypted transport for sensitive communication.
-   Least privilege.
-   Network segmentation.
-   Secure secret management.
-   Administrative and operational audit.
-   Protected evidence access.
-   Audited changes to users, roles, models, zones and thresholds.

## 11.2 Privacy and Responsible Use

-   Processing limited to approved purposes.
-   Human-in-the-loop operational decisions.
-   No facial recognition in V1.
-   No automated criminal-intent inference.
-   CSI sensing limited to authorized instrumented environments.
-   Configurable retention.

## 11.3 Performance

-   Horizontally scalable inference workers.
-   GPU sizing based on benchmarked model, resolution, FPS and stream
    count.
-   Indexed historical metadata.
-   Graceful degradation when individual sources fail.

## 11.4 Availability

-   Critical service health monitoring.
-   Source disconnection recording.
-   Restart/recovery procedures.
-   Production redundancy based on deployment criticality.

## 11.5 Usability

-   Operational information prioritized over decorative effects.
-   Consistent severity/status language.
-   Clear separation of Observation, Event, Verified Event and Incident.
-   Experimental capabilities visibly identified.

## 11.6 Maintainability

-   Replaceable detector interface.
-   Replaceable tracker interface.
-   Sensor adapters.
-   Version-pinned and license-reviewed open-source dependencies.
-   Configuration-driven rules where practical.

------------------------------------------------------------------------

# 12. Infrastructure and GPU Requirements

Supervision itself is not the primary GPU workload. GPU demand is driven
mainly by the selected neural inference model, stream resolution,
processed FPS, number of simultaneous streams and any segmentation/pose
workload.

The POC should include: - application/backend server; -
PostgreSQL/PostGIS; - object/local storage; - event/message service as
required; - one suitable NVIDIA GPU workstation/server for
representative inference; - four authorized/prerecorded video feeds; -
CSI-capable test hardware; - operator workstation; - controlled network.

Production sizing shall follow benchmark results rather than fixed
assumptions.

------------------------------------------------------------------------

# 13. POC Acceptance Criteria

ARGUS POC shall demonstrate:

1.  Four authorized/prerecorded video sources.
2.  Person and vehicle detection.
3.  Object tracking.
4.  Polygon zone configuration.
5.  Line crossing.
6.  Crowd threshold event.
7.  Restricted-zone event.
8.  Dwell/stopped-object event.
9.  Operator event queue.
10. Human verification.
11. Incident creation.
12. Incident assignment/status workflow.
13. GIS representation.
14. Historical metadata search.
15. Evidence reference access.
16. Audit history.
17. CSI presence/movement in an instrumented test area.
18. Pose only when local POC validation succeeds.
19. Vision + RF fused event.
20. Human verification retained for the fused event.

------------------------------------------------------------------------

# 14. Out of Scope --- V1

-   Facial recognition.
-   Automated identity matching.
-   Autonomous enforcement.
-   Automated criminal-intent determination.
-   Citywide production deployment.
-   Unvalidated through-wall pose claims.
-   Weaponized/autonomous response.
-   Social-media intelligence.
-   Strategic intelligence functions belonging to other products.

------------------------------------------------------------------------

# 15. Implementation Roadmap

  -----------------------------------------------------------------------
  Phase                   Scope                   Output
  ----------------------- ----------------------- -----------------------
  1                       Vision Foundation       Video ingestion,
                                                  detector adapter,
                                                  Supervision analytics,
                                                  tracker, zones, lines,
                                                  event API

  2                       Command                 Authentication, RBAC,
                                                  dashboard, GIS, events,
                                                  incidents, audit

  3                       Crowd & Vehicle         Occupancy, thresholds,
                                                  flow, stopped/dwell
                                                  analytics

  4                       Sense                   CSI lab, sensor
                                                  registry, presence,
                                                  movement, calibration,
                                                  pose evaluation

  5                       Fusion                  Correlation engine,
                                                  multi-source rules,
                                                  explainability UI

  6                       Insight                 Search, evidence
                                                  references, analytics
                                                  and reporting

  7                       Pilot Hardening         Benchmarking, GPU
                                                  sizing, security,
                                                  monitoring,
                                                  backup/recovery and UAT
  -----------------------------------------------------------------------

------------------------------------------------------------------------

# 16. Test Scenarios

  -----------------------------------------------------------------------
  ID                      Scenario                Expected Result
  ----------------------- ----------------------- -----------------------
  TS-001                  Camera offline          Camera state changes
                                                  and operator sees
                                                  health issue

  TS-002                  Person enters           Configured event
                          restricted zone         created

  TS-003                  Object crosses virtual  Count increments
                          line                    

  TS-004                  Crowd threshold crossed Crowd event enters
                                                  queue

  TS-005                  Vehicle exceeds dwell   Stopped/dwell event
                          threshold               created

  TS-006                  CSI presence            Sensor observation
                                                  displayed with
                                                  validation state

  TS-007                  Vision + RF correlation Fused event displays
                                                  both sources

  TS-008                  Operator dismisses      Reason and actor
                          event                   audited

  TS-009                  Operator verifies event Verification actor/time
                                                  stored

  TS-010                  Incident assignment     Assignment appears in
                                                  timeline

  TS-011                  Metadata search         Authorized matching
                                                  results returned

  TS-012                  Unauthorized evidence   Access denied
                          access                  

  TS-013                  Inference service       Processing health shows
                          unavailable             degraded/unavailable

  TS-014                  Threshold changed       Configuration audit
                                                  record created
  -----------------------------------------------------------------------

------------------------------------------------------------------------

# 17. Traceability

  Objective                       Requirement Groups
  ------------------------------- ------------------------------------------
  Unified situational awareness   CAM, GIS, EVT
  Visual intelligence             VIS, TRK, ZON, LIN, DWL
  Crowd safety                    CRD
  Traffic awareness               VEH
  RF sensing                      SEN, CSI
  Multi-sensor understanding      FUS
  Human-controlled response       VER, INC
  Investigation                   SRC, EVD
  Accountability                  AUTH, audit, security
  Scalability                     Performance, availability
  Responsible operation           Privacy and responsible-use requirements

------------------------------------------------------------------------

# 18. Final Product Definition

ARGUS is a modular, auditable and human-centered **Multi-Sensor AI
Situational Awareness Platform**.

``` text
SEE
Authorized video
   |
SENSE
CSI + approved sensors
   |
UNDERSTAND
Detection + Tracking + Zones + Rules + Fusion
   |
VERIFY
Authorized human review
   |
RESPOND
Incident + GIS + Assignment + Evidence + Analytics
```

**ARGUS --- See. Sense. Understand. Respond.**
