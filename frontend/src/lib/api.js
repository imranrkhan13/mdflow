/**
 * API base URL:
 * - Locally: Vite proxies /api → http://127.0.0.1:8000 (see vite.config.js)
 * - On Vercel: VITE_API_URL must point to your HF Space backend, e.g.
 *   https://your-username-mindflow-backend.hf.space
 *
 * VITE_API_URL is set in Vercel's project → Settings → Environment Variables.
 * It is NOT a secret — it's just a public URL. No API keys here.
 */
const BASE = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/api`
  : '/api'

async function call(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, options)
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

/* In-flight + resolved responses, keyed by path+body. Re-clicking a node or
 * switching tabs returns the previous answer instantly instead of refetching. */
const _cache = new Map()

function cachedCall(path, options) {
  const key = `${path}:${options.body || ''}`
  if (_cache.has(key)) return _cache.get(key)
  const p = call(path, options).catch((e) => { _cache.delete(key); throw e })
  _cache.set(key, p)
  return p
}

export async function uploadDocument(file) {
  const form = new FormData()
  form.append('file', file)
  return call('/upload', { method: 'POST', body: form })
}

export async function importRepo(url) {
  return call('/repo/import', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
  })
}

export async function explainSection(projectId, sectionId, mode = 'explain') {
  return cachedCall('/explain', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ project_id: projectId, section_id: sectionId, mode }),
  })
}

export async function generateInterviewPrep(projectId) {
  return cachedCall('/explain/interview', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ project_id: projectId }),
  })
}

export async function explainArchitecture(projectId) {
  return cachedCall('/explain/architecture', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ project_id: projectId }),
  })
}

export async function listVoices() {
  return call('/video/voices')
}

export async function startVideoGeneration(projectId, sectionId, voice = 'narrator') {
  return call('/video/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ project_id: projectId, section_id: sectionId, voice }),
  })
}

export async function getVideoStatus(jobId) {
  return call(`/video/status/${jobId}`)
}

export function videoDownloadUrl(jobId) {
  return `${BASE}/video/download/${jobId}`
}
