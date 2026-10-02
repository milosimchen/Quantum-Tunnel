import { formatAngle } from './angles'

const WIRE_SPACING = 60
const GATE_SPACING = 70
const MARGIN_LEFT = 50
const MARGIN_TOP = 30
const GATE_BOX_SIZE = 36


// Theme tokens (index.css). SVG presentation attributes can't read CSS
// variables, so every colour below is applied through a style prop.
const COLORS = {
  wire: 'var(--wire)',
  trace: 'var(--accent)',
  traceHighlight: 'var(--accent-hover)',
  gateBoxFill: 'var(--surface)',
  gateBoxStroke: 'var(--accent)',
  gateBoxStrokeHighlight: 'var(--accent-hover)',
  gateText: 'var(--accent)',
  qubitLabel: 'var(--text-3)',
  pending: 'var(--ai)',
}

function CircuitDiagram({
  gates,
  numQubits,
  interactive = false,
  onGateDrop,
  onWireClick,
  pendingControlQubit,
  highlightedIndices = null,
}) {
  const width = MARGIN_LEFT + (gates.length + 1) * GATE_SPACING
  // Extra room below the last wire when a rotation's angle label hangs under its box.
  const angleRoom = gates.some((g) => g.params?.length) ? 16 : 0
  const height = MARGIN_TOP * 2 + (numQubits - 1) * WIRE_SPACING + angleRoom

  function qubitY(qubitIndex) {
    return MARGIN_TOP + qubitIndex * WIRE_SPACING
  }

  function gateX(gateIndex) {
    return MARGIN_LEFT + (gateIndex + 1) * GATE_SPACING
  }

  function handleDragOver(event) {
    if (!interactive) return
    event.preventDefault()
  }

  function handleDrop(event, qubitIndex) {
    if (!interactive) return
    event.preventDefault()
    const gateName = event.dataTransfer.getData('text/plain')
    if (gateName && onGateDrop) {
      onGateDrop(gateName, qubitIndex)
    }
  }

  function handleWireClick(qubitIndex) {
    if (!interactive || !onWireClick) return
    onWireClick(qubitIndex)
  }

  // Whether highlighting is active at all -- if highlightedIndices is null,
  // every gate renders at full opacity as before (no filtering).
  const isHighlighting = highlightedIndices !== null

  function gateOpacity(gateIndex) {
    if (!isHighlighting) return 1
    return highlightedIndices.includes(gateIndex) ? 1 : 0.2
  }

  function gateColors(gateIndex) {
    const isHighlighted = isHighlighting && highlightedIndices.includes(gateIndex)
    return {
      trace: isHighlighted ? COLORS.traceHighlight : COLORS.trace,
      stroke: isHighlighted ? COLORS.gateBoxStrokeHighlight : COLORS.gateBoxStroke,
    }
  }

  return (
    <svg width={width} height={height} style={{ background: 'transparent' }}>

      {Array.from({ length: numQubits }).map((_, qubitIndex) => {
        const isPendingControl = pendingControlQubit === qubitIndex
        return (
          <g key={`wire-group-${qubitIndex}`}>
            {interactive && (
              <rect
                x={MARGIN_LEFT}
                y={qubitY(qubitIndex) - 15}
                width={width - MARGIN_LEFT * 1.5}
                height={30}
                fill="transparent"
                style={{ cursor: 'pointer' }}
                onDragOver={handleDragOver}
                onDrop={(e) => handleDrop(e, qubitIndex)}
                onClick={() => handleWireClick(qubitIndex)}
              />
            )}
            <line
              x1={MARGIN_LEFT}
              y1={qubitY(qubitIndex)}
              x2={width - MARGIN_LEFT / 2}
              y2={qubitY(qubitIndex)}
              strokeWidth={isPendingControl ? 2.5 : 1.5}
              style={{ pointerEvents: 'none', stroke: isPendingControl ? COLORS.pending : COLORS.wire }}
            />
          </g>
        )
      })}

      {Array.from({ length: numQubits }).map((_, qubitIndex) => (
        <text
          key={`label-${qubitIndex}`}
          x={10}
          y={qubitY(qubitIndex) + 5}
          fontSize={13}
          fontFamily="'JetBrains Mono', monospace"
          style={{ pointerEvents: 'none', fill: COLORS.qubitLabel }}
        >
          q{qubitIndex}
        </text>
      ))}

      {gates.map((gate, index) => {
        const x = gateX(index)
        const opacity = gateOpacity(index)
        const { trace, stroke } = gateColors(index)
        const ys = gate.qubits.map(qubitY)

        const dot = (y, key) => <circle key={key} cx={x} cy={y} r={6} style={{ fill: trace }} />
        const cross = (y, key) => (
          <g key={key}>
            <line x1={x - 7} y1={y - 7} x2={x + 7} y2={y + 7} strokeWidth={2} style={{ stroke: trace }} />
            <line x1={x - 7} y1={y + 7} x2={x + 7} y2={y - 7} strokeWidth={2} style={{ stroke: trace }} />
          </g>
        )
        const target = (y, key) => (
          <g key={key}>
            <circle cx={x} cy={y} r={13} strokeWidth={2} style={{ fill: COLORS.gateBoxFill, stroke: trace }} />
            <line x1={x - 13} y1={y} x2={x + 13} y2={y} strokeWidth={2} style={{ stroke: trace }} />
            <line x1={x} y1={y - 13} x2={x} y2={y + 13} strokeWidth={2} style={{ stroke: trace }} />
          </g>
        )
        const box = (y, label, key) => (
          <g key={key}>
            <rect x={x - GATE_BOX_SIZE / 2} y={y - GATE_BOX_SIZE / 2} width={GATE_BOX_SIZE} height={GATE_BOX_SIZE} rx={8} strokeWidth={1.5} style={{ fill: COLORS.gateBoxFill, stroke }} />
            <text x={x} y={y + 5} fontSize={label.length > 2 ? 11.5 : 13} fontFamily="'JetBrains Mono', monospace" textAnchor="middle" style={{ fill: COLORS.gateText }}>
              {label}
            </text>
          </g>
        )
        const angleLabel = (y) => gate.params?.length > 0 && (
          <text key="angle" x={x} y={y + GATE_BOX_SIZE / 2 + 13} fontSize={10.5} fontFamily="'JetBrains Mono', monospace" textAnchor="middle" style={{ fill: COLORS.qubitLabel }}>
            {formatAngle(gate.params[0])}
          </text>
        )

        let parts
        if (gate.qubits.length === 1) {
          parts = [box(ys[0], gate.name.toUpperCase(), 'b'), angleLabel(ys[0])]
        } else if (gate.name === 'swap') {
          parts = [cross(ys[0], 'a'), cross(ys[1], 'b')]
        } else if (gate.name === 'cx' || gate.name === 'ccx') {
          parts = [...ys.slice(0, -1).map((y, i) => dot(y, `c${i}`)), target(ys[ys.length - 1], 't')]
        } else if (gate.name === 'cz') {
          parts = [dot(ys[0], 'a'), dot(ys[1], 'b')]
        } else if (gate.name === 'rzz') {
          parts = [box(ys[0], 'ZZ', 'a'), box(ys[1], 'ZZ', 'b'), angleLabel(Math.max(...ys))]
        } else {
          // Controlled single-qubit gate (CP, CRZ, CY): dot on the control, labelled box on the target.
          const label = { cp: 'P', crz: 'RZ', cy: 'Y' }[gate.name] || gate.name.toUpperCase()
          parts = [dot(ys[0], 'c'), box(ys[1], label, 't'), angleLabel(ys[1])]
        }

        return (
          <g key={index} style={{ pointerEvents: 'none', opacity }}>
            {ys.length > 1 && (
              <line x1={x} y1={Math.min(...ys)} x2={x} y2={Math.max(...ys)} strokeWidth={2} style={{ stroke: trace }} />
            )}
            {parts}
          </g>
        )
      })}
    </svg>
  )
}

export default CircuitDiagram