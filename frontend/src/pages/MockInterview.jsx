import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import PageHeader from '../PageHeader'
import CircuitDiagram from '../CircuitDiagram'
import CodeEditor from '../CodeEditor'
import SparkleIcon from '../SparkleIcon'
import { useAuth } from '../AuthContext'
import { useCopilotPage } from '../useCopilotPage'
import { apiUrl } from '../api'
import { recordPracticeAttempt } from '../progress'
import { getCareerPath } from '../careerPath'
import { PATHS_BY_ID } from '../paths'

const ROUNDS = [
  { key: 'concepts', title: 'Concept questions', graded: 'Graded exactly' },
  { key: 'code', title: 'Write the circuit', graded: 'Verified by the grader' },
  { key: 'explain', title: 'Explain your thinking', graded: 'AI feedback on a fixed rubric' },
  { key: 'design', title: 'System design', graded: 'AI feedback on a fixed rubric' },
]

function formatClock(seconds) {
  const sign = seconds < 0 ? '+' : ''
  const s = Math.abs(seconds)
  return `${sign}${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`
}

// Counts down for the current round; goes into overtime rather than cutting you off.
function RoundTimer({ minutes, startedAt }) {
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(id)
  }, [])
  const remaining = minutes * 60 - Math.floor((now - startedAt) / 1000)
  return (
    <span className={`round-timer ${remaining < 0 ? 'round-timer-over' : ''}`} aria-label={remaining < 0 ? 'Over time' : 'Time left'}>
      {remaining < 0 ? 'Over time ' : ''}{formatClock(remaining)}
    </span>
  )
}

function MockInterview() {
  const { user, profile } = useAuth()
  const pathId = getCareerPath(profile)
  const [session, setSession] = useState(null)
  const [loadError, setLoadError] = useState(null)
  const [roundIndex, setRoundIndex] = useState(-1) // -1 = intro, 4 = scorecard
  const [roundStartedAt, setRoundStartedAt] = useState(null)
  const [results, setResults] = useState({})
  const durations = useRef({})

  useCopilotPage({ kind: 'interview' })

  async function start() {
    setLoadError(null)
    try {
      const response = await fetch(apiUrl(`/interview/mock${pathId ? `?path=${pathId}` : ''}`))
      setSession(await response.json())
      setResults({})
      durations.current = {}
      setRoundIndex(0)
      setRoundStartedAt(Date.now())
    } catch (e) {
      setLoadError(`Couldn't start the interview: ${e.message}`)
    }
  }

  function finishRound(key, result) {
    durations.current[key] = Math.round((Date.now() - roundStartedAt) / 1000)
    setResults((current) => ({ ...current, [key]: result }))
    setRoundIndex((i) => i + 1)
    setRoundStartedAt(Date.now())
    window.scrollTo(0, 0)
  }

  if (roundIndex === -1 || !session) {
    return (
      <div className="app-shell">
        <PageHeader />
        <Link to="/interview" className="back-link">← Interview Prep</Link>
        <section className="module-intro">
          <p className="eyebrow">Mock interview</p>
          <h1 className="module-title">A 25-minute practice interview</h1>
          <p className="module-lede">
            Four rounds, like a real technical screen: concept questions, writing a circuit in code, explaining your reasoning, and a short
            system-design question. Each round has a suggested time; you can run over, and the scorecard will show it.
          </p>
          {pathId && <p className="module-note">Tailored to your path: {PATHS_BY_ID[pathId].title}. <Link to="/path">Change</Link></p>}
        </section>
        <ol className="mock-rounds-preview">
          {ROUNDS.map((round, i) => (
            <li key={round.key}>
              <span className="track-number">{String(i + 1).padStart(2, '0')}</span>
              <span className="mock-round-title">{round.title}</span>
              <span className={`mock-graded ${round.graded.startsWith('AI') ? 'mock-graded-ai' : ''}`}>{round.graded}</span>
            </li>
          ))}
        </ol>
        {loadError && <p className="error-text">{loadError}</p>}
        <button className="btn btn-primary btn-lg" onClick={start}>Start the interview</button>
        <p className="caveat mock-caveat">Rounds 3 and 4 send your written answers to an AI model for feedback. Nothing else leaves the site.</p>
      </div>
    )
  }

  if (roundIndex >= ROUNDS.length) {
    return <Scorecard session={session} results={results} durations={durations.current} onRestart={start} />
  }

  const round = ROUNDS[roundIndex]
  return (
    <div className="app-shell">
      <PageHeader />
      <div className="mock-progress">
        <ol className="mock-steps" aria-label="Interview rounds">
          {ROUNDS.map((r, i) => (
            <li key={r.key} className={i === roundIndex ? 'mock-step-current' : i < roundIndex ? 'mock-step-done' : ''} aria-current={i === roundIndex ? 'step' : undefined}>
              {i + 1}. {r.title}
            </li>
          ))}
        </ol>
        <RoundTimer key={round.key} minutes={session.time_minutes[round.key]} startedAt={roundStartedAt} />
      </div>

      {round.key === 'concepts' && <ConceptsRound questions={session.questions} user={user} onDone={(r) => finishRound('concepts', r)} />}
      {round.key === 'code' && <CodeRound challenge={session.code_challenge} user={user} onDone={(r) => finishRound('code', r)} />}
      {round.key === 'explain' && <WrittenRound prompt={session.explain} label="Explain your thinking" onDone={(r) => finishRound('explain', r)} />}
      {round.key === 'design' && <WrittenRound prompt={session.design} label="System design" onDone={(r) => finishRound('design', r)} />}
    </div>
  )
}

