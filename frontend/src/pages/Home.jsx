import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import PageHeader from '../PageHeader'
import { useAuth } from '../AuthContext'
import { useCopilotPage } from '../useCopilotPage'
import { loadCompletedLessons, loadPracticeAttempts, loadSavedJobs, summarizeAttempts } from '../progress'
import { ALL_LESSONS } from '../study/lessons'

const CHALLENGE_COUNT = 15

const MODULES = [
  {
    path: '/study',
    title: 'Study',
    description: 'From intuition to the math and the hardware. 17 lessons with live circuits.',
    icon: <path d="M3 5h7a2 2 0 012 2v11a2 2 0 00-2-2H3zM19 5h-7M19 5v11h-7" />,
  },
  {
    path: '/studio',
    title: 'Studio',
    description: 'Build, simplify and verify circuits, with every claim checked by unitary math.',
    icon: <><line x1="2" y1="7" x2="20" y2="7" /><line x1="2" y1="15" x2="20" y2="15" /><rect x="5" y="3" width="6" height="8" rx="1.5" /><line x1="16" y1="7" x2="16" y2="15" /><circle cx="16" cy="15" r="2.5" /></>,
  },
  {
    path: '/interview',
    title: 'Interview Prep',
    description: 'Graded circuit challenges and the concept questions interviewers ask.',
    icon: <><circle cx="11" cy="11" r="9" /><path d="M7 11l3 3 5-6" /></>,
  },
  {
    path: '/jobs',
    title: 'Opportunities',
    description: 'Live quantum roles, saved-job tracking and a prep plan for each one.',
    icon: <><rect x="2" y="6" width="18" height="13" rx="2" /><path d="M8 6V4a1 1 0 011-1h4a1 1 0 011 1v2" /></>,
  },
]

function BlochSphere() {
  return (
    <svg width="88" height="88" viewBox="0 0 92 92" fill="none" aria-hidden="true">
      <circle cx="46" cy="46" r="38" strokeWidth="1.1" style={{ stroke: 'var(--border-strong)' }} />
      <ellipse cx="46" cy="46" rx="38" ry="12" strokeWidth="1.1" style={{ stroke: 'var(--border-strong)' }} />
      <line x1="46" y1="8" x2="46" y2="84" strokeDasharray="2 4" style={{ stroke: 'var(--border-strong)' }} />
      <line x1="46" y1="46" x2="72" y2="22" strokeWidth="2" strokeLinecap="round" style={{ stroke: 'var(--accent)' }} />
      <circle cx="72" cy="22" r="4" style={{ fill: 'var(--accent)' }} />
    </svg>
  )
}

function Home() {
  useCopilotPage({ kind: 'home' })
  const { user, profile } = useAuth()
  const [progress, setProgress] = useState(null)

  useEffect(() => {
    Promise.all([loadCompletedLessons(user), loadPracticeAttempts(user), loadSavedJobs(user)]).then(([lessons, attempts, jobs]) => {
      const circuitAttempts = attempts.filter((a) => !a.challenge_id.startsWith('quiz:'))
      setProgress({ lessons, solved: summarizeAttempts(circuitAttempts).solved, jobs })
    })
  }, [user])

  const nextLesson = progress && ALL_LESSONS.find((l) => !progress.lessons.has(l.id))
  const lessonCount = progress ? ALL_LESSONS.filter((l) => progress.lessons.has(l.id)).length : 0
  const solvedCount = progress ? progress.solved.size : 0
  const interviewing = progress ? progress.jobs.filter((j) => j.status === 'interviewing').length : 0
  const isNew = progress && lessonCount === 0 && solvedCount === 0
  const name = profile?.display_name

  return (
    <div className="app-shell">
      <PageHeader />

      <section className="home-hero">
        <div className="home-hero-copy">
          <p className="eyebrow">{name ? `Welcome back, ${name}` : 'Quantum computing practice'}</p>
          <h1>Practice quantum computing the way you'll be tested.</h1>
          <p className="home-hero-lede">
            Build circuits from memory, get graded by exact math, and walk into interviews knowing your weak spots.
          </p>
          <div className="home-hero-actions">
            {nextLesson ? (
              <Link className="btn btn-primary btn-lg" to={`/study/${nextLesson.id}`}>
                {isNew ? 'Start with lesson 1' : `Continue: ${nextLesson.title}`}
              </Link>
            ) : (
              <Link className="btn btn-primary btn-lg" to="/interview">Practice a challenge</Link>
            )}
            <Link className="btn btn-lg" to="/studio">Open Studio</Link>
          </div>
        </div>

        <aside className="progress-card" aria-label="Your progress">
          <div className="progress-card-head">
            <p className="eyebrow">Your progress</p>
            <BlochSphere />
          </div>
          <div className="progress-row">
            <div className="progress-row-label"><span>Lessons</span><span>{lessonCount} / {ALL_LESSONS.length}</span></div>
            <div className="progress-bar"><span style={{ width: `${(lessonCount / ALL_LESSONS.length) * 100}%` }} /></div>
          </div>
          <div className="progress-row">
            <div className="progress-row-label"><span>Challenges solved</span><span>{solvedCount} / {CHALLENGE_COUNT}</span></div>
            <div className="progress-bar"><span style={{ width: `${(solvedCount / CHALLENGE_COUNT) * 100}%` }} /></div>
          </div>
          <div className="progress-footer">
            <span>Saved jobs</span>
            <span className="mono">{progress ? progress.jobs.length : 0}{interviewing > 0 && ` · ${interviewing} interviewing`}</span>
          </div>
          {!user && <p className="caveat">Saved in this browser. <Link to="/login">Sign in</Link> to keep progress across devices.</p>}
        </aside>
      </section>

      <nav className="module-grid" aria-label="Modules">
        {MODULES.map((mod, i) => (
          <Link to={mod.path} className="module-card" key={mod.path}>
            <span className="module-card-top">
              <span className="module-number">{String(i + 1).padStart(2, '0')}</span>
              <svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{mod.icon}</svg>
            </span>
            <h2>{mod.title}</h2>
            <p>{mod.description}</p>
          </Link>
        ))}
      </nav>

      <footer className="site-footer">
        <span>Every grade is computed by exact unitary comparison. The AI explains; it never decides.</span>
        <span>Qiskit · verified</span>
      </footer>
    </div>
  )
}

export default Home
