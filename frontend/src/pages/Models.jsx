import { useEffect, useState } from 'react'
import { api } from '../api'
import { useAuth } from '../App'

export default function Models() {
  const { user } = useAuth()
  const [models, setModels] = useState([])
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState(null)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const canManage = ['admin', 'ml_engineer'].includes(user?.role)

  async function load() {
    setLoading(true)
    try {
      const data = await api.listModels()
      setModels(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  async function handlePromote(id, tag) {
    setActionLoading(id)
    setError('')
    setSuccess('')
    try {
      await api.promoteModel(id)
      setSuccess(`Model "${tag}" promoted to active`)
      await load()
    } catch (err) {
      setError(err.message)
    } finally {
      setActionLoading(null)
    }
  }

  async function handleRollback() {
    setActionLoading('rollback')
    setError('')
    setSuccess('')
    try {
      const res = await api.rollbackModel()
      setSuccess(`Rolled back to "${res.version_tag}"`)
      await load()
    } catch (err) {
      setError(err.message)
    } finally {
      setActionLoading(null)
    }
  }

  return (
    <div>
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h1>Model Registry</h1>
          <p>All registered model versions with performance metrics</p>
        </div>
        {canManage && (
          <button className="btn btn-danger" onClick={handleRollback} disabled={actionLoading === 'rollback'}>
            {actionLoading === 'rollback' ? <span className="spinner" /> : '↩ Rollback'}
          </button>
        )}
      </div>

      {error && <div className="error-msg" style={{ marginBottom: 16 }}>{error}</div>}
      {success && <div className="success-msg" style={{ marginBottom: 16 }}>✓ {success}</div>}

      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        {loading ? (
          <div style={{ padding: 32, textAlign: 'center', color: 'var(--text2)' }}>
            <span className="spinner" />
          </div>
        ) : models.length === 0 ? (
          <div style={{ padding: 48, textAlign: 'center' }}>
            <div style={{ fontSize: 32, color: 'var(--text3)', marginBottom: 8 }}>⬡</div>
            <div style={{ color: 'var(--text2)', fontSize: 13 }}>No models registered yet</div>
            <div style={{ color: 'var(--text3)', fontSize: 12, marginTop: 4 }}>
              Run the training script to create your first model
            </div>
          </div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Version</th>
                <th>AUC-ROC</th>
                <th>F1</th>
                <th>Precision</th>
                <th>Recall</th>
                <th>Status</th>
                <th>Created</th>
                {canManage && <th>Action</th>}
              </tr>
            </thead>
            <tbody>
              {models.map(m => (
                <tr key={m.id}>
                  <td>
                    <span style={{ fontFamily: 'var(--mono)', fontWeight: 700 }}>{m.version_tag}</span>
                  </td>
                  <td><span style={{ fontFamily: 'var(--mono)', color: 'var(--teal)' }}>{Number(m.auc_roc).toFixed(4)}</span></td>
                  <td><span style={{ fontFamily: 'var(--mono)' }}>{Number(m.f1_score).toFixed(4)}</span></td>
                  <td><span style={{ fontFamily: 'var(--mono)' }}>{Number(m.precision).toFixed(4)}</span></td>
                  <td><span style={{ fontFamily: 'var(--mono)' }}>{Number(m.recall).toFixed(4)}</span></td>
                  <td>
                    <span className={`badge ${m.is_active ? 'badge-green' : 'badge-gray'}`}>
                      {m.is_active ? 'active' : 'inactive'}
                    </span>
                  </td>
                  <td style={{ color: 'var(--text2)', fontSize: 12 }}>
                    {new Date(m.created_at).toLocaleDateString()}
                  </td>
                  {canManage && (
                    <td>
                      {!m.is_active && (
                        <button
                          className="btn btn-ghost"
                          style={{ padding: '6px 12px', fontSize: 12 }}
                          onClick={() => handlePromote(m.id, m.version_tag)}
                          disabled={actionLoading === m.id}
                        >
                          {actionLoading === m.id ? <span className="spinner" /> : 'Promote'}
                        </button>
                      )}
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
