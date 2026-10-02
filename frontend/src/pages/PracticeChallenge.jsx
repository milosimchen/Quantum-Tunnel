import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import PageHeader from '../PageHeader'
import { useCopilotPage } from '../useCopilotPage'
import { useCopilot } from '../CopilotContext'
import SparkleIcon from '../SparkleIcon'
import CircuitDiagram from '../CircuitDiagram'
import { useAuth } from '../AuthContext'
import { apiUrl } from '../api'
import { recordPracticeAttempt } from '../progress'
import { usePracticeCircuit } from '../usePracticeCircuit'
import ChipMap from '../ChipMap'
import CodeEditor from '../CodeEditor'
import { gatesToQasm } from '../qasm'
import { COMMON_ANGLES, gateLabel, parseAngle } from '../angles'

const DEFAULT_PALETTE = ['h', 'x', 'y', 'z', 's', 't', 'cx', 'cz']
// Every gate the practice builder can place (hardware challenges list theirs explicitly).
const KNOWN_GATES = new Set([...DEFAULT_PALETTE, 'rz', 'sx', 'swap', 'cp'])

function constraintLines(challenge) {
  const lines = []
  if (challenge.allowed_gates) lines.push(`Gates allowed: ${challenge.allowed_gates.map((g) => g.toUpperCase()).join(', ')}`)
  if (challenge.allowed_qubits) lines.push(`Only touch qubit ${challenge.allowed_qubits.join(', ')}`)
  if (challenge.max_gates) lines.push(`At most ${challenge.max_gates} gates`)
  if (challenge.max_depth) lines.push(`Depth at most ${challenge.max_depth}`)
  if (challenge.max_two_qubit_gates) lines.push(`At most ${challenge.max_two_qubit_gates} two-qubit gates (SWAP counts as 3)`)
  if (challenge.device) lines.push(`Two-qubit gates only between connected qubits on ${challenge.device.name}`)
  if (challenge.qubit_gate_rules) {
    for (const [qubit, names] of Object.entries(challenge.qubit_gate_rules)) {
      lines.push(`Qubit ${qubit} only in ${names.map((g) => g.toUpperCase()).join(', ')} gates`)
    }
  }
  if (challenge.min_fidelity) lines.push(`Fidelity at least ${challenge.min_fidelity} under the chip's noise`)
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

  // "Next" stays within the same track.
  const track = catalog.challenges[index].track
  const next = catalog.challenges.slice(index + 1).find((c) => c.track === track)
  const challenge = catalog.challenges[index]
  const backTo = challenge.track === 'foundations' ? '/interview' : `/interview?tab=${challenge.track}`
  // key resets all state when moving between challenges.
  return challenge.kind === 'numeric'
    ? <NumericWorkspace key={challengeId} challenge={challenge} next={next} backTo={backTo} />
    : <ChallengeWorkspace key={challengeId} challenge={challenge} next={next} backTo={backTo} />
}

function Shell({ children }) {
  return (
    <div className="app-shell">
      <PageHeader />
      {children}
    </div>
  )
}

