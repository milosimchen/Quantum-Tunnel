import { useState } from 'react'
import CircuitDiagram from '../CircuitDiagram'
import PageHeader from '../PageHeader'
import { useCopilotPage } from '../useCopilotPage'
import { useCircuit, displayName } from '../CircuitContext'

const PALETTE_GATES = ['h', 'x', 'y', 'z', 's', 't', 'cx', 'cz']

function Studio() {
  const {
    gates,
    gateName, setGateName,
    qubitInput, setQubitInput,
    scanResult,
    isScanning,
    errorMessage,
    currentNumQubits,
    pendingTwoQubitGate,
    handleAddGate,
    handleDeleteGate,
    handleScan,
    cancelPendingGate,
    handleGateDrop,
    completeTwoQubitGate,
    minQubits, addQubit, removeQubit,
    clearCircuit,
    nlRequest, setNlRequest,
    isGenerating,
    generationMessage,
    handleGenerateCircuit,
    setIsMathDeepDiveOpen,
    fetchMathDeepDive,
  } = useCircuit()

  const [selectedStepIndex, setSelectedStepIndex] = useState(null)
  useCopilotPage({ kind: 'studio' })

  function handleDragStart(event, gate) {
    event.dataTransfer.setData('text/plain', gate)
  }

  function handleStepClick(index) {
    setSelectedStepIndex((current) => (current === index ? null : index))
  }

  function handleClearCircuit() {
    clearCircuit()
    setSelectedStepIndex(null)
  }

  function handleNlKeyDown(event) {
    if (event.key === 'Enter' && !isGenerating) {
      handleGenerateCircuit()
    }
  }

  const diagramNumQubits = Math.max(currentNumQubits, minQubits)

  const highlightedIndices =
    selectedStepIndex !== null && scanResult
      ? scanResult.simplification_steps[selectedStepIndex].affected_gate_indices
      : null

  return (
    <div className="app-shell">
      <PageHeader subtitle="verified circuit analysis" />

      <div className="nl-hero">
        <p className="nl-label">describe a circuit</p>
        <div className="nl-row">
          <input
            type="text"
            className="nl-input"
            value={nlRequest}
            onChange={(e) => setNlRequest(e.target.value)}
            onKeyDown={handleNlKeyDown}
            placeholder='e.g. "build a Bell state on qubits 2 and 4" or "add an H on qubit 0"'
            disabled={isGenerating}
          />
          <button
            className="btn nl-submit"
            onClick={handleGenerateCircuit}
            disabled={isGenerating || !nlRequest.trim()}
          >
            {isGenerating ? 'generating...' : 'generate'}
          </button>
        </div>
        {generationMessage && (
          <p className={generationMessage.type === 'error' ? 'error-text' : 'success-text'}>
            {generationMessage.text}
          </p>
        )}
      </div>

      <div className="layout layout-three-col">
        <div className="col">
          <div className="panel">
            <p className="panel-label">Gate palette</p>
            <div className="qubit-controls">
                <span className="field-label">Qubits: {diagramNumQubits}</span>
                <button className="qubit-btn" onClick={addQubit}>+</button>
                <button className="qubit-btn" onClick={removeQubit}>−</button>
            </div>
            <div className="gate-palette">
              {PALETTE_GATES.map((gate) => (
                <div
                  key={gate}
                  className="gate-chip"
                  draggable
                  onDragStart={(e) => handleDragStart(e, gate)}
                >
                  {gate.toUpperCase()}
                </div>
              ))}
            </div>
            <p className="drop-hint">drag onto a wire in the diagram</p>

            {pendingTwoQubitGate && (
              <div className="pending-gate-banner">
                Placing {pendingTwoQubitGate.name.toUpperCase()} — control on q{pendingTwoQubitGate.controlQubit}. Click another wire for the target.
                <button className="cancel-pending" onClick={cancelPendingGate}>cancel</button>
              </div>
            )}

            <p className="panel-label" style={{ marginTop: '20px' }}>Or add manually</p>
            <div className="field-row">
              <span className="field-label">Gate</span>
              <select value={gateName} onChange={(e) => setGateName(e.target.value)}>
                <option value="h">H — Hadamard</option>
                <option value="x">X — Pauli-X</option>
                <option value="y">Y — Pauli-Y</option>
                <option value="z">Z — Pauli-Z</option>
                <option value="s">S — Phase</option>
                <option value="t">T</option>
                <option value="cx">CX — CNOT</option>
                <option value="cz">CZ</option>
              </select>
            </div>
            <div className="field-row">
              <span className="field-label">Qubit(s)</span>
              <input
                type="text"
                value={qubitInput}
                onChange={(e) => setQubitInput(e.target.value)}
                placeholder="e.g. 0 or 0,1"
              />
            </div>
            <button className="btn" onClick={handleAddGate}>+ add gate</button>
          </div>

          <div className="panel" style={{ flex: 1 }}>
            <p className="panel-label">Circuit ({gates.length})</p>
            {gates.length === 0 ? (
              <p className="empty-state">No gates yet.</p>
            ) : (
              <div className="gate-list">
                {gates.map((gate, index) => (
                  <div className="gate-row" key={index}>
                    <span>{gate.name.toUpperCase()} · q{gate.qubits.join(',')}</span>
                    <button className="remove-btn" onClick={() => handleDeleteGate(index)}>✕</button>
                  </div>
                ))}
              </div>
            )}
            <button
              className="btn"
              style={{ marginTop: 'auto', width: '100%' }}
              onClick={handleScan}
              disabled={gates.length === 0 || isScanning}
            >
              {isScanning ? 'scanning...' : 'scan circuit'}
            </button>
            <button
              className="btn"
              style={{ marginTop: '8px', width: '100%' }}
              onClick={handleClearCircuit}
              disabled={gates.length === 0}
            >
              clear circuit
            </button>
            <button
              className="btn btn-teal"
              style={{ marginTop: '8px', width: '100%' }}
              onClick={() => { setIsMathDeepDiveOpen(true); fetchMathDeepDive('original') }}
              disabled={gates.length === 0}
            >
              math deep dive
            </button>
          </div>
        </div>

        <div className="panel">
          <p className="scope-title active">original — {gates.length} gates</p>
          <CircuitDiagram
            gates={gates}
            numQubits={diagramNumQubits}
            interactive={true}
            onGateDrop={handleGateDrop}
            onWireClick={completeTwoQubitGate}
            pendingControlQubit={pendingTwoQubitGate ? pendingTwoQubitGate.controlQubit : null}
            highlightedIndices={highlightedIndices}
          />

          {errorMessage && <p className="error-text">{errorMessage}</p>}

          {scanResult && (
            <>
              <div className="divider-label">
                simplified — {scanResult.simplified_gate_count} gates
              </div>
              {scanResult.final_circuit_gates.length === 0 ? (
                <p className="empty-state">Fully simplified away — empty circuit.</p>
              ) : (
                <CircuitDiagram
                  gates={scanResult.final_circuit_gates}
                  numQubits={currentNumQubits}
                />
              )}
            </>
          )}
        </div>

        <div className="panel">
          <p className="panel-label">Readout</p>
          {!scanResult ? (
            <p className="empty-state">Scan a circuit to see results.</p>
          ) : (
            <>
              <table className="metric-table">
                <tbody>
                  <tr><td>Gate count</td><td>{scanResult.original_gate_count} → {scanResult.simplified_gate_count}</td></tr>
                  <tr><td>Depth</td><td>{scanResult.original_depth} → {scanResult.simplified_depth}</td></tr>
                  <tr><td>Motifs found</td><td>{scanResult.motifs_found.length || '—'}</td></tr>
                  <tr><td>Target match</td><td>{scanResult.target_match ? displayName(scanResult.target_match) : '—'}</td></tr>
                </tbody>
              </table>

              {scanResult.motifs_found.length > 0 && (
                <div className="motif-list">
                  {scanResult.motifs_found.map((m, index) => (
                    <div className="motif-item" key={index}>
                      {displayName(m.motif)} <span className="motif-qubits">· q{m.qubits.join(',')}</span>
                    </div>
                  ))}
                </div>
              )}

              <p className="panel-label" style={{ marginTop: '16px' }}>
                Steps <span style={{ textTransform: 'none', letterSpacing: 0, fontSize: '9.5px', color: 'var(--text-muted)' }}>— click to trace</span>
              </p>
              {scanResult.simplification_steps.length === 0 ? (
                <p className="empty-state">None found.</p>
              ) : (
                <div className="step-list">
                  {scanResult.simplification_steps.map((step, index) => (
                    <div
                      className={`step-item clickable-step ${selectedStepIndex === index ? 'selected' : ''}`}
                      key={index}
                      onClick={() => handleStepClick(index)}
                    >
                      <strong style={{ color: 'var(--amber)', display: 'block' }}>{step.rule}</strong>
                      gates {step.before_gate_count}→{step.after_gate_count} · depth {step.before_depth}→{step.after_depth}
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}

export default Studio