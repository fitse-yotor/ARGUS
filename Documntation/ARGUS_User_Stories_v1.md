# ARGUS --- User Stories & Acceptance Criteria

**Version:** 1.0\
**Product:** ARGUS\
**Motto:** *See. Sense. Understand. Respond.*

## 1. Story Conventions

Priority uses **Must / Should / Could**. Each story is independently
testable. AI observations remain decision-support outputs and do not
automatically constitute an operational incident.

## Epic 1 --- Identity & Access

### US-001 --- Secure Login

**As an** ARGUS user, **I want** secure authentication **so that** only
authorized personnel access the platform.\
**Priority:** Must

**Acceptance Criteria** - Valid credentials grant authorized access. -
Invalid credentials are rejected. - User receives only assigned
permissions. - Authentication events are auditable.

### US-002 --- Role-Based Permissions

**As an** administrator, **I want** roles and permissions **so that**
users only access functions needed for their duties.\
**Priority:** Must

**Acceptance Criteria** - Permissions can be assigned by role. -
Restricted navigation/actions are unavailable. - Camera/sensor scope can
be limited. - Changes are audited.

## Epic 2 --- Live Operations

### US-003 --- Camera Wall

**As an** operator, **I want** a configurable camera wall **so that** I
can monitor several authorized areas together.\
**Priority:** Must

**Acceptance Criteria** - Operator can select permitted feeds. - Camera
name/location/status are visible. - Offline sources show an explicit
health state. - Layout supports multiple feeds.

### US-004 --- Camera Health

**As an** operator, **I want** source health indicators **so that** I
know when coverage is degraded.\
**Priority:** Must

**Acceptance Criteria** - Online/Degraded/Offline states are visible. -
Status changes update without requiring reconfiguration. - Health issue
can be filtered.

## Epic 3 --- Vision Analytics

### US-005 --- Object Detection

**As an** operator, **I want** supported objects detected in video **so
that** video can become structured operational metadata.\
**Priority:** Must

**Acceptance Criteria** - Approved classes are detected by configured
model. - Detection includes confidence and timestamp. - Model/version
can be traced where feasible.

### US-006 --- Object Tracking

**As an** operator, **I want** detections tracked across frames **so
that** movement, crossing and dwell can be measured.\
**Priority:** Must

**Acceptance Criteria** - Temporary track IDs are produced. - Track
metadata supports zone/line analytics. - Tracker can be replaced through
an adapter.

### US-007 --- Configure Polygon Zone

**As an** administrator, **I want** to draw a polygon zone **so that**
analytics can be specific to an operational area.\
**Priority:** Must

**Acceptance Criteria** - Polygon can be drawn/edited. - Zone type and
object class are configurable. - Threshold/schedule/severity can be
saved. - Change is audited.

### US-008 --- Restricted-Zone Event

**As an** operator, **I want** a restricted-zone event **so that** I can
review supported presence quickly.\
**Priority:** Must

**Acceptance Criteria** - Event contains camera, zone and time. -
Supporting source reference is available. - Verify/Dismiss actions are
available. - Intent is not inferred automatically.

### US-009 --- Line Crossing

**As a** traffic/event operator, **I want** line-crossing counts **so
that** movement through gates or roads can be measured.\
**Priority:** Must

**Acceptance Criteria** - Virtual line is configurable. - Crossing
increments count. - Direction is available where supported.

### US-010 --- Dwell Event

**As an** operator, **I want** a dwell threshold event **so that** I can
review an object remaining in a configured area.\
**Priority:** Should

**Acceptance Criteria** - Dwell duration is configurable. - Event
contains zone and duration. - Event remains observational, not an intent
judgment.

## Epic 4 --- Crowd Safety

### US-011 --- Crowd Occupancy

**As an** event commander, **I want** current zone occupancy **so that**
I can understand crowd concentration.\
**Priority:** Must

**Acceptance Criteria** - Current supported count is visible. - Zone and
camera are identified. - Count updates during processing.

### US-012 --- Crowd Threshold

**As an** event commander, **I want** threshold events **so that**
rising congestion can receive attention.\
**Priority:** Must

**Acceptance Criteria** - Multiple thresholds can be configured. -
Transition creates an event. - Trend and supporting camera can be
reviewed.

### US-013 --- Entry/Exit Flow

**As an** event commander, **I want** entry/exit counts **so that** gate
flow can be understood.\
**Priority:** Should

**Acceptance Criteria** - Directional lines can be configured. - Counts
are separated where supported. - Dashboard displays flow.

## Epic 5 --- Vehicle / Traffic

### US-014 --- Vehicle Count

**As a** traffic operator, **I want** vehicle counts **so that** traffic
volume can be monitored.\
**Priority:** Must

### US-015 --- Vehicle Direction

**As a** traffic operator, **I want** movement direction **so that**
abnormal or congested flow can be reviewed.\
**Priority:** Should

### US-016 --- Stopped Vehicle

