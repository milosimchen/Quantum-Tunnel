import { useCircuit, displayName } from './CircuitContext'

function CopilotDock() {
  const {
    isCopilotOpen, setIsCopilotOpen,
    scanResult,
    showLimitations, setShowLimitations,
    chatQuestion, setChatQuestion,
    chatHistory,
    isAsking,
    gates,
    handleAskQuestion,
    addGateDirect,
  } = useCircuit()

  function handleClose() {
    setIsCopilotOpen(false)
  }

  return (
    <>
      {isCopilotOpen && <div className="copilot-overlay" onClick={handleClose} />}

      <div className={`copilot-dock ${isCopilotOpen ? 'copilot-dock-open' : ''}`}>
        <div className="copilot-dock-header">
          <div className="ai-copilot-header">
            <span className="ai-dot"></span>
            <span className="ai-copilot-title">AI copilot</span>
          </div>
          <button className="copilot-close" onClick={handleClose} aria-label="Close copilot">✕</button>
        </div>

        <div className="ai-scroll-area">
          {!scanResult ? (
            <p className="empty-state">Scan a circuit in Studio to start a conversation.</p>
          ) : (
            <>
              <div className="copilot-steps">
                {scanResult.step_summaries.map((step, index) => (
                  <div className="copilot-step" key={index}>
                    <span className="num">{index + 1}.</span>
                    <span>{step.rule_applied} — gates {step.before_gate_count}→{step.after_gate_count}, depth {step.before_depth}→{step.after_depth}</span>
                  </div>
                ))}
              </div>

               <div className="ai-block">
                {scanResult.interpretation ? scanResult.interpretation : '[Interpretation could not be verified against the underlying data.]'}
                <button className="limitations-toggle" onClick={() => setShowLimitations(!showLimitations)}>i</button>
              </div>

              {scanResult.single_gate_completion && (
                <div className="completion-callout">
                  <div className="completion-callout-title">suggested next gate</div>
                  Adding <strong>{scanResult.single_gate_completion.gate_name.toUpperCase()}</strong> on
                  qubits {JSON.stringify(scanResult.single_gate_completion.gate_qubits)} would exactly complete
                  a match to <strong>{displayName(scanResult.single_gate_completion.target_name)}</strong>.
                  <button
                    className="completion-apply-btn"
                    onClick={() => addGateDirect(
                      scanResult.single_gate_completion.gate_name,
                      scanResult.single_gate_completion.gate_qubits
                    )}
                  >
                    apply
                  </button>
                </div>
              )}

              {showLimitations && (
                <div className="limitations-popover">{scanResult.limitations}</div>
              )}

              <div className="chat-log">
                {chatHistory.length === 0 ? (
                  <p className="empty-state">Ask a question about this circuit below.</p>
                ) : (
                  chatHistory.map((entry, index) => (
                    <div className="chat-entry" key={index}>
                      <div className="chat-q">{entry.question}</div>
                      <div className="chat-a">{entry.answer}</div>
                      {entry.canAnswer === false && (
                        <div className="warning-text">The circuit data could not fully answer this question.</div>
                      )}
                      {entry.verified === false && (
                        <div className="danger-text">⚠ This answer failed automated consistency verification.</div>
                      )}
                    </div>
                  ))
                )}
              </div>
            </>
          )}
        </div>

        <div className="chat-input-row">
          <input
            type="text"
            value={chatQuestion}
            onChange={(e) => setChatQuestion(e.target.value)}
            placeholder="Ask about this circuit…"
            disabled={gates.length === 0}
          />
          <button
            className="btn btn-teal"
            onClick={handleAskQuestion}
            disabled={gates.length === 0 || isAsking || !chatQuestion.trim()}
          >
            {isAsking ? 'asking...' : 'ask'}
          </button>
        </div>
      </div>
    </>
  )
}

export default CopilotDock