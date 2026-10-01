import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import CircuitDiagram from '../CircuitDiagram'
import { useCircuit } from '../CircuitContext'
import { apiUrl } from '../api'
import { RichText, Tex } from './RichText'

function toGateObjects(gates) {
  return gates.map(([name, qubits, params]) => ({ name, qubits, ...(params ? { params } : {}) }))
}

function CircuitBlock({ block }) {
  const { loadCircuit } = useCircuit()
  const navigate = useNavigate()
  const gates = toGateObjects(block.gates)
  const [state, setState] = useState(null)
  const [error, setError] = useState(null)

  // The output state is always computed by Qiskit, so lesson text can never drift from the truth.
  useEffect(() => {
    let cancelled = false
    fetch(apiUrl('/state'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ num_qubits: block.numQubits, gates: gates.map((g) => ({ params: [], ...g })) }),
    })
      .then((response) => (response.ok ? response.json() : Promise.reject(new Error(`status ${response.status}`))))
      .then((data) => !cancelled && setState(data))
      .catch((e) => !cancelled && setError(e.message))
    return () => { cancelled = true }
    // block is static lesson content, so it never changes for a mounted block.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function openInStudio() {
    loadCircuit(gates, block.numQubits)
    navigate('/studio')
  }

  return (
    <figure className="lesson-circuit">
      <div className="diagram-scroll">
        <CircuitDiagram gates={gates} numQubits={block.numQubits} />
      </div>
      <figcaption>
        <p className="lesson-circuit-caption">{block.caption}</p>
        <p className="lesson-circuit-state">
          Output state (computed by Qiskit):{' '}
          {state ? <code>{state.dirac}</code> : error ? <span className="error-text">unavailable ({error})</span> : <span className="empty-state">computing…</span>}
        </p>
        <button className="btn" onClick={openInStudio}>open in Studio →</button>
      </figcaption>
    </figure>
  )
}

function CheckBlock({ block }) {
  const [choice, setChoice] = useState(null)
  const answered = choice !== null
  return (
    <div className="lesson-check">
      <p className="panel-label">Quick check</p>
      <p className="lesson-check-question"><RichText text={block.question} /></p>
      <div className="quiz-choices">
        {block.choices.map((text, i) => {
          let state = ''
          if (answered && i === block.answer) state = 'choice-correct'
          else if (answered && i === choice) state = 'choice-wrong'
          return (
            <button key={i} className={`quiz-choice ${state}`} disabled={answered} onClick={() => setChoice(i)}>
              <span className="quiz-letter">{String.fromCharCode(65 + i)}</span>
              {text}
            </button>
          )
        })}
      </div>
      {answered && (
        <div className={`quiz-feedback ${choice === block.answer ? 'feedback-pass' : 'feedback-fail'}`}>
          <strong>{choice === block.answer ? 'Correct.' : 'Not quite.'}</strong> {block.explanation}
          <button className="link-btn" style={{ marginLeft: 8 }} onClick={() => setChoice(null)}>try again</button>
        </div>
      )}
    </div>
  )
}

function PracticeBlock({ block, challengeTitles }) {
  return (
    <div className="lesson-practice">
      <p className="panel-label">Practice this in Interview Prep</p>
      <div className="chip-row">
        {block.challenges.map((id) => (
          <Link key={id} className="filter-chip" to={`/interview/challenge/${id}`}>
            {challengeTitles[id] || id} →
          </Link>
        ))}
      </div>
    </div>
  )
}

function LessonBlocks({ blocks, challengeTitles = {} }) {
  return blocks.map((block, i) => {
    switch (block.type) {
      case 'p':
        return <p key={i} className="lesson-p"><RichText text={block.text} /></p>
      case 'math':
        return <div key={i} className="lesson-math"><Tex tex={block.tex} display /></div>
      case 'note':
        return <aside key={i} className="lesson-note"><RichText text={block.text} /></aside>
      case 'circuit':
        return <CircuitBlock key={i} block={block} />
      case 'check':
        return <CheckBlock key={i} block={block} />
      case 'practice':
        return <PracticeBlock key={i} block={block} challengeTitles={challengeTitles} />
      default:
        return null
    }
  })
}

export default LessonBlocks
