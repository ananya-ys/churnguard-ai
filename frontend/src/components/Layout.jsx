import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../App'
import { useState, useEffect } from 'react'
import { api } from '../api'

const NAV = [
  { to: '/',        label: 'Dashboard',    icon: '◈' },
  { to: '/predict', label: 'Predict',      icon: '⟡' },
  { to: '/batch',   label: 'Batch Upload', icon: '⊞' },
  { to: '/models',  label: 'Models',       icon: '⬡' },
  { to: '/jobs',    label: 'Jobs',         icon: '◎' },
]

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [health, setHealth] = useState(null)

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth({ status: 'error' }))
    const t = setInterval(() => {
      api.health().then(setHealth).catch(() => setHealth({ status: 'error' }))
    }, 30000)
    return () => clearInterval(t)
  }, [])

  function handleLogout() {
    logout()
    navigate('/login')
  }

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>
      {/* Sidebar */}
      <aside style={{
        width: 220,
        background: 'var(--bg2)',
        borderRight: '1px solid var(--border)',
        display: 'flex',
        flexDirection: 'column',
        flexShrink: 0,
      }}>
        {/* Logo */}
        <div style={{ padding: '24px 20px 20px', borderBottom: '1px solid var(--border)' }}>
          <div style={{ fontFamily: 'var(--mono)', fontSize: 13, color: 'var(--teal)', fontWeight: 700, letterSpacing: '0.05em' }}>
            CHURNGUARD
          </div>
          <div style={{ fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--text3)', marginTop: 2 }}>
            AI · v1.0.0
          </div>
        </div>

        {/* System status */}
        <div style={{ padding: '12px 20px', borderBottom: '1px solid var(--border)', fontSize: 11 }}>
          <div style={{ color: 'var(--text3)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 6 }}>System</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: health?.database === 'ok' ? 'var(--teal)' : 'var(--red)', flexShrink: 0 }} />
            <span style={{ color: 'var(--text2)' }}>Database</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: health?.redis === 'ok' ? 'var(--teal)' : 'var(--red)', flexShrink: 0 }} />
            <span style={{ color: 'var(--text2)' }}>Redis</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: health?.model_loaded ? 'var(--teal)' : 'var(--yellow)', flexShrink: 0 }} />
            <span style={{ color: 'var(--text2)' }}>Model {health?.model_loaded ? 'Loaded' : 'Not Loaded'}</span>
          </div>
        </div>

        {/* Nav */}
        <nav style={{ padding: '12px 10px', flex: 1 }}>
          {NAV.map(({ to, label, icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              style={({ isActive }) => ({
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                padding: '9px 12px',
                borderRadius: 'var(--radius)',
                color: isActive ? 'var(--teal)' : 'var(--text2)',
                background: isActive ? 'rgba(0,229,195,0.08)' : 'transparent',
                fontSize: 13,
                fontWeight: isActive ? 600 : 400,
                marginBottom: 2,
                transition: 'all 0.1s',
                textDecoration: 'none',
              })}
            >
              <span style={{ fontFamily: 'var(--mono)', fontSize: 14, width: 16, textAlign: 'center' }}>{icon}</span>
              {label}
            </NavLink>
          ))}
        </nav>

        {/* User */}
        <div style={{ padding: '16px 20px', borderTop: '1px solid var(--border)' }}>
          <div style={{ fontSize: 12, color: 'var(--text2)', marginBottom: 2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {user?.email}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span className="badge badge-gray" style={{ fontSize: 10 }}>{user?.role}</span>
            <button onClick={handleLogout} style={{ background: 'none', border: 'none', color: 'var(--text3)', fontSize: 11, cursor: 'pointer', fontFamily: 'var(--mono)' }}>
              logout
            </button>
          </div>
        </div>
      </aside>

      {/* Main */}
      <main style={{ flex: 1, overflow: 'auto', padding: '32px 36px' }}>
        <Outlet />
      </main>
    </div>
  )
}
