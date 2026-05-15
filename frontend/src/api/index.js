const BASE = '/api'

async function request(path, options = {}) {
  const { body, headers: extraHeaders, ...rest } = options
  const hasBody = body !== undefined

  const res = await fetch(`${BASE}${path}`, {
    headers: {
      ...(hasBody ? { 'Content-Type': 'application/json' } : {}),
      ...extraHeaders,
    },
    body: hasBody ? JSON.stringify(body) : undefined,
    ...rest,
  })

  if (!res.ok) {
    let detail = `HTTP ${res.status}`
    try {
      const err = await res.json()
      detail = err.detail || err.message || detail
    } catch {
      // ignore parse errors
    }
    throw new Error(detail)
  }

  return res.json()
}

export const api = {
  health: () => request('/health'),
  toolCheck: () => request('/toolcheck'),

  interfaces: {
    list: () => request('/interfaces'),
    monitor: (iface, action) =>
      request('/monitor', { method: 'POST', body: { interface: iface, action } }),
    checkKill: (iface) =>
      request('/checkkill', { method: 'POST', body: { interface: iface } }),
  },

  airodump: {
    jobs: () => request('/airodump/jobs'),
    start: (params) => request('/airodump/start', { method: 'POST', body: params }),
    stop: (jobId) => request('/airodump/stop', { method: 'POST', body: { job_id: jobId } }),
    results: (jobId) => request(`/airodump/results/${encodeURIComponent(jobId)}`),
  },

  aireplay: {
    deauth: (params) => request('/aireplay/deauth', { method: 'POST', body: params }),
  },

  aircrack: {
    crack: (params) => request('/aircrack/crack', { method: 'POST', body: params }),
    validate: (path) => request(`/aircrack/validate?path=${encodeURIComponent(path)}`),
    status: (jobId) => request(`/aircrack/${encodeURIComponent(jobId)}/status`),
    stop: (jobId) => request(`/aircrack/${encodeURIComponent(jobId)}/stop`, { method: 'POST' }),
  },

  captures: {
    list: () => request('/captures'),
    capFiles: () => request('/captures/cap'),
    delete: (filename) =>
      request(`/captures/${encodeURIComponent(filename)}`, { method: 'DELETE' }),
  },

  handshake: {
    start: (params) => request('/handshake/start', { method: 'POST', body: params }),
    status: (jobId) => request(`/handshake/${encodeURIComponent(jobId)}/status`),
    stop: (jobId) =>
      request(`/handshake/${encodeURIComponent(jobId)}/stop`, { method: 'POST' }),
  },
}
