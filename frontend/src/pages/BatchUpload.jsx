import { useState, useRef } from 'react'
import { api } from '../api'
import { Link } from 'react-router-dom'

export default function BatchUpload() {
  const [file, setFile] = useState(null)
  const [dragging, setDragging] = useState(false)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const inputRef = useRef()

  function handleDrop(e) {
    e.preventDefault()
    setDragging(false)
    const f = e.dataTransfer.files[0]
    if (f?.name.endsWith('.csv')) setFile(f)
    else setError('Only CSV files are accepted')
  }

  async function handleUpload() {
    if (!file) return
    setLoading(true)
    setError('')
    setResult(null)
    try {
      const res = await api.uploadCSV(file)
      setResult(res)
      setFile(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <div className="page-header">
        <h1>Batch Upload</h1>
        <p>Upload a CSV file to predict churn for thousands of customers at once</p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: 24, alignItems: 'start' }}>
        <div>
          {/* Drop zone */}
          <div
            onDragOver={e => { e.preventDefault(); setDragging(true) }}
            onDragLeave={() => setDragging(false)}
            onDrop={handleDrop}
            onClick={() => inputRef.current.click()}
            style={{
              border: `2px dashed ${dragging ? 'var(--teal)' : file ? 'rgba(0,229,195,0.4)' : 'var(--border2)'}`,
              borderRadius: 'var(--radius)',
              padding: '48px 24px',
              textAlign: 'center',
              cursor: 'pointer',
              background: dragging ? 'rgba(0,229,195,0.04)' : 'var(--bg2)',
              transition: 'all 0.15s',
              marginBottom: 16,
            }}
          >
            <input
              ref={inputRef} type="file" accept=".csv"
              style={{ display: 'none' }}
              onChange={e => { setFile(e.target.files[0]); setError('') }}
            />
            <div style={{ fontSize: 36, marginBottom: 12, color: 'var(--text3)' }}>⊞</div>
            {file ? (
              <>
                <div style={{ fontFamily: 'var(--mono)', fontSize: 14, color: 'var(--teal)', fontWeight: 700 }}>{file.name}</div>
                <div style={{ color: 'var(--text2)', fontSize: 12, marginTop: 4 }}>
                  {(file.size / 1024).toFixed(1)} KB · Click to change
                </div>
              </>
            ) : (
              <>
                <div style={{ fontWeight: 600, marginBottom: 4 }}>Drop CSV file here or click to browse</div>
                <div style={{ color: 'var(--text2)', fontSize: 12 }}>Max 50MB · Must match the 19-field telecom schema</div>
              </>
            )}
          </div>

          {error && <div className="error-msg" style={{ marginBottom: 16 }}>{error}</div>}

          {result && (
            <div className="success-msg" style={{ marginBottom: 16 }}>
              ✓ Job queued — ID: <span style={{ fontFamily: 'var(--mono)' }}>{result.job_id}</span>
              <br />
              <Link to="/jobs" style={{ color: 'var(--teal)', fontSize: 12, marginTop: 4, display: 'inline-block' }}>
                → View job status
              </Link>
            </div>
          )}

          <button
            className="btn btn-primary"
            onClick={handleUpload}
            disabled={!file || loading}
          >
            {loading ? <><span className="spinner" /> Uploading...</> : '⊞ Upload & Process'}
          </button>
        </div>

        {/* Schema reference */}
        <div className="card">
          <div style={{ fontSize: 11, color: 'var(--text2)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 12 }}>
            Required CSV Columns
          </div>
          {[
            'state', 'account_length', 'area_code',
            'international_plan', 'voice_mail_plan',
            'number_vmail_messages', 'total_day_minutes',
            'total_day_calls', 'total_day_charge',
            'total_eve_minutes', 'total_eve_calls', 'total_eve_charge',
            'total_night_minutes', 'total_night_calls', 'total_night_charge',
            'total_intl_minutes', 'total_intl_calls', 'total_intl_charge',
            'customer_service_calls'
          ].map(col => (
            <div key={col} style={{
              fontFamily: 'var(--mono)', fontSize: 11,
              color: 'var(--text2)', padding: '4px 0',
              borderBottom: '1px solid var(--border)',
            }}>
              {col}
            </div>
          ))}
          <div style={{ marginTop: 12, fontSize: 11, color: 'var(--text3)' }}>
            19 columns required. international_plan and voice_mail_plan must be "yes" or "no".
          </div>
        </div>
      </div>
    </div>
  )
}