function ConceptsRound({ questions, user, onDone }) {
  const [index, setIndex] = useState(0)
  const [choice, setChoice] = useState(null)
  const [feedback, setFeedback] = useState(null)
  const [answers, setAnswers] = useState([])
  const question = questions[index]

  async function submit() {
    const response = await fetch(apiUrl('/interview/answer'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question_id: question.id, choice }),
    })
    const data = await response.json()
    setFeedback(data)
    setAnswers((current) => [...current, { id: question.id, topic: question.topic, correct: data.correct }])
    recordPracticeAttempt(user, { challenge_id: `quiz:${question.id}`, skill: question.topic, difficulty: question.difficulty, passed: data.correct, gate_count: null })
  }

  function next() {
    if (index + 1 >= questions.length) {
      onDone({ answers })
      return
    }
    setIndex(index + 1)
    setChoice(null)
    setFeedback(null)
  }

  return (
    <div className="quiz-card mock-card">
      <div className="quiz-meta">
        <span className="skill-tag">{question.topic}</span>
        <span className="quiz-position">Question {index + 1} of {questions.length}</span>
      </div>
      <h2 className="quiz-question">{question.question}</h2>
      {question.code && <pre className="lesson-code quiz-code"><code>{question.code}</code></pre>}
      <div className="quiz-choices">
        {question.choices.map((text, i) => {
          let state = i === choice ? 'choice-selected' : ''
          if (feedback) state = i === feedback.answer ? 'choice-correct' : i === choice ? 'choice-wrong' : ''
          return (
            <button key={i} className={`quiz-choice ${state}`} disabled={Boolean(feedback)} onClick={() => setChoice(i)}>
              <span className="quiz-letter">{String.fromCharCode(65 + i)}</span>
              {text}
            </button>
          )
        })}
      </div>
      {feedback && (
        <div className={`quiz-feedback ${feedback.correct ? 'feedback-pass' : 'feedback-fail'}`}>
          <strong>{feedback.correct ? 'Correct.' : 'Not quite.'}</strong> {feedback.explanation}
        </div>
      )}
      <div className="quiz-actions">
        <span />
        {feedback ? (
          <button className="btn btn-primary" onClick={next}>{index + 1 >= questions.length ? 'Next round →' : 'Next question →'}</button>
        ) : (
          <button className="btn btn-primary" onClick={submit} disabled={choice === null}>Lock in answer</button>
        )}
      </div>
    </div>
  )
}

const MAX_CODE_CHECKS = 3

