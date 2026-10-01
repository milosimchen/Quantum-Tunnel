// Drawing of a simulated chip's connectivity: which qubits a two-qubit gate can join.
const UNIT = 56
const PAD = 22

function ChipMap({ device }) {
  const xs = device.layout.map(([x]) => x)
  const ys = device.layout.map(([, y]) => y)
  const width = (Math.max(...xs) - Math.min(...xs)) * UNIT + PAD * 2
  const height = (Math.max(...ys) - Math.min(...ys)) * UNIT + PAD * 2
  const at = (q) => [PAD + device.layout[q][0] * UNIT, PAD + device.layout[q][1] * UNIT]
  const edges = device.edges.map(([a, b]) => `${a}–${b}`).join(', ')

  return (
    <figure className="chip-map">
      <svg width={width} height={height} role="img" aria-label={`${device.name} connectivity: ${edges}`}>
        {device.edges.map(([a, b]) => {
          const [x1, y1] = at(a)
          const [x2, y2] = at(b)
          return <line key={`${a}-${b}`} x1={x1} y1={y1} x2={x2} y2={y2} strokeWidth={2} style={{ stroke: 'var(--border-strong)' }} />
        })}
        {device.layout.map((_, q) => {
          const [x, y] = at(q)
          return (
            <g key={q}>
              <circle cx={x} cy={y} r={14} strokeWidth={1.5} style={{ fill: 'var(--surface)', stroke: 'var(--accent)' }} />
              <text x={x} y={y + 4} textAnchor="middle" fontSize={12} fontFamily="'JetBrains Mono', monospace" style={{ fill: 'var(--text)' }}>{q}</text>
            </g>
          )
        })}
      </svg>
      <figcaption>
        <strong>{device.name}</strong> · {device.description} Native gates: {device.native_gates.map((g) => g.toUpperCase()).join(', ')}.
        CNOT error {Math.round(device.error_rates.two_qubit * 1000) / 10}%, T1 {device.error_rates.t1_us} µs.
      </figcaption>
    </figure>
  )
}

export default ChipMap
