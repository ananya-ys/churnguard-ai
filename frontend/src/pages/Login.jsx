import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../App'

export default function Login() {
  const [tab, setTab] = useState('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState('api_user')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const { login } = useAuth()
  const navigate = useNavigate()

  async function handleSubmit(e) {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      if (tab === 'login') {
        const { access_token } = await api.login(email, password)
        const user = await (async () => {
          const old = localStorage.getItem('token')
          localStorage.setItem('token', access_token)
          const u = await api.me()
          if (!old) localStorage.removeItem('token')
          return u
        })()
        login(access_token, user)
        navigate('/')
      } else {
        await api.register(email, password, role)
        setTab('login')
        setError('')
        setPassword('')
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      minHeight: '100vh',
      background: 'var(--bg)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      position: 'relative',
      overflow: 'hidden',
    }}>
      {/* Grid background */}
      <div style={{
        position: 'absolute', inset: 0,
        backgroundImage: 'linear-gradient(var(--border) 1px, transparent 1px), linear-gradient(90deg, var(--border) 1px, transparent 1px)',
        backgroundSize: '40px 40px',
        opacity: 0.4,
      }} />

      <div style={{ position: 'relative', width: 400 }}>
        {/* Header */}
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <div style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--teal)', letterSpacing: '0.2em', textTransform: 'uppercase', marginBottom: 12 }}>
            ◈ ChurnGuard AI
          </div>
          <h1 style={{ fontSize: 28, fontWeight: 700, letterSpacing: '-0.03em', color: 'var(--text)' }}>
            Customer Churn<br />Prediction Platform
          </h1>
          <p style={{ color: 'var(--text2)', fontSize: 13, marginTop: 8 }}>
            ML-powered churn detection at production scale
          </p>
        </div>

        {/* Card */}
        <div className="card" style={{ border: '1px solid var(--border2)' }}>
          {/* Tabs */}
          <div style={{ display: 'flex', borderBottom: '1px solid var(--border)', marginBottom: 24, marginTop: -8 }}>
            {['login', 'register'].map(t => (
              <button
                key={t}
                onClick={() => { setTab(t); setError('') }}
                style={{
                  flex: 1, padding: '12px', background: 'none', border: 'none',
                  borderBottom: tab === t ? '2px solid var(--teal)' : '2px solid transparent',
                  color: tab === t ? 'var(--text)' : 'var(--text2)',
                  fontWeight: tab === t ? 600 : 400,
                  fontSize: 13, cursor: 'pointer',
                  fontFamily: 'var(--sans)',
                  textTransform: 'capitalize',
                  transition: 'all 0.15s',
                  marginBottom: -1,
                }}
              >
                {t}
              </button>
            ))}
          </div>

          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label className="label">Email</label>
              <input
                type="email" value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="admin@example.com"
                required
              />
            </div>

            <div className="form-group">
              <label className="label">Password</label>
              <input
                type="password" value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="••••••••"
                required minLength={8}
              />
            </div>

            {tab === 'register' && (
              <div className="form-group">
                <label className="label">Role</label>
                <select value={role} onChange={e => setRole(e.target.value)}>
                  <option value="api_user">API User</option>
                  <option value="analyst">Analyst</option>
                  <option value="ml_engineer">ML Engineer</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
            )}

            {error && <div className="error-msg">{error}</div>}

            {tab === 'register' && !error && (
              <div className="success-msg" style={{ display: 'none' }} id="reg-success">
                Account created. Please login.
              </div>
            )}

            <button
              type="submit"
              className="btn btn-primary"
              disabled={loading}
              style={{ width: '100%', justifyContent: 'center', marginTop: 20, padding: '12px' }}
            >
              {loading ? <span className="spinner" /> : tab === 'login' ? 'Sign In' : 'Create Account'}
            </button>
          </form>
        </div>

        <p style={{ textAlign: 'center', fontSize: 11, color: 'var(--text3)', marginTop: 20, fontFamily: 'var(--mono)' }}>
          FastAPI · PostgreSQL · Redis · Celery · scikit-learn
        </p>
      </div>
    </div>
  )
}