function CodeRound({ challenge, user, onDone }) {
  const [code, setCode] = useState(challenge.starter)
  const [result, setResult] = useState(null)
  const [checks, setChecks] = useState(0)
  const [error, setError] = useState(null)
  const [isChecking, setIsChecking] = useState(false)

  async function check() {
    setIsChecking(true)
    setError(null)
    try {
      const response = await fetch(apiUrl('/practice/check'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ challenge_id: challenge.id, qasm: code }),
      })
      const data = await response.json()
      if (!response.ok) {
        // A parse error doesn't use up one of the checks.
        setError(data.detail || 'Check failed.')
        return
      }
      setResult(data)
      setChecks((n) => n + 1)
      recordPracticeAttempt(user, { challenge_id: challenge.id, skill: challenge.skill, difficulty: challenge.difficulty, passed: data.passed, gate_count: data.gate_count })
    } catch (e) {
      setError(`Couldn't reach the server: ${e.message}`)
    } finally {
      setIsChecking(false)
    }
  }

  const finished = result?.passed || checks >= MAX_CODE_CHECKS

  return (
    <div className="mock-card">
      <section className="challenge-header">
        <h1 className="module-title">{challenge.title}</h1>
        <p className="challenge-prompt">{challenge.prompt}</p>
        <p className="module-note">Write your answer in OpenQASM. You get {MAX_CODE_CHECKS} checks, like asking an interviewer to run your code; syntax errors don't count.</p>
      </section>
      <div className="practice-layout">
        <div className="panel">
          <CodeEditor id="mock-code" label="Program" value={code} onChange={(v) => { setCode(v); setResult(null) }} rows={14} />
        </div>
        <div className="panel practice-diagram-panel">
          <p className="panel-label">Your circuit, as parsed</p>
          <div className="diagram-scroll">
            <CircuitDiagram gates={result?.parsed_gates || []} numQubits={challenge.num_qubits} />
          </div>
          <div className="practice-actions">
            {!finished && (
              <button className="btn btn-primary" onClick={check} disabled={isChecking || !code.trim()}>
                {isChecking ? 'Checking…' : `Check (${MAX_CODE_CHECKS - checks} left)`}
              </button>
            )}
            <button className={`btn ${finished ? 'btn-primary' : ''}`} onClick={() => onDone({ passed: Boolean(result?.passed), checks, challenge })}>
              {finished ? 'Next round →' : 'Skip to next round'}
            </button>
          </div>
          {error && <p className="error-text">{error}</p>}
          {result && (
            <div className={`practice-result ${result.passed ? 'feedback-pass' : 'feedback-fail'}`}>
              <strong>{result.passed ? 'Verified: correct.' : 'Not yet.'}</strong>
              <ul className="check-list">
                {result.checks.map((c) => (
                  <li key={c.label} className={c.passed ? 'check-pass' : 'check-fail'}>
                    <span aria-hidden>{c.passed ? '✓' : '✗'}</span> {c.label}{c.detail && <span className="check-detail"> {c.detail}</span>}
                  </li>
                ))}
              </ul>
              {result.your_state && <p className="state-readout">Your program produces: <code>{result.your_state}</code></p>}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function WrittenRound({ prompt, label, onDone }) {
  const [answer, setAnswer] = useState('')
  const [feedback, setFeedback] = useState(null)
  const [error, setError] = useState(null)
  const [isSending, setIsSending] = useState(false)
  const words = answer.trim() ? answer.trim().split(/\s+/).length : 0

  async function submit() {
    setIsSending(true)
    setError(null)
    try {
      const response = await fetch(apiUrl('/interview/rubric_feedback'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt_id: prompt.id, answer }),
      })
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || `status ${response.status}`)
      setFeedback(data)
    } catch (e) {
      setError(`Couldn't get feedback: ${e.message}`)
    } finally {
      setIsSending(false)
    }
  }

  return (
    <div className="mock-card">
      <section className="challenge-header">
        <p className="eyebrow">{label}</p>
        <h1 className="mock-prompt">{prompt.prompt}</h1>
      </section>
      <div className="panel mock-written">
        <label className="field-label" htmlFor="mock-answer">Your answer</label>
        <textarea id="mock-answer" rows={9} value={answer} onChange={(e) => setAnswer(e.target.value)} disabled={Boolean(feedback?.assessed)} placeholder="Answer as you would out loud: a few clear sentences." />
        <span className="caveat">{words} words</span>
        {error && <p className="error-text">{error}</p>}

        {feedback && !feedback.assessed && <p className="warning-text">{feedback.message}</p>}

        {feedback?.assessed && (
          <div className="ai-feedback">
            <p className="ai-feedback-head"><SparkleIcon size={14} /> AI feedback · {feedback.score}/{feedback.out_of} rubric points</p>
            <ul className="check-list">
              {feedback.criteria.map((c) => (
                <li key={c.id} className={c.met ? 'check-pass' : 'check-fail'}>
                  <span aria-hidden>{c.met ? '✓' : c.met === false ? '✗' : '–'}</span> {c.text}
                  <span className="check-detail"> {c.reason}</span>
                </li>
              ))}
            </ul>
            <p>{feedback.overall_feedback}</p>
            <p><strong>Try next time:</strong> {feedback.suggestion}</p>
            <p className="caveat">The rubric is fixed and written in advance; an AI model judged each point, and the score is counted from those judgments. AI judgments can be wrong.</p>
          </div>
        )}

        <div className="practice-actions">
          {!feedback?.assessed && (
            <button className="btn btn-ai" onClick={submit} disabled={isSending || words === 0}>
              <SparkleIcon /> {isSending ? 'Getting feedback…' : 'Submit for feedback'}
            </button>
          )}
          <button className={`btn ${feedback?.assessed ? 'btn-primary' : ''}`} onClick={() => onDone({ prompt, feedback: feedback?.assessed ? feedback : null })}>
            {feedback?.assessed ? 'Next →' : 'Skip'}
          </button>
        </div>
      </div>
    </div>
  )
}

