import { apiUrl } from './api'

// Latest passing attempt with a saved circuit, per challenge.
export function solvedWithCircuits(attempts) {
  const best = new Map()
  for (const a of attempts) {
    if (!a.passed || a.challenge_id.startsWith('quiz:') || !Array.isArray(a.gates) || a.gates.length === 0) continue
    if (!best.has(a.challenge_id)) best.set(a.challenge_id, a) // attempts arrive newest first
  }
  return [...best.values()]
}

// Re-runs each circuit through the grader. Rows are browser-written, so this
// (not the stored "passed" flag) is what makes an entry count as verified.
export async function verifySolutions(entries) {
  if (entries.length === 0) return new Set()
  const response = await fetch(apiUrl('/practice/verify'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      items: entries.map((e) => ({
        challenge_id: e.challenge_id,
        gates: e.gates.map(({ name, qubits, params }) => ({ name, qubits, params: params || [] })),
      })),
    }),
  })
  if (!response.ok) throw new Error(`verification failed (status ${response.status})`)
  const data = await response.json()
  return new Set(data.results.filter((r) => r.verified).map((r) => r.challenge_id))
}
