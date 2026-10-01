import { formatAngle } from './angles'

const WIRE_SPACING = 60
const GATE_SPACING = 70
const MARGIN_LEFT = 50
const MARGIN_TOP = 30
const GATE_BOX_SIZE = 36

const TWO_QUBIT_GATES = new Set(['cx', 'cz', 'swap'])

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

        if (TWO_QUBIT_GATES.has(gate.name)) {
          const [controlQubit, targetQubit] = gate.qubits
          const yControl = qubitY(controlQubit)
          const yTarget = qubitY(targetQubit)

          return (
            <g key={index} style={{ pointerEvents: 'none', opacity }}>
              <line x1={x} y1={yControl} x2={x} y2={yTarget} strokeWidth={2} style={{ stroke: trace }} />
              {gate.name === 'swap' ? (
                <>
                  <line x1={x - 7} y1={yControl - 7} x2={x + 7} y2={yControl + 7} strokeWidth={2} style={{ stroke: trace }} />
                  <line x1={x - 7} y1={yControl + 7} x2={x + 7} y2={yControl - 7} strokeWidth={2} style={{ stroke: trace }} />
                </>
              ) : (
                <circle cx={x} cy={yControl} r={6} style={{ fill: trace }} />
              )}
              {gate.name === 'swap' ? (
                <>
                  <line x1={x - 7} y1={yTarget - 7} x2={x + 7} y2={yTarget + 7} strokeWidth={2} style={{ stroke: trace }} />
                  <line x1={x - 7} y1={yTarget + 7} x2={x + 7} y2={yTarget - 7} strokeWidth={2} style={{ stroke: trace }} />
                </>
              ) : gate.name === 'cx' ? (
                <>
                  <circle cx={x} cy={yTarget} r={13} strokeWidth={2} style={{ fill: COLORS.gateBoxFill, stroke: trace }} />
                  <line x1={x - 13} y1={yTarget} x2={x + 13} y2={yTarget} strokeWidth={2} style={{ stroke: trace }} />
                  <line x1={x} y1={yTarget - 13} x2={x} y2={yTarget + 13} strokeWidth={2} style={{ stroke: trace }} />
                </>
              ) : (
                <circle cx={x} cy={yTarget} r={6} style={{ fill: trace }} />
              )}
            </g>
          )
        }

        const y = qubitY(gate.qubits[0])
        return (
          <g key={index} style={{ pointerEvents: 'none', opacity }}>
            <rect
              x={x - GATE_BOX_SIZE / 2}
              y={y - GATE_BOX_SIZE / 2}
              width={GATE_BOX_SIZE}
              height={GATE_BOX_SIZE}
              rx={8}
              strokeWidth={1.5}
              style={{ fill: COLORS.gateBoxFill, stroke }}
            />
            <text
              x={x}
              y={y + 5}
              fontSize={13}
              fontFamily="'JetBrains Mono', monospace"
              textAnchor="middle"
              style={{ fill: COLORS.gateText }}
            >
              {gate.name.toUpperCase()}
            </text>
            {gate.params?.length > 0 && (
              <text
                x={x}
                y={y + GATE_BOX_SIZE / 2 + 13}
                fontSize={10.5}
                fontFamily="'JetBrains Mono', monospace"
                textAnchor="middle"
                style={{ fill: COLORS.qubitLabel }}
              >
                {formatAngle(gate.params[0])}
              </text>
            )}
          </g>
        )
      })}
    </svg>
  )
}

export default CircuitDiagram