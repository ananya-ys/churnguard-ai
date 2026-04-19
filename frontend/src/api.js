const BASE_URL = import.meta.env.VITE_API_URL || ''

function getToken() {
  return localStorage.getItem('token')
}

function authHeaders() {
  return {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${getToken()}`
  }
}

async function handleResponse(res) {
  const data = await res.json()
  if (!res.ok) throw new Error(data.message || 'Request failed')
  return data
}

export const api = {
  // Auth
  async login(email, password) {
    const form = new URLSearchParams()
    form.append('username', email)
    form.append('password', password)
    const res = await fetch(`${BASE_URL}/api/v1/auth/login`, {
      method: 'POST',
      body: form
    })
    return handleResponse(res)
  },

  async register(email, password, role = 'api_user') {
    const res = await fetch(`${BASE_URL}/api/v1/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, role })
    })
    return handleResponse(res)
  },

  async me() {
    const res = await fetch(`${BASE_URL}/api/v1/auth/me`, {
      headers: authHeaders()
    })
    return handleResponse(res)
  },

  // Health
  async health() {
    const res = await fetch(`${BASE_URL}/health`)
    return handleResponse(res)
  },

  // Predict
  async predict(records) {
    const res = await fetch(`${BASE_URL}/api/v1/predict`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({ records })
    })
    return handleResponse(res)
  },

  // Models
  async listModels() {
    const res = await fetch(`${BASE_URL}/api/v1/models`, {
      headers: authHeaders()
    })
    return handleResponse(res)
  },

  async getActiveModel() {
    const res = await fetch(`${BASE_URL}/api/v1/models/active`, {
      headers: authHeaders()
    })
    return handleResponse(res)
  },

  async promoteModel(id) {
    const res = await fetch(`${BASE_URL}/api/v1/models/${id}/promote`, {
      method: 'POST',
      headers: authHeaders()
    })
    return handleResponse(res)
  },

  async rollbackModel() {
    const res = await fetch(`${BASE_URL}/api/v1/models/rollback`, {
      method: 'POST',
      headers: authHeaders()
    })
    return handleResponse(res)
  },

  // Batch Jobs
  async uploadCSV(file) {
    const form = new FormData()
    form.append('file', file)
    const res = await fetch(`${BASE_URL}/api/v1/upload`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${getToken()}` },
      body: form
    })
    return handleResponse(res)
  },

  async listJobs() {
    const res = await fetch(`${BASE_URL}/api/v1/jobs`, {
      headers: authHeaders()
    })
    return handleResponse(res)
  },

  async getJob(jobId) {
    const res = await fetch(`${BASE_URL}/api/v1/jobs/${jobId}`, {
      headers: authHeaders()
    })
    return handleResponse(res)
  },
}
