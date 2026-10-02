// Backend base URL. VITE_API_URL (frontend/.env.local, or the host's settings)
// wins. Without it, local development uses the dev server and production
// builds use the deployed backend, so a missing variable can never make the
// live site call someone's localhost.
const PRODUCTION_API = 'https://quantum-tunnel-api.onrender.com'
const DEFAULT_API = import.meta.env.DEV ? 'http://127.0.0.1:8000' : PRODUCTION_API

export const API_BASE = (import.meta.env.VITE_API_URL || DEFAULT_API).replace(/\/$/, '')

export function apiUrl(path) {
  return `${API_BASE}${path}`
}
