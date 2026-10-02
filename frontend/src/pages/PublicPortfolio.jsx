import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import PageHeader from '../PageHeader'
import { supabase } from '../supabase'
import { solvedWithCircuits, verifySolutions } from '../portfolio'
import { VerifiedList, useChallengeCatalog } from './Portfolio'
import { PATHS_BY_ID } from '../paths'

// Anyone can open this. Rows come from the owner's browser, so nothing is
// shown as verified until the grader has re-run the circuit on this visit.
function PublicPortfolio() {
  const { slug } = useParams()
  const challenges = useChallengeCatalog()
  const [owner, setOwner] = useState(undefined)
  const [entries, setEntries] = useState(null)
  const [verified, setVerified] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!supabase) {
      setOwner(null)
      return
    }
    ;(async () => {
      const { data: profile } = await supabase
        .from('profiles')
        .select('id, display_name, career_path, portfolio_slug')
        .eq('portfolio_slug', slug)
        .eq('portfolio_public', true)
        .maybeSingle()
      setOwner(profile || null)
      if (!profile) return
      const { data: attempts, error: loadError } = await supabase
        .from('practice_attempts')
        .select('challenge_id, passed, gates, created_at')
        .eq('user_id', profile.id)
        .eq('passed', true)
        .order('created_at', { ascending: false })
        .limit(500)
      if (loadError) {
        setError(loadError.message)
        return
      }
      const solved = solvedWithCircuits(attempts)
      setEntries(solved)
      try {
        setVerified(await verifySolutions(solved))
      } catch (e) {
        setError(`Couldn't verify solutions: ${e.message}`)
      }
    })()
  }, [slug])

  if (owner === undefined) return <div className="app-shell"><PageHeader /><p className="empty-state">Loading…</p></div>
  if (owner === null) {
    return (
      <div className="app-shell">
        <PageHeader />
        <p className="empty-state">There's no public portfolio at this address. <Link to="/home">Go to Quantum Tunnel</Link></p>
      </div>
    )
  }

  const count = entries && verified ? entries.filter((e) => verified.has(e.challenge_id)).length : null
  return (
    <div className="app-shell">
      <PageHeader />
      <section className="module-intro">
        <p className="eyebrow">Verified portfolio</p>
        <h1 className="module-title">{owner.display_name || owner.portfolio_slug}</h1>
        {owner.career_path && PATHS_BY_ID[owner.career_path] && <p className="module-lede">Preparing for: {PATHS_BY_ID[owner.career_path].title}</p>}
        <p className="module-note">
          {count === null ? 'Re-running every circuit through the grader…' : `${count} circuit challenge${count === 1 ? '' : 's'} solved. Each one was re-checked just now by exact unitary or state comparison in Qiskit, not taken on trust.`}
        </p>
      </section>
      {error && <p className="error-text">{error}</p>}
      {entries && verified && <VerifiedList entries={entries} verified={verified} challenges={challenges} />}
    </div>
  )
}

export default PublicPortfolio
