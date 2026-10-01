// The Quantum Tunnel mark: a Bloch sphere with its state vector in the accent colour.
function BrandMark({ size = 26 }) {
  return (
    <svg className="brand-mark" width={size} height={size} viewBox="0 0 26 26" fill="none" aria-hidden="true">
      <circle cx="13" cy="13" r="11" style={{ stroke: 'var(--text-3)' }} strokeWidth="1.3" />
      <ellipse cx="13" cy="13" rx="11" ry="3.8" style={{ stroke: 'var(--text-3)' }} strokeWidth="1.3" />
      <g className="state-vector">
        <line x1="13" y1="13" x2="20" y2="6" style={{ stroke: 'var(--accent)' }} strokeWidth="1.8" strokeLinecap="round" />
        <circle cx="20" cy="6" r="2.4" style={{ fill: 'var(--accent)' }} />
      </g>
    </svg>
  )
}

export default BrandMark
