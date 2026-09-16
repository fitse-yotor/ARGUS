import React, { useState, useEffect, useRef, useCallback } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity,
  Video,
  Radio,
  Map,
  Shield,
  Search,
  ChartColumn,
  Settings,
  LayoutDashboard,
  Folder,
  Play,
  Upload,
  LogOut,
  ChevronRight,
  TriangleAlert,
  Crosshair,
  Waypoints,
  Camera,
  ArrowUpRight,
  Users,
  Car,
  Menu,
  X,
} from "lucide-react";
import { api, apiPage, clock } from "./api";
import "./style.css";

const NAV = [
  ["Overview", LayoutDashboard],
  ["Operations", Video],
  ["Live Cameras", Camera],
  ["ARGUS Vision", Crosshair],
  ["Traffic Analysis", Waypoints],
  ["Convoy Analysis", Shield],
  ["ARGUS Sense", Radio],
  ["GIS Command", Map],
  ["Events & Alerts", TriangleAlert],
  ["Incidents", Folder],
  ["Investigation", Search],
  ["Evidence", Folder],
  ["Analytics", ChartColumn],
  ["Administration", Settings],
  ["Demo Control", Play],
];
const MODES = [
  "Detect & Annotate",
  "Event / Crowd",
  "Traffic",
  "Convoy",
  "General",
];
const ZONES = [
  "Monitoring Zone",
  "Restricted Zone",
  "Crowd Zone",
  "Traffic Zone",
  "Lane",
  "Entrance",
  "Exit",
  "Waiting Zone",
  "No-Stopping Zone",
  "Convoy Corridor",
];
const fmtDate = (v) => (v ? new Date(v).toLocaleString() : "");
// Speeds and distances exist only where an operator has drawn a road calibration.
const kmh = (v) => (v == null ? "—" : `${Math.round(v)} km/h`);
const metres = (v) => (v == null ? "—" : `${Math.round(v)} m`);
const seconds = (v) => (v == null ? "—" : `${v.toFixed(1)} s`);
const GEOMETRY_LABELS = {
  line: "Counting line",
  route: "Convoy route",
  calibration: "Road calibration",
};
function geometryLabel(g) {
  if (g.kind === "calibration")
    return `Road calibration · ${g.width_m} × ${g.length_m} m`;
  return `${GEOMETRY_LABELS[g.kind] || g.type} · ${g.object_class}${
    g.speed_limit_kmh ? ` · limit ${g.speed_limit_kmh} km/h` : ""
  }`;
}
const framePoint = (e, r) => [
  Math.min(1, Math.max(0, (e.clientX - r.left) / r.width)),
  Math.min(1, Math.max(0, (e.clientY - r.top) / r.height)),
];
function Badge({ value }) {
  return (
    <span
      className={
        "badge " +
        (/FAILED|CRITICAL|OFFLINE|CONGESTED/.test(value)
          ? "red"
          : /HIGH|REVIEW|DEGRADED|SIMULATED|HEAVY/.test(value)
            ? "amber"
            : /HEALTHY|COMPLETED|VERIFIED|RESOLVED/.test(value)
              ? "green"
              : "")
      }
    >
      {value}
    </span>
  );
}
function Empty({ children }) {
  return <div className="empty">{children}</div>;
}
function Panel({ title, action, children }) {
  return (
    <section className="panel">
      <div className="panel-head">
        <h3>{title}</h3>
        {action}
      </div>
      {children}
    </section>
  );
}
function Metrics({ items }) {
  const icons = [Video, Users, Car, TriangleAlert, Folder, Activity];
  return (
    <div className="metrics">
      {items.map(([name, value], index) => (
        <div className="metric" key={name}>
          <div className="metric-top">
            <span>{name}</span>
            {React.createElement(icons[index % icons.length], { size: 18 })}
          </div>
          <strong>{value ?? "—"}</strong>
        </div>
      ))}
    </div>
  );
}
function App() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [user, setUser] = useState(null),
    [checked, setChecked] = useState(false),
    [page, setPage] = useState("Overview"),
    [error, setError] = useState(""),
    [videos, setVideos] = useState([]),
    [jobs, setJobs] = useState([]),
    [health, setHealth] = useState({}),
    [selected, setSelected] = useState(""),
    [event, setEvent] = useState(null),
    [seek, setSeek] = useState(null),
    [cameraId, setCameraId] = useState(""),
    [revision, setRevision] = useState(0);
  const run = useCallback(async (fn) => {
    try {
      setError("");
      return await fn();
    } catch (e) {
      setError(e.message);
      return null;
    }
  }, []);
  const refresh = () => setRevision((v) => v + 1);
  useEffect(() => {
    api("/auth/me")
      .then(setUser)
      .catch(() => {})
      .finally(() => setChecked(true));
  }, []);
  useEffect(() => {
    if (!user) return;
    let live = true;
    const load = () =>
      Promise.all([api("/videos"), api("/jobs"), api("/health")])
        .then(([v, j, h]) => {
          if (live) {
            setVideos(v);
            setJobs(j);
            setHealth(h);
          }
        })
        .catch((e) => live && setError(e.message));
    load();
    const id = setInterval(load, 2500);
    return () => {
      live = false;
      clearInterval(id);
    };
  }, [user, revision]);
  const navigate = (p) => {
    setMenuOpen(false);
    setPage(p);
    setEvent(null);
  };
  const openVideo = (id, time = null, job = null) => {
    setSelected(id);
    setSeek(time === null ? null : { time, job, nonce: Date.now() });
    setPage("ARGUS Vision");
    setEvent(null);
  };
  const openCamera = (id) => {
    setCameraId(id);
    setPage("Live Cameras");
    setEvent(null);
  };
  if (!checked) return <div className="loading">Connecting to ARGUS…</div>;
  if (!user) return <Login onLogin={setUser} run={run} error={error} />;
  const can = (p) => user.permissions.includes(p);
  return (
    <div className={`shell ${menuOpen ? "menu-open" : ""}`}>
      {menuOpen && (
        <button
          className="nav-backdrop"
          aria-label="Close navigation"
          onClick={() => setMenuOpen(false)}
        />
      )}
      <aside>
        <div className="brand">
          <div className="brand-logo">
            <img src="/argus-logo.png" alt="ARGUS logo" />
          </div>
          <div>
            ARGUS<small>COMMAND PLATFORM</small>
          </div>
        </div>
        <div className="workspace-label">OPERATIONAL WORKSPACE</div>
        <nav aria-label="Main navigation">
          {NAV.filter(
            ([p]) => p !== "Administration" || can("admin") || can("audit"),
          ).map(([p, Icon]) => (
            <button
              key={p}
              title={p}
              aria-current={page === p ? "page" : undefined}
              className={page === p ? "active" : ""}
              onClick={() => navigate(p)}
            >
              <Icon size={17} />
              <span className="nav-text">{p}</span>
              {p === "Events & Alerts" && <span className="nav-dot" />}
            </button>
          ))}
        </nav>
        <div className="sidebar-footer">
          <span className="status-dot" /> LOCAL WORKSPACE{" "}
          <small>See. Sense. Understand. Respond.</small>
        </div>
      </aside>
      <main>
        <header>
          <button
            className="menu-toggle"
            aria-label={menuOpen ? "Close menu" : "Open menu"}
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen(!menuOpen)}
          >
            {menuOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
          <div className="breadcrumb">
            Workspace <ChevronRight size={13} />
            <span>{page}</span>
          </div>
          <div className="header-right">
            <span className="status-dot" /> {health.Backend || "CONNECTING"}
            <span className="divider" />
            <span className="user-avatar" aria-hidden="true">
              {user.username.slice(0, 2).toUpperCase()}
            </span>
            <span>
              {user.username} <small>{user.role}</small>
            </span>
            <button
              aria-label="Sign out"
              onClick={() =>
                run(async () => {
                  await api("/auth/logout", { method: "POST" });
                  setUser(null);
                })
              }
            >
              <LogOut size={17} />
            </button>
          </div>
        </header>
        <div className="content">
          <div className="page-heading">
            <div>
              <div className="eyebrow">
                ARGUS / {page === "ARGUS Sense" ? "SENSE" : "COMMAND"}
              </div>
              <h1>{event ? "Event review" : page}</h1>
              <p>
                {page === "ARGUS Sense"
                  ? "RF room simulation · controlled demonstration"
                  : page === "Overview"
                    ? "Your operations, connected. Your next decision, informed."
                    : "Multi-sensor situational awareness · local operations"}
              </p>
            </div>
            <div className="page-actions">
              <Badge value="LOCAL WORKSPACE" />
              <button
                className="primary"
                onClick={() => navigate("Operations")}
              >
                <Upload size={15} /> Upload video
              </button>
            </div>
          </div>
          {error && (
            <div role="alert" className="error">
              {error}
              <button onClick={() => setError("")}>Dismiss</button>
            </div>
          )}
          {event ? (
            <EventDetail
              id={event}
              can={can}
              run={run}
              refresh={refresh}
              openVideo={openVideo}
              openCamera={openCamera}
            />
          ) : page === "Overview" ? (
            <Overview
              navigate={navigate}
              revision={revision}
              health={health}
              openEvent={setEvent}
              openVideo={openVideo}
              videos={videos}
              run={run}
            />
          ) : [
              "Operations",
              "ARGUS Vision",
              "Traffic Analysis",
              "Convoy Analysis",
            ].includes(page) ? (
            <Vision
              {...{
                page,
                videos,
                jobs,
                selected,
                setSelected,
                seek,
                run,
                refresh,
                can,
              }}
              openEvent={setEvent}
            />
          ) : page === "Live Cameras" ? (
            <Live
              run={run}
              can={can}
              openEvent={setEvent}
              cameraId={cameraId}
              setCameraId={setCameraId}
            />
          ) : page === "ARGUS Sense" ? (
            <Sense run={run} can={can} />
          ) : ["Events & Alerts", "Investigation", "Evidence"].includes(
              page,
            ) ? (
            <Events
              key={page}
              page={page}
              videos={videos}
              openEvent={setEvent}
              openVideo={openVideo}
              openCamera={openCamera}
              run={run}
              revision={revision}
            />
          ) : page === "Incidents" ? (
            <Incidents run={run} can={can} openEvent={setEvent} />
          ) : page === "Analytics" ? (
            <Analytics run={run} revision={revision} />
          ) : page === "GIS Command" ? (
            <GIS videos={videos} run={run} openVideo={openVideo} openCamera={openCamera} />
          ) : page === "Administration" ? (
            <Admin {...{ run, can, health, videos, jobs }} />
          ) : page === "Demo Control" ? (
            <Demo {...{ run, refresh, can, videos, openVideo, navigate }} />
          ) : null}
        </div>
        <footer>
          ARGUS — See. Sense. Understand. Respond.
          <span>AI observations require human review.</span>
        </footer>
      </main>
    </div>
  );
}
function Login({ onLogin, run, error }) {
  const [username, setUsername] = useState("admin"),
    [password, setPassword] = useState("");
  return (
    <div className="login">
      <div className="login-brand">
        <div className="login-logo">
          <img
            src="/argus-logo.png"
            alt="ARGUS — AI-powered multi-sensor situational awareness platform"
          />
        </div>
        <div className="eyebrow">INTELLIGENCE. IN PERSPECTIVE.</div>
        <h1>
          A clearer picture.
          <br />A confident response.
        </h1>
        <p>
          Bring vision, sensor intelligence, and investigation together in one
          command workspace.
        </p>
        <div className="login-capabilities">
          <span>
            <Video size={16} /> Computer vision
          </span>
          <span>
            <Radio size={16} /> Sensor intelligence
          </span>
          <span>
            <Shield size={16} /> Human oversight
          </span>
        </div>
      </div>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          run(async () =>
            onLogin(
              await api("/auth/login", {
                method: "POST",
                body: { username, password },
              }),
            ),
          );
        }}
      >
        <div className="eyebrow">AUTHORIZED ACCESS</div>
        <div className="login-form-icon">
          <Shield size={24} />
        </div>
        <h2>Welcome to ARGUS</h2>
        <p>Sign in to your local operational environment.</p>
        <label>
          Username
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            required
          />
        </label>
        <label>
          Password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
          />
        </label>
        {error && <div className="error">{error}</div>}
        <button className="primary">
          Sign in <ChevronRight size={16} />
        </button>
        <small>
          Protected workspace · Access is managed by your administrator.
        </small>
      </form>
    </div>
  );
}
function Overview({
  revision,
  health,
  openEvent,
  openVideo,
  videos,
  run,
  navigate,
}) {
  const [data, setData] = useState(null);
  useEffect(() => {
    run(async () => setData(await api("/analytics")));
  }, [revision]);
  if (!data) return <Empty>Loading operational data…</Empty>;
  return (
    <>
      <section className="overview-hero">
        <div className="hero-copy">
          <div className="hero-kicker">
            <span className="status-dot" /> ARGUS COMMAND CENTER
          </div>
          <h2>
            See the whole picture.
            <br />
            <span>Act with confidence.</span>
          </h2>
          <p>
            One workspace for your video intelligence, sensor activity, and
            operational response.
          </p>
          <button onClick={() => navigate("Live Cameras")}>
            Open live cameras <ArrowUpRight size={17} />
          </button>
        </div>
        <div className="hero-brand">
          <img
            src="/argus-logo.png"
            alt="ARGUS — See. Sense. Understand. Respond."
          />
        </div>
      </section>
      <div className="section-heading">
        <h2>Operational snapshot</h2>
        <span>Recorded analysis & activity</span>
      </div>
      <Metrics
        items={[
          ["VIDEOS ANALYZED", data.videos_analyzed],
          ["PEOPLE OBSERVED", data.people_observed],
          ["VEHICLES OBSERVED", data.vehicles_observed],
          ["ACTIVE EVENTS", data.active_events],
          ["OPEN INCIDENTS", data.open_incidents],
          ["PROCESSING JOBS", data.processing_jobs],
        ]}
      />
      <div className="workspace-shortcuts">
        {[
          [
            "ARGUS Vision",
            "Analyze & understand",
            "Detection, tracking, and video intelligence",
            Crosshair,
          ],
          [
            "Investigation",
            "Find what matters",
            "Search observations and review evidence",
            Search,
          ],
          [
            "GIS Command",
            "Connect the context",
            "Explore sources in your map workspace",
            Map,
          ],
        ].map(([target, title, description, Icon]) => (
          <button key={target} onClick={() => navigate(target)}>
            <div className="shortcut-icon">
              <Icon size={21} />
            </div>
            <div>
              <strong>{title}</strong>
              <small>{description}</small>
            </div>
            <ArrowUpRight size={17} />
          </button>
        ))}
      </div>
      <div className="grid-two">
        <Panel
          title="Recent analysis"
          action={<span className="eyebrow">RECORDED VIDEO</span>}
        >
          {data.recent_analysis.length ? (
            data.recent_analysis.map((j) => (
              <button
                className="record"
                key={j.id}
                onClick={() => openVideo(j.video_id)}
              >
                <div className="record-icon">
                  <Video size={22} />
                </div>
                <div>
                  <strong>
                    {videos.find((v) => v.id === j.video_id)?.filename ||
                      j.video_id.slice(0, 8)}
                  </strong>
                  <small>
                    {j.mode} · {fmtDate(j.created_at)}
                  </small>
                  <progress value={j.progress} max="100" />
                </div>
                <Badge value={j.state} />
              </button>
            ))
          ) : (
            <Empty>
              Upload an authorized video to begin real detection and tracking.
            </Empty>
          )}
        </Panel>
        <Panel title="System readiness">
          {Object.entries(health)
            .filter(([k, v]) => typeof v === "string")
            .map(([k, v]) => (
              <div className="stat-row" key={k}>
                <span>{k}</span>
                <Badge value={v} />
              </div>
            ))}
        </Panel>
      </div>
      <Panel
        title="Recent events"
        action={<span className="eyebrow">HUMAN REVIEW REQUIRED</span>}
      >
        <EventTable events={data.recent_events} openEvent={openEvent} />
      </Panel>
    </>
  );
}
function EventTable({ events, openEvent }) {
  return events.length ? (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            <th>PRIORITY</th>
            <th>EVENT / RULE</th>
            <th>TRACK</th>
            <th>VIDEO TIME</th>
            <th>STATUS</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {events.map((e) => (
            <tr key={e.id}>
              <td>
                <Badge value={e.priority} />
              </td>
              <td>
                <strong>{e.type}</strong>
                <small>{e.zone || "Video-wide condition"}</small>
              </td>
              <td>{e.track_id || "—"}</td>
              <td>{clock(e.video_time)}</td>
              <td>
                <Badge value={e.status} />
              </td>
              <td>
                <button onClick={() => openEvent(e.id)}>
                  Review <ChevronRight size={13} />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  ) : (
    <Empty>No events match this view.</Empty>
  );
}
function Vision({
  page,
  videos,
  jobs,
  selected,
  setSelected,
  seek,
  run,
  refresh,
  can,
  openEvent,
}) {
  const [mode, setMode] = useState("Detect & Annotate"),
    [fps, setFps] = useState(10),
    [confidence, setConfidence] = useState(0.3),
    [congestion, setCongestion] = useState(12),
    [freeFlow, setFreeFlow] = useState(50),
    [uploading, setUploading] = useState(false),
    [jobId, setJobId] = useState(""),
    [geo, setGeo] = useState([]),
    [events, setEvents] = useState([]),
    [tracks, setTracks] = useState([]),
    [windowRows, setWindowRows] = useState([]),
    [time, setTime] = useState(0),
    [draw, setDraw] = useState(null),
    [points, setPoints] = useState([]),
    [draft, setDraft] = useState({
      name: "",
      type: "Crowd Zone",
      object_class: "all",
      threshold: 10,
      dwell_seconds: 30,
      stop_seconds: 10,
      severity: "MEDIUM",
      enabled: true,
      events: true,
      elevated_ratio: 0.8,
      critical_ratio: 1.25,
      speed_limit_kmh: 0,
      width_m: 3.5,
      length_m: 20,
    }),
    [editing, setEditing] = useState(null),
    [activeTrack, setActiveTrack] = useState(null),
    [overlay, setOverlay] = useState(true),
    [convoyContext, setConvoyContext] = useState(null),
    [annotatedView, setAnnotatedView] = useState(true),
    [heatmap, setHeatmap] = useState(false),
    [heatGroup, setHeatGroup] = useState("all"),
    [locked, setLocked] = useState(null),
    [lockPath, setLockPath] = useState(null),
    [lockInput, setLockInput] = useState(""),
    [imgsz, setImgsz] = useState(640),
    [classes, setClasses] = useState([]),
    [tiling, setTiling] = useState(false),
    [minBox, setMinBox] = useState(0),
    [savedNote, setSavedNote] = useState("");
  const player = useRef(null),
    lastWindow = useRef(-1),
    fileInput = useRef(null),
    dragging = useRef(null),
    suppressClick = useRef(false);
  const video = videos.find((v) => v.id === selected),
    videoJobs = jobs.filter((j) => j.video_id === selected),
    job = videoJobs.find((j) => j.id === jobId) || videoJobs[0];
  useEffect(() => {
    if (page === "Traffic Analysis") setMode("Traffic");
    else if (page === "Convoy Analysis") setMode("Convoy");
  }, [page]);
  useEffect(() => {
    if (!selected && videos[0]) setSelected(videos[0].id);
  }, [videos]);
  useEffect(() => {
    setJobId("");
    setTime(0);
    setWindowRows([]);
    lastWindow.current = -1;
    setPoints([]);
    setDraw(null);
    if (selected)
      run(async () => setGeo(await api(`/videos/${selected}/geometries`)));
  }, [selected]);
  useEffect(() => {
    if (seek) {
      setJobId(seek.job || "");
      setTime(seek.time);
      if (player.current) player.current.currentTime = seek.time;
    }
  }, [seek]);
  useEffect(() => {
    if (!job) {
      setEvents([]);
      setTracks([]);
      return;
    }
    let live = true;
    const load = () =>
      Promise.all([
        api(`/events?job_id=${job.id}`),
        api(`/jobs/${job.id}/tracks`),
      ])
        .then(([e, t]) => {
          if (live) {
            setEvents(e);
            setTracks(t);
          }
        })
        .catch((e) => {});
    load();
    const id = setInterval(load, 2500);
    return () => {
      live = false;
      clearInterval(id);
    };
  }, [job?.id]);
  useEffect(() => {
    if (job?.mode === "Convoy")
      api(`/jobs/${job.id}/convoy?video_time=${time}`)
        .then(setConvoyContext)
        .catch(() => {});
  }, [job?.id, Math.floor(time), tracks]);
  useEffect(() => {
    setLocked(null);
  }, [job?.id]);
  useEffect(() => {
    if (!job || !locked) {
      setLockPath(null);
      return;
    }
    let live = true;
    api(`/jobs/${job.id}/track-path?track_id=${locked}`)
      .then((p) => live && setLockPath(p))
      .catch((e) => {
        if (live) {
          setLocked(null);
          run(() => Promise.reject(e));
        }
      });
    return () => {
      live = false;
    };
  }, [job?.id, locked, job?.state]);
  const segment = Math.floor(time / 20);
  useEffect(() => {
    if (!job) return;
    let live = true;
    api(
      `/jobs/${job.id}/observations?start=${Math.max(0, segment * 20 - 1)}&end=${segment * 20 + 21}`,
    )
      .then((r) => live && setWindowRows(r))
      .catch(() => {});
    return () => {
      live = false;
    };
  }, [job?.id, segment, job?.frame]);
  const row = windowRows.filter((r) => r.time <= time + 0.03).at(-1),
    current = row && time - row.time < 1.5 ? row : null,
    stats = current?.analytics || job?.summary || {};
  // Locked box at the playhead, interpolated between sampled observations.
  const lockedBox = (() => {
    const path = lockPath?.path || [];
    let i = path.findIndex((p) => p.time > time);
    if (i === -1) i = path.length;
    const a = path[i - 1],
      b = path[i];
    if (!a || time - a.time > 1.5) return null;
    if (!b || b.time - a.time > 1.5) return a.box;
    const k = (time - a.time) / (b.time - a.time);
    return a.box.map((v, j) => v + (b.box[j] - v) * k);
  })();
  const seekTo = (t) => {
    if (player.current) {
      player.current.currentTime = t;
      player.current.pause();
    }
    setTime(t);
  };
  const upload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setUploading(true);
    await run(async () => {
      const body = new FormData();
      body.append("file", file);
      const v = await api("/videos", { method: "POST", body });
      setSelected(v.id);
      refresh();
    });
    setUploading(false);
    e.target.value = "";
  };
  const saveGeometry = () =>
    run(async () => {
      const data = { ...draft, kind: draw, points };
      await api(
        editing ? `/geometries/${editing}` : `/videos/${selected}/geometries`,
        { method: editing ? "PUT" : "POST", body: data },
      );
      setGeo(await api(`/videos/${selected}/geometries`));
      setDraw(null);
      setPoints([]);
      setEditing(null);
    });
  // Supervision boxes and zones are burned into the annotated video; drawing uses the clean source.
  const showAnnotated = annotatedView && job?.annotated_available && !draw;
  const convoyTracks = tracks.filter((t) => t.convoy_role),
    visibleConvoy = (current?.objects || []).filter((o) =>
      convoyTracks.some(
        (t) => t.track_id === o.track_id && time >= t.designated_at,
      ),
    );
  return (
    <>
      {page === "Tracking" && <p className="notice">Tracking follows every detected object through the video and shows how long each person or vehicle remains visible. Select a box to inspect its path.</p>}
      {page === "Convoy Analysis" && <p className="notice">Convoy analysis adds designated vehicle roles, route progress, spacing and traffic delay alerts. Select a vehicle box in a Convoy run to designate it.</p>}
      <div className="toolbar">
        <select
          aria-label="Video source"
          value={selected}
          onChange={(e) => setSelected(e.target.value)}
        >
          <option value="">Select uploaded video</option>
          {videos.map((v) => (
            <option key={v.id} value={v.id}>
              {v.filename}
            </option>
          ))}
        </select>
        <input
          ref={fileInput}
          type="file"
          accept="video/*,.mkv,.m4v,.mts,.m2ts,.ts,.flv,.wmv,.3gp,.mpg,.mpeg,.ogv"
          hidden
          onChange={upload}
        />
        {can("operate") && (
          <button
            className="primary"
            disabled={uploading}
            onClick={() => fileInput.current.click()}
          >
            <Upload size={16} />
            {uploading ? "Uploading and preparing video…" : "Upload video"}
          </button>
        )}
        <span className="muted">
          MP4, MOV, AVI, MKV, WEBM, M4V, MPG, 3GP, WMV, FLV, TS · up to 1 GB
        </span>
      </div>
      {!video ? (
        <Empty>
          Choose a video from your device. ARGUS validates the media before
          analysis.
        </Empty>
      ) : (
        <>
          <div className="source-info">
            <strong>{video.filename}</strong>
            <span>
              {video.metadata_json.width} × {video.metadata_json.height}
            </span>
            <span>{video.metadata_json.fps.toFixed(2)} FPS</span>
            <span>{clock(video.metadata_json.duration)}</span>
            <span>
              {(video.metadata_json.file_size / 1048576).toFixed(1)} MB
            </span>
          </div>
          <div className="analysis-layout">
            <div>
              <Panel
                title="Video analysis"
                action={
                  <div className="inline">
                    <label className="check">
                      <input
                        type="checkbox"
                        checked={overlay}
                        onChange={(e) => setOverlay(e.target.checked)}
                      />{" "}
                      Overlays
                    </label>
                    {job?.annotated_available && (
                      <>
                        <label className="check">
                          <input
                            type="checkbox"
                            checked={annotatedView}
                            onChange={(e) => setAnnotatedView(e.target.checked)}
                          />{" "}
                          Supervision annotated
                        </label>
                        <a
                          className="button-link"
                          href={`/api/jobs/${job.id}/annotated?download=true`}
                        >
                          Download annotated
                        </a>
                      </>
                    )}
                    {job?.heatmap_available && (
                      <>
                        <label className="check">
                          <input
                            type="checkbox"
                            checked={heatmap}
                            onChange={(e) => setHeatmap(e.target.checked)}
                          />{" "}
                          Heatmap
                        </label>
                        {heatmap && (
                          <select
                            aria-label="Heatmap objects"
                            value={heatGroup}
                            onChange={(e) => setHeatGroup(e.target.value)}
                          >
                            {["all", "person", "vehicle", "other"].map((g) => (
                              <option key={g}>{g}</option>
                            ))}
                          </select>
                        )}
                      </>
                    )}
                    <Badge value={job?.state || "READY"} />
                  </div>
                }
              >
                <div
                  className="video-stage"
                  style={{
                    aspectRatio: `${video.metadata_json.width}/${video.metadata_json.height}`,
                  }}
                >
                  <video
                    ref={player}
                    key={
                      selected +
                      !!video.playback +
                      (showAnnotated ? job.id : "source")
                    }
                    src={
                      showAnnotated
                        ? `/api/jobs/${job.id}/annotated`
                        : `/api/videos/${selected}/media`
                    }
                    controls
                    onTimeUpdate={(e) => setTime(e.target.currentTime)}
                    onLoadedMetadata={() => {
                      // Keeps position when switching between source and annotated video.
                      player.current.currentTime = time;
                    }}
                  />
                  {heatmap && job?.heatmap_available && (
                    <img
                      className="heatmap-layer"
                      alt=""
                      src={`/api/jobs/${job.id}/heatmap.png?group=${heatGroup}&v=${job.state}`}
                    />
                  )}
                  {overlay && (
                    <svg
                      className={"overlay " + (draw ? "drawing" : "")}
                      viewBox="0 0 1000 1000"
                      preserveAspectRatio="none"
                      onClick={(e) => {
                        if (!draw) return;
                        if (suppressClick.current) {
                          suppressClick.current = false;
                          return;
                        }
                        player.current.pause();
                        const r = e.currentTarget.getBoundingClientRect();
                        const limit =
                          draw === "line" ? 2 : draw === "calibration" ? 4 : 0;
                        setPoints((p) =>
                          limit && p.length >= limit
                            ? p
                            : [...p, framePoint(e, r)],
                        );
                      }}
                      onPointerMove={(e) => {
                        if (dragging.current === null) return;
                        // Capture now: pointerup may clear the ref before React runs the updater.
                        const index = dragging.current;
                        const moved = framePoint(
                          e,
                          e.currentTarget.getBoundingClientRect(),
                        );
                        setPoints((p) =>
                          p.map((q, i) => (i === index ? moved : q)),
                        );
                      }}
                      onPointerUp={() => (dragging.current = null)}
                      onPointerLeave={() => (dragging.current = null)}
                    >
                      {geo
                        .filter((g) => g.enabled && !showAnnotated)
                        .map((g) =>
                          g.kind === "line" || g.kind === "route" ? (
                            <polyline
                              key={g.id}
                              points={g.points
                                .map((p) => p.map((v) => v * 1000).join(","))
                                .join(" ")}
                              className={
                                g.kind === "route" ? "route-line" : "zone-line"
                              }
                            />
                          ) : (
                            <polygon
                              key={g.id}
                              points={g.points
                                .map((p) => p.map((v) => v * 1000).join(","))
                                .join(" ")}
                              className={
                                g.kind === "calibration"
                                  ? "calibration-polygon"
                                  : "zone-polygon"
                              }
                            />
                          ),
                        )}
                      {(current?.objects || []).map((o) => {
                        const [x, y, x2, y2] = o.box;
                        const cv = convoyTracks.some(
                          (t) =>
                            t.track_id === o.track_id &&
                            time >= t.designated_at,
                        );
                        return (
                          <g
                            key={o.track_id}
                            className={
                              cv
                                ? "convoy-box"
                                : showAnnotated
                                  ? "object-box hit-only"
                                  : "object-box"
                            }
                            style={{
                              pointerEvents: draw ? "none" : "auto",
                              cursor: "pointer",
                            }}
                            onClick={() => {
                              if (job?.mode === "Convoy") {
                                player.current.pause();
                                setActiveTrack(o);
                              } else setLocked(o.track_id);
                            }}
                          >
                            <rect
                              x={x * 1000}
                              y={y * 1000}
                              width={(x2 - x) * 1000}
                              height={(y2 - y) * 1000}
                            />
                            <text
                              x={x * 1000 + 3}
                              y={Math.max(18, y * 1000 - 8)}
                            >
                              {o.track_id} · {o.object_class.toUpperCase()} ·{" "}
                              {Math.round(o.confidence * 100)}%
                              {o.object_class === "person" && ` · ${clock(o.observed_seconds ?? o.duration)} observed`}
                              {o.speed_kmh != null && ` · ${kmh(o.speed_kmh)}`}
                              {cv ? " · CONVOY" : ""}
                            </text>
                          </g>
                        );
                      })}
                      {locked && lockPath && (
                        <>
                          {lockedBox && (
                            <path
                              className="lock-dim"
                              fillRule="evenodd"
                              d={`M0 0H1000V1000H0Z M${lockedBox[0] * 1000} ${lockedBox[1] * 1000}H${lockedBox[2] * 1000}V${lockedBox[3] * 1000}H${lockedBox[0] * 1000}Z`}
                            />
                          )}
                          <polyline
                            className="lock-path"
                            points={lockPath.path
                              .filter((p) => p.time <= time)
                              .map(
                                (p) =>
                                  `${p.position[0] * 1000},${p.position[1] * 1000}`,
                              )
                              .join(" ")}
                          />
                          {lockedBox && (
                            <g className="locked-box">
                              <rect
                                x={lockedBox[0] * 1000}
                                y={lockedBox[1] * 1000}
                                width={(lockedBox[2] - lockedBox[0]) * 1000}
                                height={(lockedBox[3] - lockedBox[1]) * 1000}
                              />
                              <text
                                x={lockedBox[0] * 1000 + 3}
                                y={Math.max(18, lockedBox[1] * 1000 - 8)}
                              >
                                LOCKED {locked}
                              </text>
                            </g>
                          )}
                        </>
                      )}
                      {points.length > 0 && (
                        <polyline
                          className="drawing-line"
                          points={points
                            .map((p) => p.map((v) => v * 1000).join(","))
                            .join(" ")}
                        />
                      )}
                      {draw &&
                        points.map((p, i) => (
                          <ellipse
                            key={i}
                            className="vertex-handle"
                            cx={p[0] * 1000}
                            cy={p[1] * 1000}
                            rx="9"
                            ry={
                              (9 * video.metadata_json.width) /
                              video.metadata_json.height
                            }
                            onPointerDown={(e) => {
                              e.stopPropagation();
                              // Keep receiving moves if the pointer leaves the overlay; points clamp to the frame.
                              e.currentTarget.ownerSVGElement.setPointerCapture(
                                e.pointerId,
                              );
                              dragging.current = i;
                              suppressClick.current = true;
                            }}
                          >
                            <title>Drag to move point {i + 1}</title>
                          </ellipse>
                        ))}
                    </svg>
                  )}
                </div>
                <div className="timeline">
                  <div className="timeline-track" />
                  <span>00:00</span>
                  <span>{clock(video.metadata_json.duration)}</span>
                  {events.map((e) => (
                    <button
                      key={e.id}
                      title={`${clock(e.video_time)} ${e.type}`}
                      style={{
                        left: `${Math.min(98, (e.video_time / video.metadata_json.duration) * 100)}%`,
                      }}
                      onClick={() => seekTo(e.video_time)}
                      aria-label={`Seek to ${e.type} at ${clock(e.video_time)}`}
                    />
                  ))}
                </div>
                <div className="video-tools">
                  <span>
                    {clock(time)} / {clock(video.metadata_json.duration)}
                  </span>
                  {job?.state === "COMPLETED" && (
                    <>
                      {savedNote && <span className="muted">{savedNote}</span>}
                      {can("operate") && (
                        <button
                          onClick={() =>
                            run(async () => {
                              player.current.pause();
                              const s = await api("/saved-detections", {
                                method: "POST",
                                body: {
                                  job_id: job.id,
                                  video_time: time,
                                  classes: classes.length ? classes : null,
                                },
                              });
                              setSavedNote(
                                `Saved ${s.detections.length} detections at ${clock(s.video_time)}`,
                              );
                            })
                          }
                        >
                          Save detections
                        </button>
                      )}
                      <a
                        className="button-link"
                        href={`/api/jobs/${job.id}/detections?format=csv${classes.length ? `&classes=${encodeURIComponent(classes.join(","))}` : ""}`}
                      >
                        Export CSV
                      </a>
                      <a
                        className="button-link"
                        href={`/api/jobs/${job.id}/detections?format=json${classes.length ? `&classes=${encodeURIComponent(classes.join(","))}` : ""}`}
                      >
                        JSON
                      </a>
                    </>
                  )}
                  {can("configure") && (
                    <>
                      <button
                        onClick={() => {
                          player.current.pause();
                          setDraw("zone");
                          setPoints([]);
                          setEditing(null);
                          setDraft((d) => ({
                            ...d,
                            name: `Zone ${geo.length + 1}`,
                          }));
                        }}
                      >
                        Draw zone
                      </button>
                      <button
                        onClick={() => {
                          player.current.pause();
                          setDraw("line");
                          setPoints([]);
                          setEditing(null);
                          setDraft((d) => ({
                            ...d,
                            name: `Line ${geo.length + 1}`,
                          }));
                        }}
                      >
                        Draw line
                      </button>
                      {(page === "Convoy Analysis" ||
                        job?.mode === "Convoy") && (
                        <button
                          onClick={() => {
                            player.current.pause();
                            setDraw("route");
                            setPoints([]);
                            setEditing(null);
                            setDraft((d) => ({ ...d, name: "Convoy route" }));
                          }}
                        >
                          Draw route
                        </button>
                      )}
                      <button
                        onClick={() => {
                          player.current.pause();
                          const existing = geo.find(
                            (g) => g.kind === "calibration",
                          );
                          setDraw("calibration");
                          // One calibration per view, so the button edits the existing one.
                          setPoints(existing ? existing.points : []);
                          setEditing(existing ? existing.id : null);
                          setDraft((d) => ({
                            ...d,
                            ...(existing || {
                              name: "Road calibration",
                              width_m: 3.5,
                              length_m: 20,
                            }),
                          }));
                        }}
                      >
                        {geo.some((g) => g.kind === "calibration")
                          ? "Edit road calibration"
                          : "Calibrate road"}
                      </button>
                    </>
                  )}
                </div>
              </Panel>
              {draw && (
                <Panel
                  title={editing ? "Edit analytics geometry" : `Draw ${draw}`}
                >
                  <div className="form-grid">
                    <label>
                      Name
                      <input
                        value={draft.name}
                        onChange={(e) =>
                          setDraft({ ...draft, name: e.target.value })
                        }
                      />
                    </label>
                    {draw === "calibration" && (
                      <>
                        <label>
                          Measured width, point 1 → 2 (m)
                          <input
                            type="number"
                            min="0.5"
                            step="0.1"
                            value={draft.width_m ?? 3.5}
                            onChange={(e) =>
                              setDraft({ ...draft, width_m: +e.target.value })
                            }
                          />
                        </label>
                        <label>
                          Measured length, point 2 → 3 (m)
                          <input
                            type="number"
                            min="0.5"
                            step="0.5"
                            value={draft.length_m ?? 20}
                            onChange={(e) =>
                              setDraft({ ...draft, length_m: +e.target.value })
                            }
                          />
                        </label>
                      </>
                    )}
                    {draw !== "route" && draw !== "calibration" && (
                      <>
                        <label>
                          Type
                          <select
                            value={draft.type}
                            onChange={(e) =>
                              setDraft({ ...draft, type: e.target.value })
                            }
                          >
                            {ZONES.map((z) => (
                              <option key={z}>{z}</option>
                            ))}
                          </select>
                        </label>
                        <label>
                          Object class
                          <select
                            value={draft.object_class}
                            onChange={(e) =>
                              setDraft({
                                ...draft,
                                object_class: e.target.value,
                              })
                            }
                          >
                            {[
                              "all",
                              "person",
                              "vehicle",
                              "car",
                              "bus",
                              "truck",
                              "motorcycle",
                            ].map((z) => (
                              <option key={z}>{z}</option>
                            ))}
                          </select>
                        </label>
                        <label>
                          Occupancy threshold
                          <input
                            type="number"
                            min="1"
                            value={draft.threshold}
                            onChange={(e) =>
                              setDraft({ ...draft, threshold: +e.target.value })
                            }
                          />
                        </label>
                        <label>
                          Dwell seconds
                          <input
                            type="number"
                            min="0"
                            value={draft.dwell_seconds}
                            onChange={(e) =>
                              setDraft({
                                ...draft,
                                dwell_seconds: +e.target.value,
                              })
                            }
                          />
                        </label>
                        <label>
                          Stop seconds
                          <input
                            type="number"
                            min="1"
                            value={draft.stop_seconds}
                            onChange={(e) =>
                              setDraft({
                                ...draft,
                                stop_seconds: +e.target.value,
                              })
                            }
                          />
                        </label>
                        <label>
                          Severity
                          <select
                            value={draft.severity}
                            onChange={(e) =>
                              setDraft({ ...draft, severity: e.target.value })
                            }
                          >
                            {["LOW", "MEDIUM", "HIGH", "CRITICAL"].map((s) => (
                              <option key={s}>{s}</option>
                            ))}
                          </select>
                        </label>
                        <label className="check">
                          <input
                            type="checkbox"
                            checked={draft.events}
                            onChange={(e) =>
                              setDraft({ ...draft, events: e.target.checked })
                            }
                          />{" "}
                          Line events enabled
                        </label>
                        {draw === "zone" && (
                          <>
                            <label>
                              Speed limit km/h (0 = no speed rule)
                              <input
                                type="number"
                                min="0"
                                max="400"
                                value={draft.speed_limit_kmh ?? 0}
                                onChange={(e) =>
                                  setDraft({
                                    ...draft,
                                    speed_limit_kmh: +e.target.value,
                                  })
                                }
                              />
                            </label>
                            <label>
                              Elevated at × threshold
                              <input
                                type="number"
                                min="0.05"
                                max="0.95"
                                step="0.05"
                                value={draft.elevated_ratio ?? 0.8}
                                onChange={(e) =>
                                  setDraft({
                                    ...draft,
                                    elevated_ratio: +e.target.value,
                                  })
                                }
                              />
                            </label>
                            <label>
                              Critical at × threshold
                              <input
                                type="number"
                                min="1.05"
                                max="10"
                                step="0.05"
                                value={draft.critical_ratio ?? 1.25}
                                onChange={(e) =>
                                  setDraft({
                                    ...draft,
                                    critical_ratio: +e.target.value,
                                  })
                                }
                              />
                            </label>
                          </>
                        )}
                      </>
                    )}
                  </div>
                  <div className="toolbar">
                    <span>
                      {draw === "calibration" ? (
                        <>
                          Click the four corners of a road rectangle you have
                          measured, in order: near-left, near-right, far-right,
                          far-left. Point 1 → 2 spans the width, point 2 → 3 the
                          length.
                        </>
                      ) : (
                        <>
                          Click{" "}
                          {draw === "line"
                            ? "two endpoints"
                            : draw === "route"
                              ? "at least two points along the convoy path"
                              : "at least three corners"}{" "}
                          on the paused frame, then drag points to adjust.
                        </>
                      )}{" "}
                      {points.length} points.
                    </span>
                    <button onClick={() => setPoints([])}>Redraw</button>
                    <button onClick={() => setPoints((p) => p.slice(0, -1))}>
                      Undo point
                    </button>
                    <button className="primary" onClick={saveGeometry}>
                      Save
                    </button>
                    <button onClick={() => setDraw(null)}>Cancel</button>
                  </div>
                  <p className="notice">
                    {draw === "route"
                      ? "Routes measure convoy progress in frame coordinates and apply immediately; they do not change detections or events."
                      : draw === "calibration"
                        ? "Calibration maps this road surface to metres. Convoy distance, spacing and arrival use it immediately; speed on tracks, lane flow and speed rules need a new analysis run. It assumes a fixed camera and a flat road, and is least accurate far from the camera."
                        : "Start a new analysis to apply changed rules. Previous events retain their original rules."}
                  </p>
                </Panel>
              )}
              <Metrics
                items={[
                  ["VISIBLE PEOPLE", stats.people],
                  ["VISIBLE VEHICLES", stats.vehicles],
                  [
                    "TOTAL TRACKS",
                    stats.total_objects ??
                      (stats.total_people || 0) + (stats.total_vehicles || 0),
                  ],
                  ["STOPPED VEHICLES", stats.stopped_vehicles],
                ]}
              />
              {Object.keys(job?.summary?.total_classes || {}).length > 0 && (
                <Panel
                  title="Detected objects"
                  action={<span className="eyebrow">TEMPORARY TRACKS</span>}
                >
                  <div className="table-scroll">
                    <table>
                      <thead>
                        <tr>
                          <th>CLASS</th>
                          <th>VISIBLE NOW</th>
                          <th>TRACKS IN VIDEO</th>
                        </tr>
                      </thead>
                      <tbody>
                        {Object.entries(job.summary.total_classes)
                          .sort((a, b) => b[1] - a[1])
                          .map(([name, total]) => (
                            <tr key={name}>
                              <td>{name}</td>
                              <td>{stats.classes?.[name] || 0}</td>
                              <td>{total}</td>
                            </tr>
                          ))}
                      </tbody>
                    </table>
                  </div>
                </Panel>
              )}
              {(stats.zones || []).length > 0 && (
                <Panel title="Zone & line measurements">
                  {stats.zones.map((z) => (
                    <div className="zone-result" key={z.id}>
                      <strong>{z.name}</strong>
                      {z.kind === "line" ? (
                        <span>
                          IN {z.IN} · OUT {z.OUT} · TOTAL {z.TOTAL}
                          {z.flow_per_hour ? ` · ${z.flow_per_hour}/h` : ""}
                          {z.average_speed_kmh != null &&
                            ` · ${kmh(z.average_speed_kmh)}`}
                          {Object.entries(z.by_class || {})
                            .map(([c, v]) => ` · ${c} ${v.IN}/${v.OUT}`)
                            .join("")}
                        </span>
                      ) : (
                        <>
                          <span>
                            Occupancy {z.occupancy} / {z.threshold} · Max{" "}
                            {z.maximum}
                          </span>
                          <span>
                            Entry {z.entry_rate}/min · Exit {z.exit_rate}/min
                            {z.flow_per_hour ? ` · ${z.flow_per_hour}/h` : ""}
                          </span>
                          {z.average_speed_kmh != null && (
                            <span>
                              Average {kmh(z.average_speed_kmh)}
                              {z.speed_limit_kmh
                                ? ` · limit ${z.speed_limit_kmh} km/h`
                                : ""}
                            </span>
                          )}
                          <span>
                            {Object.entries(z.classes || {})
                              .map(([c, n]) => `${c} ${n}`)
                              .join(" · ") || "Empty"}
                          </span>
                          <Badge value={z.status} />
                        </>
                      )}
                    </div>
                  ))}
                </Panel>
              )}
              <Panel title="Event timeline">
                <EventTable events={events} openEvent={openEvent} />
              </Panel>
            </div>
            <div>
              <Panel title="Analysis controls">
                <div className="stack">
                  <label>
                    Analysis mode
                    <select
                      value={mode}
                      onChange={(e) => setMode(e.target.value)}
                    >
                      {MODES.map((m) => (
                        <option key={m}>{m}</option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Processing FPS
                    <input
                      type="number"
                      min="1"
                      max="30"
                      value={fps}
                      onChange={(e) => setFps(+e.target.value)}
                    />
                  </label>
                  <label>
                    Detection confidence
                    <input
                      type="number"
                      min=".05"
                      max=".95"
                      step=".05"
                      value={confidence}
                      onChange={(e) => setConfidence(+e.target.value)}
                    />
                  </label>
                  <label>
                    Detection input size
                    <select
                      value={imgsz}
                      onChange={(e) => setImgsz(+e.target.value)}
                    >
                      {[640, 960, 1280].map((s) => (
                        <option key={s} value={s}>
                          {s}px{s > 640 ? " · small objects, slower" : ""}
                        </option>
                      ))}
                    </select>
                  </label>
                  <DetectionFilterFields
                    value={{ classes, tiling, min_box: minBox }}
                    onChange={(v) => {
                      setClasses(v.classes || []);
                      setTiling(v.tiling);
                      setMinBox(v.min_box);
                    }}
                  />
                  <label>
                    Congestion vehicle threshold
                    <input
                      type="number"
                      min="1"
                      value={congestion}
                      onChange={(e) => setCongestion(+e.target.value)}
                    />
                  </label>
                  <label>
                    Free-flow speed km/h
                    <input
                      type="number"
                      min="5"
                      max="200"
                      value={freeFlow}
                      onChange={(e) => setFreeFlow(+e.target.value)}
                    />
                    <small className="muted">
                      Used with a road calibration: traffic states fall as
                      measured speed drops below this.
                    </small>
                  </label>
                  {can("operate") && (
                    <button
                      className="primary"
                      disabled={videoJobs.some((j) =>
                        ["QUEUED", "PROCESSING"].includes(j.state),
                      )}
                      onClick={() =>
                        run(async () => {
                          const j = await api(`/videos/${selected}/jobs`, {
                            method: "POST",
                            body: {
                              mode,
                              fps,
                              confidence,
                              congestion_count: congestion,
                              free_flow_kmh: freeFlow,
                              imgsz,
                              classes: classes.length ? classes : null,
                              tiling,
                              min_box: minBox,
                            },
                          });
                          setJobId(j.id);
                          refresh();
                        })
                      }
                    >
                      <Play size={16} /> Start analysis
                    </button>
                  )}
                  {job && (
                    <>
                      <label>
                        Analysis run
                        <select
                          value={job.id}
                          onChange={(e) => {
                            setJobId(e.target.value);
                            setWindowRows([]);
                          }}
                        >
                          {videoJobs.map((j) => (
                            <option key={j.id} value={j.id}>
                              {j.mode} · {j.state} · {j.id.slice(0, 6)}
                            </option>
                          ))}
                        </select>
                      </label>
                      <progress value={job.progress} max="100" />
                      <strong>
                        {job.progress.toFixed(1)}% · {job.state}
                      </strong>
                      <small>
                        Frames {job.frame.toLocaleString()} /{" "}
                        {video.metadata_json.frame_count.toLocaleString()}
                        <br />
                        {job.processing_fps.toFixed(1)} processing FPS ·{" "}
                        {clock(job.elapsed)} elapsed
                      </small>
                      {job.progress > 0 && job.progress < 100 && (
                        <small>
                          Estimated remaining{" "}
                          {clock(job.elapsed * (100 / job.progress - 1))}
                        </small>
                      )}
                      {job.error && <div className="error">{job.error}</div>}
                      {can("operate") &&
                        ["QUEUED", "PROCESSING"].includes(job.state) && (
                          <button
                            onClick={() =>
                              run(async () => {
                                await api(`/jobs/${job.id}/cancel`, {
                                  method: "POST",
                                });
                                refresh();
                              })
                            }
                          >
                            Cancel analysis
                          </button>
                        )}
                    </>
                  )}
                </div>
              </Panel>
              {job && (
                <Panel
                  title="Lock tracking"
                  action={
                    locked && (
                      <button onClick={() => setLocked(null)}>Unlock</button>
                    )
                  }
                >
                  <div className="stack">
                    {locked ? (
                      <LockDetails
                        locked={locked}
                        path={lockPath}
                        time={time}
                        box={lockedBox}
                        player={player}
                        seekTo={seekTo}
                      />
                    ) : (
                      <>
                        <p>
                          Click a box on the video, pick a visible track, or
                          enter a track ID to lock onto one object.
                        </p>
                        <form
                          className="inline"
                          onSubmit={(e) => {
                            e.preventDefault();
                            const m = lockInput
                              .trim()
                              .toUpperCase()
                              .match(/^([POV])-?(\d{1,4})$/);
                            if (m)
                              setLocked(`${m[1]}-${m[2].padStart(4, "0")}`);
                          }}
                        >
                          <input
                            aria-label="Track ID to lock"
                            placeholder="P-0003"
                            value={lockInput}
                            onChange={(e) => setLockInput(e.target.value)}
                          />
                          <button>Lock</button>
                        </form>
                        <div className="chip-row">
                          {(current?.objects || []).map((o) => (
                            <button
                              key={o.track_id}
                              onClick={() => setLocked(o.track_id)}
                            >
                              {o.track_id} · {o.object_class}
                            </button>
                          ))}
                        </div>
                      </>
                    )}
                  </div>
                </Panel>
              )}
              <Panel title="Configured zones & lines">
                {geo.length ? (
                  geo.map((g) => (
                    <div className="geometry-item" key={g.id}>
                      <strong>{g.name}</strong>
                      <small>{geometryLabel(g)}</small>
                      {can("configure") && (
                        <div className="inline">
                          <button
                            onClick={() => {
                              setEditing(g.id);
                              setDraft(g);
                              setPoints(g.points);
                              setDraw(g.kind);
                              player.current.pause();
                            }}
                          >
                            Edit
                          </button>
                          <button
                            onClick={() =>
                              run(async () => {
                                await api(`/geometries/${g.id}`, {
                                  method: "PUT",
                                  body: { ...g, enabled: !g.enabled },
                                });
                                setGeo(
                                  await api(`/videos/${selected}/geometries`),
                                );
                              })
                            }
                          >
                            {g.enabled ? "Disable" : "Enable"}
                          </button>
                          <button
                            onClick={() =>
                              run(async () => {
                                await api(`/geometries/${g.id}`, {
                                  method: "DELETE",
                                });
                                setGeo(
                                  await api(`/videos/${selected}/geometries`),
                                );
                              })
                            }
                          >
                            Delete
                          </button>
                        </div>
                      )}
                    </div>
                  ))
                ) : (
                  <Empty>
                    Pause the video and draw a zone or counting line.
                  </Empty>
                )}
              </Panel>
              {(job?.mode === "Traffic" || job?.mode === "Convoy") && (
                <Panel title="Traffic context">
                  <TrafficPanel stats={stats} />
                </Panel>
              )}
              {job?.mode === "Convoy" && (
                <Panel title="Convoy status">
                  <div className="stack">
                    <p>
                      Pause and click a visible vehicle box to designate it.
                    </p>
                    <span>Designated vehicles: {convoyTracks.length}</span>
                    <span>
                      Route progress:{" "}
                      {convoyContext?.route_progress != null
                        ? `${convoyContext.route_progress}% · ${convoyContext.route_progress_track}`
                        : "Not measurable"}
                    </span>
                    <small>{convoyContext?.route_progress_note}</small>
                    <ConvoyPhysical
                      physical={convoyContext?.physical}
                      arrival={
                        convoyContext?.arrival_video_time != null
                          ? `at ${clock(convoyContext.arrival_video_time)}`
                          : null
                      }
                    />
                    {convoyContext?.vehicles.map((v) => (
                      <div key={v.track_id}>
                        <strong>
                          {v.track_id} ·{" "}
                          {v.observable ? "VISIBLE" : "NOT OBSERVABLE"}
                        </strong>
                        <small>
                          Continuity {v.continuity}%
                          {v.speed_kmh != null && ` · ${kmh(v.speed_kmh)}`}
                          {v.position &&
                            ` · Position ${v.position.map((n) => n.toFixed(3)).join(", ")}`}
                          <br />
                          {v.direction || "—"} · {clock(v.tracking_duration)}{" "}
                          since designation
                          <br />
                          Nearby tracks: {v.nearby_tracks?.join(", ") || "None"}
                          {v.route && (
                            <>
                              <br />
                              {v.route.route}:{" "}
                              {v.route.on_route
                                ? `${v.route.progress}%`
                                : "outside route tolerance"}
                            </>
                          )}
                        </small>
                      </div>
                    ))}
                    {convoyContext?.timeline?.length > 0 && (
                      <div className="convoy-timeline">
                        <strong>Operational timeline</strong>
                        {convoyContext.timeline.map((e, i) => (
                          <button key={i} onClick={() => seekTo(e.time)}>
                            <span>{clock(e.time)}</span>
                            {e.text}
                          </button>
                        ))}
                      </div>
                    )}
                    <span>Currently visible: {visibleConvoy.length}</span>
                    <span>
                      Other visible vehicles:{" "}
                      {Math.max(
                        0,
                        (stats.vehicles || 0) - visibleConvoy.length,
                      )}
                    </span>
                    {convoyTracks.map((t) => (
                      <div key={t.id}>
                        <strong>
                          {t.track_id} · {t.convoy_role}
                        </strong>
                        <small>
                          From {clock(t.designated_at)} · {t.data.direction}
                          <br />
                          Observed {clock(t.data.duration)} · {t.data.state}
                        </small>
                      </div>
                    ))}
                    {activeTrack && can("operate") && (
                      <>
                        <strong>
                          {activeTrack.track_id} · {activeTrack.direction}
                        </strong>
                        {["Convoy Lead", "Convoy Vehicle"].map((role) => (
                          <button
                            key={role}
                            onClick={() =>
                              run(async () => {
                                const tr = tracks.find(
                                  (t) => t.track_id === activeTrack.track_id,
                                );
                                if (!tr)
                                  throw Error(
                                    "Track is still saving; try again shortly",
                                  );
                                await api(`/tracks/${tr.id}/convoy`, {
                                  method: "POST",
                                  body: { role, video_time: time },
                                });
                                setTracks(await api(`/jobs/${job.id}/tracks`));
                                setActiveTrack(null);
                              })
                            }
                          >
                            Mark as {role}
                          </button>
                        ))}
                      </>
                    )}
                  </div>
                </Panel>
              )}
            </div>
          </div>
        </>
      )}
    </>
  );
}
const PAGE_SIZE = 50;
const COCO_CLASSES = [
  "person",
  "bicycle",
  "car",
  "motorcycle",
  "airplane",
  "bus",
  "train",
  "truck",
  "boat",
  "traffic light",
  "fire hydrant",
  "stop sign",
  "parking meter",
  "bench",
  "bird",
  "cat",
  "dog",
  "horse",
  "sheep",
  "cow",
  "elephant",
  "bear",
  "zebra",
  "giraffe",
  "backpack",
  "umbrella",
  "handbag",
  "tie",
  "suitcase",
  "frisbee",
  "skis",
  "snowboard",
  "sports ball",
  "kite",
  "baseball bat",
  "baseball glove",
  "skateboard",
  "surfboard",
  "tennis racket",
  "bottle",
  "wine glass",
  "cup",
  "fork",
  "knife",
  "spoon",
  "bowl",
  "banana",
  "apple",
  "sandwich",
  "orange",
  "broccoli",
  "carrot",
  "hot dog",
  "pizza",
  "donut",
  "cake",
  "chair",
  "couch",
  "potted plant",
  "bed",
  "dining table",
  "toilet",
  "tv",
  "laptop",
  "mouse",
  "remote",
  "keyboard",
  "cell phone",
  "microwave",
  "oven",
  "toaster",
  "sink",
  "refrigerator",
  "book",
  "clock",
  "vase",
  "scissors",
  "teddy bear",
  "hair drier",
  "toothbrush",
];
const QUICK_CLASSES = [
  "person",
  "vehicle",
  "car",
  "bus",
  "truck",
  "motorcycle",
  "bicycle",
  "boat",
];
function DetectionFilterFields({ value, onChange }) {
  const classes = value.classes || [];
  const set = (patch) => onChange({ ...value, classes, ...patch });
  const toggle = (c) =>
    set({
      classes: classes.includes(c)
        ? classes.filter((x) => x !== c)
        : [...classes, c],
    });
  return (
    <div className="stack detection-filters">
      <span className="field-label">
        Detect only {classes.length ? "" : "· all classes allowed by the mode"}
      </span>
      <div className="chip-row">
        {QUICK_CLASSES.map((c) => (
          <button
            type="button"
            key={c}
            className={classes.includes(c) ? "selected" : ""}
            onClick={() => toggle(c)}
          >
            {c}
          </button>
        ))}
        {classes
          .filter((c) => !QUICK_CLASSES.includes(c))
          .map((c) => (
            <button
              type="button"
              key={c}
              className="selected"
              onClick={() => toggle(c)}
            >
              {c} ×
            </button>
          ))}
      </div>
      <select
        aria-label="Add class filter"
        value=""
        onChange={(e) => e.target.value && toggle(e.target.value)}
      >
        <option value="">Add another class…</option>
        {COCO_CLASSES.filter((c) => !classes.includes(c)).map((c) => (
          <option key={c}>{c}</option>
        ))}
      </select>
      <label className="check">
        <input
          type="checkbox"
          checked={!!value.tiling}
          onChange={(e) => set({ tiling: e.target.checked })}
        />{" "}
        Detect small objects (tiled, about 4× slower)
      </label>
      <label>
        Ignore boxes smaller than (px)
        <input
          type="number"
          min="0"
          max="500"
          value={value.min_box || 0}
          onChange={(e) => set({ min_box: +e.target.value })}
        />
      </label>
    </div>
  );
}
function SavedDetections({ run, openVideo, openCamera }) {
  const [items, setItems] = useState([]);
  const load = () => run(async () => setItems(await api("/saved-detections")));
  useEffect(() => {
    load();
  }, []);
  return (
    <Panel
      title={`Saved detections (${items.length})`}
      action={<button onClick={load}>Refresh</button>}
    >
      {items.length ? (
        <div className="evidence-grid">
          {items.map((s) => (
            <div className="saved-card" key={s.id}>
              <img
                src={s.image_url}
                alt={`Saved detections from ${s.source}`}
              />
              <strong>
                {s.source} · {clock(s.video_time)}
              </strong>
              <small>
                {s.detections.length} detections
                {s.detections.length
                  ? ": " +
                    Object.entries(
                      s.detections.reduce(
                        (a, o) => ({
                          ...a,
                          [o.object_class]: (a[o.object_class] || 0) + 1,
                        }),
                        {},
                      ),
                    )
                      .map(([c, n]) => `${c} ${n}`)
                      .join(", ")
                  : ""}
              </small>
              <small>
                {s.actor} · {fmtDate(s.created_at)}
                {s.note ? ` · ${s.note}` : ""}
              </small>
              <div className="inline">
                <button
                  onClick={() =>
                    s.camera_id
                      ? openCamera(s.camera_id)
                      : openVideo(s.video_id, s.video_time, s.job_id)
                  }
                >
                  Open
                </button>
                <a className="button-link" href={s.image_url} download>
                  Image
                </a>
                <button
                  onClick={() =>
                    run(async () => {
                      await api(`/saved-detections/${s.id}`, {
                        method: "DELETE",
                      });
                      load();
                    })
                  }
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <Empty>
          Use “Save detections” on a video or live camera to keep a frame with
          its detections.
        </Empty>
      )}
    </Panel>
  );
}
function LockDetails({ locked, path, time, box, player, seekTo }) {
  if (!path) return <Empty>Loading track {locked}…</Empty>;
  const s = path.summary || {},
    rows = path.path;
  const first = rows[0]?.time ?? s.first_seen ?? 0,
    last = rows.at(-1)?.time ?? s.last_seen ?? 0;
  return (
    <>
      <div className="lock-head">
        {path.crop_url && (
          <img src={path.crop_url} alt={`${locked} best view`} />
        )}
        <div>
          <strong>{locked}</strong>
          <small>{path.object_class || "object"}</small>
          <Badge value={box ? "IN VIEW" : "NOT VISIBLE NOW"} />
        </div>
      </div>
      <FollowView player={player} box={box} />
      {[
        ["First seen", clock(first)],
        ["Last seen", clock(last)],
        ["Observed for", clock(s.duration ?? last - first)],
        ["Direction", s.direction || rows.at(-1)?.direction || "—"],
        ["Samples", rows.length],
        ...(s.max_speed_kmh != null
          ? [
              [
                "Speed now",
                kmh(
                  rows.filter((r) => r.time <= time).at(-1)?.speed_kmh ?? null,
                ),
              ],
              ["Fastest measured", kmh(s.max_speed_kmh)],
              ["Average measured", kmh(s.mean_speed_kmh)],
            ]
          : []),
      ].map(([k, v]) => (
        <div className="stat-row" key={k}>
          <span>{k}</span>
          <strong>{v}</strong>
        </div>
      ))}
      {Object.entries(s.zones || {}).map(([zone, dwell]) => (
        <div className="stat-row" key={zone}>
          <span>Zone · {zone}</span>
          <strong>{clock(dwell)} longest dwell</strong>
        </div>
      ))}
      <div className="inline">
        <button onClick={() => seekTo(first)}>Jump to first seen</button>
        <button onClick={() => seekTo(last)}>Jump to last seen</button>
      </div>
    </>
  );
}
function FollowView({ player, box }) {
  const canvas = useRef(null),
    boxRef = useRef(box);
  boxRef.current = box;
  useEffect(() => {
    let frame;
    const draw = () => {
      const v = player.current,
        c = canvas.current,
        b = boxRef.current;
      if (v && c && b && v.videoWidth) {
        const vw = v.videoWidth,
          vh = v.videoHeight;
        const cx = ((b[0] + b[2]) / 2) * vw,
          cy = ((b[1] + b[3]) / 2) * vh;
        const h = Math.min(
            vh,
            Math.max((b[3] - b[1]) * vh, (b[2] - b[0]) * vw * 0.75, 24) * 1.6,
          ),
          w = Math.min(vw, (h * 4) / 3);
        const sx = Math.max(0, Math.min(vw - w, cx - w / 2)),
          sy = Math.max(0, Math.min(vh - h, cy - h / 2));
        c.getContext("2d").drawImage(v, sx, sy, w, h, 0, 0, c.width, c.height);
      }
      frame = requestAnimationFrame(draw);
    };
    draw();
    return () => cancelAnimationFrame(frame);
  }, []);
  return box ? (
    <canvas className="follow-view" ref={canvas} width="320" height="240" />
  ) : (
    <div className="follow-view empty">Not visible at this moment</div>
  );
}
const SEARCH_EXAMPLES = [
  "people who stayed in a zone for more than 2 minutes",
  "red car today",
  "person in a white coat on live cameras",
  "vehicles stopped over 30 seconds in the last hour",
  "verified crowd events with more than 20 people",
  "P-0003 moving north",
];
function NaturalSearch({ run, openEvent, openVideo, openCamera }) {
  const [q, setQ] = useState(""),
    [result, setResult] = useState(null),
    [busy, setBusy] = useState(false);
  const search = async (text = q) => {
    if (!text.trim()) return;
    setQ(text);
    setBusy(true);
    await run(async () =>
      setResult(await api(`/nl-search?q=${encodeURIComponent(text)}`)),
    );
    setBusy(false);
  };
  const openTrack = (t) =>
    t.camera_id
      ? openCamera(t.camera_id)
      : openVideo(t.video_id, t.first_seen, t.job_id);
  return (
    <Panel
      title="Natural language search"
      action={<span className="eyebrow">OFFLINE PARSER · LOCAL CLIP</span>}
    >
      <form
        className="nl-search"
        onSubmit={(e) => {
          e.preventDefault();
          search();
        }}
      >
        <input
          aria-label="Natural language search"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="e.g. people who stayed in Gate B for more than 2 minutes yesterday"
        />
        <button className="primary" disabled={busy}>
          <Search size={16} /> {busy ? "Searching…" : "Search"}
        </button>
      </form>
      <div className="chip-row">
        {SEARCH_EXAMPLES.map((x) => (
          <button key={x} type="button" onClick={() => search(x)}>
            {x}
          </button>
        ))}
      </div>
      {result && (
        <div className="stack">
          <div className="chip-row">
            {result.understood.length ? (
              result.understood.map((c) => (
                <span className="chip" key={c}>
                  {c}
                </span>
              ))
            ) : (
              <span className="muted">
                No filters recognized; showing the most recent matches.
              </span>
            )}
          </div>
          {result.visual.note && <p className="notice">{result.visual.note}</p>}
          {result.visual.applied && (
            <small className="muted">
              Ranked by appearance similarity to “
              {result.visual.prompt.replace("a photo of ", "")}”. Similarity is
              a search aid, not identification.
            </small>
          )}
          {result.searched.tracks && (
            <>
              <h3>{result.tracks.length} tracks</h3>
              {result.tracks.length ? (
                <div className="result-grid">
                  {result.tracks.map((t) => (
                    <button
                      key={t.id}
                      className="result-card"
                      onClick={() => openTrack(t)}
                    >
                      {t.crop_url ? (
                        <img
                          src={t.crop_url}
                          alt={`${t.track_id} ${t.object_class}`}
                        />
                      ) : (
                        <div className="empty">No crop</div>
                      )}
                      <strong>
                        {t.track_id} · {t.object_class}
                      </strong>
                      <small>
                        {t.video} · {clock(t.first_seen)} · {clock(t.duration)}
                        {t.score != null
                          ? ` · match ${Math.round(t.score * 100)}`
                          : ""}
                      </small>
                    </button>
                  ))}
                </div>
              ) : (
                <Empty>No tracks match.</Empty>
              )}
            </>
          )}
          {result.searched.events && (
            <>
              <h3>{result.events.length} events</h3>
              <EventTable events={result.events} openEvent={openEvent} />
            </>
          )}
        </div>
      )}
    </Panel>
  );
}
function TrafficPanel({ stats }) {
  const lanes = (stats.zones || []).filter(
    (z) => z.type === "Lane" || z.type === "Traffic Zone" || z.kind === "line",
  );
  return (
    <div className="stack">
      <div className="inline">
        <Badge value={stats.traffic_state || "NO DATA"} />
        {stats.calibrated ? (
          <Badge value="CALIBRATED" />
        ) : (
          <span className="muted">Frame-relative counts only</span>
        )}
      </div>
      {[
        ["Median speed", kmh(stats.median_speed_kmh)],
        ["Average speed", kmh(stats.average_speed_kmh)],
        ["Measured vehicles", stats.speed_samples ?? 0],
        ["Over the limit now", stats.speeding_vehicles ?? 0],
        [
          "New vehicle tracks",
          `${(stats.vehicles_per_minute || 0).toFixed(1)} / min`,
        ],
      ].map(([k, v]) => (
        <div className="stat-row" key={k}>
          <span>{k}</span>
          <strong>{v}</strong>
        </div>
      ))}
      {lanes.length > 0 && (
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>LANE / LINE</th>
                <th>VEHICLES / HOUR</th>
                <th>SPEED</th>
                <th>OCCUPANCY</th>
              </tr>
            </thead>
            <tbody>
              {lanes.map((z) => (
                <tr key={z.id}>
                  <td>{z.name}</td>
                  <td>{z.flow_per_hour ?? "—"}</td>
                  <td>{kmh(z.average_speed_kmh)}</td>
                  <td>
                    {z.kind === "line"
                      ? `${z.TOTAL} crossings`
                      : `${z.occupancy} / ${z.threshold}`}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <small className="muted">
        {stats.calibrated
          ? `Speed estimated from calibration "${stats.calibration}"; flow counts the last ${
              lanes[0]?.flow_window_seconds ?? 0
            } s scaled to an hour. State from ${stats.traffic_basis}, free flow ${stats.free_flow_kmh} km/h.`
          : "Draw a road calibration on this view to measure speed, hourly flow and physical spacing. Speed rules need a new analysis run."}
      </small>
    </div>
  );
}
function ConvoyPhysical({ physical, arrival }) {
  if (!physical) return null;
  if (!physical.calibrated)
    return <small className="muted">{physical.note}</small>;
  return (
    <>
      {[
        ["Lead vehicle", physical.lead_track || "—"],
        ["Lead speed", kmh(physical.lead_speed_kmh)],
        ["Convoy average speed", kmh(physical.average_speed_kmh)],
        ["Convoy length", metres(physical.convoy_length_m)],
        ["Largest gap", metres(physical.largest_gap_m)],
        [
          "ETA to route end",
          physical.eta_seconds == null
            ? "—"
            : `${clock(physical.eta_seconds)}${arrival ? ` · ${arrival}` : ""}`,
        ],
      ].map(([k, v]) => (
        <div className="stat-row" key={k}>
          <span>{k}</span>
          <strong>{v}</strong>
        </div>
      ))}
      {physical.vehicles.map((v, i) => (
        <div className="stat-row" key={v.track_id}>
          <span>
            {i + 1}. {v.track_id}
            {v.extrapolated ? " · outside calibrated area" : ""}
          </span>
          <strong>
            {kmh(v.speed_kmh)}
            {v.distance_m != null && ` · ${metres(v.distance_m)} along`}
            {v.gap_m != null &&
              ` · gap ${metres(v.gap_m)}${
                v.time_gap_s != null ? ` (${seconds(v.time_gap_s)})` : ""
              }`}
          </strong>
        </div>
      ))}
      <small className="muted">{physical.note}</small>
    </>
  );
}
function ZoneCounts({ zones }) {
  return zones.map((z) => (
    <div className="zone-result" key={z.id}>
      <strong>{z.name}</strong>
      {z.kind === "line" ? (
        <span>
          IN {z.IN} · OUT {z.OUT}
          {z.flow_per_hour ? ` · ${z.flow_per_hour}/h` : ""}
          {z.average_speed_kmh != null && ` · ${kmh(z.average_speed_kmh)}`}
          {Object.entries(z.by_class || {})
            .map(([c, v]) => ` · ${c} ${v.IN}/${v.OUT}`)
            .join("")}
        </span>
      ) : (
        <>
          <span>
            {z.occupancy} / {z.threshold} ·{" "}
            {Object.entries(z.classes || {})
              .map(([c, n]) => `${c} ${n}`)
              .join(" · ") || "empty"}
            {z.flow_per_hour ? ` · ${z.flow_per_hour}/h` : ""}
            {z.average_speed_kmh != null && ` · ${kmh(z.average_speed_kmh)}`}
          </span>
          <Badge value={z.status} />
        </>
      )}
    </div>
  ));
}
const CAMERA_DEFAULT = {
  name: "",
  url: "",
  mode: "Detect & Annotate",
  fps: 5,
  confidence: 0.3,
  imgsz: 960,
  width: 1280,
  classes: [],
  tiling: false,
  min_box: 0,
};
function Live({ run, can, openEvent, cameraId, setCameraId }) {
  const [cameras, setCameras] = useState([]),
    [watchlist, setWatchlist] = useState([]),
    [watchLabel, setWatchLabel] = useState(""),
    [watchTrack, setWatchTrack] = useState(""),
    [cameraLocation, setCameraLocation] = useState({name:"",latitude:9.03,longitude:38.74}),
    [adding, setAdding] = useState(false),
    [form, setForm] = useState(CAMERA_DEFAULT),
    [heat, setHeat] = useState(false),
    [heatGroup, setHeatGroup] = useState("all"),
    [heatTick, setHeatTick] = useState(0),
    [events, setEvents] = useState([]),
    [configuring, setConfiguring] = useState(false),
    [lockInput, setLockInput] = useState("");
  const load = () =>
    api("/cameras")
      .then(setCameras)
      .catch(() => {});
  useEffect(() => {
    load();
    const id = setInterval(load, 1000);
    return () => clearInterval(id);
  }, []);
  useEffect(() => {
    if (!cameras.some((c) => c.id === cameraId) && cameras[0])
      setCameraId(cameras[0].id);
  }, [cameras]);
  const cam = cameras.find((c) => c.id === cameraId);
  useEffect(() => {
    if (!cam) { setWatchlist([]); return; }
    const refresh = () => api(`/cameras/${cam.id}/watchlist`).then(setWatchlist).catch(() => {});
    refresh();
    const timer = setInterval(refresh, 5000);
    return () => clearInterval(timer);
  }, [cam?.id]);
  useEffect(() => {
    if (cam?.location?.name) setCameraLocation(cam.location);
    else setCameraLocation({name:"",latitude:9.03,longitude:38.74});
  }, [cam?.id, cam?.location?.name]);
  useEffect(() => {
    if (!cam) return;
    const loadEvents = () =>
      api(`/events?video_id=${cam.video_id}&limit=15`)
        .then(setEvents)
        .catch(() => {});
    loadEvents();
    const e = setInterval(loadEvents, 5000),
      h = setInterval(() => setHeatTick((v) => v + 1), 10000);
    return () => {
      clearInterval(e);
      clearInterval(h);
    };
  }, [cam?.id]);
  const s = cam?.status || {},
    summary = s.summary || {};
  const lock = (track_id) =>
    run(async () => {
      await api(`/cameras/${cam.id}/lock`, {
        method: "POST",
        body: { track_id },
      });
      load();
    });
  const update = (body) =>
    run(async () => {
      await api(`/cameras/${cam.id}`, { method: "PUT", body });
      load();
    });
  const field = (key, label, input) => (
    <label key={key}>
      {label}
      {input}
    </label>
  );
  return (
    <>
      <div className="toolbar">
        <select
          aria-label="Camera"
          value={cameraId}
          onChange={(e) => setCameraId(e.target.value)}
        >
          <option value="">Select camera</option>
          {cameras.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name} · {c.state}
            </option>
          ))}
        </select>
        {can("configure") && (
          <button className="primary" onClick={() => setAdding(!adding)}>
            <Camera size={16} /> {adding ? "Close" : "Add camera"}
          </button>
        )}
        <span className="muted">
          RTSP · HTTP(S) / HLS · EarthCam page links
        </span>
      </div>
      {adding && (
        <Panel title="Add live camera">
          <form
            className="form-grid"
            onSubmit={(e) => {
              e.preventDefault();
              run(async () => {
                const c = await api("/cameras", { method: "POST", body: form });
                setForm(CAMERA_DEFAULT);
                setAdding(false);
                setCameraId(c.id);
                load();
              });
            }}
          >
            {field(
              "name",
              "Name",
              <input
                required
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
              />,
            )}
            {field(
              "url",
              "Stream URL",
              <input
                required
                placeholder="rtsp://user:password@192.168.1.20:554/stream1"
                value={form.url}
                onChange={(e) => setForm({ ...form, url: e.target.value })}
              />,
            )}
            {field(
              "mode",
              "Analysis mode",
              <select
                value={form.mode}
                onChange={(e) => setForm({ ...form, mode: e.target.value })}
              >
                {MODES.map((m) => (
                  <option key={m}>{m}</option>
                ))}
              </select>,
            )}
            {field(
              "fps",
              "Analysis FPS",
              <input
                type="number"
                min="1"
                max="15"
                value={form.fps}
                onChange={(e) => setForm({ ...form, fps: +e.target.value })}
              />,
            )}
            {field(
              "imgsz",
              "Detection input size",
              <select
                value={form.imgsz}
                onChange={(e) => setForm({ ...form, imgsz: +e.target.value })}
              >
                {[640, 960, 1280].map((v) => (
                  <option key={v} value={v}>
                    {v}px
                  </option>
                ))}
              </select>,
            )}
            {field(
              "width",
              "Processing width",
              <select
                value={form.width}
                onChange={(e) => setForm({ ...form, width: +e.target.value })}
              >
                {[640, 960, 1280, 1920].map((v) => (
                  <option key={v} value={v}>
                    {v}px
                  </option>
                ))}
              </select>,
            )}
            <DetectionFilterFields
              value={form}
              onChange={(v) => setForm({ ...form, ...v })}
            />
            <button className="primary">Save and start</button>
          </form>
          <p className="notice">
            Passwords in stream URLs are stored locally and masked in the
            interface. Monitor only cameras you are authorized to use; public
            webcam terms (for example EarthCam) may restrict use beyond personal
            viewing.
          </p>
        </Panel>
      )}
      {cameras.length > 0 && (
        <Panel title={`All camera feeds · ${cameras.length}`}>
          <div className="camera-grid">
            {cameras.map((c) => (
              <button className={`camera-tile ${c.id === cameraId ? "selected" : ""}`} key={c.id} onClick={() => setCameraId(c.id)}>
                <div className="camera-tile-image">
                  {c.enabled ? <img src={`/api/cameras/${c.id}/stream?session=${c.status?.job_id || ""}`} alt={`${c.name} feed`} loading="lazy" /> : <span>Camera stopped</span>}
                </div>
                <strong>{c.name}</strong>
                <small>{c.location?.name || "Location not set"} · {c.mode} · {c.state}</small>
              </button>
            ))}
          </div>
        </Panel>
      )}
      {!cam ? (
        <Empty>Add an RTSP or stream URL to start live analysis.</Empty>
      ) : (
        <div className="analysis-layout">
          <div>
            <Panel
              title={cam.name}
              action={
                <div className="inline">
                  <label className="check">
                    <input
                      type="checkbox"
                      checked={heat}
                      onChange={(e) => setHeat(e.target.checked)}
                    />{" "}
                    Heatmap
                  </label>
                  {heat && (
                    <select
                      aria-label="Heatmap objects"
                      value={heatGroup}
                      onChange={(e) => setHeatGroup(e.target.value)}
                    >
                      {["all", "person", "vehicle", "other"].map((g) => (
                        <option key={g}>{g}</option>
                      ))}
                    </select>
                  )}
                  <Badge value={cam.state} />
                </div>
              }
            >
              {configuring ? (
                <LiveZoneEditor cam={cam} run={run} />
              ) : (
                <div
                  className="video-stage"
                  style={{
                    aspectRatio: s.width ? `${s.width}/${s.height}` : "16/9",
                  }}
                >
                  {cam.enabled && (
                    <img
                      className="live-view"
                      src={`/api/cameras/${cam.id}/stream?session=${s.job_id || ""}`}
                      alt={`${cam.name} live annotated view`}
                    />
                  )}
                  {heat && s.job_id && (
                    <img
                      className="heatmap-layer"
                      alt=""
                      src={`/api/jobs/${s.job_id}/heatmap.png?group=${heatGroup}&t=${heatTick}`}
                      onError={(e) => (e.currentTarget.style.display = "none")}
                      onLoad={(e) => (e.currentTarget.style.display = "")}
                    />
                  )}
                </div>
              )}
              {s.error && cam.state !== "LIVE" && (
                <div className="error">{s.error}</div>
              )}
              <div className="video-tools">
                <span>
                  {cam.state === "LIVE"
                    ? `${s.fps} FPS analysed · ${s.width}×${s.height} · ${s.device || ""} · up ${clock(s.uptime)}`
                    : cam.state}
                </span>
                {cam.state === "LIVE" && s.job_id && (
                  <>
                    {can("operate") && (
                      <button
                        onClick={() =>
                          run(async () => {
                            const saved = await api("/saved-detections", {
                              method: "POST",
                              body: {
                                camera_id: cam.id,
                                classes: cam.classes?.length
                                  ? cam.classes
                                  : null,
                              },
                            });
                            window.alert(
                              `Saved ${saved.detections.length} detections. See Evidence → Saved detections.`,
                            );
                          })
                        }
                      >
                        Save detections
                      </button>
                    )}
                    <a
                      className="button-link"
                      href={`/api/jobs/${s.job_id}/detections?format=csv`}
                    >
                      Export CSV
                    </a>
                  </>
                )}
                {can("configure") && (
                  <>
                    <button onClick={() => setConfiguring(!configuring)}>
                      {configuring ? "Back to live view" : "Zones & lines"}
                    </button>
                    <button onClick={() => update({ enabled: !cam.enabled })}>
                      {cam.enabled ? "Stop" : "Start"}
                    </button>
                  </>
                )}
                {can("admin") && (
                  <button
                    onClick={() => {
                      if (
                        window.confirm(
                          `Delete camera ${cam.name}? Recorded events and clips are kept.`,
                        )
                      )
                        run(async () => {
                          await api(`/cameras/${cam.id}`, { method: "DELETE" });
                          setCameraId("");
                          load();
                        });
                    }}
                  >
                    Delete
                  </button>
                )}
              </div>
            </Panel>
            <Metrics
              items={[
                ["VISIBLE PEOPLE", summary.people],
                ["VISIBLE VEHICLES", summary.vehicles],
                ["VISIBLE OBJECTS", summary.objects],
                ["TRACKS THIS SESSION", summary.total_objects],
              ]}
            />
            {cam.mode === "Traffic" && <p className="notice">Traffic mode measures vehicle flow, speed and congestion across the full scene.</p>}
            {cam.mode === "Convoy" && <p className="notice">Convoy mode follows designated vehicles, their route progress, spacing and delay alerts.</p>}
            {(summary.zones || []).length > 0 && (
              <Panel title="Zone & line counts">
                <ZoneCounts zones={summary.zones} />
              </Panel>
            )}
            {(cam.mode === "Traffic" || cam.mode === "Convoy") && (
              <Panel title="Traffic context">
                <TrafficPanel stats={summary} />
              </Panel>
            )}
            <Panel title="Recent camera events">
              {events.find((e) => e.type === "Blacklist Track Alert") && <p className="error">Watchlist alert: {events.find((e) => e.type === "Blacklist Track Alert").track_id} detected. Open the event to review its screenshot.</p>}
              <EventTable events={events} openEvent={openEvent} />
            </Panel>
          </div>
          <div>
            <Panel
              title="Lock tracking"
              action={
                s.locked &&
                can("operate") && (
                  <button onClick={() => lock(null)}>Unlock</button>
                )
              }
            >
              <div className="stack">
                {s.locked ? (
                  <>
                    <div className="lock-head">
                      <div>
                        <strong>{s.locked.track_id}</strong>
                        <small>
                          {s.locked.object_class || "Waiting for this ID"}
                        </small>
                        <Badge
                          value={
                            s.locked.visible ? "IN VIEW" : "NOT VISIBLE NOW"
                          }
                        />
                      </div>
                    </div>
                    {s.locked.known &&
                      [
                        ["Observed time", clock(s.locked.observed_seconds ?? s.locked.duration)],
                        ["Direction", s.locked.direction || "—"],
                        ["Last seen", `${s.locked.seconds_since_seen}s ago`],
                        ...(s.locked.max_speed_kmh != null
                          ? [
                              ["Speed", kmh(s.locked.speed_kmh)],
                              ["Fastest measured", kmh(s.locked.max_speed_kmh)],
                            ]
                          : []),
                      ].map(([k, v]) => (
                        <div className="stat-row" key={k}>
                          <span>{k}</span>
                          <strong>{v}</strong>
                        </div>
                      ))}
                    {Object.entries(s.locked.zones || {}).map(([z, d]) => (
                      <div className="stat-row" key={z}>
                        <span>Zone · {z}</span>
                        <strong>{clock(d)} longest dwell</strong>
                      </div>
                    ))}
                    <small className="muted">
                      Other objects are dimmed and a zoomed follow view appears
                      top-right of the live image.
                    </small>
                  </>
                ) : (
                  <p>
                    Select a visible track, or enter its ID, to lock onto it.
                  </p>
                )}
                {can("operate") && (
                  <>
                    <form
                      className="inline"
                      onSubmit={(e) => {
                        e.preventDefault();
                        const m = lockInput
                          .trim()
                          .toUpperCase()
                          .match(/^([POV])-?(\d{1,4})$/);
                        if (m) lock(`${m[1]}-${m[2].padStart(4, "0")}`);
                      }}
                    >
                      <input
                        aria-label="Track ID to lock"
                        placeholder="P-0003"
                        value={lockInput}
                        onChange={(e) => setLockInput(e.target.value)}
                      />
                      <button>Lock</button>
                    </form>
                    <div className="chip-row">
                      {(s.visible || []).map((o) => (
                        <button
                          key={o.track_id}
                          className={
                            s.locked?.track_id === o.track_id ? "selected" : ""
                          }
                          onClick={() => lock(o.track_id)}
                        >
                          {o.track_id} · {o.object_class}{" "}
                          {Math.round(o.confidence * 100)}%
                          {o.object_class === "person" && ` · observed ${clock(o.observed_seconds ?? o.duration)}`}
                          {o.speed_kmh != null && ` · ${kmh(o.speed_kmh)}`}
                        </button>
                      ))}
                    </div>
                  </>
                )}
              </div>
            </Panel>
            <Panel title="Person track watchlist">
              <p className="notice">Watch a person track in this camera session. On its next detection, ARGUS saves a screenshot and creates a high priority event. Track IDs reset when the session restarts.</p>
              {can("operate") && <form className="inline" onSubmit={(e) => { e.preventDefault(); run(async () => { await api(`/cameras/${cam.id}/watchlist`, {method:"POST",body:{track_id:watchTrack,label:watchLabel}}); setWatchLabel(""); setWatchTrack(""); setWatchlist(await api(`/cameras/${cam.id}/watchlist`)); }); }}>
                <select aria-label="Person track" required value={watchTrack} onChange={(e) => setWatchTrack(e.target.value)}><option value="">Select person</option>{(s.visible || []).filter((o) => o.object_class === "person").map((o) => <option key={o.track_id} value={o.track_id}>{o.track_id} · {clock(o.observed_seconds ?? o.duration)} observed</option>)}</select>
                <input aria-label="Watchlist label" required placeholder="Reason or case label" value={watchLabel} onChange={(e) => setWatchLabel(e.target.value)} />
                <button>Add to watchlist</button>
              </form>}
              {watchlist.filter((w) => w.job_id === s.job_id).map((w) => <div className="stat-row" key={w.id}><span>{w.track_id} · {w.label} · {w.alerted ? "Alert captured" : "Watching"}</span>{can("operate") && <button onClick={() => run(async () => { await api(`/cameras/${cam.id}/watchlist/${w.id}`,{method:"DELETE"}); setWatchlist(await api(`/cameras/${cam.id}/watchlist`)); })}>Remove</button>}</div>)}
            </Panel>
            <Panel title="Camera location">
              <p>{cam.location?.name || "Location not set"}</p>
              {can("configure") && <form className="form-grid" onSubmit={(e) => { e.preventDefault(); run(async () => { await api(`/videos/${cam.video_id}/location`,{method:"PUT",body:cameraLocation}); load(); }); }}>
                <label>Location name<input required value={cameraLocation.name} onChange={(e) => setCameraLocation({...cameraLocation,name:e.target.value})} /></label>
                {["latitude","longitude"].map((k) => <label key={k}>{k}<input type="number" step="any" required value={cameraLocation[k]} onChange={(e) => setCameraLocation({...cameraLocation,[k]:+e.target.value})} /></label>)}
                <button>Save camera point</button>
              </form>}
            </Panel>
            {cam.mode === "Convoy" && (
              <Panel title="Convoy status">
                <LiveConvoyPanel cam={cam} status={s} run={run} can={can} />
              </Panel>
            )}
            <Panel title="Detected objects">
              {Object.keys(summary.total_classes || {}).length ? (
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>CLASS</th>
                        <th>VISIBLE NOW</th>
                        <th>TRACKS THIS SESSION</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(summary.total_classes)
                        .sort((a, b) => b[1] - a[1])
                        .map(([name, total]) => (
                          <tr key={name}>
                            <td>{name}</td>
                            <td>{summary.classes?.[name] || 0}</td>
                            <td>{total}</td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <Empty>No objects detected yet.</Empty>
              )}
            </Panel>
            <Panel title="Camera settings">
              <div className="stack">
                <small className="muted">{cam.url}</small>
                {can("configure") ? (
                  <>
                    {[
                      ["mode", "Analysis mode", MODES],
                      ["fps", "Analysis FPS", [1, 2, 5, 10, 15]],
                      ["imgsz", "Detection input size", [640, 960, 1280]],
                      ["width", "Processing width", [640, 960, 1280, 1920]],
                    ].map(([key, label, options]) => (
                      <label key={key}>
                        {label}
                        <select
                          value={cam[key]}
                          onChange={(e) =>
                            update({
                              [key]:
                                key === "mode"
                                  ? e.target.value
                                  : +e.target.value,
                            })
                          }
                        >
                          {options.map((o) => (
                            <option key={o} value={o}>
                              {o}
                            </option>
                          ))}
                        </select>
                      </label>
                    ))}
                    <DetectionFilterFields
                      value={{
                        classes: cam.classes || [],
                        tiling: cam.tiling,
                        min_box: cam.min_box,
                      }}
                      onChange={(v) =>
                        update({
                          classes: v.classes?.length ? v.classes : null,
                          tiling: v.tiling,
                          min_box: v.min_box,
                        })
                      }
                    />
                    <small className="muted">
                      Changing settings restarts the camera session; counts and
                      track IDs start again.
                    </small>
                  </>
                ) : (
                  <span>
                    {cam.mode} · {cam.fps} FPS · {cam.imgsz}px
                  </span>
                )}
              </div>
            </Panel>
          </div>
        </div>
      )}
    </>
  );
}
function LiveConvoyPanel({ cam, status, run, can }) {
  const convoy = status.convoy,
    vehicles = (status.visible || []).filter((o) =>
      o.track_id.startsWith("V-"),
    ),
    designated = convoy?.vehicles || [];
  const designate = (track_id, role) =>
    run(async () => {
      await api(`/cameras/${cam.id}/convoy`, {
        method: "POST",
        body: { track_id, role },
      });
    });
  const arrival =
    convoy?.eta_seconds != null
      ? new Date(Date.now() + convoy.eta_seconds * 1000).toLocaleTimeString()
      : null;
  return (
    <div className="stack">
      {cam.state !== "LIVE" && (
        <small className="muted">
          Designation needs a running session; the camera is {cam.state}.
        </small>
      )}
      <span>Designated vehicles: {designated.length}</span>
      {designated.map((v) => (
        <div key={v.track_id}>
          <strong>
            {v.track_id} · {v.role} ·{" "}
            {v.observable ? "VISIBLE" : "NOT OBSERVABLE"}
          </strong>
          <small>
            {kmh(v.speed_kmh)} · tracked {clock(v.tracking_duration)}
            {v.route &&
              ` · ${v.route.route}: ${
                v.route.on_route
                  ? `${v.route.progress}%`
                  : "outside route tolerance"
              }`}
          </small>
          {can("operate") && (
            <button onClick={() => designate(v.track_id, null)}>
              Clear designation
            </button>
          )}
        </div>
      ))}
      <ConvoyPhysical
        physical={convoy?.physical}
        arrival={arrival ? `about ${arrival}` : null}
      />
      {can("operate") && (
        <>
          <span>Designate a visible vehicle</span>
          <div className="chip-row">
            {vehicles.length ? (
              vehicles.map((o) => (
                <span key={o.track_id} className="inline">
                  <button onClick={() => designate(o.track_id, "Convoy Lead")}>
                    {o.track_id} lead
                  </button>
                  <button
                    onClick={() => designate(o.track_id, "Convoy Vehicle")}
                  >
                    convoy
                  </button>
                </span>
              ))
            ) : (
              <small className="muted">No vehicles in view.</small>
            )}
          </div>
        </>
      )}
      {convoy?.timeline?.length > 0 && (
        <div className="convoy-timeline">
          <strong>Session timeline</strong>
          {convoy.timeline
            .slice()
            .reverse()
            .map((e, i) => (
              <button key={i} disabled>
                <span>{clock(e.time)}</span>
                {e.text}
              </button>
            ))}
        </div>
      )}
      <small className="muted">
        Times are seconds since this camera session started. A vehicle seen this
        second may need a moment before it can be designated.
      </small>
    </div>
  );
}
function LiveZoneEditor({ cam, run }) {
  const [geo, setGeo] = useState([]),
    [kind, setKind] = useState("zone"),
    [points, setPoints] = useState([]),
    [snap, setSnap] = useState(Date.now()),
    [draft, setDraft] = useState({
      name: "Zone 1",
      type: "Crowd Zone",
      object_class: "all",
      threshold: 10,
      dwell_seconds: 30,
      severity: "MEDIUM",
      speed_limit_kmh: 0,
      width_m: 3.5,
      length_m: 20,
    });
  const POINT_LIMIT = { line: 2, calibration: 4 };
  const loadGeo = () =>
    run(async () => setGeo(await api(`/videos/${cam.video_id}/geometries`)));
  useEffect(() => {
    loadGeo();
  }, [cam.id]);
  const s = cam.status || {};
  const toPoints = (pts) =>
    pts.map((p) => p.map((v) => v * 1000).join(",")).join(" ");
  return (
    <div className="stack">
      <div
        className="video-stage"
        style={{ aspectRatio: s.width ? `${s.width}/${s.height}` : "16/9" }}
      >
        <img
          className="live-view"
          src={`/api/cameras/${cam.id}/frame.jpg?raw=true&t=${snap}`}
          alt="Latest camera frame for drawing"
        />
        <svg
          className="overlay drawing"
          viewBox="0 0 1000 1000"
          preserveAspectRatio="none"
          onClick={(e) => {
            const r = e.currentTarget.getBoundingClientRect();
            setPoints((p) =>
              POINT_LIMIT[kind] && p.length >= POINT_LIMIT[kind]
                ? p
                : [...p, framePoint(e, r)],
            );
          }}
        >
          {geo.map((g) =>
            g.kind === "zone" || g.kind === "calibration" ? (
              <polygon
                key={g.id}
                className={
                  g.kind === "calibration"
                    ? "calibration-polygon"
                    : "zone-polygon"
                }
                points={toPoints(g.points)}
              />
            ) : (
              <polyline
                key={g.id}
                className={g.kind === "route" ? "route-line" : "zone-line"}
                points={toPoints(g.points)}
              />
            ),
          )}
          {points.length > 0 && (
            <polyline className="drawing-line" points={toPoints(points)} />
          )}
        </svg>
      </div>
      <div className="form-grid">
        <label>
          Draw
          <select
            value={kind}
            onChange={(e) => {
              setKind(e.target.value);
              setPoints([]);
            }}
          >
            <option value="zone">Zone (3+ points)</option>
            <option value="line">Counting line (2 points)</option>
            <option value="calibration">Road calibration (4 corners)</option>
            <option value="route">Convoy route (2+ points)</option>
          </select>
        </label>
        {kind === "calibration" && (
          <>
            <label>
              Measured width, point 1 → 2 (m)
              <input
                type="number"
                min="0.5"
                step="0.1"
                value={draft.width_m}
                onChange={(e) =>
                  setDraft({ ...draft, width_m: +e.target.value })
                }
              />
            </label>
            <label>
              Measured length, point 2 → 3 (m)
              <input
                type="number"
                min="0.5"
                step="0.5"
                value={draft.length_m}
                onChange={(e) =>
                  setDraft({ ...draft, length_m: +e.target.value })
                }
              />
            </label>
          </>
        )}
        <label>
          Name
          <input
            value={draft.name}
            onChange={(e) => setDraft({ ...draft, name: e.target.value })}
          />
        </label>
        {kind === "zone" && (
          <label>
            Type
            <select
              value={draft.type}
              onChange={(e) => setDraft({ ...draft, type: e.target.value })}
            >
              {ZONES.filter((z) => z !== "Convoy Corridor").map((z) => (
                <option key={z}>{z}</option>
              ))}
            </select>
          </label>
        )}
        <label>
          Object class
          <select
            value={draft.object_class}
            onChange={(e) =>
              setDraft({ ...draft, object_class: e.target.value })
            }
          >
            {[
              "all",
              "person",
              "vehicle",
              "car",
              "bus",
              "truck",
              "motorcycle",
            ].map((c) => (
              <option key={c}>{c}</option>
            ))}
          </select>
        </label>
        {kind === "zone" && (
          <>
            <label>
              Occupancy threshold
              <input
                type="number"
                min="1"
                value={draft.threshold}
                onChange={(e) =>
                  setDraft({ ...draft, threshold: +e.target.value })
                }
              />
            </label>
            <label>
              Dwell seconds
              <input
                type="number"
                min="0"
                value={draft.dwell_seconds}
                onChange={(e) =>
                  setDraft({ ...draft, dwell_seconds: +e.target.value })
                }
              />
            </label>
            <label>
              Speed limit km/h (0 = no speed rule)
              <input
                type="number"
                min="0"
                max="400"
                value={draft.speed_limit_kmh}
                onChange={(e) =>
                  setDraft({ ...draft, speed_limit_kmh: +e.target.value })
                }
              />
            </label>
          </>
        )}
      </div>
      <div className="toolbar">
        <span>
          {kind === "calibration"
            ? "Click four measured road corners: near-left, near-right, far-right, far-left."
            : "Click on the frame."}{" "}
          {points.length} points
        </span>
        <button onClick={() => setSnap(Date.now())}>Refresh frame</button>
        <button onClick={() => setPoints((p) => p.slice(0, -1))}>
          Undo point
        </button>
        <button
          className="primary"
          onClick={() =>
            run(async () => {
              await api(`/videos/${cam.video_id}/geometries`, {
                method: "POST",
                body: { ...draft, kind, points },
              });
              setPoints([]);
              setDraft((d) => ({
                ...d,
                name: `${kind === "line" ? "Line" : kind === "route" ? "Route" : kind === "calibration" ? "Road calibration" : "Zone"} ${geo.length + 2}`,
              }));
              loadGeo();
            })
          }
        >
          Save {kind}
        </button>
      </div>
      <p className="notice">
        The live service applies saved geometry within about five seconds. Zone
        counts restart when rules change; track IDs continue. A road calibration
        starts measuring speed and spacing on the next frames, without
        restarting the session.
      </p>
      {geo.map((g) => (
        <div className="geometry-item" key={g.id}>
          <strong>{g.name}</strong>
          <small>{geometryLabel(g)}</small>
          <div className="inline">
            <button
              onClick={() =>
                run(async () => {
                  await api(`/geometries/${g.id}`, { method: "DELETE" });
                  loadGeo();
                })
              }
            >
              Delete
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
function Events({
  page,
  videos,
  openEvent,
  openVideo,
  openCamera,
  run,
  revision,
}) {
  const [rows, setRows] = useState([]),
    [filters, setFilters] = useState({}),
    [view, setView] = useState("Events"),
    [offset, setOffset] = useState(0),
    [total, setTotal] = useState(0);
  const search = (start = 0) =>
    run(async () => {
      const params = new URLSearchParams(
        Object.entries(filters).filter(([, v]) => v),
      );
      params.set("offset", start);
      params.set("limit", PAGE_SIZE);
      const path =
        view === "Tracks"
          ? "/track-search"
          : page === "Investigation"
            ? "/search"
            : "/events";
      const result = await apiPage(`${path}?${params}`);
      setRows(result.items);
      setTotal(result.total);
      setOffset(start);
    });
  useEffect(() => {
    setRows([]);
    setTotal(0);
    setOffset(0);
    search();
  }, [revision, view]);
  return (
    <>
      {page === "Evidence" && (
        <SavedDetections
          run={run}
          openVideo={openVideo}
          openCamera={openCamera}
        />
      )}
      {page === "Investigation" && (
        <NaturalSearch
          run={run}
          openEvent={openEvent}
          openVideo={openVideo}
          openCamera={openCamera}
        />
      )}
      {page === "Investigation" && (
        <div className="tabs">
          {[
            ["Events", "Event metadata"],
            ["Tracks", "Track metadata"],
          ].map(([t, label]) => (
            <button
              key={t}
              className={view === t ? "selected" : ""}
              onClick={() => setView(t)}
            >
              {label}
            </button>
          ))}
        </div>
      )}
      <Panel
        title={
          page === "Investigation"
            ? "Search recorded observations"
            : "Event filters"
        }
      >
        <form
          className="filter-grid"
          onSubmit={(e) => {
            e.preventDefault();
            search();
          }}
        >
          {[
            ["date_from", "From date"],
            ["date_to", "To date"],
            ["track_id", "Track ID"],
            ["zone", "Zone"],
            ["incident", "Incident number"],
          ].map(([key, label]) => (
            <label key={key}>
              {label}
              <input
                type={key.startsWith("date") ? "date" : "text"}
                value={filters[key] || ""}
                onChange={(e) =>
                  setFilters({ ...filters, [key]: e.target.value })
                }
              />
            </label>
          ))}
          <label>
            Video
            <select
              value={filters.video_id || ""}
              onChange={(e) =>
                setFilters({ ...filters, video_id: e.target.value })
              }
            >
              <option value="">All videos</option>
              {videos.map((v) => (
                <option key={v.id} value={v.id}>
                  {v.filename}
                </option>
              ))}
            </select>
          </label>
          {[
            ["mode", "Analysis mode", MODES],
            [
              "object_class",
              "Object class",
              view === "Tracks"
                ? ["person", "vehicle", "car", "bus", "truck", "motorcycle"]
                : ["person", "car", "bus", "truck", "motorcycle"],
            ],
            [
              "event_type",
              "Event type",
              [
                "Restricted Zone Entry",
                "Crowd Threshold",
                "Line Crossing",
                "Dwell Threshold",
                "Stopped Vehicle",
                "Speeding",
                "Traffic Congestion",
                "Convoy Traffic Delay",
                "Video Processing Failure",
              ],
            ],
            [
              "status",
              "Status",
              [
                "NEW",
                "UNDER REVIEW",
                "VERIFIED",
                "DISMISSED",
                "CONVERTED TO INCIDENT",
              ],
            ],
          ].map(([key, label, options]) => (
            <label key={key}>
              {label}
              <select
                value={filters[key] || ""}
                onChange={(e) =>
                  setFilters({ ...filters, [key]: e.target.value })
                }
              >
                <option value="">All</option>
                {options.map((o) => (
                  <option key={o}>{o}</option>
                ))}
              </select>
            </label>
          ))}
          <button className="primary">
            <Search size={16} /> Search
          </button>
        </form>
      </Panel>
      <Panel
        title={`${total} matching ${view === "Tracks" ? "tracks" : "events"}`}
        action={
          <div className="inline pager">
            <span className="muted">
              {total
                ? `${offset + 1}–${Math.min(offset + PAGE_SIZE, total)}`
                : "0"}
            </span>
            <button
              disabled={offset === 0}
              onClick={() => search(Math.max(0, offset - PAGE_SIZE))}
            >
              Previous
            </button>
            <button
              disabled={offset + PAGE_SIZE >= total}
              onClick={() => search(offset + PAGE_SIZE)}
            >
              Next
            </button>
          </div>
        }
      >
        {view === "Tracks" ? (
          <TrackTable tracks={rows} openVideo={openVideo} />
        ) : page === "Evidence" ? (
          <div className="evidence-grid">
            {rows.map((e) => (
              <button key={e.id} onClick={() => openEvent(e.id)}>
                {e.snapshot_url ? (
                  <img src={e.snapshot_url} alt={`${e.type} event snapshot`} />
                ) : (
                  <div className="empty">No snapshot</div>
                )}
                <strong>{e.type}</strong>
                <small>
                  {clock(e.video_time)} ·{" "}
                  {e.track_id || e.zone || "Video condition"}
                </small>
              </button>
            ))}
          </div>
        ) : (
          <EventTable events={rows} openEvent={openEvent} />
        )}
      </Panel>
    </>
  );
}
function TrackTable({ tracks, openVideo }) {
  return tracks.length ? (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            <th>TRACK</th>
            <th>CLASS</th>
            <th>VIDEO / MODE</th>
            <th>FIRST SEEN</th>
            <th>OBSERVED TIME</th>
            <th>DIRECTION</th>
            <th>CONVOY</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {tracks.map((t) => (
            <tr key={t.id}>
              <td>
                <strong>{t.track_id}</strong>
              </td>
              <td>{t.object_class}</td>
              <td>
                {t.video || t.video_id.slice(0, 8)}
                <small>{t.mode}</small>
              </td>
              <td>{clock(t.first_seen)}</td>
              <td>{clock(t.observed_seconds ?? t.duration)}</td>
              <td>{t.direction || "—"}</td>
              <td>{t.convoy_role || "—"}</td>
              <td>
                <button
                  onClick={() => openVideo(t.video_id, t.first_seen, t.job_id)}
                >
                  Open video <ChevronRight size={13} />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  ) : (
    <Empty>No tracks match this search.</Empty>
  );
}
function EventDetail({ id, run, can, refresh, openVideo, openCamera }) {
  const [event, setEvent] = useState(null),
    [note, setNote] = useState(""),
    [title, setTitle] = useState("");
  const video = useRef(null);
  const load = () =>
    run(async () => {
      const e = await api(`/events/${id}`);
      setEvent(e);
      setTitle(e.type);
    });
  useEffect(() => {
    load();
  }, [id]);
  if (!event) return <Empty>Loading evidence…</Empty>;
  return (
    <>
      <div className="review-banner">
        AI EVENT IS DECISION SUPPORT AND REQUIRES HUMAN REVIEW
      </div>
      <div className="grid-two">
        <Panel title={event.type} action={<Badge value={event.status} />}>
          {event.snapshot_url && (
            <img
              className="snapshot"
              src={event.snapshot_url}
              alt="Recorded event snapshot"
            />
          )}
          {event.clip_url ? (
            <video className="review-video" src={event.clip_url} controls />
          ) : (
            !event.camera && (
              <video
                className="review-video"
                ref={video}
                src={`/api/videos/${event.video_id}/media`}
                controls
                onLoadedMetadata={() => {
                  video.current.currentTime = event.video_time;
                }}
              />
            )
          )}
          <div className="toolbar">
            {event.camera ? (
              <button onClick={() => openCamera(event.camera.id)}>
                Open live camera {event.camera.name}
              </button>
            ) : (
              <button
                onClick={() =>
                  openVideo(event.video_id, event.video_time, event.job_id)
                }
              >
                Open annotated analysis at {clock(event.video_time)}
              </button>
            )}
          </div>
        </Panel>
        <Panel title="Review & verification">
          <div className="stack">
            {[
              ["Event ID", event.id],
              ["Timestamp", fmtDate(event.created_at)],
              ["Source video", event.video.filename],
              ["Video time", clock(event.video_time)],
              ["Frame", event.frame],
              ["Zone", event.zone || "—"],
              ["Track", event.track_id || "—"],
              ["Class", event.object_class || "—"],
              [
                "Confidence",
                event.confidence == null
                  ? "Not applicable"
                  : `${Math.round(event.confidence * 100)}%`,
              ],
              ["Priority", event.priority],
            ].map(([k, v]) => (
              <div className="stat-row" key={k}>
                <span>{k}</span>
                <strong>{v}</strong>
              </div>
            ))}
            <details open>
              <summary>Rule and measurements</summary>
              <pre>
                {JSON.stringify(
                  { rule: event.rule, analytics: event.analytics },
                  null,
                  2,
                )}
              </pre>
            </details>
            {can("review") && event.status !== "CONVERTED TO INCIDENT" && (
              <>
                <label>
                  Operator note
                  <textarea
                    value={note}
                    onChange={(e) => setNote(e.target.value)}
                    placeholder="Describe your review decision"
                  />
                </label>
                <div className="inline">
                  {[
                    ["VERIFIED", "Verify"],
                    ["DISMISSED", "Dismiss"],
                    ["UNDER REVIEW", "Further review"],
                  ].map(([action, label]) => (
                    <button
                      key={action}
                      className={action === "VERIFIED" ? "primary" : ""}
                      onClick={() =>
                        run(async () => {
                          await api(`/events/${id}/review`, {
                            method: "POST",
                            body: { action, note },
                          });
                          load();
                          refresh();
                        })
                      }
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </>
            )}
            {can("incident") && event.status === "VERIFIED" && (
              <>
                <label>
                  Incident title
                  <input
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                  />
                </label>
                <button
                  className="primary"
                  onClick={() =>
                    run(async () => {
                      await api(`/events/${id}/incident`, {
                        method: "POST",
                        body: {
                          title,
                          category: event.type,
                          priority: event.priority,
                        },
                      });
                      load();
                      refresh();
                    })
                  }
                >
                  Create incident
                </button>
              </>
            )}
          </div>
        </Panel>
      </div>
      <Panel title="Review history">
        {event.reviews.map((r, i) => (
          <div className="record" key={i}>
            <Badge value={r.action} />
            <div>
              <strong>
                {r.actor} · {fmtDate(r.timestamp)}
              </strong>
              <p>{r.note}</p>
            </div>
          </div>
        ))}
      </Panel>
      <Panel title="Related events">
        <EventTable
          events={event.related}
          openEvent={(id) =>
            openVideo(
              event.video_id,
              event.related.find((e) => e.id === id).video_time,
              event.job_id,
            )
          }
        />
      </Panel>
    </>
  );
}
function Incidents({ run, can, openEvent }) {
  const [rows, setRows] = useState([]),
    [users, setUsers] = useState([]),
    [selected, setSelected] = useState(""),
    [draft, setDraft] = useState({
      state: "ASSIGNED",
      assignment: "",
      note: "",
      priority: "MEDIUM",
    });
  const load = () =>
    run(async () => {
      setRows(await api("/incidents"));
      setUsers(await api("/users"));
    });
  useEffect(() => {
    load();
  }, []);
  const current = rows.find((i) => i.id === selected);
  const next = {
    VERIFIED: ["ASSIGNED"],
    ASSIGNED: ["RESPONDING"],
    RESPONDING: ["MONITORING", "RESOLVED"],
    MONITORING: ["RESPONDING", "RESOLVED"],
    RESOLVED: ["CLOSED"],
    CLOSED: [],
  };
  return (
    <div className="grid-two">
      <Panel title="Incident register">
        {rows.length ? (
          rows.map((i) => (
            <button
              className="record"
              key={i.id}
              onClick={() => {
                setSelected(i.id);
                setDraft({
                  state: next[i.state][0] || i.state,
                  assignment: i.assignment || "",
                  note: "",
                  priority: i.priority,
                });
              }}
            >
              <div>
                <small>{i.number}</small>
                <strong>{i.title}</strong>
                <small>
                  {i.assignment || "Unassigned"} ·{" "}
                  {i.location?.name || "Location not supplied"}
                </small>
              </div>
              <Badge value={i.state} />
            </button>
          ))
        ) : (
          <div className="stack">
            <p className="notice">Sample incidents below show how reports appear. They are examples, not live records.</p>
            {[
              ["SAMPLE-001", "Crowding at Meskel Square", "HIGH", "RESPONDING"],
              ["SAMPLE-002", "Stopped vehicle on Bole Road", "MEDIUM", "ASSIGNED"],
              ["SAMPLE-003", "Camera offline near Piazza", "HIGH", "MONITORING"],
            ].map(([number,title,priority,state]) => <div className="record" key={number}><div><small>{number} · DEMO</small><strong>{title}</strong><small>{priority} priority · Addis Ababa</small></div><Badge value={state} /></div>)}
            <small>Verify an event and create an incident to add a real report.</small>
          </div>
        )}
      </Panel>
      <Panel title={current?.number || "Incident workspace"}>
        {current ? (
          <div className="stack">
            <h2>{current.title}</h2>
            <Badge value={current.priority} />
            <p>{current.category}</p>
            {current.event.snapshot_url && (
              <img
                className="snapshot"
                src={current.event.snapshot_url}
                alt="Incident source snapshot"
              />
            )}
            <button onClick={() => openEvent(current.event_id)}>
              Open originating event and evidence
            </button>
            {current.timeline.map((t, i) => (
              <div className="timeline-record" key={i}>
                <strong>
                  {t.state} · {t.actor}
                </strong>
                <small>
                  {fmtDate(t.timestamp)} {t.assignment && `· ${t.assignment}`}
                </small>
                <p>{t.note}</p>
              </div>
            ))}
            {can("incident") && current.state !== "CLOSED" && (
              <>
                <label>
                  State
                  <select
                    value={draft.state}
                    onChange={(e) =>
                      setDraft({ ...draft, state: e.target.value })
                    }
                  >
                    {[current.state, ...next[current.state]].map((s) => (
                      <option key={s}>{s}</option>
                    ))}
                  </select>
                </label>
                <label>
                  Assign to
                  <select
                    value={draft.assignment}
                    onChange={(e) =>
                      setDraft({ ...draft, assignment: e.target.value })
                    }
                  >
                    <option value="">Select operational user</option>
                    {users
                      .filter(
                        (u) =>
                          u.enabled &&
                          [
                            "Administrator",
                            "Operator",
                            "Incident Controller",
                            "Supervisor",
                          ].includes(u.role),
                      )
                      .map((u) => (
                        <option key={u.id}>{u.username}</option>
                      ))}
                  </select>
                </label>
                <label>
                  Priority
                  <select
                    value={draft.priority}
                    onChange={(e) =>
                      setDraft({ ...draft, priority: e.target.value })
                    }
                  >
                    {["LOW", "MEDIUM", "HIGH", "CRITICAL"].map((p) => (
                      <option key={p}>{p}</option>
                    ))}
                  </select>
                </label>
                <label>
                  Update / resolution note
                  <textarea
                    value={draft.note}
                    onChange={(e) =>
                      setDraft({ ...draft, note: e.target.value })
                    }
                  />
                </label>
                <button
                  className="primary"
                  onClick={() =>
                    run(async () => {
                      await api(`/incidents/${current.id}`, {
                        method: "PUT",
                        body: {
                          ...draft,
                          assignment: draft.assignment || null,
                        },
                      });
                      await load();
                      setDraft((d) => ({ ...d, note: "" }));
                    })
                  }
                >
                  Record update
                </button>
              </>
            )}
          </div>
        ) : (
          <Empty>Select an incident to coordinate its response.</Empty>
        )}
      </Panel>
    </div>
  );
}
function Sense({ run, can }) {
  const [data, setData] = useState(null),
    [speed, setSpeed] = useState(1),
    [trail, setTrail] = useState([]);
  useEffect(() => {
    let live = true;
    const update = () =>
      api("/simulation")
        .then((s) => {
          if (live) {
            setData(s);
            setTrail((t) =>
              s.observation.presence
                ? [...t, [s.observation.x, s.observation.y]].slice(-100)
                : [],
            );
          }
        })
        .catch(() => {});
    update();
    const id = setInterval(update, 250);
    return () => {
      live = false;
      clearInterval(id);
    };
  }, []);
  const o = data?.observation;
  const control = (mode) =>
    run(async () => {
      await api("/simulation", { method: "POST", body: { mode, speed } });
      setTrail([]);
    });
  if (!o) return <Empty>Connecting to simulation provider…</Empty>;
  const edges = [
    [0, 1],
    [1, 2],
    [1, 3],
    [2, 4],
    [3, 5],
    [1, 6],
    [6, 7],
    [6, 8],
  ];
  return (
    <>
      <div className="simulation-banner">
        SIMULATED RF/CSI DATA — MVP DEMONSTRATION
      </div>
      <Metrics
        items={[
          ["PRESENCE", o.presence ? "DETECTED" : "NONE"],
          ["MOVEMENT", o.movement],
          ["POSE", o.pose],
          ["CONFIDENCE", `${Math.round(o.confidence * 100)}%`],
        ]}
      />
      <div className="analysis-layout">
        <Panel
          title="RF Room 01 / floor plan"
          action={<span className="eyebrow">8 × 6 METERS · SIMULATED</span>}
        >
          <svg className="floorplan" viewBox="0 0 880 690">
            <defs>
              <pattern
                id="grid"
                width="50"
                height="50"
                patternUnits="userSpaceOnUse"
              >
                <path
                  d="M 50 0 L 0 0 0 50"
                  fill="none"
                  stroke="#253443"
                  strokeWidth="1"
                />
              </pattern>
              <clipPath id="roomClip">
                <rect x="40" y="40" width="800" height="600" />
              </clipPath>
            </defs>
            <rect width="880" height="690" fill="#101a24" />
            <rect x="40" y="40" width="800" height="600" fill="url(#grid)" />
            <g clipPath="url(#roomClip)">
              {o.nodes.map((n) => (
                <g key={n.id}>
                  <circle
                    cx={40 + n.x * 100}
                    cy={40 + n.y * 100}
                    r="280"
                    fill="#4680a5"
                    fillOpacity=".04"
                    stroke="#426078"
                    strokeDasharray="5 9"
                  />
                  <circle
                    cx={40 + n.x * 100}
                    cy={40 + n.y * 100}
                    r="160"
                    fill="none"
                    stroke="#34516a"
                    strokeDasharray="4 8"
                  />
                </g>
              ))}
              <polyline
                points={trail
                  .map(([x, y]) => `${40 + x * 100},${40 + y * 100}`)
                  .join(" ")}
                fill="none"
                stroke="#73b7c8"
                strokeWidth="2"
                opacity=".55"
              />
            </g>
            <path
              d="M40 285 V40 H840 V640 H40 V390"
              fill="none"
              stroke="#9baab5"
              strokeWidth="7"
            />
            <path
              d="M40 390 H145 M145 390 A105 105 0 0 0 40 285"
              fill="none"
              stroke="#697f8e"
              strokeWidth="2"
            />
            <text x="60" y="440" fill="#899ca9" fontSize="12">
              ENTRY
            </text>
            <rect
              x="610"
              y="90"
              width="150"
              height="70"
              fill="#23313d"
              stroke="#546674"
            />
            <text x="642" y="130" fill="#94a5b4" fontSize="13">
              WORKSTATION
            </text>
            <rect
              x="610"
              y="200"
              width="70"
              height="50"
              fill="#23313d"
              stroke="#546674"
            />
            <text x="40" y="675" fill="#aab7c4" fontSize="13">
              FLOOR 01 · CONTROLLED TEST ROOM
            </text>
            {o.nodes.map((n) => (
              <g key={n.id}>
                <circle
                  cx={40 + n.x * 100}
                  cy={40 + n.y * 100}
                  r="9"
                  fill="#81b9df"
                />
                <circle
                  cx={40 + n.x * 100}
                  cy={40 + n.y * 100}
                  r="17"
                  fill="none"
                  stroke="#81b9df"
                />
                <text
                  x={65 + n.x * 100}
                  y={40 + n.y * 100}
                  fill="#cad5de"
                  fontSize="14"
                >
                  {n.id}
                </text>
              </g>
            ))}
            {o.presence && (
              <g transform={`translate(${40 + o.x * 100},${40 + o.y * 100})`}>
                <ellipse cy="48" rx="25" ry="10" fill="#7ccac0" opacity=".12" />
                {edges.map(([a, b], i) => (
                  <line
                    key={i}
                    x1={o.joints[a][0] * 100}
                    y1={o.joints[a][1] * 100}
                    x2={o.joints[b][0] * 100}
                    y2={o.joints[b][1] * 100}
                    stroke={o.pose === "FALLING" ? "#e6b35c" : "#80cfc4"}
                    strokeWidth="5"
                    strokeLinecap="round"
                  />
                ))}
                <circle
                  cx={o.joints[0][0] * 100}
                  cy={o.joints[0][1] * 100 - 9}
                  r="10"
                  stroke="#80cfc4"
                  strokeWidth="3"
                  fill="#15252d"
                />
                <text x="30" y="-30" fill="#d8eee9" fontSize="12">
                  SIM-P01
                </text>
              </g>
            )}
          </svg>
        </Panel>
        <div>
          <Panel title="Demo controls">
            <div className="stack">
              <p>
                Repeatable synthetic observations. No RF hardware is connected.
              </p>
              <div className="control-grid">
                {[
                  "No Person",
                  "Enter Room",
                  "Walk",
                  "Stand",
                  "Sit",
                  "Fall",
                  "Exit Room",
                  "Random Movement",
                  "Moving Left",
                  "Moving Right",
                ].map((m) => (
                  <button
                    disabled={!can("operate")}
                    className={data.mode === m ? "selected" : ""}
                    key={m}
                    onClick={() => control(m)}
                  >
                    {m}
                  </button>
                ))}
              </div>
              <label>
                Simulation speed · {speed}×
                <input
                  type="range"
                  min=".25"
                  max="4"
                  step=".25"
                  value={speed}
                  onChange={(e) => setSpeed(+e.target.value)}
                  onPointerUp={() => control(data.mode)}
                />
              </label>
              <div className="stat-row">
                <span>Position</span>
                <strong>
                  {o.x.toFixed(2)}, {o.y.toFixed(2)} m
                </strong>
              </div>
              {o.nodes.map((n) => (
                <div className="stat-row" key={n.id}>
                  <span>CSI node {n.id}</span>
                  <Badge value={`${Math.round(n.quality * 100)}% QUALITY`} />
                </div>
              ))}
            </div>
          </Panel>
          <Panel title="Synthetic CSI subcarriers">
            <svg viewBox="0 0 320 100" className="waveform">
              <polyline
                points={o.csi_amplitude
                  .map((v, i) => `${i * 10},${90 - (v - 0.7) * 130}`)
                  .join(" ")}
                fill="none"
                stroke="#80b7d0"
                strokeWidth="2"
              />
            </svg>
            <small className="pad">Synthetic amplitude · 32 subcarriers</small>
          </Panel>
        </div>
      </div>
      <div className="grid-two">
        <Panel title="Simulation timeline">
          {data.timeline
            ?.slice()
            .reverse()
            .map((e, i) => (
              <div className="stat-row" key={i}>
                <strong>{e.mode}</strong>
                <span>{fmtDate(e.timestamp)}</span>
              </div>
            ))}
        </Panel>
        <Panel title="Normalized sensor observation">
          <pre>
            {JSON.stringify(
              { ...o, joints: undefined, csi_amplitude: undefined },
              null,
              2,
            )}
          </pre>
        </Panel>
      </div>
    </>
  );
}
function Analytics({ run, revision }) {
  const [d, setD] = useState(null);
  useEffect(() => {
    run(async () => setD(await api("/analytics")));
  }, [revision]);
  if (!d) return <Empty>Loading metadata…</Empty>;
  return (
    <>
      <Metrics
        items={[
          ["PEOPLE TRACKS", d.people_observed],
          ["VEHICLE TRACKS", d.vehicles_observed],
          ["EVENTS", d.event_count],
          ["VIDEOS PROCESSED", d.videos_analyzed],
          ["AVG PROCESSING", clock(d.average_processing_time)],
        ]}
      />
      <div className="grid-two">
        {[
          ["Events by type", d.events_by_type],
          ["Events over time", d.events_over_time],
        ].map(([title, values]) => (
          <Panel key={title} title={title}>
            <div className="chart">
              {Object.entries(values).length ? (
                Object.entries(values).map(([key, n]) => (
                  <div key={key}>
                    <span>{key}</span>
                    <div
                      className="bar"
                      style={{
                        width: `${Math.max(2, (n / Math.max(...Object.values(values))) * 100)}%`,
                      }}
                    />
                    <strong>{n}</strong>
                  </div>
                ))
              ) : (
                <Empty>No processed event metadata yet.</Empty>
              )}
            </div>
          </Panel>
        ))}
      </div>
      <p className="notice">
        People and vehicle totals use the latest completed analysis per video to
        avoid counting reanalysis twice. Event totals include all retained
        analysis runs.
      </p>
    </>
  );
}
function GIS({ videos, run, openVideo, openCamera }) {
  const holder = useRef(null),
    mapRef = useRef(null),
    [id, setId] = useState(""),
    [location, setLocation] = useState({
      name: "",
      latitude: 9.03,
      longitude: 38.74,
    }),
    [layer, setLayer] = useState("cameras"),
    [incidents, setIncidents] = useState([]),
    [events, setEvents] = useState([]),
    [cameras, setCameras] = useState([]),
    [localVideos, setLocalVideos] = useState(videos);
  useEffect(() => {
    setLocalVideos(videos);
  }, [videos]);
  useEffect(() => {
    run(async () => {
      setIncidents(await api("/incidents"));
      setEvents(await api("/events"));
      setCameras(await api("/cameras"));
    });
  }, []);
  useEffect(() => {
    let map,
      live = true;
    run(async () => {
      const { default: maplibre } = await import("maplibre-gl");
      await import("maplibre-gl/dist/maplibre-gl.css");
      if (!live) return;
      map = new maplibre.Map({
        container: holder.current,
        style: {
          version: 8,
          sources: {
            osm: {
              type: "raster",
              tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
              tileSize: 256,
              attribution: "© OpenStreetMap contributors",
            },
          },
          layers: [
            {
              id: "osm",
              type: "raster",
              source: "osm",
              paint: {
                "raster-saturation": -0.7,
                "raster-brightness-max": 0.65,
              },
            },
          ],
        },
        center: [38.75, 9.03],
        zoom: 11,
      });
      mapRef.current = map;
      map.addControl(new maplibre.NavigationControl());
      const items =
        layer === "cameras"
          ? cameras.map((c) => ({...c, camera: c}))
          : layer === "analysis"
          ? localVideos
          : layer === "events"
            ? events.map((e) => ({
                ...localVideos.find((v) => v.id === e.video_id),
                event: e,
              }))
            : incidents.map((i) => ({
                ...localVideos.find((v) => v.id === i.event.video_id),
                event: i.event,
                incident: i,
              }));
      for (const v of items) {
        if (v.location?.longitude == null) continue;
        const button = document.createElement("button");
        button.className = "map-marker";
        button.textContent = layer === "cameras" ? "C" : layer === "analysis" ? "V" : layer === "events" ? "E" : "I";
        button.title = `${v.location.name} · ${v.camera?.name || v.filename}`;
        button.onclick = () => v.camera ? openCamera(v.camera.id) : openVideo(v.id, v.event?.video_time ?? null, v.event?.job_id);
        new maplibre.Marker({ element: button })
          .setLngLat([v.location.longitude, v.location.latitude])
          .addTo(map);
      }
    });
    return () => {
      live = false;
      map?.remove();
    };
  }, [localVideos, layer, events, incidents, cameras]);
  return (
    <>
      <p className="notice">
        Addis Ababa camera points use the demonstration coordinates supplied in Live Cameras. Base map requires network access.
      </p>
      <div className="toolbar">
        <label>
          Map layer
          <select value={layer} onChange={(e) => setLayer(e.target.value)}>
            <option value="analysis">Analyses</option>
            <option value="cameras">Live cameras</option>
            <option value="events">Events</option>
            <option value="incidents">Incidents</option>
          </select>
        </label>
      </div>
      <div className="map" ref={holder} />
      <Panel title="Associate a demonstration location">
        <form
          className="form-grid"
          onSubmit={(e) => {
            e.preventDefault();
            run(async () => {
              await api(`/videos/${id}/location`, {
                method: "PUT",
                body: location,
              });
              setLocalVideos(await api("/videos"));
            });
          }}
        >
          <label>
            Video
            <select value={id} required onChange={(e) => setId(e.target.value)}>
              <option value="">Choose video</option>
              {videos.map((v) => (
                <option key={v.id} value={v.id}>
                  {v.filename}
                </option>
              ))}
            </select>
          </label>
          <label>
            Location name
            <input
              required
              value={location.name}
              onChange={(e) =>
                setLocation({ ...location, name: e.target.value })
              }
            />
          </label>
          {["latitude", "longitude"].map((k) => (
            <label key={k}>
              {k}
              <input
                type="number"
                step="any"
                value={location[k]}
                onChange={(e) =>
                  setLocation({ ...location, [k]: +e.target.value })
                }
              />
            </label>
          ))}
          <button className="primary">Save supplied location</button>
        </form>
      </Panel>
    </>
  );
}
function Admin({ run, can, health, videos, jobs }) {
  const [tab, setTab] = useState("System Health"),
    [users, setUsers] = useState([]),
    [roles, setRoles] = useState({}),
    [audit, setAudit] = useState([]),
    [query, setQuery] = useState(""),
    [draft, setDraft] = useState({
      username: "",
      password: "",
      role: "Operator",
    }),
    [models, setModels] = useState([]),
    [modelDraft, setModelDraft] = useState({
      name: "",
      version: "",
      filename: "",
    });
  const load = () =>
    run(async () => {
      setUsers(await api("/users"));
      setRoles(await api("/roles"));
      setModels(await api("/models"));
      if (can("audit"))
        setAudit(await api("/audit?q=" + encodeURIComponent(query)));
    });
  useEffect(() => {
    load();
  }, []);
  return (
    <>
      <div className="tabs">
        {[
          "System Health",
          "Videos",
          "Analysis Jobs",
          "Users & Roles",
          "Models",
          "Audit",
        ].map((t) => (
          <button
            className={tab === t ? "selected" : ""}
            key={t}
            onClick={() => setTab(t)}
          >
            {t}
          </button>
        ))}
      </div>
      <Panel title={tab}>
        {tab === "System Health" ? (
          <>
            {Object.entries(health)
              .filter(([, v]) => typeof v !== "object")
              .map(([k, v]) => (
                <div className="stat-row" key={k}>
                  <span>{k.replaceAll("_", " ")}</span>
                  <Badge value={String(v)} />
                </div>
              ))}
            {Object.entries(health.gpu || {}).map(([k, v]) => (
              <div className="stat-row" key={"gpu-" + k}>
                <span>gpu {k.replaceAll("_", " ")}</span>
                <span>{v ?? "Not exposed by platform"}</span>
              </div>
            ))}
          </>
        ) : tab === "Videos" ? (
          videos.map((v) => (
            <div className="record" key={v.id}>
              <strong>{v.filename}</strong>
              <span>{clock(v.metadata_json.duration)}</span>
              {can("admin") && (
                <button
                  onClick={() =>
                    run(async () => {
                      await api(`/videos/${v.id}/archive`, { method: "POST" });
                      location.reload();
                    })
                  }
                >
                  Archive
                </button>
              )}
            </div>
          ))
        ) : tab === "Analysis Jobs" ? (
          jobs.map((j) => (
            <div className="record" key={j.id}>
              <strong>{j.id.slice(0, 10)}</strong>
              <span>
                {j.mode} · {j.progress.toFixed(1)}%
              </span>
              <Badge value={j.state} />
            </div>
          ))
        ) : tab === "Models" ? (
          <div className="stack">
            <h3>YOLO11 nano · COCO classes</h3>
            <p>
              Configured through MODEL_PATH and DEVICE. Each job records its
              model path and inference settings.
            </p>
            <p>
              Supervision normalizes and annotates detections. Roboflow Trackers
              provides ByteTrack behind the tracking adapter.
            </p>
            <p>
              Model installation: <code>python scripts/download_model.py</code>
            </p>
            {models.map((m) => (
              <div key={m.id}>
                <strong>
                  {m.name} · {m.version}
                </strong>
                <small>
                  {m.filename} ·{" "}
                  {m.available ? "Weights available" : "Weights missing"}
                  <br />
                  {m.sha256 || "Checksum recorded at activation / analysis"}
                </small>
                <label>
                  Registry state
                  <select
                    disabled={!can("admin")}
                    value={m.state}
                    onChange={(e) =>
                      run(async () => {
                        await api(`/models/${m.id}/state`, {
                          method: "PUT",
                          body: { state: e.target.value },
                        });
                        load();
                      })
                    }
                  >
                    {[
                      "TESTING",
                      "APPROVED",
                      "ACTIVE",
                      "DEPRECATED",
                      "DISABLED",
                    ].map((state) => (
                      <option key={state}>{state}</option>
                    ))}
                  </select>
                </label>
              </div>
            ))}
            {can("admin") && (
              <form
                className="stack"
                onSubmit={(e) => {
                  e.preventDefault();
                  run(async () => {
                    await api("/models", { method: "POST", body: modelDraft });
                    load();
                  });
                }}
              >
                <h3>Register approved local weights</h3>
                {["name", "version", "filename"].map((k) => (
                  <label key={k}>
                    {k}
                    <input
                      required
                      value={modelDraft[k]}
                      onChange={(e) =>
                        setModelDraft({ ...modelDraft, [k]: e.target.value })
                      }
                    />
                  </label>
                ))}
                <button>Register model</button>
              </form>
            )}
            <Badge value={health.Detector || "OFFLINE"} />
          </div>
        ) : tab === "Users & Roles" ? (
          <>
            <div className="stack">
              {users.map((u) => (
                <div className="stat-row" key={u.id}>
                  <strong>{u.username}</strong>
                  <span>{u.enabled ? "Enabled" : "Disabled"}</span>
                  {can("admin") ? (
                    <select
                      aria-label={`Role for ${u.username}`}
                      value={u.role}
                      onChange={(e) =>
                        run(async () => {
                          await api(`/users/${u.id}/role`, {
                            method: "PUT",
                            body: { role: e.target.value },
                          });
                          load();
                        })
                      }
                    >
                      {Object.keys(roles).map((r) => (
                        <option key={r}>{r}</option>
                      ))}
                    </select>
                  ) : (
                    <span>{u.role}</span>
                  )}
                  {can("admin") && u.enabled && (
                    <button
                      onClick={() =>
                        run(async () => {
                          await api(`/users/${u.id}/disable`, {
                            method: "POST",
                          });
                          load();
                        })
                      }
                    >
                      Disable
                    </button>
                  )}
                </div>
              ))}
            </div>
            {can("admin") && (
              <form
                className="form-grid"
                onSubmit={(e) => {
                  e.preventDefault();
                  run(async () => {
                    await api("/users", { method: "POST", body: draft });
                    setDraft({ ...draft, username: "", password: "" });
                    load();
                  });
                }}
              >
                <label>
                  Username
                  <input
                    required
                    value={draft.username}
                    onChange={(e) =>
                      setDraft({ ...draft, username: e.target.value })
                    }
                  />
                </label>
                <label>
                  Password (12+ characters)
                  <input
                    type="password"
                    minLength="12"
                    required
                    value={draft.password}
                    onChange={(e) =>
                      setDraft({ ...draft, password: e.target.value })
                    }
                  />
                </label>
                <label>
                  Role
                  <select
                    value={draft.role}
                    onChange={(e) =>
                      setDraft({ ...draft, role: e.target.value })
                    }
                  >
                    {Object.keys(roles).map((r) => (
                      <option key={r}>{r}</option>
                    ))}
                  </select>
                </label>
                <button className="primary">Create user</button>
              </form>
            )}
            <div className="stack">
              {Object.entries(roles).map(([role, permissions]) => (
                <div className="stat-row" key={role}>
                  <strong>{role}</strong>
                  {can("admin") && role !== "Administrator" ? (
                    <div className="inline">
                      {[
                        "read",
                        "operate",
                        "configure",
                        "review",
                        "incident",
                        "admin",
                        "audit",
                      ].map((p) => (
                        <label className="check" key={p}>
                          <input
                            type="checkbox"
                            checked={permissions.includes(p)}
                            onChange={(e) =>
                              run(async () => {
                                await api(
                                  `/roles/${encodeURIComponent(role)}`,
                                  {
                                    method: "PUT",
                                    body: {
                                      permissions: e.target.checked
                                        ? [...permissions, p]
                                        : permissions.filter((x) => x !== p),
                                    },
                                  },
                                );
                                load();
                              })
                            }
                          />
                          {p}
                        </label>
                      ))}
                    </div>
                  ) : (
                    <span>{permissions.join(", ")}</span>
                  )}
                </div>
              ))}
            </div>
          </>
        ) : tab === "Audit" ? (
          <>
            <form
              className="toolbar"
              onSubmit={(e) => {
                e.preventDefault();
                load();
              }}
            >
              <input
                placeholder="Filter actor, action or resource"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
              <button>Search audit</button>
            </form>
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>TIME</th>
                    <th>ACTOR</th>
                    <th>ACTION</th>
                    <th>RESOURCE / DETAIL</th>
                  </tr>
                </thead>
                <tbody>
                  {audit.map((a) => (
                    <tr key={a.id}>
                      <td>{fmtDate(a.created_at)}</td>
                      <td>{a.actor}</td>
                      <td>{a.action}</td>
                      <td>
                        <small>{a.resource}</small>
                        <details>
                          <summary>Details</summary>
                          <pre>{JSON.stringify(a.detail, null, 2)}</pre>
                        </details>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        ) : null}
      </Panel>
      <p className="notice">
        Configure zones, lines and their rules in the video workspace.
        Simulation settings are available in ARGUS Sense.
      </p>
    </>
  );
}
function Demo({ run, refresh, can, videos, openVideo, navigate }) {
  const [selected, setSelected] = useState(""),
    [result, setResult] = useState("");
  return (
    <>
      <div className="review-banner">
        DEMO CONTROL · Video scenarios run real inference. RF scenarios use
        labeled synthetic observations.
      </div>
      <div className="grid-two">
        <Panel title="Video scenario launcher">
          <div className="stack">
            <label>
              Load an uploaded sample
              <select
                value={selected}
                onChange={(e) => setSelected(e.target.value)}
              >
                <option value="">Select your authorized sample</option>
                {videos.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.filename}
                  </option>
                ))}
              </select>
            </label>
            <p>No sample surveillance footage is downloaded or preloaded.</p>
            {[
              ["Event / Crowd", "Crowd Zone", "person"],
              ["Traffic", "No-Stopping Zone", "vehicle"],
              ["Convoy", "Convoy Corridor", "vehicle"],
            ].map(([mode, type, cls]) => (
              <button
                key={mode}
                disabled={!selected || !can("operate")}
                onClick={() =>
                  run(async () => {
                    await api(`/videos/${selected}/geometries`, {
                      method: "POST",
                      body: {
                        kind: "zone",
                        name: `Demo ${mode}`,
                        type,
                        object_class: cls,
                        points: [
                          [0.1, 0.1],
                          [0.9, 0.1],
                          [0.9, 0.95],
                          [0.1, 0.95],
                        ],
                        threshold: 3,
                        dwell_seconds: 5,
                        stop_seconds: 3,
                        severity: "MEDIUM",
                      },
                    });
                    await api(`/videos/${selected}/geometries`, {
                      method: "POST",
                      body: {
                        kind: "line",
                        name: "Demo counting line",
                        points: [
                          [0.5, 0.1],
                          [0.5, 0.95],
                        ],
                        object_class: cls,
                      },
                    });
                    await api(`/videos/${selected}/jobs`, {
                      method: "POST",
                      body: { mode, fps: 5, congestion_count: 5 },
                    });
                    refresh();
                    openVideo(selected);
                  })
                }
              >
                Run {mode} scenario
              </button>
            ))}
            <small>
              Presets draw a broad zone and vertical counting line. Adjust these
              to match the actual scene for meaningful measurements.
            </small>
          </div>
        </Panel>
        <Panel title="RF demonstration">
          <div className="stack">
            <h2>One room. Two CSI nodes.</h2>
            <p>
              Repeat presence, movement and pose states using the deterministic
              simulator.
            </p>
            <button
              className="primary"
              onClick={() =>
                run(async () => {
                  await api("/simulation", {
                    method: "POST",
                    body: { mode: "Enter Room", speed: 1 },
                  });
                  navigate("ARGUS Sense");
                })
              }
            >
              Start RF room scenario
            </button>
            <Badge value="SIMULATED RF / CSI" />
          </div>
        </Panel>
      </div>
      {can("admin") && (
        <Panel title="Reset demonstration workflow">
          <div className="stack">
            <p>
              Clear incidents or events to repeat the presentation. Reset also
              clears the RF session. Uploaded videos, analysis results and audit
              records are retained. Clearing events also removes their linked
              incidents.
            </p>
            <div className="inline">
              {[
                ["clear-incidents", "Clear incidents"],
                ["clear-events", "Clear events and incidents"],
                ["reset", "Reset demo workflow"],
              ].map(([action, label]) => (
                <button
                  key={action}
                  onClick={() => {
                    if (
                      window.confirm(
                        `${label}? This deletes the selected workflow records and preserves the audit trail.`,
                      )
                    )
                      run(async () => {
                        await api(`/demo/${action}`, { method: "POST" });
                        setResult(label + " completed");
                        refresh();
                      });
                  }}
                >
                  {label}
                </button>
              ))}
            </div>
            {result && <p>{result}</p>}
          </div>
        </Panel>
      )}
    </>
  );
}

createRoot(document.getElementById("root")).render(<App />);