function ChallengeWorkspace({ challenge, next, backTo }) {
  const { user } = useAuth()
  const [angleText, setAngleText] = useState('pi/2')
  const angle = parseAngle(angleText)
  const circuit = usePracticeCircuit(challenge.num_qubits, angle)
  const [armedGate, setArmedGate] = useState(null)
  const [result, setResult] = useState(null)
  const [isChecking, setIsChecking] = useState(false)
  const [checkError, setCheckError] = useState(null)
  const [hintsShown, setHintsShown] = useState(0)
  const [solution, setSolution] = useState(null)
  const [attemptCount, setAttemptCount] = useState(0)
  const { openCopilot } = useCopilot()

  // Code mode: answer in OpenQASM instead of the visual builder.
  const codeOnly = challenge.answer_mode === 'qasm'
  const [mode, setMode] = useState(codeOnly ? 'code' : 'builder')
  const [code, setCode] = useState(() => challenge.starter || gatesToQasm([], challenge.num_qubits))
  const [parsedGates, setParsedGates] = useState(null)

  // The copilot sees the challenge, the user's gates or code and the grader's last verdict, never the answer key.
  useCopilotPage({
    kind: 'challenge',
    challenge_id: challenge.id,
    gates: mode === 'code' ? parsedGates || [] : circuit.gates,
    qasm: mode === 'code' ? code : undefined,
    last_check: result,
  })

  const palette = (challenge.allowed_gates || DEFAULT_PALETTE).filter((g) => KNOWN_GATES.has(g))
  const usesAngles = palette.includes('rz') || palette.includes('cp')
  const constraints = constraintLines(challenge)

  // Any edit makes the previous verdict stale; never show a result for a circuit that has changed.
  useEffect(() => {
    setResult(null)
  }, [circuit.gates, code, mode])

  function switchMode(next) {
    // Switching to code starts from whatever is in the builder.
    if (next === 'code') setCode(gatesToQasm(circuit.gates, challenge.num_qubits))
    setMode(next)
  }

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
        body: JSON.stringify(mode === 'code' ? { challenge_id: challenge.id, qasm: code } : { challenge_id: challenge.id, gates: circuit.gates }),
      })
      const data = await response.json()
      if (!response.ok) {
        setCheckError(data.detail || 'Check failed.')
        return
      }
      setResult(data)
      if (data.parsed_gates) setParsedGates(data.parsed_gates)
      setAttemptCount((n) => n + 1)
      recordPracticeAttempt(user, {
        challenge_id: challenge.id,
        skill: challenge.skill,
        difficulty: challenge.difficulty,
        passed: data.passed,
        gate_count: data.gate_count,
        gates: mode === 'code' ? data.parsed_gates : circuit.gates,
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
      <Link to={backTo} className="back-link">← all challenges</Link>

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

      {challenge.device && <ChipMap device={challenge.device} />}

      {!codeOnly && (
        <div className="mode-switch" role="tablist" aria-label="Answer with">
          <button role="tab" aria-selected={mode === 'builder'} className={`mode-option ${mode === 'builder' ? 'mode-option-active' : ''}`} onClick={() => switchMode('builder')}>Builder</button>
          <button role="tab" aria-selected={mode === 'code'} className={`mode-option ${mode === 'code' ? 'mode-option-active' : ''}`} onClick={() => switchMode('code')}>Code (OpenQASM)</button>
        </div>
      )}

      <div className="practice-layout">
        <div className="panel">
          {mode === 'code' ? (
            <CodeEditor id="qasm-editor" label={codeOnly ? 'Program' : 'Program (converted from your builder circuit)'} value={code} onChange={setCode} rows={14} />
          ) : (<>
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

          {usesAngles && (
            <div className="angle-picker">
              <label className="field-label" htmlFor="rz-angle">Rotation angle (RZ, CP)</label>
              <div className="chip-row">
                {COMMON_ANGLES.map((a) => (
                  <button key={a.label} type="button" className={`filter-chip ${angle !== null && Math.abs(angle - a.value) < 1e-9 ? 'filter-chip-active' : ''}`} onClick={() => setAngleText(a.label)}>
                    {a.label}
                  </button>
                ))}
              </div>
              <input id="rz-angle" type="text" value={angleText} onChange={(e) => setAngleText(e.target.value)} aria-describedby="rz-angle-help" />
              <span id="rz-angle-help" className={angle === null ? 'error-text' : 'caveat'}>
                {angle === null ? 'Not an angle. Try pi/2, -pi/4 or 3pi/4.' : 'Used for the next RZ or CP you place. Accepts pi/2, π/4, 1.57…'}
              </span>
            </div>
          )}

          {circuit.pendingTwoQubitGate && (
            <div className="pending-gate-banner">
              Placing {gateLabel(circuit.pendingTwoQubitGate)}: control on q{circuit.pendingTwoQubitGate.controlQubit}. Click another wire for the target.
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
                  <span>{i + 1}. {gateLabel(gate)} on q{gate.qubits.join(', q')}</span>
                  <button className="remove-btn" onClick={() => circuit.removeGate(i)} aria-label={`Remove gate ${i + 1}`}>remove</button>
                </div>
              ))}
            </div>
          )}
          {circuit.gates.length > 0 && (
            <button className="link-btn" style={{ marginTop: 8 }} onClick={circuit.clear}>clear circuit</button>
          )}
          </>)}
        </div>

        <div className="panel practice-diagram-panel">
          <p className="panel-label">
            Diagram · {challenge.num_qubits} qubit{challenge.num_qubits > 1 ? 's' : ''}
            {mode === 'code' && ' · drawn from your program after each check'}
          </p>
          <div className="diagram-scroll">
            {mode === 'code' ? (
              <CircuitDiagram gates={parsedGates || []} numQubits={challenge.num_qubits} />
            ) : (
              <CircuitDiagram
                gates={circuit.gates}
                numQubits={challenge.num_qubits}
                interactive
                onGateDrop={circuit.handleGateDrop}
                onWireClick={handleWireClick}
                pendingControlQubit={circuit.pendingTwoQubitGate?.controlQubit}
              />
            )}
          </div>

          <div className="practice-actions">
            <button className="btn btn-primary" onClick={handleCheck} disabled={isChecking || (mode === 'code' ? !code.trim() : circuit.gates.length === 0)}>
              {isChecking ? 'Checking…' : 'Check answer'}
            </button>
            {hintsShown < (challenge.hints?.length || 0) && (
              <button className="btn" onClick={() => setHintsShown((n) => n + 1)}>
                {hintsShown === 0 ? 'Hint' : 'Another hint'}
              </button>
            )}
            <button className="btn btn-ai" onClick={() => openCopilot('interview', 'Give me a hint for this challenge without giving away the answer.')}>
              <SparkleIcon /> Ask the copilot
            </button>
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
              {typeof result.fidelity === 'number' && (
                <p className="state-readout">Simulated fidelity on {challenge.device?.name}: <code>{result.fidelity.toFixed(3)}</code></p>
              )}
              {result.your_state && (
                <p className="state-readout">Your circuit produces: <code>{result.your_state}</code></p>
              )}
              {result.passed && <p className="result-explanation">{result.explanation}</p>}
              {result.passed && next && (
                <Link className="btn btn-primary" to={`/interview/challenge/${next.id}`}>Next: {next.title} →</Link>
              )}
            </div>
          )}

          {solution && (
            <div className="solution-box">
              <p className="panel-label">One solution (others may also be correct)</p>
              <p><code>{solution.gates.map((g) => `${gateLabel(g)} q${g.qubits.join(',')}`).join(' → ')}</code></p>
              <p className="result-explanation">{solution.explanation}</p>
              <button
                className="link-btn"
                onClick={() => {
                  const gates = solution.gates.map(({ name, qubits, params }) => (params?.length ? { name, qubits, params } : { name, qubits }))
                  if (mode === 'code') setCode(gatesToQasm(gates, challenge.num_qubits))
                  else circuit.setGates(gates)
                }}
              >
                {mode === 'code' ? 'load it into the editor' : 'load it into the builder'}
              </button>
            </div>
          )}

          <p className="caveat">Grading is done by exact state or unitary comparison in Qiskit, not by the AI. Qubit 0 is the rightmost digit in states like |01⟩.</p>
        </div>
      </div>
    </Shell>
  )
}

