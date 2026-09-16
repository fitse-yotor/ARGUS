# ARGUS --- Detailed Use Case Specification

**Product:** ARGUS --- Multi-Sensor AI Situational Awareness Platform\
**Motto:** *See. Sense. Understand. Respond.*\
**Version:** 1.0

## 1. Purpose

This document defines the principal operational use cases for ARGUS. It
covers ARGUS Vision, ARGUS Sense, ARGUS Fusion, ARGUS Command and ARGUS
Insight. AI and sensor observations are decision-support inputs;
configured operational incidents remain subject to authorized human
review.

## 2. Actors

  -----------------------------------------------------------------------
  Actor                               Responsibility
  ----------------------------------- -----------------------------------
  Command Center Operator             Monitors sources, reviews events,
                                      verifies/dismisses observations

  Incident Controller                 Assigns, escalates, monitors and
                                      closes incidents

  Supervisor / Commander              Maintains operational picture and
                                      reviews priorities/performance

  Investigator / Analyst              Searches authorized historical
                                      metadata/evidence

  System Administrator                Configures users, cameras, sensors,
                                      zones, rules and thresholds

  AI Administrator                    Manages approved models, inference
                                      services and calibration

  Auditor                             Reviews audit/evidence access
                                      trails
  -----------------------------------------------------------------------

## 3. Use Case Map

``` text
Camera/Sensors
     |
     v
[Observe Environment]
     |
     +--> UC-01 Live Monitoring
     +--> UC-02 Configure Zone
     +--> UC-03 Restricted Zone
     +--> UC-04 Crowd Monitoring
     +--> UC-05 Line Crossing
     +--> UC-06 Vehicle Monitoring
     +--> UC-07 Dwell Event
     +--> UC-08 RF Presence
                         |
                         v
                  UC-09 Sensor Fusion
                         |
                         v
                  UC-10 Verify Event
                         |
                         v
                  UC-11 Create Incident
                         |
                         v
                  UC-12 Assign/Respond
                         |
                         v
                  UC-13 Resolve/Close

Historical Data --> UC-14 Investigation Search --> UC-15 Evidence Review
GIS --> UC-16 Operational Map
Admin --> UC-17 Camera/Sensor Config
Admin --> UC-18 AI/Rule Config
Supervisor --> UC-19 Analytics
Auditor --> UC-20 Audit Review
```

## UC-01 --- Monitor Live Operations

**Primary Actor:** Command Center Operator\
**Preconditions:** User authenticated; assigned camera permissions
exist; sources configured.\
**Trigger:** Operator opens Live Operations.

**Main Flow** 1. ARGUS loads permitted camera groups. 2. Platform checks
stream health. 3. Operator selects a layout. 4. ARGUS displays selected
feeds. 5. Active zones, counts and permitted overlays are displayed. 6.
Operator may select a feed for detailed monitoring.

**Alternative:** Offline camera is shown with health state instead of
misleading stale imagery.\
**Postcondition:** Viewing activity is subject to configured audit
policy.

## UC-02 --- Configure Monitoring Zone

**Actor:** System Administrator\
**Preconditions:** Camera registered and accessible.

1.  Administrator selects camera.
2.  Current reference frame is displayed.
3.  Administrator draws polygon.
4.  Enters zone name/type.
5.  Selects object classes.
6.  Configures threshold/dwell/schedule/severity.
7.  Saves configuration.
8.  ARGUS validates polygon/rule.
9.  Configuration becomes active.
10. Change is audited.

## UC-03 --- Restricted-Zone Presence

**Actor:** Operator\
**Trigger:** Supported tracked object satisfies restricted-zone rule.

1.  Detector produces a supported detection.
2.  Tracking associates the object across frames.
3.  Zone analytics determine that the track entered the polygon.
4.  ARGUS creates an observation/event.
5.  Event enters queue.
6.  Operator opens supporting information.
7.  Operator verifies, dismisses or requests review.
8.  If verified and policy requires, an incident is created.

**Constraint:** Presence alone shall not be treated as proof of unlawful
intent.

## UC-04 --- Crowd Threshold Monitoring

**Actor:** Event Commander / Operator

1.  Person detections enter zone analytics.
2.  Current occupancy is calculated.
3.  ARGUS compares count against configured thresholds.
4.  Threshold transition is recorded.
5.  Event appears with zone, count, trend and camera.
6.  Operator reviews.
7.  Verified operational condition may become an incident.
8.  ARGUS continues monitoring until occupancy normalizes.

## UC-05 --- Line Crossing

**Actor:** Traffic/Event Operator

1.  Administrator configures line and permitted classes.
2.  Tracks approach line.
3.  Track crosses line.
4.  Direction is calculated where supported.
5.  Counter increments.
6.  Event is created only if an event rule is enabled.

## UC-06 --- Vehicle Flow Monitoring

**Actor:** Traffic Operator

1.  Vehicle detections are tracked.
2.  Vehicle counts are aggregated by configured line/zone.
3.  Direction/occupancy indicators are updated.
4.  Operator views current flow.
5.  Configured congestion conditions may create an event.

