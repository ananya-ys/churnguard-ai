import { useState, useEffect, useCallback } from "react";
import { Routes, Route, Navigate, Link, useLocation } from "react-router-dom";

const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

// ── Auth helpers ────────────────────────────────────────────────────────────
function getToken() { return localStorage.getItem("token") ?? ""; }
function setToken(t) { localStorage.setItem("token", t); }
function clearToken() { localStorage.removeItem("token"); }

async function apiFetch(path, opts = {}) {
  const token = getToken();
  const res = await fetch(`${API}${path}`, {
    ...opts,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(opts.headers ?? {}),
    },
  });
  if (res.status === 401) { clearToken(); window.location.href = "/login"; }
  return res;
}

// ── Reusable UI components ─────────────────────────────────────────────────
const Card = ({ children, className = "" }) => (
  <div className={`bg-gray-800 border border-gray-700 rounded-xl p-5 ${className}`}>{children}</div>
);

const Badge = ({ children, color = "blue" }) => {
  const colors = {
    blue: "bg-blue-900/50 text-blue-300 border border-blue-700",
    green: "bg-green-900/50 text-green-300 border border-green-700",
    yellow: "bg-yellow-900/50 text-yellow-300 border border-yellow-700",
    red: "bg-red-900/50 text-red-300 border border-red-700",
    purple: "bg-purple-900/50 text-purple-300 border border-purple-700",
    gray: "bg-gray-700 text-gray-300 border border-gray-600",
  };
  return (
    <span className={`text-xs font-mono px-2 py-0.5 rounded ${colors[color] ?? colors.gray}`}>
      {children}
    </span>
  );
};

const Stat = ({ label, value, sub, color = "text-white" }) => (
  <div className="flex flex-col gap-0.5">
    <span className="text-xs text-gray-400 uppercase tracking-wider">{label}</span>
    <span className={`text-2xl font-bold font-mono ${color}`}>{value}</span>
    {sub && <span className="text-xs text-gray-500">{sub}</span>}
  </div>
);

const Btn = ({ children, onClick, disabled, variant = "primary", size = "md", className = "" }) => {
  const base = "rounded-lg font-medium transition-all duration-150 focus:outline-none";
  const sizes = { sm: "px-3 py-1.5 text-sm", md: "px-4 py-2 text-sm", lg: "px-6 py-3 text-base" };
  const variants = {
    primary: "bg-violet-600 hover:bg-violet-500 text-white disabled:opacity-40",
    secondary: "bg-gray-700 hover:bg-gray-600 text-gray-200 border border-gray-600",
    danger: "bg-red-700 hover:bg-red-600 text-white",
    ghost: "text-gray-400 hover:text-white hover:bg-gray-700",
  };
  return (
    <button onClick={onClick} disabled={disabled}
      className={`${base} ${sizes[size]} ${variants[variant]} ${className}`}>
      {children}
    </button>
  );
};

// ── Layout + Nav ────────────────────────────────────────────────────────────
function Layout({ children }) {
  const { pathname } = useLocation();
  const nav = [
    { to: "/", label: "Dashboard", icon: "⚡" },
    { to: "/predict", label: "Predict", icon: "🔮" },
    { to: "/batch", label: "Batch Jobs", icon: "📦" },
    { to: "/models", label: "Models", icon: "🤖" },
    { to: "/experiments", label: "Experiments", icon: "🧪" },
    { to: "/drift", label: "Drift", icon: "📊" },
    { to: "/explain", label: "Explain", icon: "🧠" },
    { to: "/abtests", label: "A/B Tests", icon: "⚗️" },
  ];
  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 flex">
      <aside className="w-56 bg-gray-900 border-r border-gray-800 flex flex-col py-6 px-3 gap-1">
        <div className="px-3 pb-6">
          <div className="text-violet-400 font-bold text-lg">ChurnGuard AI</div>
          <div className="text-gray-500 text-xs mt-0.5">v4.0 MLOps Platform</div>
        </div>
        {nav.map(n => (
          <Link key={n.to} to={n.to}
            className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors
              ${pathname === n.to
                ? "bg-violet-900/50 text-violet-300 border border-violet-800"
                : "text-gray-400 hover:text-gray-200 hover:bg-gray-800"}`}>
            <span>{n.icon}</span>{n.label}
          </Link>
        ))}
        <div className="mt-auto px-3">
          <Btn variant="ghost" size="sm" onClick={() => { clearToken(); window.location.href = "/login"; }} className="w-full text-left">
            Sign out
          </Btn>
        </div>
      </aside>
      <main className="flex-1 overflow-auto p-8">{children}</main>
    </div>
  );
}

// ── Login page ──────────────────────────────────────────────────────────────
function Login({ onLogin }) {
  const [email, setEmail] = useState("");
  const [pw, setPw] = useState("");
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setLoading(true); setErr("");
    const form = new URLSearchParams();
    form.append("username", email); form.append("password", pw);
    const res = await fetch(`${API}/api/v1/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: form,
    });
    setLoading(false);
    if (!res.ok) { setErr("Invalid credentials"); return; }
    const data = await res.json();
    setToken(data.access_token);
    onLogin();
  }

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center">
      <div className="w-96">
        <div className="text-center mb-8">
          <div className="text-4xl mb-2">⚡</div>
          <h1 className="text-2xl font-bold text-white">ChurnGuard AI</h1>
          <p className="text-gray-400 text-sm mt-1">MLOps Production Platform</p>
        </div>
        <Card>
          <form onSubmit={submit} className="flex flex-col gap-4">
            <div>
              <label className="block text-xs text-gray-400 mb-1">Email</label>
              <input value={email} onChange={e => setEmail(e.target.value)}
                className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-violet-500"
                placeholder="admin@example.com" type="email" required />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">Password</label>
              <input value={pw} onChange={e => setPw(e.target.value)}
                className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-violet-500"
                placeholder="••••••••" type="password" required />
            </div>
            {err && <p className="text-red-400 text-xs">{err}</p>}
            <Btn disabled={loading}>{loading ? "Signing in…" : "Sign in"}</Btn>
          </form>
        </Card>
      </div>
    </div>
  );
}

