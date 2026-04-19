import { useEffect, useState } from 'react'
import { api } from '../api'

const STATUS_BADGE = {
  queued:     'badge-yellow',
  processing: 'badge-yellow',
  completed:  'badge-green',
  failed:     'badge-red',
}

export default function Jobs() {
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  async function load() {
    try {
      const data = await api.listJobs()
      setJobs(data.items || [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    // Poll every 5s if any jobs are in-progress
    const t = setInterval(() => {
      load()
    }, 5000)
    return () => clearInterval(t)
  }, [])

  function downloadResults(jobId) {
    const token = localStorage.getItem('token')
    const base = import.meta.env.VITE_API_URL || ''
    window.open(`${base}/api/v1/jobs/${jobId}/results?token=${token}`, '_blank')
  }

  return (
    <div>
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h1>Batch Jobs</h1>
          <p>Status of all CSV batch prediction jobs · Auto-refreshes every 5s</p>
        </div>
        <button className="btn btn-ghost" onClick={load}>↻ Refresh</button>
      </div>

      {error && <div className="error-msg" style={{ marginBottom: 16 }}>{error}</div>}

      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        {loading ? (
          <div style={{ padding: 32, textAlign: 'center' }}>
            <span className="spinner" />
          </div>
        ) : jobs.length === 0 ? (
          <div style={{ padding: 48, textAlign: 'center' }}>
            <div style={{ fontSize: 32, color: 'var(--text3)', marginBottom: 8 }}>◎</div>
            <div style={{ color: 'var(--text2)', fontSize: 13 }}>No jobs yet</div>
            <div style={{ color: 'var(--text3)', fontSize: 12, marginTop: 4 }}>
              Upload a CSV file to create a batch job
            </div>
          </div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Job ID</th>
                <th>Filename</th>
                <th>Status</th>
                <th>Progress</th>
                <th>Created</th>
                <th>Completed</th>
                <th>Results</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map(job => (
                <tr key={job.job_id}>
                  <td>
                    <span style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--text2)' }}>
                      {job.job_id.slice(0, 8)}…
                    </span>
                  </td>
                  <td style={{ maxWidth: 180, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {job.filename}
                  </td>
                  <td>
                    <span className={`badge ${STATUS_BADGE[job.status] || 'badge-gray'}`}>
                      {job.status === 'processing' && <span className="spinner" style={{ width: 10, height: 10, borderWidth: 1.5 }} />}
                      {job.status}
                    </span>
                  </td>
                  <td>
                    {job.row_count ? (
                      <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--text2)', marginBottom: 3 }}>
                          <span>{job.processed_count} / {job.row_count}</span>
                          <span>{Math.round((job.processed_count / job.row_count) * 100)}%</span>
                        </div>
                        <div style={{ background: 'var(--bg3)', height: 4, borderRadius: 2, overflow: 'hidden' }}>
                          <div style={{
                            width: `${(job.processed_count / job.row_count) * 100}%`,
                            height: '100%',
                            background: job.status === 'failed' ? 'var(--red)' : 'var(--teal)',
                            borderRadius: 2,
                          }} />
                        </div>
                      </div>
                    ) : (
                      <span style={{ color: 'var(--text3)', fontSize: 12 }}>{job.processed_count} rows</span>
                    )}
                  </td>
                  <td style={{ color: 'var(--text2)', fontSize: 12 }}>
                    {new Date(job.created_at).toLocaleString()}
                  </td>
                  <td style={{ color: 'var(--text2)', fontSize: 12 }}>
                    {job.completed_at ? new Date(job.completed_at).toLocaleString() : '—'}
                  </td>
                  <td>
                    {job.status === 'completed' ? (
                      <button
                        className="btn btn-ghost"
                        style={{ padding: '5px 10px', fontSize: 11 }}
                        onClick={() => downloadResults(job.job_id)}
                      >
                        ↓ Download
                      </button>
                    ) : job.status === 'failed' ? (
                      <span style={{ color: 'var(--red)', fontSize: 11 }} title={job.error_message}>
                        ✗ Failed
                      </span>
                    ) : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
