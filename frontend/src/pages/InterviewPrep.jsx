import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import PageHeader from '../PageHeader'
import ConceptQuiz from '../ConceptQuiz'
import { useAuth } from '../AuthContext'
import { apiUrl } from '../api'
import { loadPracticeAttempts, summarizeAttempts } from '../progress'

const DIFFICULTY_BLURBS = {
  'warm-up': 'Single gates and basic identities.',
  core: 'The circuits interviewers expect you to build from memory.',
  challenge: 'Constraints, protocols and optimization.',
}

function InterviewPrep() {
  const { user, accountsEnabled } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()
  const tab = searchParams.get('tab') === 'concepts' ? 'concepts' : 'circuits'

  const [catalog, setCatalog] = useState(null)
  const [attempts, setAttempts] = useState([])
  const [loadError, setLoadError] = useState(null)

  useEffect(() => {
    fetch(apiUrl('/practice/challenges'))
      .then((response) => response.json())
      .then(setCatalog)
      .catch((e) => setLoadError(`Couldn't load challenges: ${e.message}`))
  }, [])

  useEffect(() => {
    loadPracticeAttempts(user).then(setAttempts)
  }, [user])

  const { solved, tried } = summarizeAttempts(attempts)
  const circuitChallenges = catalog?.challenges || []
  const solvedCircuitCount = circuitChallenges.filter((c) => solved.has(c.id)).length

  return (
    <div className="app-shell">
      <PageHeader subtitle="interview prep" />

      <section className="module-intro">
        <h1 className="module-title">Interview Prep</h1>
        <p className="module-lede">
          Build canonical circuits from memory and answer the concept questions interviewers ask.
          Every answer is graded by the same verification engine as Studio, never by the AI.
        </p>
        {!user && accountsEnabled && (
          <p className="module-note">
            Progress is saved in this browser. <Link to="/login">Sign in</Link> to keep it across devices and let the copilot tailor practice to you.
          </p>
        )}
      </section>

      <div className="tab-row" role="tablist">
        <button role="tab" aria-selected={tab === 'circuits'} className={`tab ${tab === 'circuits' ? 'tab-active' : ''}`} onClick={() => setSearchParams({})}>
          Circuit challenges
          {catalog && <span className="tab-count">{solvedCircuitCount}/{circuitChallenges.length}</span>}
        </button>
        <button role="tab" aria-selected={tab === 'concepts'} className={`tab ${tab === 'concepts' ? 'tab-active' : ''}`} onClick={() => setSearchParams({ tab: 'concepts' })}>
          Concept questions
        </button>
      </div>

      {tab === 'concepts' ? (
        <ConceptQuiz attempts={attempts} onAnswered={(attempt) => setAttempts((current) => [attempt, ...current])} />
      ) : loadError ? (
        <p className="error-text">{loadError}</p>
      ) : !catalog ? (
        <p className="empty-state">Loading challenges…</p>
      ) : (
        catalog.difficulties.map((difficulty) => {
          const group = circuitChallenges.filter((c) => c.difficulty === difficulty)
          return (
            <section key={difficulty} className="challenge-group">
              <div className="challenge-group-head">
                <h2>{difficulty}</h2>
                <p>{DIFFICULTY_BLURBS[difficulty]}</p>
              </div>
              <div className="challenge-grid">
                {group.map((challenge) => {
                  const status = solved.has(challenge.id) ? 'solved' : tried.has(challenge.id) ? 'tried' : 'new'
                  return (
                    <Link key={challenge.id} to={`/interview/challenge/${challenge.id}`} className={`challenge-card challenge-${status}`}>
                      <div className="challenge-card-top">
                        <span className="skill-tag">{challenge.skill_label}</span>
                        {status === 'solved' && <span className="status-tag status-solved">✓ solved</span>}
                        {status === 'tried' && <span className="status-tag">in progress</span>}
                      </div>
                      <h3>{challenge.title}</h3>
                      <p>{challenge.prompt}</p>
                    </Link>
                  )
                })}
              </div>
            </section>
          )
        })
      )}
    </div>
  )
}

export default InterviewPrep
