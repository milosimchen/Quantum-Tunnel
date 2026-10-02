import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import PageHeader from '../PageHeader'
import { useAuth } from '../AuthContext'
import { useCopilotPage } from '../useCopilotPage'
import { apiUrl } from '../api'
import { loadPracticeAttempts } from '../progress'
import { solvedWithCircuits, verifySolutions } from '../portfolio'
import { buildNotebook, downloadJson } from '../notebook'

function useChallengeCatalog() {
  const [challenges, setChallenges] = useState({})
  useEffect(() => {
    fetch(apiUrl('/practice/challenges'))
      .then((response) => response.json())
      .then((data) => setChallenges(Object.fromEntries(data.challenges.map((c) => [c.id, c]))))
      .catch(() => {})
  }, [])
  return challenges
}

export function VerifiedList({ entries, verified, challenges }) {
  return (
    <ul className="portfolio-list">
      {entries.filter((e) => verified.has(e.challenge_id) && challenges[e.challenge_id]).map((entry) => {
        const c = challenges[entry.challenge_id]
        return (
          <li key={entry.challenge_id} className="portfolio-item">
            <span className="portfolio-check" aria-hidden>✓</span>
            <div>
              <p className="portfolio-title">{c.title}</p>
              <p className="portfolio-prompt">{c.prompt}</p>
            </div>
            <span className="portfolio-meta">
              <span className="skill-tag">{c.skill_label}</span>
              <span className="status-tag">{c.difficulty}</span>
              <span className="portfolio-gates">{entry.gates.length} gates</span>
            </span>
          </li>
        )
      })}
    </ul>
  )
}

const SLUG_PATTERN = /^[a-z0-9][a-z0-9-]{2,39}$/

function Portfolio() {
  const { user, profile, updateProfile, accountsEnabled } = useAuth()
  const challenges = useChallengeCatalog()
  const [entries, setEntries] = useState(null)
  const [verified, setVerified] = useState(null)
  const [error, setError] = useState(null)
  const [slug, setSlug] = useState('')
  const [shareNotice, setShareNotice] = useState(null)
  useCopilotPage({ kind: 'interview' })

  useEffect(() => {
    loadPracticeAttempts(user).then(async (attempts) => {
      const solved = solvedWithCircuits(attempts)
      setEntries(solved)
      try {
        setVerified(await verifySolutions(solved))
      } catch (e) {
        setError(`Couldn't verify solutions: ${e.message}`)
      }
    })
  }, [user])

  useEffect(() => {
    if (profile?.portfolio_slug) setSlug(profile.portfolio_slug)
    else if (profile?.display_name) setSlug(profile.display_name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 40))
  }, [profile])

  const verifiedEntries = entries && verified ? entries.filter((e) => verified.has(e.challenge_id) && challenges[e.challenge_id]) : []
  const isPublic = Boolean(profile?.portfolio_public)
  const publicUrl = profile?.portfolio_slug ? `${window.location.origin}/u/${profile.portfolio_slug}` : null

  function exportNotebook() {
    const name = profile?.display_name || ''
    downloadJson('quantum-tunnel-solutions.ipynb', buildNotebook({ name, entries: verifiedEntries, challenges }))
  }

  async function setPublic(makePublic) {
    setShareNotice(null)
    if (makePublic && !SLUG_PATTERN.test(slug)) {
      setShareNotice('Pick an address of 3–40 lowercase letters, numbers or hyphens.')
      return
    }
    const message = await updateProfile(makePublic ? { portfolio_public: true, portfolio_slug: slug } : { portfolio_public: false })
    if (message && /portfolio_/.test(message)) setShareNotice('Public portfolios need one database update: run supabase/migrations/003_portfolio.sql in Supabase.')
    else if (message && /duplicate|unique/i.test(message)) setShareNotice('That address is taken. Try another.')
    else if (message) setShareNotice(message)
    else setShareNotice(makePublic ? 'Your portfolio is public.' : 'Your portfolio is private again.')
  }

  return (
    <div className="app-shell">
      <PageHeader />
      <section className="module-intro">
        <p className="eyebrow">Proof of work</p>
        <h1 className="module-title">Your verified solutions</h1>
        <p className="module-lede">
          Hiring managers want evidence, not "familiar with quantum computing". Every circuit here was re-checked by the grader just now:
          export them as a Jupyter notebook for GitHub, or share a public page.
        </p>
      </section>

      <div className="portfolio-actions">
        <div className="panel portfolio-panel">
          <h2>Jupyter notebook</h2>
          <p className="auth-muted">One section per verified solution, with code that rebuilds your circuit in Qiskit. Good for a GitHub repo or an application.</p>
          <button className="btn btn-primary" onClick={exportNotebook} disabled={verifiedEntries.length === 0}>
            Download notebook ({verifiedEntries.length})
          </button>
        </div>
        <div className="panel portfolio-panel">
          <h2>Public page</h2>
          {!user ? (
            <p className="auth-muted">{accountsEnabled ? <><Link to="/login">Sign in</Link> to publish a public portfolio page.</> : 'Public pages need accounts to be set up.'}</p>
          ) : (
            <>
              <p className="auth-muted">Shows your name and verified solutions only. Visitors' browsers re-verify every circuit, so the page can't overstate what you've done.</p>
              <label className="field-label" htmlFor="portfolio-slug">Address</label>
              <div className="slug-row">
                <span className="slug-prefix">/u/</span>
                <input id="portfolio-slug" value={slug} onChange={(e) => setSlug(e.target.value.toLowerCase())} disabled={isPublic} />
              </div>
              <div className="practice-actions">
                {isPublic ? (
                  <>
                    <a className="btn btn-primary" href={publicUrl} target="_blank" rel="noopener noreferrer">Open public page ↗</a>
                    <button className="btn" onClick={() => setPublic(false)}>Make private</button>
                  </>
                ) : (
                  <button className="btn btn-primary" onClick={() => setPublic(true)}>Make public</button>
                )}
              </div>
              {shareNotice && <p className="module-note">{shareNotice}</p>}
            </>
          )}
        </div>
      </div>

      {error && <p className="error-text">{error}</p>}
      {!entries || !verified ? (
        <p className="empty-state">Verifying your solutions…</p>
      ) : verifiedEntries.length === 0 ? (
        <p className="empty-state">
          No verified solutions yet. Solve challenges in <Link to="/interview">Interview Prep</Link> and they'll appear here.
          (Solutions from before this feature didn't save their circuits, so solve them again to include them.)
        </p>
      ) : (
        <VerifiedList entries={entries} verified={verified} challenges={challenges} />
      )}
    </div>
  )
}

export { useChallengeCatalog }
export default Portfolio