**As a** traffic operator, **I want** stopped-vehicle events in
configured zones **so that** possible obstruction can be reviewed.\
**Priority:** Should

**Acceptance Criteria** - Zone and dwell threshold are configurable. -
Event links to supporting source. - Operator determines action.

## Epic 6 --- ARGUS Sense

### US-017 --- Register CSI Sensor

**As an** administrator, **I want** CSI nodes registered **so that**
their observations have known site/zone context.\
**Priority:** Must for Sense POC

### US-018 --- RF Presence

**As a** facility operator, **I want** validated RF presence
observations **so that** an instrumented zone provides an additional
sensing signal.\
**Priority:** Must for Sense POC

**Acceptance Criteria** - Sensor health is visible. - Observation has
time and zone. - Validation state is visible.

### US-019 --- RF Movement

**As a** facility operator, **I want** movement observations **so that**
changes in an instrumented environment can be reviewed.\
**Priority:** Should

### US-020 --- Experimental RF Pose

**As a** technical evaluator, **I want** experimental pose visualization
**so that** the CSI POC can be assessed.\
**Priority:** Could / Experimental

**Acceptance Criteria** - Only enabled after controlled testing. - UI
labels capability Experimental/POC. - Calibration state is visible. -
Failure/uncertainty is not represented as certainty.

## Epic 7 --- Sensor Fusion

### US-021 --- Correlate Vision and RF

**As an** operator, **I want** related Vision and RF observations
correlated **so that** multi-source events can be prioritized.\
**Priority:** Must for Fusion POC

**Acceptance Criteria** - Both sources are linked. - Correlation rule is
visible. - Time/location relationship is retained. - Human verification
remains required.

### US-022 --- Explain Fusion

**As an** operator, **I want** to see why a fusion event was generated
**so that** I can make an informed review.\
**Priority:** Must

### US-023 --- Event Deduplication

**As an** operator, **I want** repeated observations grouped/suppressed
**so that** one continuing condition does not overwhelm the queue.\
**Priority:** Should

## Epic 8 --- Event Verification

### US-024 --- Review Event

**As an** operator, **I want** all supporting information in one
workspace **so that** I can review efficiently.\
**Priority:** Must

### US-025 --- Verify Event

**As an** operator, **I want** to verify an event **so that** it can
enter incident workflow when appropriate.\
**Priority:** Must

### US-026 --- Dismiss Event

**As an** operator, **I want** to dismiss a non-actionable event with a
reason **so that** the system records the decision.\
**Priority:** Must

## Epic 9 --- Incident Management

### US-027 --- Create Incident

**As an** authorized operator, **I want** to create an incident from a
verified event **so that** response can be coordinated.\
**Priority:** Must

### US-028 --- Assign Incident

**As an** incident controller, **I want** to assign an incident **so
that** responsibility is clear.\
**Priority:** Must

### US-029 --- Incident Timeline

**As a** controller, **I want** a chronological timeline **so that** I
can understand what happened and when.\
**Priority:** Must

### US-030 --- Escalate Incident

**As a** controller, **I want** to escalate an incident **so that**
higher-priority handling can occur where authorized.\
**Priority:** Should

### US-031 --- Resolve and Close

**As a** controller, **I want** to resolve and close incidents with
notes **so that** the operational record is complete.\
**Priority:** Must

## Epic 10 --- GIS

### US-032 --- Operational Map

**As a** commander, **I want** cameras, sensors, events and incidents on
a map **so that** I can understand geographic context.\
**Priority:** Must

### US-033 --- GIS Filters

**As a** commander, **I want** map filters **so that** I can focus on
relevant operational objects.\
**Priority:** Should

## Epic 11 --- Investigation & Evidence

### US-034 --- Metadata Search

**As an** investigator, **I want** search by time, camera, zone,
object/event type **so that** I can find relevant references quickly.\
**Priority:** Must

### US-035 --- Evidence Access

**As an** investigator, **I want** authorized evidence links **so that**
I can review relevant material.\
**Priority:** Must

### US-036 --- Evidence Access Audit

**As an** auditor, **I want** protected evidence access recorded **so
that** accountability is maintained.\
**Priority:** Must

## Epic 12 --- Analytics & Administration

### US-037 --- Operational KPIs

**As a** supervisor, **I want** event, incident and source-health KPIs
**so that** I can understand current operations.\
**Priority:** Must

### US-038 --- Response Metrics

**As a** supervisor, **I want** verification/assignment/resolution
timing **so that** workflow performance can be reviewed.\
**Priority:** Should

### US-039 --- Model Registry

**As an** AI administrator, **I want** approved model/version management
**so that** inference changes are controlled.\
**Priority:** Must

### US-040 --- Audit Review

**As an** auditor, **I want** read-only audit search **so that**
operational and administrative actions can be reviewed.\
**Priority:** Must

## 3. POC Story Set

The first demonstration should implement US-003, 005, 006, 007, 008,
009, 011, 012, 014, 016, 018, 021, 022, 024, 025, 027, 028, 029, 032,
034, 037 and 040.
