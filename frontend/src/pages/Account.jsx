import { useState, useEffect } from 'react'
import { useNavigate, Navigate } from 'react-router-dom'
import PageHeader from '../PageHeader'
import { useAuth } from '../AuthContext'
import { EXPERIENCE_LEVELS, GOALS } from '../profileOptions'

function Account() {
  const { user, profile, isLoading, updateProfile, signOut } = useAuth()
  const navigate = useNavigate()

  const [displayName, setDisplayName] = useState('')
  const [experienceLevel, setExperienceLevel] = useState('')
  const [goal, setGoal] = useState('')
  const [targetRole, setTargetRole] = useState('')
  const [error, setError] = useState(null)
  const [saved, setSaved] = useState(false)
  const [isSaving, setIsSaving] = useState(false)

  useEffect(() => {
    if (!profile) return
    setDisplayName(profile.display_name || '')
    setExperienceLevel(profile.experience_level || '')
    setGoal(profile.goal || '')
    setTargetRole(profile.target_role || '')
  }, [profile])

  if (isLoading) return null
  if (!user) return <Navigate to="/login" replace />

  const isOnboarding = profile && !profile.onboarded

  async function handleSave(event) {
    event.preventDefault()
    setError(null)
    setSaved(false)
    setIsSaving(true)
    const message = await updateProfile({
      display_name: displayName.trim() || null,
      experience_level: experienceLevel || null,
      goal: goal || null,
      target_role: targetRole.trim() || null,
      onboarded: true,
    })
    setIsSaving(false)
    if (message) {
      setError(message)
      return
    }
    if (isOnboarding) navigate('/home')
    else setSaved(true)
  }

  async function handleSignOut() {
    await signOut()
    navigate('/home')
  }

  return (
    <div className="app-shell">
      <PageHeader subtitle="account" />
      <div className="auth-card">
        <h2>{isOnboarding ? 'Tell us about yourself' : 'Your profile'}</h2>
        <p className="auth-muted">
          The copilot uses this to pitch explanations at the right level and to suggest what to work on next.
        </p>

        <form onSubmit={handleSave} className="auth-form">
          <label className="field-label" htmlFor="display-name">name</label>
          <input id="display-name" value={displayName} onChange={(e) => setDisplayName(e.target.value)} />

          <fieldset className="choice-group">
            <legend className="field-label">experience</legend>
            {EXPERIENCE_LEVELS.map((option) => (
              <label key={option.value} className={`choice ${experienceLevel === option.value ? 'choice-selected' : ''}`}>
                <input type="radio" name="experience" value={option.value} checked={experienceLevel === option.value} onChange={() => setExperienceLevel(option.value)} />
                {option.label}
              </label>
            ))}
          </fieldset>

          <fieldset className="choice-group">
            <legend className="field-label">main goal</legend>
            {GOALS.map((option) => (
              <label key={option.value} className={`choice ${goal === option.value ? 'choice-selected' : ''}`}>
                <input type="radio" name="goal" value={option.value} checked={goal === option.value} onChange={() => setGoal(option.value)} />
                {option.label}
              </label>
            ))}
          </fieldset>

          <label className="field-label" htmlFor="target-role">target role (optional)</label>
          <input
            id="target-role"
            placeholder="e.g. quantum software engineer"
            value={targetRole}
            onChange={(e) => setTargetRole(e.target.value)}
          />

          {error && <p className="error-text">{error}</p>}
          {saved && <p className="success-text">Saved.</p>}

          <button className="btn btn-teal" type="submit" disabled={isSaving}>
            {isSaving ? 'saving…' : isOnboarding ? 'continue' : 'save'}
          </button>
        </form>

        {!isOnboarding && (
          <p className="auth-muted auth-switch">
            Signed in as {user.email} ·{' '}
            <button className="link-btn" type="button" onClick={handleSignOut}>sign out</button>
          </p>
        )}
      </div>
    </div>
  )
}

export default Account
