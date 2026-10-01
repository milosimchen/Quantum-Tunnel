// Backend base URL. Set VITE_API_URL in frontend/.env.local (or in the host's
// environment settings when deployed); falls back to the local dev server.
export const API_BASE = (import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')

export function apiUrl(path) {
  return `${API_BASE}${path}`
}