// Calculation tasks (T1 decay, readout mitigation, ZNE...): a number in, graded
// on the server against an answer computed from the same parameters.
function NumericWorkspace({ challenge, next, backTo }) {
  const { user } = useAuth()
  const { openCopilot } = useCopilot()
  const [valueText, setValueText] = useState('')
  const [result, setResult] = useState(null)
  const [isChecking, setIsChecking] = useState(false)
  const [checkError, setCheckError] = useState(null)
  const [hintsShown, setHintsShown] = useState(0)
  const [solution, setSolution] = useState(null)
  const [attemptCount, setAttemptCount] = useState(0)

  useCopilotPage({ kind: 'challenge', challenge_id: challenge.id, gates: [], last_check: result })

  const value = valueText.trim() === '' ? null : Number(valueText.replace(',', '.'))
  const isValid = value !== null && Number.isFinite(value)

  async function handleCheck(event) {
    event.preventDefault()
    if (!isValid) return
    setIsChecking(true)
    setCheckError(null)
    try {
      const response = await fetch(apiUrl('/practice/check'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ challenge_id: challenge.id, value }),
      })
      const data = await response.json()
      if (!response.ok) {
        setCheckError(data.detail || 'Check failed.')
        return
      }
      setResult(data)
      setAttemptCount((n) => n + 1)
      recordPracticeAttempt(user, { challenge_id: challenge.id, skill: challenge.skill, difficulty: challenge.difficulty, passed: data.passed, gate_count: null })
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
      <section className="challenge-header">
        <Link to={backTo} className="back-link">← all challenges</Link>
        <div className="challenge-card-top">
          <span className="skill-tag">{challenge.skill_label}</span>
          <span className="status-tag">{challenge.difficulty}</span>
          <span className="status-tag">calculation</span>
        </div>
        <h1 className="module-title">{challenge.title}</h1>
        <p className="challenge-prompt">{challenge.prompt}</p>
      </section>

      <div className="panel numeric-panel">
        <form className="numeric-form" onSubmit={handleCheck}>
          <label className="field-label" htmlFor="numeric-answer">Your answer</label>
          <div className="numeric-row">
            <input id="numeric-answer" type="text" inputMode="decimal" value={valueText} onChange={(e) => { setValueText(e.target.value); setResult(null) }} placeholder="e.g. 0.42" />
            <button className="btn btn-primary" type="submit" disabled={!isValid || isChecking}>{isChecking ? 'Checking…' : 'Check answer'}</button>
          </div>
          {valueText && !isValid && <span className="error-text">Enter a number, like 0.42.</span>}
        </form>

        <div className="practice-actions">
          {hintsShown < (challenge.hints?.length || 0) && (
            <button className="btn" onClick={() => setHintsShown((n) => n + 1)}>{hintsShown === 0 ? 'Hint' : 'Another hint'}</button>
          )}
          <button className="btn btn-ai" onClick={() => openCopilot('interview', 'Give me a hint for this calculation without giving away the answer.')}>
            <SparkleIcon /> Ask the copilot
          </button>
          {attemptCount > 0 && !solution && !result?.passed && (
            <button className="link-btn" onClick={handleShowSolution}>show the answer</button>
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
            <strong>{result.passed ? 'Correct.' : 'Not yet.'}</strong>
            <ul className="check-list">
              {result.checks.map((c) => (
                <li key={c.label} className={c.passed ? 'check-pass' : 'check-fail'}>
                  <span aria-hidden>{c.passed ? '✓' : '✗'}</span> {c.label}
                  {c.detail && <span className="check-detail"> {c.detail}</span>}
                </li>
              ))}
            </ul>
            {result.passed && <p className="result-explanation">Computed answer: <code>{result.answer}</code>. {result.explanation}</p>}
            {result.passed && next && <Link className="btn btn-primary" to={`/interview/challenge/${next.id}`}>Next: {next.title} →</Link>}
          </div>
        )}

        {solution && (
          <div className="solution-box">
            <p className="panel-label">Answer</p>
            <p><code>{solution.answer}</code></p>
            <p className="result-explanation">{solution.explanation}</p>
          </div>
        )}

        <p className="caveat">The answer is computed in code from the numbers in the question, not by the AI.</p>
      </div>
    </Shell>
  )
}

export default PracticeChallenge
