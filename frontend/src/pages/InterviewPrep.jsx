import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import PageHeader from '../PageHeader'
import { useCopilotPage } from '../useCopilotPage'
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
  const requestedTab = searchParams.get('tab')
  const tab = ['concepts', 'hardware', 'advanced', 'code'].includes(requestedTab) ? requestedTab : 'circuits'
  useCopilotPage({ kind: 'interview' })

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
  const allChallenges = catalog?.challenges || []
  const trackFor = { circuits: 'foundations', hardware: 'hardware', advanced: 'advanced', code: 'code' }
  const inTrack = (t) => allChallenges.filter((c) => c.track === t)
  const solvedIn = (t) => inTrack(t).filter((c) => solved.has(c.id)).length
  const circuitChallenges = tab === 'concepts' ? [] : inTrack(trackFor[tab])

  return (
    <div className="app-shell">
      <PageHeader />

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
          Circuit fundamentals
          {catalog && <span className="tab-count">{solvedIn('foundations')}/{inTrack('foundations').length}</span>}
        </button>
        <button role="tab" aria-selected={tab === 'hardware'} className={`tab ${tab === 'hardware' ? 'tab-active' : ''}`} onClick={() => setSearchParams({ tab: 'hardware' })}>
          Real hardware
          {catalog && <span className="tab-count">{solvedIn('hardware')}/{inTrack('hardware').length}</span>}
        </button>
        <button role="tab" aria-selected={tab === 'advanced'} className={`tab ${tab === 'advanced' ? 'tab-active' : ''}`} onClick={() => setSearchParams({ tab: 'advanced' })}>
          Advanced
          {catalog && <span className="tab-count">{solvedIn('advanced')}/{inTrack('advanced').length}</span>}
        </button>
        <button role="tab" aria-selected={tab === 'code'} className={`tab ${tab === 'code' ? 'tab-active' : ''}`} onClick={() => setSearchParams({ tab: 'code' })}>
          Code
          {catalog && <span className="tab-count">{solvedIn('code')}/{inTrack('code').length}</span>}
        </button>
        <button role="tab" aria-selected={tab === 'concepts'} className={`tab ${tab === 'concepts' ? 'tab-active' : ''}`} onClick={() => setSearchParams({ tab: 'concepts' })}>
          Concept questions
        </button>
      </div>

      {tab === 'hardware' && (
        <p className="track-intro">
          Simulated chips with limited wiring, native gate sets and realistic noise, including errors while qubits sit idle.
          Fidelity is computed by noisy simulation, so depth and two-qubit gate count really cost you, just as on real hardware.
        </p>
      )}

      {tab === 'advanced' && (
        <p className="track-intro">
          The circuits behind real algorithms and error correction: Grover, the QFT, phase estimation, Hamiltonian simulation and
          syndrome extraction. Each one has a matching lesson in Study's Advanced section.
        </p>
      )}

      {tab === 'code' && (
        <p className="track-intro">
          Write and debug OpenQASM, the format circuits are exchanged in (and part of IBM's Qiskit developer exam). Every other
          circuit challenge can be answered in code too: switch any challenge to Code. For code reading, see the "Code reading" topic in Concept questions.
        </p>
      )}

      {tab === 'concepts' ? (
        <ConceptQuiz initialTopic={searchParams.get('topic')} attempts={attempts} onAnswered={(attempt) => setAttempts((current) => [attempt, ...current])} />
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
                      {(challenge.device || challenge.kind === 'numeric') && (
                        <span className="challenge-card-meta">{challenge.kind === 'numeric' ? 'Calculation' : `Chip: ${challenge.device.name}`}</span>
                      )}
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
