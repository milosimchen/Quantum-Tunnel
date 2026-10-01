const WIRE_SPACING = 60
const GATE_SPACING = 70
const MARGIN_LEFT = 50
const MARGIN_TOP = 30
const GATE_BOX_SIZE = 36

const TWO_QUBIT_GATES = new Set(['cx', 'cz'])

const COLORS = {
  wire: '#34392A',
  wireHover: '#5A6148',
  trace: '#FFB020',
  traceHighlight: '#FFCB6B',
  gateBoxFill: '#101209',
  gateBoxStroke: '#FFB020',
  gateBoxStrokeHighlight: '#FFCB6B',
  gateText: '#FFB020',
  qubitLabel: '#656350',
  pending: '#7DD3C0',
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
  const height = MARGIN_TOP * 2 + (numQubits - 1) * WIRE_SPACING

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
      <defs>
        <filter id="amber-glow" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="2" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

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
              stroke={isPendingControl ? COLORS.pending : COLORS.wire}
              strokeWidth={isPendingControl ? 2.5 : 1.5}
              style={{ pointerEvents: 'none' }}
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
          fontFamily="'IBM Plex Mono', monospace"
          fill={COLORS.qubitLabel}
          style={{ pointerEvents: 'none' }}
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
            <g key={index} filter="url(#amber-glow)" style={{ pointerEvents: 'none', opacity }}>
              <line x1={x} y1={yControl} x2={x} y2={yTarget} stroke={trace} strokeWidth={1.6} />
              <circle cx={x} cy={yControl} r={5} fill={trace} />
              {gate.name === 'cx' ? (
                <>
                  <circle cx={x} cy={yTarget} r={12} fill={COLORS.gateBoxFill} stroke={trace} strokeWidth={1.6} />
                  <line x1={x - 12} y1={yTarget} x2={x + 12} y2={yTarget} stroke={trace} strokeWidth={1.6} />
                  <line x1={x} y1={yTarget - 12} x2={x} y2={yTarget + 12} stroke={trace} strokeWidth={1.6} />
                </>
              ) : (
                <circle cx={x} cy={yTarget} r={5} fill={trace} />
              )}
            </g>
          )
        }

        const y = qubitY(gate.qubits[0])
        return (
          <g key={index} filter="url(#amber-glow)" style={{ pointerEvents: 'none', opacity }}>
            <rect
              x={x - GATE_BOX_SIZE / 2}
              y={y - GATE_BOX_SIZE / 2}
              width={GATE_BOX_SIZE}
              height={GATE_BOX_SIZE}
              rx={3}
              fill={COLORS.gateBoxFill}
              stroke={stroke}
              strokeWidth={1.4}
            />
            <text
              x={x}
              y={y + 5}
              fontSize={13}
              fontFamily="'IBM Plex Mono', monospace"
              fill={COLORS.gateText}
              textAnchor="middle"
            >
              {gate.name.toUpperCase()}
            </text>
          </g>
        )
      })}
    </svg>
  )
}

export default CircuitDiagram