import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import PageHeader from '../PageHeader'
import { useCopilotPage } from '../useCopilotPage'
import { useAuth } from '../AuthContext'
import { loadCompletedLessons } from '../progress'
import { TRACKS, ALL_LESSONS } from '../study/lessons'

function Study() {
  const { user, accountsEnabled } = useAuth()
  const [completed, setCompleted] = useState(new Set())
  useCopilotPage({ kind: 'study' })

  useEffect(() => {
    loadCompletedLessons(user).then(setCompleted)
  }, [user])

  const doneCount = ALL_LESSONS.filter((l) => completed.has(l.id)).length
  const nextLesson = ALL_LESSONS.find((l) => !completed.has(l.id))
  const percent = Math.round((doneCount / ALL_LESSONS.length) * 100)

  return (
    <div className="app-shell">
      <PageHeader />

      <section className="module-intro">
        <h1 className="module-title">Study</h1>
        <p className="module-lede">
          Quantum computing from the intuition down to the math and the hardware. Every example circuit is live:
          its output is computed by Qiskit, and you can open it in Studio to experiment.
        </p>
        {!user && accountsEnabled && (
          <p className="module-note">
            Progress is saved in this browser. <Link to="/login">Sign in</Link> to keep it across devices.
          </p>
        )}
      </section>

      <div className="study-progress">
        <div className="study-progress-text">
          <span>{doneCount} of {ALL_LESSONS.length} lessons complete</span>
          {nextLesson && (
            <Link className="btn btn-primary" to={`/study/${nextLesson.id}`}>
              {doneCount === 0 ? 'start' : 'continue'}: {nextLesson.title} →
            </Link>
          )}
        </div>
        <div className="progress-bar" role="progressbar" aria-valuenow={percent} aria-valuemin={0} aria-valuemax={100}>
          <span style={{ width: `${percent}%` }} />
        </div>
      </div>

      <div className="track-list">
        {TRACKS.map((track, trackIndex) => {
          const trackDone = track.lessons.filter((l) => completed.has(l.id)).length
          return (
            <section key={track.id} className="track">
              <div className="track-head">
                <span className="track-number">{String(trackIndex + 1).padStart(2, '0')}</span>
                <div>
                  <h2>{track.title}</h2>
                  <p>{track.blurb}</p>
                </div>
                <span className="track-count">{trackDone}/{track.lessons.length}</span>
              </div>
              <ol className="lesson-list">
                {track.lessons.map((lesson) => (
                  <li key={lesson.id}>
                    <Link to={`/study/${lesson.id}`} className={`lesson-link ${completed.has(lesson.id) ? 'lesson-done' : ''}`}>
                      <span className="lesson-check-mark" aria-hidden>{completed.has(lesson.id) ? '✓' : '○'}</span>
                      <span className="lesson-link-title">{lesson.title}</span>
                      <span className="lesson-minutes">{lesson.minutes} min</span>
                    </Link>
                  </li>
                ))}
              </ol>
            </section>
          )
        })}
      </div>
    </div>
  )
}

export default Study
