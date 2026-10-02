import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import PageHeader from '../PageHeader'
import { useAuth } from '../AuthContext'
import { useCopilotPage } from '../useCopilotPage'
import { apiUrl } from '../api'
import { PATHS, PATHS_BY_ID, isStepDone, pathProgress } from '../paths'
import { getCareerPath, saveCareerPath } from '../careerPath'
import { usePathProgress } from '../usePathProgress'
import { describeStep } from '../pathSteps'

function PathPage() {
  const { user, profile, updateProfile } = useAuth()
  const [pathId, setPathId] = useState(() => getCareerPath(profile))
  const [isChoosing, setIsChoosing] = useState(false)
  const [notice, setNotice] = useState(null)
  const [challengeTitles, setChallengeTitles] = useState({})
  const progress = usePathProgress(user)

  // The profile may arrive after first render.
  useEffect(() => {
    const saved = getCareerPath(profile)
    if (saved) setPathId(saved)
  }, [profile])

  useEffect(() => {
    fetch(apiUrl('/practice/challenges'))
      .then((response) => response.json())
      .then((data) => setChallengeTitles(Object.fromEntries(data.challenges.map((c) => [c.id, c.title]))))
      .catch(() => {})
  }, [])

  const path = pathId ? PATHS_BY_ID[pathId] : null
  const summary = path && progress ? pathProgress(path, progress) : null
  useCopilotPage({ kind: 'home', path: pathId })

  async function choose(id) {
    setPathId(id)
    setIsChoosing(false)
    setNotice(await saveCareerPath(user, id, updateProfile))
  }

  if (!path || isChoosing) {
    return (
      <div className="app-shell">
        <PageHeader />
        <section className="module-intro">
          <p className="eyebrow">Your path</p>
          <h1 className="module-title">Which kind of quantum role are you aiming for?</h1>
          <p className="module-lede">
            A survey of 57 quantum companies found the skills they hire for fall into separate software, hardware and business
            clusters, plus quantum-specific research roles. Pick one and you'll get a staged plan through the site. You can switch any time.
          </p>
        </section>
        <div className="path-grid">
          {PATHS.map((p) => (
            <button key={p.id} className={`path-card ${p.id === pathId ? 'path-card-current' : ''}`} onClick={() => choose(p.id)}>
              <span className="path-card-title">{p.title}</span>
              <span className="path-card-roles">{p.roleExamples}</span>
              <span className="path-card-why">{p.why}</span>
              <span className="path-card-cta">{p.id === pathId ? 'Current path' : 'Choose this path →'}</span>
            </button>
          ))}
        </div>
        <p className="caveat path-source">
          Source: Hughes et al., "Assessing the Needs of the Quantum Industry", IEEE Transactions on Education (2022).
        </p>
      </div>
    )
  }

  const percent = summary ? Math.round((summary.done / summary.total) * 100) : 0
  const next = summary?.next ? describeStep(summary.next, challengeTitles) : null

  return (
    <div className="app-shell">
      <PageHeader />
      <section className="module-intro">
        <p className="eyebrow">Your path</p>
        <h1 className="module-title">{path.title}</h1>
        <p className="module-lede">{path.why}</p>
        <p className="module-note">Typical roles: {path.roleExamples}. <button className="link-btn" onClick={() => setIsChoosing(true)}>Change path</button></p>
        {notice && <p className="module-note">{notice}</p>}
      </section>

      <div className="study-progress">
        <div className="study-progress-text">
          <span>{summary ? `${summary.done} of ${summary.total} steps done` : 'Loading your progress…'}</span>
          {next && <Link className="btn btn-primary" to={next.path}>Next: {next.title} →</Link>}
          {summary && !next && <Link className="btn btn-primary" to="/jobs">Path complete: find roles →</Link>}
        </div>
        <div className="progress-bar" role="progressbar" aria-valuenow={percent} aria-valuemin={0} aria-valuemax={100}>
          <span style={{ width: `${percent}%` }} />
        </div>
      </div>

      <ol className="path-stages">
        {path.stages.map((stage, i) => {
          const stageDone = progress ? stage.steps.filter((s) => isStepDone(s, progress)).length : 0
          return (
            <li key={stage.title} className="path-stage">
              <div className="path-stage-head">
                <span className="track-number">{String(i + 1).padStart(2, '0')}</span>
                <h2>{stage.title}</h2>
                <span className="track-count">{stageDone}/{stage.steps.length}</span>
              </div>
              <ul className="path-steps">
                {stage.steps.map((step) => {
                  const info = describeStep(step, challengeTitles)
                  const done = progress && isStepDone(step, progress)
                  const isNext = summary?.next === step
                  return (
                    <li key={`${step.kind}-${step.id}`}>
                      <Link to={info.path} className={`path-step ${done ? 'path-step-done' : ''} ${isNext ? 'path-step-next' : ''}`}>
                        <span className="lesson-check-mark" aria-hidden>{done ? '✓' : '○'}</span>
                        <span className="path-step-kind">{info.label}</span>
                        <span className="path-step-title">{info.title}</span>
                        <span className="lesson-minutes">{isNext ? 'next' : info.meta}</span>
                      </Link>
                    </li>
                  )
                })}
              </ul>
            </li>
          )
        })}
      </ol>
      {!user && <p className="caveat">Your path and progress are saved in this browser. <Link to="/login">Sign in</Link> to keep them across devices.</p>}
    </div>
  )
}

export default PathPage
