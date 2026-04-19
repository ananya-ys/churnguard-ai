import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../App'

export default function Dashboard() {
  const { user } = useAuth()
  const [health, setHealth] = useState(null)
  const [activeModel, setActiveModel] = useState(null)
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      api.health(),
      api.getActiveModel().catch(() => null),
      api.listJobs().catch(() => ({ items: [] })),
    ]).then(([h, m, j]) => {
      setHealth(h)
      setActiveModel(m)
      setJobs(j?.items || [])
    }).finally(() => setLoading(false))
  }, [])

  const completedJobs = jobs.filter(j => j.status === 'completed').length
  const failedJobs = jobs.filter(j => j.status === 'failed').length

  return (
    <div>
      <div className="page-header">
        <h1>Dashboard</h1>
        <p>Welcome back, {user?.email} · {new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}</p>
      </div>

      {loading ? (
        <div style={{ color: 'var(--text2)', display: 'flex', alignItems: 'center', gap: 10 }}>
          <span className="spinner" /> Loading system status...
        </div>
      ) : (
        <>
          {/* Status row */}
          <div className="grid-4" style={{ marginBottom: 24 }}>
            <div className="stat-card">
              <div className="stat-label">API Status</div>
              <div className="stat-value" style={{ fontSize: 18, marginTop: 8 }}>
                <span className={`badge ${health?.status === 'ok' ? 'badge-green' : 'badge-red'}`}>
                  {health?.status || 'unknown'}
                </span>
              </div>
              <div className="stat-sub">v{health?.version || '—'}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Model</div>
              <div className="stat-value" style={{ fontSize: 18, marginTop: 8 }}>
                <span className={`badge ${health?.model_loaded ? 'badge-green' : 'badge-yellow'}`}>
                  {health?.model_loaded ? 'active' : 'not loaded'}
                </span>
              </div>
              <div className="stat-sub">{activeModel?.version_tag || 'No model promoted'}</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Completed Jobs</div>
              <div className="stat-value">{completedJobs}</div>
              <div className="stat-sub">batch predictions</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Failed Jobs</div>
              <div className="stat-value" style={{ color: failedJobs > 0 ? 'var(--red)' : 'var(--text)' }}>
                {failedJobs}
              </div>
              <div className="stat-sub">requires attention</div>
            </div>
          </div>

          {/* Active model info */}
          {activeModel && (
            <div className="card" style={{ marginBottom: 24 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20 }}>
                <div>
                  <div style={{ fontSize: 11, color: 'var(--text2)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 4 }}>Active Model</div>
                  <div style={{ fontFamily: 'var(--mono)', fontSize: 18, fontWeight: 700 }}>{activeModel.version_tag}</div>
                </div>
                <span className="badge badge-green">ACTIVE</span>
              </div>
              <div className="grid-4">
                {[
                  { label: 'AUC-ROC', value: Number(activeModel.auc_roc).toFixed(4) },
                  { label: 'F1 Score', value: Number(activeModel.f1_score).toFixed(4) },
                  { label: 'Precision', value: Number(activeModel.precision).toFixed(4) },
                  { label: 'Recall', value: Number(activeModel.recall).toFixed(4) },
                ].map(({ label, value }) => (
                  <div key={label} style={{ textAlign: 'center', padding: '12px', background: 'var(--bg3)', borderRadius: 'var(--radius)' }}>
                    <div style={{ fontSize: 11, color: 'var(--text2)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>{label}</div>
                    <div style={{ fontFamily: 'var(--mono)', fontSize: 22, fontWeight: 700, color: 'var(--teal)', marginTop: 4 }}>{value}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Quick actions */}
          <div className="card">
            <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 16, color: 'var(--text2)', textTransform: 'uppercase', letterSpacing: '0.08em', fontSize: 11 }}>
              Quick Actions
            </div>
            <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
              <Link to="/predict" className="btn btn-primary">⟡ New Prediction</Link>
              <Link to="/batch" className="btn btn-ghost">⊞ Upload CSV</Link>
              <Link to="/models" className="btn btn-ghost">⬡ Manage Models</Link>
              <Link to="/jobs" className="btn btn-ghost">◎ View Jobs</Link>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
