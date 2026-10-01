// Rotation angles for RZ/RX/RY: parsing user input and showing angles as
// multiples of π, so "pi/2", "π/2", "-pi/4", "1.5708" and "3*pi/4" all work.

export const COMMON_ANGLES = [
  { label: 'π/4', value: Math.PI / 4 },
  { label: 'π/2', value: Math.PI / 2 },
  { label: 'π', value: Math.PI },
  { label: '3π/2', value: (3 * Math.PI) / 2 },
  { label: '−π/2', value: -Math.PI / 2 },
  { label: '−π/4', value: -Math.PI / 4 },
]

// Returns a number, or null if the text isn't a simple angle expression.
export function parseAngle(text) {
  const cleaned = String(text).trim().toLowerCase().replace(/π/g, 'pi').replace(/−/g, '-').replace(/\s+/g, '')
  if (!cleaned) return null
  // [sign][coefficient][*]pi[/denominator]  or a plain decimal number.
  const piMatch = cleaned.match(/^(-?)(\d*\.?\d*)\*?pi(?:\/(\d+\.?\d*))?$/)
  if (piMatch) {
    const sign = piMatch[1] === '-' ? -1 : 1
    const coefficient = piMatch[2] === '' ? 1 : Number(piMatch[2])
    const denominator = piMatch[3] ? Number(piMatch[3]) : 1
    if (!Number.isFinite(coefficient) || !denominator) return null
    return (sign * coefficient * Math.PI) / denominator
  }
  const plain = Number(cleaned)
  return Number.isFinite(plain) ? plain : null
}

// 1.5707963 -> "π/2"; falls back to two decimals for anything else.
export function formatAngle(value) {
  const ratio = value / Math.PI
  for (const denominator of [1, 2, 3, 4, 6, 8]) {
    const numerator = Math.round(ratio * denominator)
    if (numerator !== 0 && Math.abs(ratio * denominator - numerator) < 1e-6) {
      const sign = numerator < 0 ? '−' : ''
      const n = Math.abs(numerator)
      const top = n === 1 ? 'π' : `${n}π`
      return denominator === 1 ? `${sign}${top}` : `${sign}${top}/${denominator}`
    }
  }
  return Math.abs(value) < 1e-9 ? '0' : value.toFixed(2)
}

export function gateLabel(gate) {
  const name = gate.name.toUpperCase()
  return gate.params?.length ? `${name}(${formatAngle(gate.params[0])})` : name
}