## UC-07 --- Dwell / Stopped-Object Event

**Actor:** Operator

1.  Track enters configured zone.
2.  ARGUS starts dwell timer.
3.  Track remains beyond threshold.
4.  Event is created.
5.  Operator reviews source footage.
6.  Operator determines whether operational action is appropriate.

## UC-08 --- WiFi CSI Presence / Movement

**Actor:** Facility Operator\
**Preconditions:** Approved CSI hardware installed; zone calibrated.

1.  CSI node captures supported channel-state measurements.
2.  ARGUS Sense processes observations.
3.  Presence/movement result is produced.
4.  Observation receives timestamp, zone and quality/confidence.
5.  Operator sees observation and sensor validation status.

**Alternative:** Poor signal/calibration results in Degraded/Uncertain
state rather than an unsupported definitive result.

## UC-09 --- Vision + RF Sensor Fusion

**Actor:** Operator

1.  ARGUS Vision creates restricted-zone observation.
2.  ARGUS Sense creates RF presence observation.
3.  Fusion Engine evaluates time/location/rule relationship.
4.  Sources satisfy correlation rule.
5.  Fused event is created.
6.  UI displays contributing sources and fusion priority.
7.  Operator performs human verification.

## UC-10 --- Verify or Dismiss Event

**Actor:** Operator

1.  Operator opens event.
2.  ARGUS displays source, time, location, rule and supporting
    references.
3.  Operator selects Verify, Dismiss or Further Review.
4.  Reason/note is captured where required.
5.  Actor and timestamp are audited.
6.  Verified event may progress to incident workflow.

## UC-11 --- Create Incident

**Actor:** Operator / Incident Controller

1.  User selects verified event.
2.  Chooses Create Incident.
3.  ARGUS prepopulates available event information.
4.  User confirms category, priority and description.
5.  Incident ID is generated.
6.  Source events/evidence remain linked.
7.  Incident enters configured lifecycle.

## UC-12 --- Assign and Coordinate Incident

**Actor:** Incident Controller

1.  Controller opens incident.
2.  Selects authorized team/user.
3.  Assignment is recorded.
4.  Status changes to Assigned.
5.  Response updates are recorded.
6.  Timeline is continuously updated.
7.  Escalation may occur where authorized.

## UC-13 --- Resolve and Close Incident

**Actor:** Incident Controller

1.  Response outcome is recorded.
2.  Status changes to Resolved.
3.  Authorized user reviews required information.
4.  Closure reason/summary is entered.
5.  Status changes to Closed.
6.  Closure is audited.

## UC-14 --- Historical Investigation Search

**Actor:** Investigator

1.  Investigator enters date/time.
2.  Selects camera/location/zone.
3.  Selects object/event category.
4.  ARGUS queries indexed metadata.
5.  Results are returned.
6.  Investigator selects a permitted result.
7.  Associated reference is opened.
8.  Sensitive access is audited.

## UC-15 --- Evidence Review

**Actor:** Investigator / Authorized Operator

1.  User opens incident/event.
2.  Selects evidence.
3.  ARGUS validates permission.
4.  Evidence metadata and permitted media are displayed.
5.  Access is logged.

## UC-16 --- GIS Operational Awareness

**Actor:** Commander / Operator

1.  User opens GIS.
2.  ARGUS loads permitted layers.
3.  Cameras, sensors, events and incidents are displayed.
4.  User filters by area/type/status.
5.  Selecting a marker opens operational details.

## UC-17 --- Camera and Sensor Administration

**Actor:** Administrator

Includes registration, grouping, location, health configuration,
analytic enablement, sensor calibration metadata, maintenance and
disabling.

## UC-18 --- AI Model and Rule Administration

**Actor:** AI Administrator

Includes model registry, approved version selection, endpoint health,
class mapping, thresholds, rule activation, benchmark metadata and
rollback process.

## UC-19 --- Operational Analytics

**Actor:** Supervisor

1.  Supervisor selects period/area.
2.  ARGUS aggregates authorized operational metadata.
3.  Dashboard shows event/incident trends, response timing and source
    health.
4.  Supervisor exports an approved report if permitted.

## UC-20 --- Audit Review

**Actor:** Auditor

Auditor filters by user, incident, evidence, configuration or date and
reviews immutable/read-only audit records according to access policy.

## 4. Demonstration Use Case --- Operation Meskel

The controlled Addis Ababa Police demonstration combines UC-01, UC-04,
UC-10, UC-11, UC-12, UC-08, UC-09, UC-14 and UC-20 into one narrative:

``` text
Normal Monitoring
      |
Crowd Threshold
      |
Operator Review
      |
Human Verification
      |
Incident Creation
      |
Assignment / Monitoring
      |
Resolution
      |
Restricted Site Vision Event + RF Presence
      |
ARGUS Fusion
      |
Human Verification
      |
Historical Search + Audit Review
```
