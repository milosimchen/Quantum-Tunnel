import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import PageHeader from '../PageHeader'
import CircuitDiagram from '../CircuitDiagram'
import { useAuth } from '../AuthContext'
import { apiUrl } from '../api'
import { recordPracticeAttempt } from '../progress'
import { usePracticeCircuit } from '../usePracticeCircuit'

const DEFAULT_PALETTE = ['h', 'x', 'y', 'z', 's', 't', 'cx', 'cz']

function constraintLines(challenge) {
  const lines = []
  if (challenge.allowed_gates) lines.push(`Gates allowed: ${challenge.allowed_gates.map((g) => g.toUpperCase()).join(', ')}`)
  if (challenge.allowed_qubits) lines.push(`Only touch qubit ${challenge.allowed_qubits.join(', ')}`)
  if (challenge.max_gates) lines.push(`At most ${challenge.max_gates} gates`)
  if (challenge.max_depth) lines.push(`Depth at most ${challenge.max_depth}`)
  return lines
}

function PracticeChallenge() {
  const { challengeId } = useParams()
  const [catalog, setCatalog] = useState(null)
  const [loadError, setLoadError] = useState(null)

  useEffect(() => {
    fetch(apiUrl('/practice/challenges'))
      .then((response) => response.json())
      .then(setCatalog)
      .catch((e) => setLoadError(`Couldn't load the challenge: ${e.message}`))
  }, [])

  if (loadError) return <Shell><p className="error-text">{loadError}</p></Shell>
  if (!catalog) return <Shell><p className="empty-state">Loading…</p></Shell>

  const index = catalog.challenges.findIndex((c) => c.id === challengeId)
  if (index === -1) {
    return (
      <Shell>
        <p className="empty-state">That challenge doesn't exist. <Link to="/interview">Back to Interview Prep</Link></p>
      </Shell>
    )
  }

  const next = catalog.challenges[index + 1]
  // key resets all builder state when moving between challenges.
  return <ChallengeWorkspace key={challengeId} challenge={catalog.challenges[index]} next={next} />
}

function Shell({ children }) {
  return (
    <div className="app-shell">
      <PageHeader subtitle="interview prep" />
      {children}
    </div>
  )
}

