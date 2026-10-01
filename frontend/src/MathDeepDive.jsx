import { useCircuit } from './CircuitContext'

function MathDeepDive() {
  const {
    mathDeepDive,
    isMathDeepDiveOpen, setIsMathDeepDiveOpen,
    isLoadingMathDeepDive,
    mathDeepDiveView,
    fetchMathDeepDive,
    scanResult,
  } = useCircuit()

  if (!isMathDeepDiveOpen) return null

  return (
    <div className="math-dive-overlay" onClick={() => setIsMathDeepDiveOpen(false)}>
      <div className="math-dive-panel" onClick={(e) => e.stopPropagation()}>
        <div className="math-dive-header">
          <span className="ai-copilot-title">math deep dive</span>
          <button className="copilot-close" onClick={() => setIsMathDeepDiveOpen(false)}>✕</button>
        </div>

        <div className="math-dive-tabs">
          <button
            className={`math-dive-tab ${mathDeepDiveView === 'original' ? 'active' : ''}`}
            onClick={() => fetchMathDeepDive('original')}
          >
            original
          </button>
          <button
            className={`math-dive-tab ${mathDeepDiveView === 'simplified' ? 'active' : ''}`}
            onClick={() => fetchMathDeepDive('simplified')}
            disabled={!scanResult}
          >
            simplified
          </button>
        </div>

        {isLoadingMathDeepDive && <p className="empty-state">Computing...</p>}

        {!isLoadingMathDeepDive && mathDeepDive && !mathDeepDive.error && (
          <>
            <p className="panel-label" style={{ marginTop: '16px' }}>Unitary matrix</p>
            {mathDeepDive.unitary_available ? (
              <pre className="math-matrix">{mathDeepDive.unitary_matrix}</pre>
            ) : (
              <p className="empty-state">Too large to display ({mathDeepDive.num_qubits} qubits, capped at 3).</p>
            )}

            <p className="panel-label" style={{ marginTop: '16px' }}>Dirac notation</p>
            {mathDeepDive.dirac_available ? (
              <p className="math-dirac">{mathDeepDive.dirac_notation}</p>
            ) : (
              <p className="empty-state">Too large to display ({mathDeepDive.num_qubits} qubits, capped at 5).</p>
            )}

            <p className="panel-label" style={{ marginTop: '16px' }}>Observations</p>
            <p className="ai-block">{mathDeepDive.observations}</p>
          </>
        )}

        {!isLoadingMathDeepDive && mathDeepDive?.error && (
          <p className="error-text">{mathDeepDive.error}</p>
        )}
      </div>
    </div>
  )
}

export default MathDeepDive