function Scorecard({ session, results, durations, onRestart }) {
  const concepts = results.concepts?.answers || []
  const correct = concepts.filter((a) => a.correct).length
  const missedTopics = [...new Set(concepts.filter((a) => !a.correct).map((a) => a.topic))]
  const code = results.code
  const written = [results.explain, results.design]
  const missedCriteria = written.flatMap((r) => (r?.feedback?.criteria || []).filter((c) => c.met === false).map((c) => c.text))
  const overtime = ROUNDS.filter((r) => durations[r.key] > session.time_minutes[r.key] * 60)

  return (
    <div className="app-shell">
      <PageHeader />
      <section className="module-intro">
        <p className="eyebrow">Mock interview</p>
        <h1 className="module-title">Scorecard</h1>
      </section>

      <div className="scorecard">
        <div className="score-row">
          <span className="score-round">Concept questions</span>
          <span className="score-value">{correct}/{concepts.length}</span>
          <span className="score-kind">Graded exactly</span>
        </div>
        <div className="score-row">
          <span className="score-round">Write the circuit: {code?.challenge?.title}</span>
          <span className={`score-value ${code?.passed ? 'score-pass' : 'score-fail'}`}>{code?.passed ? 'Passed' : 'Not passed'}</span>
          <span className="score-kind">Verified{code?.checks ? ` · ${code.checks} check${code.checks > 1 ? 's' : ''}` : ''}</span>
        </div>
        {[['Explain your thinking', results.explain], ['System design', results.design]].map(([title, r]) => (
          <div className="score-row" key={title}>
            <span className="score-round">{title}</span>
            <span className="score-value">{r?.feedback ? `${r.feedback.score}/${r.feedback.out_of}` : 'Skipped'}</span>
            <span className="score-kind score-kind-ai"><SparkleIcon size={12} /> AI rubric feedback</span>
          </div>
        ))}
      </div>

      <section className="panel scorecard-advice">
        <h2>What to work on</h2>
        <ul>
          {missedTopics.map((t) => (
            <li key={t}>Concepts: <Link to={`/interview?tab=concepts&topic=${encodeURIComponent(t)}`}>practise {t} questions</Link></li>
          ))}
          {code && !code.passed && (
            <li>Circuits: <Link to={`/interview/challenge/${code.challenge.id}`}>retry "{code.challenge.title}"</Link> with hints and the builder</li>
          )}
          {missedCriteria.map((text) => <li key={text}>Explaining: {text}</li>)}
          {overtime.length > 0 && <li>Timing: you ran over in {overtime.map((r) => r.title.toLowerCase()).join(', ')}. In a real interview, say your plan out loud early.</li>}
          {!missedTopics.length && code?.passed && !missedCriteria.length && !overtime.length && <li>A clean run. Try another session; questions and prompts vary each time.</li>}
        </ul>
      </section>

      <div className="practice-actions">
        <button className="btn btn-primary" onClick={onRestart}>Start another interview</button>
        <Link className="btn" to="/path">Back to your path</Link>
      </div>
    </div>
  )
}

export default MockInterview