// ── Dashboard page ──────────────────────────────────────────────────────────
function Dashboard() {
  const [health, setHealth] = useState(null);
  const [active, setActive] = useState(null);
  const [metricsSummary, setMetricsSummary] = useState(null);
  const [drift, setDrift] = useState(null);

  useEffect(() => {
    fetch(`${API}/health`).then(r => r.json()).then(setHealth).catch(() => {});
    apiFetch("/api/v1/models/active").then(r => r.ok ? r.json() : null).then(setActive).catch(() => {});
    apiFetch("/api/v1/metrics/summary").then(r => r.ok ? r.json() : null).then(setMetricsSummary).catch(() => {});
    apiFetch("/api/v1/drift/latest").then(r => r.ok ? r.json() : null).then(setDrift).catch(() => {});
  }, []);

  const driftColor = !drift ? "gray"
    : drift.severity === "severe" ? "red"
    : drift.severity === "moderate" ? "yellow"
    : "green";

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">System Dashboard</h1>
        <p className="text-gray-400 text-sm mt-1">Live system health and MLOps metrics</p>
      </div>

      {/* Health row */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: "API", val: health?.status ?? "…", ok: health?.status === "ok" },
          { label: "Database", val: health?.database ?? "…", ok: health?.database === "ok" },
          { label: "Redis", val: health?.redis ?? "…", ok: health?.redis === "ok" },
          { label: "Model", val: health?.model_loaded ? "Loaded" : "Not loaded", ok: health?.model_loaded },
        ].map(({ label, val, ok }) => (
          <Card key={label}>
            <Stat label={label} value={val}
              color={ok === true ? "text-green-400" : ok === false ? "text-red-400" : "text-gray-400"} />
          </Card>
        ))}
      </div>

      {/* Model + drift row */}
      <div className="grid grid-cols-3 gap-4">
        <Card className="col-span-2">
          <div className="flex items-start justify-between mb-4">
            <div>
              <h2 className="font-semibold text-white">Active Model</h2>
              <p className="text-xs text-gray-400 mt-0.5">Currently serving predictions</p>
            </div>
            {active && <Badge color="green">active</Badge>}
          </div>
          {active ? (
            <div className="grid grid-cols-4 gap-4">
              <Stat label="Version" value={active.version_tag} color="text-violet-400" />
              <Stat label="AUC-ROC" value={active.auc_roc?.toFixed(4)} color="text-emerald-400" />
              <Stat label="F1 Score" value={active.f1_score?.toFixed(4)} color="text-blue-400" />
              <Stat label="Precision" value={active.precision?.toFixed(4)} color="text-amber-400" />
            </div>
          ) : (
            <p className="text-gray-500 text-sm">No active model — run pipeline.sh to train</p>
          )}
        </Card>

        <Card>
          <div className="flex items-start justify-between mb-4">
            <h2 className="font-semibold text-white">Latest Drift</h2>
            {drift && <Badge color={driftColor}>{drift.severity}</Badge>}
          </div>
          {drift ? (
            <div className="space-y-3">
              <Stat label="PSI Score" value={drift.overall_drift_score?.toFixed(4)}
                color={driftColor === "red" ? "text-red-400" : driftColor === "yellow" ? "text-yellow-400" : "text-green-400"} />
              <Stat label="Features Drifted" value={drift.drifted_feature_count} />
              <Stat label="Live Samples" value={drift.sample_size_live?.toLocaleString()} />
            </div>
          ) : (
            <p className="text-gray-500 text-sm">No drift check yet</p>
          )}
          <div className="mt-4">
            <Link to="/drift"><Btn variant="secondary" size="sm">View Details →</Btn></Link>
          </div>
        </Card>
      </div>

      {/* Phase roadmap */}
      <Card>
        <h2 className="font-semibold text-white mb-4">Phase Completion</h2>
        <div className="grid grid-cols-6 gap-3">
          {[
            { phase: 1, name: "Automation", done: true },
            { phase: 2, name: "ML Lifecycle", done: true },
            { phase: 3, name: "Observability", done: true },
            { phase: 4, name: "Drift", done: true },
            { phase: 5, name: "CI/CD", done: true },
            { phase: 6, name: "Differentiators", done: true },
          ].map(({ phase, name, done }) => (
            <div key={phase}
              className={`rounded-lg p-3 text-center border ${done
                ? "border-violet-700 bg-violet-900/20" : "border-gray-700 bg-gray-800/50"}`}>
              <div className={`text-lg font-bold ${done ? "text-violet-400" : "text-gray-600"}`}>P{phase}</div>
              <div className="text-xs text-gray-400 mt-0.5">{name}</div>
              <div className="mt-1">{done ? "✅" : "⏳"}</div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

// ── Models page ──────────────────────────────────────────────────────────────
function Models() {
  const [models, setModels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [promoting, setPromoting] = useState(null);
  const [msg, setMsg] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    const r = await apiFetch("/api/v1/models");
    if (r.ok) setModels(await r.json());
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  async function promote(id, tag) {
    setPromoting(id);
    const r = await apiFetch(`/api/v1/models/${id}/promote`, { method: "POST" });
    const data = await r.json();
    setMsg(r.ok ? `✅ Promoted ${tag}` : `❌ ${data.message}`);
    if (r.ok) load();
    setPromoting(null);
  }

  async function rollback() {
    const r = await apiFetch("/api/v1/models/rollback", { method: "POST" });
    const data = await r.json();
    setMsg(r.ok ? `✅ Rolled back to ${data.version_tag}` : `❌ ${data.message}`);
    if (r.ok) load();
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Model Registry</h1>
          <p className="text-gray-400 text-sm mt-1">All registered model versions</p>
        </div>
        <Btn variant="danger" size="sm" onClick={rollback}>Rollback</Btn>
      </div>
      {msg && <div className="text-sm p-3 bg-gray-800 rounded-lg border border-gray-700">{msg}</div>}
      {loading ? <p className="text-gray-500">Loading…</p> : (
        <div className="space-y-3">
          {models.map(m => (
            <Card key={m.id} className="flex items-center gap-6">
              <div className="flex-1 grid grid-cols-6 gap-4">
                <div>
                  <div className="font-mono text-violet-400 font-semibold">{m.version_tag}</div>
                  {m.is_active && <Badge color="green">active</Badge>}
                </div>
                <Stat label="AUC" value={Number(m.auc_roc).toFixed(4)} color="text-emerald-400" />
                <Stat label="F1" value={Number(m.f1_score).toFixed(4)} color="text-blue-400" />
                <Stat label="Precision" value={Number(m.precision).toFixed(4)} />
                <Stat label="Recall" value={Number(m.recall).toFixed(4)} />
                <Stat label="Rows" value={m.row_count?.toLocaleString() ?? "—"} />
              </div>
              {!m.is_active && (
                <Btn size="sm" disabled={promoting === m.id} onClick={() => promote(m.id, m.version_tag)}>
                  {promoting === m.id ? "…" : "Promote"}
                </Btn>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Experiments page (Phase 2) ──────────────────────────────────────────────
function Experiments() {
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState([]);
  const [comparison, setComparison] = useState(null);
  const [expanded, setExpanded] = useState(null);

  useEffect(() => {
    apiFetch("/api/v1/experiments").then(r => r.ok ? r.json() : []).then(setRuns).finally(() => setLoading(false));
  }, []);

  async function compare() {
    if (selected.length !== 2) return;
    const r = await apiFetch(`/api/v1/experiments/compare/${selected[0]}/${selected[1]}`);
    if (r.ok) setComparison(await r.json());
  }

  function toggleSelect(runId) {
    setSelected(prev => prev.includes(runId) ? prev.filter(x => x !== runId) : prev.length < 2 ? [...prev, runId] : prev);
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Experiment Runs</h1>
          <p className="text-gray-400 text-sm mt-1">Training lineage: dataset hash, git commit, all metrics</p>
        </div>
        <Btn disabled={selected.length !== 2} onClick={compare}>
          Compare {selected.length}/2 selected
        </Btn>
      </div>

      {comparison && (
        <Card className="border-violet-700">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-white">Model Comparison</h2>
            <Badge color="purple">{comparison.overall_winner}</Badge>
          </div>
          <div className="grid grid-cols-6 gap-2 text-xs">
            <div className="text-gray-400 font-medium">Metric</div>
            <div className="text-gray-400 font-medium">{comparison.run_a.run_id}</div>
            <div className="text-gray-400 font-medium">{comparison.run_b.run_id}</div>
            <div className="text-gray-400 font-medium">Delta</div>
            <div className="text-gray-400 font-medium">Winner</div>
            <div />
            {comparison.metric_comparisons.map(c => (
              <>
                <div key={c.metric} className="font-mono text-gray-300">{c.metric}</div>
                <div className="font-mono">{c.value_a.toFixed(4)}</div>
                <div className="font-mono">{c.value_b.toFixed(4)}</div>
                <div className={`font-mono ${c.delta > 0 ? "text-green-400" : c.delta < 0 ? "text-red-400" : "text-gray-400"}`}>
                  {c.delta > 0 ? "+" : ""}{c.delta.toFixed(4)}
                </div>
                <div><Badge color={c.winner === "tie" ? "gray" : "green"}>{c.winner}</Badge></div>
                <div />
              </>
            ))}
          </div>
        </Card>
      )}

      {loading ? <p className="text-gray-500">Loading…</p> : runs.length === 0 ? (
        <Card><p className="text-gray-400 text-sm">No experiment runs yet. Run pipeline.sh to train a model.</p></Card>
      ) : (
        <div className="space-y-2">
          {runs.map(run => (
            <Card key={run.run_id}
              className={`cursor-pointer transition-colors ${selected.includes(run.run_id) ? "border-violet-600" : ""}`}>
              <div className="flex items-start gap-4">
                <input type="checkbox" checked={selected.includes(run.run_id)}
                  onChange={() => toggleSelect(run.run_id)}
                  className="mt-1 accent-violet-500" />
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <span className="font-mono text-violet-400 font-semibold">{run.run_id}</span>
                    <Badge color="blue">{run.version_tag}</Badge>
                    <Badge color="gray">{run.estimator_key}</Badge>
                    {run.promoted && <Badge color="green">promoted</Badge>}
                    {!run.auc_gate_passed && <Badge color="red">gate failed</Badge>}
                  </div>
                  <div className="grid grid-cols-5 gap-4 text-sm">
                    <Stat label="AUC" value={run.metrics?.auc_roc?.toFixed(4) ?? "—"} color="text-emerald-400" />
                    <Stat label="F1" value={run.metrics?.f1_score?.toFixed(4) ?? "—"} color="text-blue-400" />
                    <Stat label="Dataset Hash" value={run.dataset_hash} color="text-gray-300" />
                    <Stat label="Git Commit" value={run.git_commit} color="text-amber-400" />
                    <Stat label="Duration" value={`${run.duration_seconds?.toFixed(1)}s`} />
                  </div>
                  {expanded === run.run_id && run.feature_importance && (
                    <div className="mt-4 pt-4 border-t border-gray-700">
                      <p className="text-xs text-gray-400 mb-2">Top Feature Importances</p>
                      <div className="grid grid-cols-4 gap-2">
                        {Object.entries(run.feature_importance).slice(0, 8).map(([f, v]) => (
                          <div key={f} className="text-xs">
                            <div className="text-gray-300 truncate">{f}</div>
                            <div className="h-1.5 bg-gray-700 rounded mt-1">
                              <div className="h-full bg-violet-500 rounded"
                                style={{ width: `${Math.min(v * 500, 100)}%` }} />
                            </div>
                            <div className="text-gray-500 font-mono">{v.toFixed(4)}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  <button onClick={() => setExpanded(expanded === run.run_id ? null : run.run_id)}
                    className="text-xs text-gray-500 hover:text-gray-300 mt-2">
                    {expanded === run.run_id ? "Hide details ▲" : "Show feature importance ▼"}
                  </button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Drift page (Phase 4) ──────────────────────────────────────────────────
function Drift() {
  const [reports, setReports] = useState([]);
  const [latest, setLatest] = useState(null);
  const [running, setRunning] = useState(false);
  const [msg, setMsg] = useState("");

  const load = useCallback(async () => {
    const [r1, r2] = await Promise.all([
      apiFetch("/api/v1/drift/latest"),
      apiFetch("/api/v1/drift"),
    ]);
    if (r1.ok) setLatest(await r1.json());
    if (r2.ok) setReports(await r2.json());
  }, []);

  useEffect(() => { load(); }, [load]);

  async function runCheck() {
    setRunning(true); setMsg("");
    const r = await apiFetch("/api/v1/drift/check?lookback_hours=24", { method: "POST" });
    const data = await r.json();
    setMsg(r.ok ? `✅ ${data.message} (PSI: ${data.overall_drift_score.toFixed(4)})` : `❌ ${data.message}`);
    if (r.ok) load();
    setRunning(false);
  }

  const sevColor = (s) => s === "severe" ? "red" : s === "moderate" ? "yellow" : "green";

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Data Drift Monitor</h1>
          <p className="text-gray-400 text-sm mt-1">PSI + KS test — training vs live distributions</p>
        </div>
        <Btn onClick={runCheck} disabled={running}>
          {running ? "Running…" : "Run Drift Check"}
        </Btn>
      </div>
      {msg && <div className="text-sm p-3 bg-gray-800 rounded-lg border border-gray-700">{msg}</div>}

      {latest && (
        <div className="grid grid-cols-4 gap-4">
          <Card><Stat label="Overall PSI" value={latest.overall_drift_score?.toFixed(4)}
            color={latest.drift_detected ? "text-red-400" : "text-green-400"} /></Card>
          <Card><Stat label="Severity" value={latest.severity?.toUpperCase() ?? "NONE"}
            color={sevColor(latest.severity) === "red" ? "text-red-400" : sevColor(latest.severity) === "yellow" ? "text-yellow-400" : "text-green-400"} /></Card>
          <Card><Stat label="Drifted Features" value={latest.drifted_feature_count ?? 0} /></Card>
          <Card><Stat label="Live Samples" value={latest.sample_size_live?.toLocaleString() ?? "0"} /></Card>
        </div>
      )}

      {latest?.feature_results && (
        <Card>
          <h2 className="font-semibold text-white mb-4">Per-Feature PSI Scores</h2>
          <div className="space-y-2">
            {[...latest.feature_results].sort((a, b) => (b.psi ?? 0) - (a.psi ?? 0)).map(f => (
              <div key={f.feature} className="flex items-center gap-4">
                <span className="text-sm font-mono text-gray-300 w-48 shrink-0">{f.feature}</span>
                <div className="flex-1 h-2 bg-gray-700 rounded">
                  <div className={`h-full rounded transition-all ${f.psi > 0.2 ? "bg-red-500" : f.psi > 0.1 ? "bg-yellow-500" : "bg-green-500"}`}
                    style={{ width: `${Math.min((f.psi ?? 0) * 500, 100)}%` }} />
                </div>
                <span className="text-xs font-mono text-gray-400 w-16 text-right">{f.psi?.toFixed(4) ?? "—"}</span>
                <Badge color={sevColor(f.severity)}>{f.severity}</Badge>
                {f.train_mean !== null && (
                  <span className="text-xs text-gray-500">
                    train: {f.train_mean?.toFixed(2)} → live: {f.live_mean?.toFixed(2)}
                  </span>
                )}
              </div>
            ))}
          </div>
          <div className="flex gap-4 mt-4 pt-4 border-t border-gray-700">
            <div className="flex items-center gap-1.5 text-xs text-gray-400">
              <div className="w-3 h-3 rounded bg-green-500" /> PSI &lt; 0.10 — OK
            </div>
            <div className="flex items-center gap-1.5 text-xs text-gray-400">
              <div className="w-3 h-3 rounded bg-yellow-500" /> 0.10–0.20 — Monitor
            </div>
            <div className="flex items-center gap-1.5 text-xs text-gray-400">
              <div className="w-3 h-3 rounded bg-red-500" /> &gt; 0.20 — Retrain
            </div>
          </div>
        </Card>
      )}

      {reports.length > 0 && (
        <Card>
          <h2 className="font-semibold text-white mb-4">Drift History</h2>
          <div className="space-y-2">
            {reports.map(r => (
              <div key={r.id} className="flex items-center gap-4 text-sm py-2 border-b border-gray-700 last:border-0">
                <span className="text-gray-400 font-mono text-xs">{new Date(r.created_at).toLocaleString()}</span>
                <Badge color="blue">{r.model_version_tag}</Badge>
                <span className="text-gray-300 font-mono">PSI: {r.overall_drift_score.toFixed(4)}</span>
                <Badge color={sevColor(r.severity)}>{r.severity}</Badge>
                <span className="text-gray-500">{r.drifted_feature_count} features drifted</span>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}

// ── SHAP Explain page (Phase 6) ──────────────────────────────────────────────
function Explain() {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const sampleRecord = {
    state: "CA", account_length: 128, area_code: 415,
    international_plan: "no", voice_mail_plan: "yes",
    number_vmail_messages: 25, total_day_minutes: 265.1,
    total_day_calls: 110, total_day_charge: 45.07,
    total_eve_minutes: 197.4, total_eve_calls: 99, total_eve_charge: 16.78,
    total_night_minutes: 244.7, total_night_calls: 91, total_night_charge: 11.01,
    total_intl_minutes: 10.0, total_intl_calls: 3, total_intl_charge: 2.70,
    customer_service_calls: 1,
  };

  const [record, setRecord] = useState(JSON.stringify(sampleRecord, null, 2));

  async function explain() {
    setLoading(true); setError("");
    try {
      const parsed = JSON.parse(record);
      const r = await apiFetch("/api/v1/explain", {
        method: "POST",
        body: JSON.stringify({ records: [parsed], top_n: 12 }),
      });
      const data = await r.json();
      if (!r.ok) { setError(data.message ?? "Error"); setLoading(false); return; }
      setResult(data);
    } catch (e) { setError(`Parse error: ${e.message}`); }
    setLoading(false);
  }

  const rec = result?.per_record_explanations?.[0];
  const global = result?.global_feature_importance;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">SHAP Explainability</h1>
        <p className="text-gray-400 text-sm mt-1">Why did the model predict churn? Feature-level contributions</p>
      </div>

      <div className="grid grid-cols-2 gap-6">
        <Card>
          <h2 className="font-semibold text-white mb-3">Customer Record (JSON)</h2>
          <textarea value={record} onChange={e => setRecord(e.target.value)}
            className="w-full h-72 bg-gray-900 border border-gray-700 rounded-lg p-3 text-xs font-mono text-green-400 focus:outline-none focus:border-violet-500 resize-none" />
          {error && <p className="text-red-400 text-xs mt-2">{error}</p>}
          <div className="mt-3">
            <Btn onClick={explain} disabled={loading}>
              {loading ? "Computing SHAP…" : "Explain Prediction"}
            </Btn>
          </div>
        </Card>

        {rec && (
          <Card>
            <div className="flex items-start justify-between mb-4">
              <h2 className="font-semibold text-white">Prediction Result</h2>
              <Badge color={rec.churn_probability > 0.5 ? "red" : "green"}>
                {rec.churn_probability > 0.5 ? "CHURN" : "RETAIN"}
              </Badge>
            </div>
            <div className="grid grid-cols-2 gap-4 mb-5">
              <Stat label="Churn Probability" value={`${(rec.churn_probability * 100).toFixed(1)}%`}
                color={rec.churn_probability > 0.5 ? "text-red-400" : "text-green-400"} />
              <Stat label="Base Rate" value={`${(rec.expected_value * 100).toFixed(1)}%`}
                color="text-gray-400" sub="Model baseline" />
            </div>
            <h3 className="text-xs text-gray-400 uppercase tracking-wider mb-3">Top Feature Contributions</h3>
            <div className="space-y-2">
              {rec.top_features?.map(f => (
                <div key={f.feature} className="flex items-center gap-2">
                  <span className="text-xs font-mono text-gray-300 w-40 truncate">{f.feature}</span>
                  <div className="flex-1 h-2 bg-gray-700 rounded">
                    <div
                      className={`h-full rounded ${f.direction === "increases_churn" ? "bg-red-500" : "bg-green-500"}`}
                      style={{ width: `${Math.min(f.magnitude * 200, 100)}%`, marginLeft: f.direction === "decreases_churn" ? "auto" : 0 }} />
                  </div>
                  <span className={`text-xs font-mono w-16 text-right ${f.shap_value > 0 ? "text-red-400" : "text-green-400"}`}>
                    {f.shap_value > 0 ? "+" : ""}{f.shap_value.toFixed(4)}
                  </span>
                </div>
              ))}
            </div>
          </Card>
        )}
      </div>

      {global && (
        <Card>
          <h2 className="font-semibold text-white mb-4">Global Feature Importance (Mean |SHAP|)</h2>
          <div className="grid grid-cols-2 gap-4">
            {global.slice(0, 10).map((f, i) => (
              <div key={f.feature} className="flex items-center gap-3">
                <span className="text-xs text-gray-500 w-4">{i + 1}</span>
                <span className="text-xs font-mono text-gray-300 w-44 truncate">{f.feature}</span>
                <div className="flex-1 h-2 bg-gray-700 rounded">
                  <div className="h-full bg-violet-500 rounded"
                    style={{ width: `${(f.mean_abs_shap / global[0].mean_abs_shap) * 100}%` }} />
                </div>
                <span className="text-xs font-mono text-gray-400 w-16 text-right">{f.mean_abs_shap.toFixed(4)}</span>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}

// ── A/B Tests page (Phase 6) ─────────────────────────────────────────────────
function ABTests() {
  const [tests, setTests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({ name: "", control_version_tag: "", treatment_version_tag: "", treatment_traffic_fraction: 0.2 });
  const [msg, setMsg] = useState("");

  const load = useCallback(async () => {
    const r = await apiFetch("/api/v1/ab-tests");
    if (r.ok) setTests(await r.json());
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  async function create() {
    const r = await apiFetch("/api/v1/ab-tests", { method: "POST", body: JSON.stringify(form) });
    const data = await r.json();
    setMsg(r.ok ? `✅ Created A/B test "${form.name}"` : `❌ ${data.message}`);
    if (r.ok) { load(); setCreating(false); }
  }

  async function stop(id, name) {
    const r = await apiFetch(`/api/v1/ab-tests/${id}/stop`, { method: "POST" });
    const data = await r.json();
    setMsg(r.ok ? `✅ Stopped "${name}" — Winner: ${data.winner ?? "inconclusive"}` : `❌ ${data.message}`);
    if (r.ok) load();
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">A/B Model Testing</h1>
          <p className="text-gray-400 text-sm mt-1">Split traffic between two model versions</p>
        </div>
        <Btn onClick={() => setCreating(true)}>New A/B Test</Btn>
      </div>

      {msg && <div className="text-sm p-3 bg-gray-800 rounded-lg border border-gray-700">{msg}</div>}

      {creating && (
        <Card className="border-violet-700">
          <h2 className="font-semibold text-white mb-4">Configure A/B Test</h2>
          <div className="grid grid-cols-2 gap-4">
            {[
              { key: "name", label: "Experiment Name", placeholder: "challenger-v3-vs-v2" },
              { key: "control_version_tag", label: "Control Model", placeholder: "v2" },
              { key: "treatment_version_tag", label: "Treatment Model", placeholder: "v3" },
            ].map(({ key, label, placeholder }) => (
              <div key={key}>
                <label className="block text-xs text-gray-400 mb-1">{label}</label>
                <input value={form[key]} onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}
                  placeholder={placeholder}
                  className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-violet-500" />
              </div>
            ))}
            <div>
              <label className="block text-xs text-gray-400 mb-1">Treatment Traffic ({Math.round(form.treatment_traffic_fraction * 100)}%)</label>
              <input type="range" min={5} max={50} step={5}
                value={Math.round(form.treatment_traffic_fraction * 100)}
                onChange={e => setForm(f => ({ ...f, treatment_traffic_fraction: Number(e.target.value) / 100 }))}
                className="w-full accent-violet-500" />
            </div>
          </div>
          <div className="flex gap-3 mt-4">
            <Btn onClick={create}>Start Experiment</Btn>
            <Btn variant="secondary" onClick={() => setCreating(false)}>Cancel</Btn>
          </div>
        </Card>
      )}

      {loading ? <p className="text-gray-500">Loading…</p> : tests.length === 0 ? (
        <Card><p className="text-gray-400 text-sm">No A/B tests yet. Create one above.</p></Card>
      ) : (
        <div className="space-y-4">
          {tests.map(t => (
            <Card key={t.id}>
              <div className="flex items-start justify-between mb-4">
                <div>
                  <span className="font-semibold text-white">{t.name}</span>
                  {t.is_active && <Badge color="green" className="ml-2">active</Badge>}
                  {!t.is_active && <Badge color="gray" className="ml-2">stopped</Badge>}
                  {t.description && <p className="text-xs text-gray-400 mt-0.5">{t.description}</p>}
                </div>
                {t.is_active && <Btn variant="danger" size="sm" onClick={() => stop(t.id, t.name)}>Stop Test</Btn>}
              </div>
              <div className="grid grid-cols-2 gap-6">
                {/* Control */}
                <div className="bg-gray-900 rounded-lg p-4 border border-gray-700">
                  <div className="flex items-center gap-2 mb-3">
                    <span className="text-xs text-gray-400 uppercase">Control</span>
                    <Badge color="blue">{t.control_version_tag}</Badge>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <Stat label="Requests" value={t.control_stats.requests.toLocaleString()} />
                    <Stat label="Mean Churn Prob"
                      value={t.control_stats.mean_churn_probability !== null
                        ? `${(t.control_stats.mean_churn_probability * 100).toFixed(1)}%` : "—"} />
                  </div>
                </div>
                {/* Treatment */}
                <div className="bg-gray-900 rounded-lg p-4 border border-violet-700">
                  <div className="flex items-center gap-2 mb-3">
                    <span className="text-xs text-gray-400 uppercase">Treatment ({Math.round(t.treatment_traffic_fraction * 100)}% traffic)</span>
                    <Badge color="purple">{t.treatment_version_tag}</Badge>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <Stat label="Requests" value={t.treatment_stats.requests.toLocaleString()} />
                    <Stat label="Mean Churn Prob"
                      value={t.treatment_stats.mean_churn_probability !== null
                        ? `${(t.treatment_stats.mean_churn_probability * 100).toFixed(1)}%` : "—"} />
                  </div>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Predict page ─────────────────────────────────────────────────────────────
function Predict() {
  const sample = { state:"CA", account_length:128, area_code:415, international_plan:"no", voice_mail_plan:"yes", number_vmail_messages:25, total_day_minutes:265.1, total_day_calls:110, total_day_charge:45.07, total_eve_minutes:197.4, total_eve_calls:99, total_eve_charge:16.78, total_night_minutes:244.7, total_night_calls:91, total_night_charge:11.01, total_intl_minutes:10.0, total_intl_calls:3, total_intl_charge:2.70, customer_service_calls:1 };
  const [input, setInput] = useState(JSON.stringify(sample, null, 2));
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function predict() {
    setLoading(true); setError("");
    try {
      const records = JSON.parse(input);
      const r = await apiFetch("/api/v1/predict", { method: "POST", body: JSON.stringify({ records: Array.isArray(records) ? records : [records] }) });
      const data = await r.json();
      if (!r.ok) { setError(data.message ?? "Prediction failed"); setLoading(false); return; }
      setResult(data);
    } catch (e) { setError(`Invalid JSON: ${e.message}`); }
    setLoading(false);
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Real-time Prediction</h1>
        <p className="text-gray-400 text-sm mt-1">1–500 customer records. SLO: p95 ≤ 200ms</p>
      </div>
      <div className="grid grid-cols-2 gap-6">
        <Card>
          <h2 className="font-semibold text-white mb-3">Input Record(s)</h2>
          <textarea value={input} onChange={e => setInput(e.target.value)}
            className="w-full h-80 bg-gray-900 border border-gray-700 rounded-lg p-3 text-xs font-mono text-green-400 focus:outline-none focus:border-violet-500 resize-none" />
          {error && <p className="text-red-400 text-xs mt-2">{error}</p>}
          <div className="mt-3"><Btn onClick={predict} disabled={loading}>{loading ? "Predicting…" : "Predict"}</Btn></div>
        </Card>
        <div className="space-y-4">
          {result && (
            <>
              <Card>
                <div className="grid grid-cols-3 gap-4">
                  <Stat label="Model" value={result.model_version} color="text-violet-400" />
                  <Stat label="Latency" value={`${result.latency_ms.toFixed(1)}ms`}
                    color={result.latency_ms < 200 ? "text-green-400" : "text-red-400"} />
                  <Stat label="Records" value={result.record_count} />
                </div>
              </Card>
              {result.predictions.map((p, i) => (
                <Card key={i} className={p.churn ? "border-red-700" : "border-green-800"}>
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-sm text-gray-400">Record #{i + 1}</span>
                    <Badge color={p.churn ? "red" : "green"}>{p.churn ? "CHURN" : "RETAIN"}</Badge>
                  </div>
                  <div className="grid grid-cols-3 gap-4">
                    <Stat label="Probability" value={`${(p.churn_probability * 100).toFixed(1)}%`}
                      color={p.churn ? "text-red-400" : "text-green-400"} />
                    <Stat label="Confidence" value={p.confidence_band.toUpperCase()} />
                    <Stat label="Hash" value={p.input_hash.slice(0, 8) + "…"} />
                  </div>
                  <div className="mt-2 h-2 bg-gray-700 rounded">
                    <div className={`h-full rounded transition-all ${p.churn ? "bg-red-500" : "bg-green-500"}`}
                      style={{ width: `${p.churn_probability * 100}%` }} />
                  </div>
                </Card>
              ))}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Batch page (simplified) ──────────────────────────────────────────────────
function Batch() {
  const [jobs, setJobs] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [msg, setMsg] = useState("");

  const load = useCallback(async () => {
    const r = await apiFetch("/api/v1/jobs");
    if (r.ok) { const d = await r.json(); setJobs(d.items ?? []); }
  }, []);

  useEffect(() => { load(); }, [load]);

  async function upload(e) {
    const file = e.target.files?.[0]; if (!file) return;
    setUploading(true); setMsg("");
    const fd = new FormData(); fd.append("file", file);
    const r = await fetch(`${API}/api/v1/upload`, {
      method: "POST",
      headers: { Authorization: `Bearer ${getToken()}` },
      body: fd,
    });
    const data = await r.json();
    setMsg(r.ok ? `✅ Job queued: ${data.job_id}` : `❌ ${data.message}`);
    if (r.ok) load();
    setUploading(false);
  }

  const statusColor = { queued: "gray", processing: "yellow", completed: "green", failed: "red" };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-white">Batch Prediction Jobs</h1>
      <Card>
        <div className="flex items-center gap-3">
          <input type="file" accept=".csv" id="csvUpload" className="hidden" onChange={upload} />
          <label htmlFor="csvUpload">
            <Btn variant="secondary" size="sm" disabled={uploading} onClick={() => document.getElementById('csvUpload').click()}>
              {uploading ? "Uploading…" : "Upload CSV"}
            </Btn>
          </label>
          <span className="text-xs text-gray-400">Max 50MB. Columns must match model schema.</span>
        </div>
        {msg && <p className="text-sm mt-2 text-gray-300">{msg}</p>}
      </Card>
      <div className="space-y-2">
        {jobs.map(j => (
          <Card key={j.job_id} className="flex items-center gap-6">
            <div className="flex-1 grid grid-cols-5 gap-4">
              <Stat label="Filename" value={j.filename} color="text-violet-400" />
              <div><Badge color={statusColor[j.status] ?? "gray"}>{j.status}</Badge></div>
              <Stat label="Processed" value={`${j.processed_count.toLocaleString()} / ${j.row_count?.toLocaleString() ?? "?"}`} />
              <Stat label="Created" value={new Date(j.created_at).toLocaleDateString()} />
              <Stat label="Duration"
                value={j.completed_at && j.started_at
                  ? `${Math.round((new Date(j.completed_at) - new Date(j.started_at)) / 1000)}s`
                  : "—"} />
            </div>
            {j.status === "completed" && (
              <a href={`${API}/api/v1/jobs/${j.job_id}/results`}
                download className="text-xs text-violet-400 hover:text-violet-300">
                Download ↓
              </a>
            )}
          </Card>
        ))}
      </div>
    </div>
  );
}

// ── Root App ─────────────────────────────────────────────────────────────────
export default function App() {
  const [authed, setAuthed] = useState(!!getToken());
  if (!authed) return <Login onLogin={() => setAuthed(true)} />;
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/predict" element={<Predict />} />
        <Route path="/batch" element={<Batch />} />
        <Route path="/models" element={<Models />} />
        <Route path="/experiments" element={<Experiments />} />
        <Route path="/drift" element={<Drift />} />
        <Route path="/explain" element={<Explain />} />
        <Route path="/abtests" element={<ABTests />} />
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </Layout>
  );
}
