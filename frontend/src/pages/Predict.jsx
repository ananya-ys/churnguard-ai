import { useState } from 'react'
import { api } from '../api'

const DEFAULTS = {
  state: 'CA', account_length: 120, area_code: 415,
  international_plan: 'no', voice_mail_plan: 'yes',
  number_vmail_messages: 25, total_day_minutes: 265.1,
  total_day_calls: 110, total_day_charge: 45.07,
  total_eve_minutes: 197.4, total_eve_calls: 99, total_eve_charge: 16.78,
  total_night_minutes: 244.7, total_night_calls: 91, total_night_charge: 11.01,
  total_intl_minutes: 10.0, total_intl_calls: 3, total_intl_charge: 2.70,
  customer_service_calls: 1,
}

const FIELDS = [
  { key: 'state', label: 'State', type: 'text', placeholder: 'CA' },
  { key: 'account_length', label: 'Account Length', type: 'number' },
  { key: 'area_code', label: 'Area Code', type: 'number' },
  { key: 'international_plan', label: 'International Plan', type: 'select', options: ['yes', 'no'] },
  { key: 'voice_mail_plan', label: 'Voicemail Plan', type: 'select', options: ['yes', 'no'] },
  { key: 'number_vmail_messages', label: 'Voicemail Messages', type: 'number' },
  { key: 'total_day_minutes', label: 'Day Minutes', type: 'number' },
  { key: 'total_day_calls', label: 'Day Calls', type: 'number' },
  { key: 'total_day_charge', label: 'Day Charge ($)', type: 'number' },
  { key: 'total_eve_minutes', label: 'Evening Minutes', type: 'number' },
  { key: 'total_eve_calls', label: 'Evening Calls', type: 'number' },
  { key: 'total_eve_charge', label: 'Evening Charge ($)', type: 'number' },
  { key: 'total_night_minutes', label: 'Night Minutes', type: 'number' },
  { key: 'total_night_calls', label: 'Night Calls', type: 'number' },
  { key: 'total_night_charge', label: 'Night Charge ($)', type: 'number' },
  { key: 'total_intl_minutes', label: 'Intl Minutes', type: 'number' },
  { key: 'total_intl_calls', label: 'Intl Calls', type: 'number' },
  { key: 'total_intl_charge', label: 'Intl Charge ($)', type: 'number' },
  { key: 'customer_service_calls', label: 'CS Calls', type: 'number' },
]

function ProbabilityBar({ value }) {
  const pct = Math.round(value * 100)
  const color = pct >= 70 ? 'var(--red)' : pct >= 30 ? 'var(--yellow)' : 'var(--teal)'
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
        <span style={{ fontSize: 12, color: 'var(--text2)' }}>Churn Probability</span>
        <span style={{ fontFamily: 'var(--mono)', fontWeight: 700, color, fontSize: 16 }}>{pct}%</span>
      </div>
      <div style={{ background: 'var(--bg3)', height: 8, borderRadius: 4, overflow: 'hidden' }}>
        <div style={{
          width: `${pct}%`, height: '100%', background: color,
          borderRadius: 4, transition: 'width 0.6s ease',
          boxShadow: `0 0 8px ${color}`,
        }} />
      </div>
    </div>
  )
}

export default function Predict() {
  const [form, setForm] = useState(DEFAULTS)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  function handleChange(key, value) {
    setForm(f => ({ ...f, [key]: value }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setLoading(true)
    setError('')
    setResult(null)
    try {
      const record = { ...form }
      // Coerce numeric fields
      FIELDS.forEach(f => {
        if (f.type === 'number') record[f.key] = parseFloat(record[f.key]) || 0
      })
      const res = await api.predict([record])
      setResult(res)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const prediction = result?.predictions?.[0]

  return (
    <div>
      <div className="page-header">
        <h1>Real-Time Prediction</h1>
        <p>Enter customer data to predict churn probability instantly</p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 360px', gap: 24, alignItems: 'start' }}>
        {/* Form */}
        <div className="card">
          <form onSubmit={handleSubmit}>
            <div className="grid-3" style={{ gap: 12 }}>
              {FIELDS.map(({ key, label, type, options, placeholder }) => (
                <div key={key}>
                  <label className="label">{label}</label>
                  {type === 'select' ? (
                    <select value={form[key]} onChange={e => handleChange(key, e.target.value)}>
                      {options.map(o => <option key={o} value={o}>{o}</option>)}
                    </select>
                  ) : (
                    <input
                      type={type}
                      value={form[key]}
                      onChange={e => handleChange(key, e.target.value)}
                      placeholder={placeholder}
                      step="any"
                    />
                  )}
                </div>
              ))}
            </div>

            {error && <div className="error-msg" style={{ marginTop: 16 }}>{error}</div>}

            <div style={{ marginTop: 20, display: 'flex', gap: 12 }}>
              <button type="submit" className="btn btn-primary" disabled={loading}>
                {loading ? <><span className="spinner" /> Predicting...</> : '⟡ Run Prediction'}
              </button>
              <button type="button" className="btn btn-ghost" onClick={() => setForm(DEFAULTS)}>
                Reset
              </button>
            </div>
          </form>
        </div>

        {/* Result panel */}
        <div>
          {prediction ? (
            <div className="card" style={{ border: `1px solid ${prediction.churn ? 'rgba(255,71,87,0.4)' : 'rgba(0,229,195,0.3)'}` }}>
              <div style={{ marginBottom: 20 }}>
                <div style={{ fontSize: 11, color: 'var(--text2)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 8 }}>
                  Prediction Result
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <div style={{
                    width: 48, height: 48, borderRadius: '50%',
                    background: prediction.churn ? 'rgba(255,71,87,0.15)' : 'rgba(0,229,195,0.15)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 20,
                  }}>
                    {prediction.churn ? '⚠' : '✓'}
                  </div>
                  <div>
                    <div style={{ fontSize: 22, fontWeight: 700, color: prediction.churn ? 'var(--red)' : 'var(--teal)' }}>
                      {prediction.churn ? 'Will Churn' : 'Will Stay'}
                    </div>
                    <span className={`badge ${prediction.churn ? 'badge-red' : 'badge-green'}`}>
                      {prediction.confidence_band} confidence
                    </span>
                  </div>
                </div>
              </div>

              <ProbabilityBar value={prediction.churn_probability} />

              <div style={{ marginTop: 20, padding: '12px', background: 'var(--bg3)', borderRadius: 'var(--radius)' }}>
                <div style={{ fontSize: 11, color: 'var(--text2)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                  Metadata
                </div>
                {[
                  ['Model', result.model_version],
                  ['Latency', `${result.latency_ms}ms`],
                  ['Hash', prediction.input_hash.slice(0, 16) + '…'],
                ].map(([k, v]) => (
                  <div key={k} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                    <span style={{ color: 'var(--text2)', fontSize: 12 }}>{k}</span>
                    <span style={{ fontFamily: 'var(--mono)', fontSize: 12 }}>{v}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="card" style={{ textAlign: 'center', padding: '40px 24px' }}>
              <div style={{ fontSize: 32, marginBottom: 12, color: 'var(--text3)' }}>⟡</div>
              <div style={{ color: 'var(--text2)', fontSize: 13 }}>Fill in the form and run a prediction to see results here</div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
