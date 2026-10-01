import { useEffect, useMemo, useState } from 'react'
import { useAuth } from './AuthContext'
import { apiUrl } from './api'
import { recordPracticeAttempt } from './progress'

const ALL_TOPICS = 'All topics'

function ConceptQuiz({ initialTopic, attempts, onAnswered }) {
  const { user } = useAuth()
  const [questions, setQuestions] = useState(null)
  const [loadError, setLoadError] = useState(null)
  const [topic, setTopic] = useState(initialTopic || ALL_TOPICS)
  const [index, setIndex] = useState(0)
  const [choice, setChoice] = useState(null)
  const [result, setResult] = useState(null)
  const [isChecking, setIsChecking] = useState(false)

  useEffect(() => {
    fetch(apiUrl('/interview/questions'))
      .then((response) => response.json())
      .then((data) => setQuestions(data.questions))
      .catch((e) => setLoadError(`Couldn't load questions: ${e.message}`))
  }, [])

  const topics = useMemo(
    () => [ALL_TOPICS, ...new Set((questions || []).map((q) => q.topic))],
    [questions]
  )
  const filtered = (questions || []).filter((q) => topic === ALL_TOPICS || q.topic === topic)

  // Latest result per question, from saved history.
  const lastResult = useMemo(() => {
    const map = new Map()
    for (const attempt of attempts) {
      if (!attempt.challenge_id.startsWith('quiz:')) continue
      const id = attempt.challenge_id.slice(5)
      if (!map.has(id)) map.set(id, attempt.passed)
    }
    return map
  }, [attempts])

  if (loadError) return <p className="error-text">{loadError}</p>
  if (!questions) return <p className="empty-state">Loading questions…</p>

  const question = filtered[Math.min(index, filtered.length - 1)]
  const correctCount = filtered.filter((q) => lastResult.get(q.id) === true).length

  function selectTopic(newTopic) {
    setTopic(newTopic)
    setIndex(0)
    setChoice(null)
    setResult(null)
  }

  function goTo(newIndex) {
    setIndex((newIndex + filtered.length) % filtered.length)
    setChoice(null)
    setResult(null)
  }

  async function submit() {
    if (choice === null) return
    setIsChecking(true)
    try {
      const response = await fetch(apiUrl('/interview/answer'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question_id: question.id, choice }),
      })
      const data = await response.json()
      setResult(data)
      const attempt = {
        challenge_id: `quiz:${question.id}`,
        skill: question.topic,
        difficulty: question.difficulty,
        passed: data.correct,
        gate_count: null,
      }
      await recordPracticeAttempt(user, attempt)
      onAnswered({ ...attempt, created_at: new Date().toISOString() })
    } catch (e) {
      setResult({ error: `Couldn't check your answer: ${e.message}` })
    } finally {
      setIsChecking(false)
    }
  }

  return (
    <div className="quiz">
      <div className="quiz-toolbar">
        <div className="chip-row">
          {topics.map((t) => (
            <button key={t} className={`filter-chip ${t === topic ? 'filter-chip-active' : ''}`} onClick={() => selectTopic(t)}>
              {t}
            </button>
          ))}
        </div>
        <span className="quiz-score">{correctCount}/{filtered.length} answered correctly</span>
      </div>

      <div className="quiz-card">
        <div className="quiz-meta">
          <span className="skill-tag">{question.topic}</span>
          <span className="quiz-position">Question {Math.min(index, filtered.length - 1) + 1} of {filtered.length}</span>
        </div>
        <h2 className="quiz-question">{question.question}</h2>

        <div className="quiz-choices" role="radiogroup">
          {question.choices.map((text, i) => {
            let state = ''
            if (result && !result.error) {
              if (i === result.answer) state = 'choice-correct'
              else if (i === choice) state = 'choice-wrong'
            } else if (i === choice) {
              state = 'choice-selected'
            }
            return (
              <button
                key={i}
                role="radio"
                aria-checked={i === choice}
                className={`quiz-choice ${state}`}
                onClick={() => !result && setChoice(i)}
                disabled={Boolean(result && !result.error)}
              >
                <span className="quiz-letter">{String.fromCharCode(65 + i)}</span>
                {text}
              </button>
            )
          })}
        </div>

        {result?.error && <p className="error-text">{result.error}</p>}

        {result && !result.error && (
          <div className={`quiz-feedback ${result.correct ? 'feedback-pass' : 'feedback-fail'}`}>
            <strong>{result.correct ? 'Correct.' : 'Not quite.'}</strong> {result.explanation}
          </div>
        )}

        <div className="quiz-actions">
          <button className="btn" onClick={() => goTo(index - 1)}>← previous</button>
          {result && !result.error ? (
            <button className="btn btn-teal" onClick={() => goTo(index + 1)}>next question →</button>
          ) : (
            <button className="btn btn-teal" onClick={submit} disabled={choice === null || isChecking}>
              {isChecking ? 'checking…' : 'check answer'}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

export default ConceptQuiz