function ChallengeWorkspace({ challenge, next }) {
  const { user } = useAuth()
  const circuit = usePracticeCircuit(challenge.num_qubits)
  const [armedGate, setArmedGate] = useState(null)
  const [result, setResult] = useState(null)
  const [isChecking, setIsChecking] = useState(false)
  const [checkError, setCheckError] = useState(null)
  const [hintsShown, setHintsShown] = useState(0)
  const [solution, setSolution] = useState(null)
  const [attemptCount, setAttemptCount] = useState(0)

  const palette = (challenge.allowed_gates || DEFAULT_PALETTE).filter((g) => DEFAULT_PALETTE.includes(g))
  const constraints = constraintLines(challenge)

  // Any edit makes the previous verdict stale; never show a result for a circuit that has changed.
  useEffect(() => {
    setResult(null)
  }, [circuit.gates])

  function handleWireClick(qubit) {
    if (circuit.pendingTwoQubitGate) {
      circuit.handleWireClick(qubit)
    } else if (armedGate) {
      circuit.handleGateDrop(armedGate, qubit)
    }
  }

  async function handleCheck() {
    setIsChecking(true)
    setCheckError(null)
    try {
      const response = await fetch(apiUrl('/practice/check'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ challenge_id: challenge.id, gates: circuit.gates }),
      })
      const data = await response.json()
      if (!response.ok) {
        setCheckError(data.detail || 'Check failed.')
        return
      }
      setResult(data)
      setAttemptCount((n) => n + 1)
      recordPracticeAttempt(user, {
        challenge_id: challenge.id,
        skill: challenge.skill,
        difficulty: challenge.difficulty,
        passed: data.passed,
        gate_count: data.gate_count,
      })
    } catch (e) {
      setCheckError(`Couldn't reach the server: ${e.message}`)
    } finally {
      setIsChecking(false)
    }
  }

  async function handleShowSolution() {
    const response = await fetch(apiUrl(`/practice/solution/${challenge.id}`))
    setSolution(await response.json())
  }

  return (
    <Shell>
      <Link to="/interview" className="back-link">← all challenges</Link>

      <section className="challenge-header">
        <div className="challenge-card-top">
          <span className="skill-tag">{challenge.skill_label}</span>
          <span className="status-tag">{challenge.difficulty}</span>
        </div>
        <h1 className="module-title">{challenge.title}</h1>
        <p className="challenge-prompt">{challenge.prompt}</p>
        {constraints.length > 0 && (
          <ul className="constraint-list">
            {constraints.map((line) => <li key={line}>{line}</li>)}
          </ul>
        )}
        {(challenge.has_setup || challenge.has_teardown) && (
          <p className="module-note">
            {challenge.has_setup && 'The starting gates described above are applied for you before your circuit. '}
            {challenge.has_teardown && 'The decoding gates are applied for you after your circuit.'}
          </p>
        )}
      </section>

      <div className="practice-layout">
        <div className="panel">
          <p className="panel-label">Gates</p>
          <div className="gate-palette">
            {palette.map((gate) => (
              <button
                key={gate}
                type="button"
                className={`gate-chip ${armedGate === gate ? 'gate-chip-armed' : ''}`}
                draggable
                onDragStart={(e) => e.dataTransfer.setData('text/plain', gate)}
                onClick={() => setArmedGate(armedGate === gate ? null : gate)}
                aria-pressed={armedGate === gate}
              >
                {gate.toUpperCase()}
              </button>
            ))}
          </div>
          <p className="drop-hint">drag onto a wire, or click a gate then click a wire</p>

          {circuit.pendingTwoQubitGate && (
            <div className="pending-gate-banner">
              Placing {circuit.pendingTwoQubitGate.name.toUpperCase()}: control on q{circuit.pendingTwoQubitGate.controlQubit}. Click another wire for the target.
              <button className="cancel-pending" onClick={circuit.cancelPending}>cancel</button>
            </div>
          )}
          {circuit.error && <p className="error-text">{circuit.error}</p>}

          <p className="panel-label" style={{ marginTop: 20 }}>Your circuit ({circuit.gates.length} gates)</p>
          {circuit.gates.length === 0 ? (
            <p className="empty-state">No gates yet.</p>
          ) : (
            <div className="gate-list">
              {circuit.gates.map((gate, i) => (
                <div className="gate-row" key={i}>
                  <span>{i + 1}. {gate.name.toUpperCase()} on q{gate.qubits.join(', q')}</span>
                  <button className="remove-btn" onClick={() => circuit.removeGate(i)} aria-label={`Remove gate ${i + 1}`}>remove</button>
                </div>
              ))}
            </div>
          )}
          {circuit.gates.length > 0 && (
            <button className="link-btn" style={{ marginTop: 8 }} onClick={circuit.clear}>clear circuit</button>
          )}
        </div>

        <div className="panel practice-diagram-panel">
          <p className="panel-label">Diagram · {challenge.num_qubits} qubit{challenge.num_qubits > 1 ? 's' : ''}</p>
          <div className="diagram-scroll">
            <CircuitDiagram
              gates={circuit.gates}
              numQubits={challenge.num_qubits}
              interactive
              onGateDrop={circuit.handleGateDrop}
              onWireClick={handleWireClick}
              pendingControlQubit={circuit.pendingTwoQubitGate?.controlQubit}
            />
          </div>

          <div className="practice-actions">
            <button className="btn btn-teal" onClick={handleCheck} disabled={isChecking || circuit.gates.length === 0}>
              {isChecking ? 'checking…' : 'check answer'}
            </button>
            {hintsShown < (challenge.hints?.length || 0) && (
              <button className="btn" onClick={() => setHintsShown((n) => n + 1)}>
                {hintsShown === 0 ? 'hint' : 'another hint'}
              </button>
            )}
            {attemptCount > 0 && !solution && !result?.passed && (
              <button className="link-btn" onClick={handleShowSolution}>show a solution</button>
            )}
          </div>
          {checkError && <p className="error-text">{checkError}</p>}

          {hintsShown > 0 && (
            <ol className="hint-list">
              {challenge.hints.slice(0, hintsShown).map((hint) => <li key={hint}>{hint}</li>)}
            </ol>
          )}

          {result && (
            <div className={`practice-result ${result.passed ? 'feedback-pass' : 'feedback-fail'}`}>
              <strong>{result.passed ? 'Verified: correct.' : 'Not yet.'}</strong>
              <ul className="check-list">
                {result.checks.map((c) => (
                  <li key={c.label} className={c.passed ? 'check-pass' : 'check-fail'}>
                    <span aria-hidden>{c.passed ? '✓' : '✗'}</span> {c.label}
                    {c.detail && <span className="check-detail"> {c.detail}</span>}
                  </li>
                ))}
              </ul>
              {result.your_state && (
                <p className="state-readout">Your circuit produces: <code>{result.your_state}</code></p>
              )}
              {result.passed && <p className="result-explanation">{result.explanation}</p>}
              {result.passed && next && (
                <Link className="btn btn-teal" to={`/interview/challenge/${next.id}`}>next: {next.title} →</Link>
              )}
            </div>
          )}

          {solution && (
            <div className="solution-box">
              <p className="panel-label">One solution (others may also be correct)</p>
              <p><code>{solution.gates.map((g) => `${g.name.toUpperCase()}(${g.qubits.join(',')})`).join(' → ')}</code></p>
              <p className="result-explanation">{solution.explanation}</p>
              <button className="link-btn" onClick={() => circuit.setGates(solution.gates.map(({ name, qubits }) => ({ name, qubits })))}>
                load it into the builder
              </button>
            </div>
          )}

          <p className="caveat">Grading is done by exact state or unitary comparison in Qiskit, not by the AI. Qubit 0 is the rightmost digit in states like |01⟩.</p>
        </div>
      </div>
    </Shell>
  )
}

export default PracticeChallenge
