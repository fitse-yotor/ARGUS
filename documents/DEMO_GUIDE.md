# Demonstrating ARGUS

## Prepare

Run the API, vision worker and frontend. Sign in with the local administrator credentials. Verify the worker is online; the detector reads DEGRADED / AWAITING INFERENCE until its first successful run. Create an Operator and Incident Controller in Administration for a role-based presentation if desired.

Bring authorized clips, preferably 15–60 seconds, 720p, stable viewpoint and daylight. No footage is supplied as operational demo data. The optional automated test fixture is clearly labeled and uses Ultralytics's bundled image.

| Scenario | Best input | Configure |
|---|---|---|
| Crowd | Elevated stable view of a walkway or public event, visibly separated people, arrivals/departures | Crowd polygon, person class, threshold suited to visible count; entrance counting line; waiting-zone dwell |
| Traffic | Fixed road view with cars/buses, visible movement across the frame and a stopping area | Traffic polygon or Lane zones; vehicle class; transverse counting line; No-Stopping Zone with a short appropriate threshold; road calibration for speed |
| Convoy | Short road clip with distinguishable visible vehicles and few camera cuts | Convoy mode, corridor polygon; pause and designate actual visible tracks; route and road calibration for distance and arrival |

Do not use distant compressed imagery expecting reliable small-object counts. For initial demonstration, select 5 inference FPS. A source 30-FPS video will retain its own timestamps and playback rate.

## Crowd-to-incident narrative

1. Upload; show the extracted metadata.
2. Choose Event / Crowd and draw a crowd polygon. For a short controlled demo choose a threshold the clip actually reaches.
3. Start analysis; leave for Overview to demonstrate the durable background job.
4. Return to completed playback. Show temporary IDs, current people and zone occupancy.
5. Click a Crowd Threshold marker; playback seeks to its exact recorded time.
6. Open Review. Compare the snapshot to the video, threshold, confidence where applicable and related events.
7. Enter an operator note and Verify. Create an incident.
8. Assign it to an enabled user. Record Responding, Monitoring, Resolved and Closed with notes.
9. Search by event type / video / incident. Open evidence and the audit log.
10. If the footage never crosses the threshold, explain that no event is expected; adjust the rule and start a new run. Do not substitute simulated counts.

## Traffic and convoy narrative

Use Traffic mode for vehicle counts and virtual-line IN/OUT. A stopped event requires actual small position displacement inside a No-Stopping Zone. Changing a dwell threshold alone does not establish stopped motion. Congestion uses the displayed configurable count heuristic.

To show speed, you need one real measurement on the ground: a lane width, the spacing of road markings, or a pair of landmarks whose separation you know. Pause, choose **Calibrate road**, click the four corners of that rectangle in order (near-left, near-right, far-right, far-left), and enter the width and length in metres. Draw the rectangle on the road surface itself, and keep it within the part of the view where vehicles are clearly resolved. Start a new analysis: boxes now carry km/h, lanes report vehicles per hour and average speed, and a Lane or Traffic Zone with a speed limit raises Speeding events. Say plainly that this is an estimate for situational awareness, not enforcement, and that it assumes the camera does not move.

Use Convoy mode, pause and click a visible vehicle box, then mark lead or convoy vehicle. With a route and a calibration drawn, the panel adds distance along the route, spacing between vehicles in metres, the time each needs to close its gap and an arrival estimate — these apply immediately, without re-running the analysis. On a live camera in Convoy mode, designate vehicles from the visible list instead; times are counted from the start of the camera session. Compare designation time to playback time, position, direction, nearby tracks and continuity. Traffic delay events are derived retrospectively from the saved observations after designation. Context is limited to the frame; no threat meaning is assigned to nearby vehicles.

## RF narrative

Open ARGUS Sense and read the simulation banner. Choose No Person → Enter Room → Walk → Stand → Sit → Fall → Exit Room. Show node quality, position, synthetic skeleton, motion trail, subcarrier amplitudes and the normalized observation. Repeat at a different speed. State explicitly that hardware, RF acquisition and model validation are future work.

## Reset

Cancel/wait for active jobs. Demo Control can clear incidents, clear events and their incidents, or reset the workflow and RF session. Video sources, jobs and audit remain. Select an uploaded sample and run a scenario again; broad preset geometry is editable before a subsequent analysis.
