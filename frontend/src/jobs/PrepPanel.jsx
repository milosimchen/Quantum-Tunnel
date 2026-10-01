import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../AuthContext'
import { useCopilot } from '../CopilotContext'
import { apiUrl } from '../api'
import { loadCompletedLessons, loadPracticeAttempts, summarizeAttempts } from '../progress'
import { ALL_LESSONS } from '../study/lessons'
import { prepForJob } from './jobPrep'

const LESSONS_BY_ID = Object.fromEntries(ALL_LESSONS.map((l) => [l.id, l]))

function PrepPanel({ job, onClose }) {
  const { user } = useAuth()
  const { openCopilot } = useCopilot()
  const [completedLessons, setCompletedLessons] = useState(new Set())
  const [solved, setSolved] = useState(new Set())
  const [challengeTitles, setChallengeTitles] = useState({})

  useEffect(() => {
    loadCompletedLessons(user).then(setCompletedLessons)
    loadPracticeAttempts(user).then((attempts) => setSolved(summarizeAttempts(attempts).solved))
  }, [user])

  useEffect(() => {
    fetch(apiUrl('/practice/challenges'))
      .then((response) => response.json())
      .then((data) => setChallengeTitles(Object.fromEntries(data.challenges.map((c) => [c.id, c.title]))))
      .catch(() => {})
  }, [])

  useEffect(() => {
    function onKey(event) {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const areas = prepForJob(job).slice(0, 3)

  return (
    <>
      <div className="copilot-overlay" onClick={onClose} />
      <div className="prep-panel" role="dialog" aria-modal="true" aria-labelledby="prep-title">
        <div className="prep-panel-head">
          <div>
            <p className="panel-label">Prep plan</p>
            <h2 id="prep-title">{job.title}</h2>
            <p className="job-company">{job.company}</p>
          </div>
          <button className="copilot-close" onClick={onClose} aria-label="Close prep plan">✕</button>
        </div>

        <button
          className="btn btn-teal"
          onClick={() => { onClose(); openCopilot('jobs', `Write 5 interview questions I'm likely to get for the ${job.title} role at ${job.company}, based on this posting, and tell me which ones to practice first.`) }}
        >
          ask the copilot for likely interview questions
        </button>

        <p className="module-note">
          Matched from the job title and the description snippet Adzuna provides (usually the first few sentences),
          using fixed keyword rules. Read the full posting for anything this misses.
        </p>

        {areas.map((area) => (
          <section key={area.id} className="prep-area">
            <h3>{area.label}</h3>
            {area.evidence.length > 0 ? (
              <p className="prep-evidence">
                Because the posting mentions: {area.evidence.map((k) => <span key={k} className="evidence-chip">{k}</span>)}
              </p>
            ) : (
              <p className="prep-evidence">No specific topics detected, so start with the fundamentals every interview covers.</p>
            )}

            <p className="panel-label">Read</p>
            <ul className="prep-list">
              {area.lessons.map((id) => LESSONS_BY_ID[id] && (
                <li key={id}>
                  <Link to={`/study/${id}`}>{completedLessons.has(id) ? '✓ ' : ''}{LESSONS_BY_ID[id].title}</Link>
                  <span className="lesson-minutes"> {LESSONS_BY_ID[id].minutes} min</span>
                </li>
              ))}
            </ul>

            <p className="panel-label">Build</p>
            <ul className="prep-list">
              {area.challenges.map((id) => (
                <li key={id}>
                  <Link to={`/interview/challenge/${id}`}>{solved.has(id) ? '✓ ' : ''}{challengeTitles[id] || id}</Link>
                </li>
              ))}
            </ul>

            <p className="panel-label">Quiz yourself</p>
            <div className="chip-row">
              {area.quizTopics.map((topic) => (
                <Link key={topic} className="filter-chip" to={`/interview?tab=concepts&topic=${encodeURIComponent(topic)}`}>
                  {topic} questions →
                </Link>
              ))}
            </div>
          </section>
        ))}
      </div>
    </>
  )
}

export default PrepPanel
