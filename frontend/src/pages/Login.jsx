import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import PageHeader from '../PageHeader'
import { useAuth } from '../AuthContext'

function Login() {
  const { accountsEnabled, user, profile, signInWithEmail, signUpWithEmail, signInWithGoogle } = useAuth()
  const navigate = useNavigate()

  const [mode, setMode] = useState('signin')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [notice, setNotice] = useState(null)
  const [isWorking, setIsWorking] = useState(false)

  // Already signed in: send new users to set up their profile, everyone else home.
  useEffect(() => {
    if (user && profile) {
      navigate(profile.onboarded ? '/home' : '/account', { replace: true })
    }
  }, [user, profile, navigate])

  async function handleSubmit(event) {
    event.preventDefault()
    setError(null)
    setNotice(null)
    setIsWorking(true)
    if (mode === 'signin') {
      const message = await signInWithEmail(email, password)
      if (message) setError(message)
    } else {
      const result = await signUpWithEmail(email, password)
      if (result.error) setError(result.error)
      else if (result.needsConfirmation) setNotice('Check your email for a confirmation link, then sign in.')
    }
    setIsWorking(false)
  }

  async function handleGoogle() {
    setError(null)
    const message = await signInWithGoogle()
    if (message) setError(message)
  }

  if (!accountsEnabled) {
    return (
      <div className="app-shell">
        <PageHeader subtitle="sign in" />
        <div className="auth-card">
          <h2>Accounts aren't set up yet</h2>
          <p className="auth-muted">
            Add <code>VITE_SUPABASE_URL</code> and <code>VITE_SUPABASE_ANON_KEY</code> to{' '}
            <code>frontend/.env.local</code> and restart the dev server. Until then, everything works in guest mode,
            but progress isn't saved.
          </p>
          <Link className="btn" to="/home">continue as guest</Link>
        </div>
      </div>
    )
  }

  return (
    <div className="app-shell">
      <PageHeader subtitle="sign in" />
      <div className="auth-card">
        <h2>{mode === 'signin' ? 'Welcome back' : 'Create your account'}</h2>
        <p className="auth-muted">
          An account saves your practice history, lesson progress and saved jobs, and lets the copilot tailor its help to you.
        </p>

        <button className="btn auth-google" onClick={handleGoogle} type="button">
          continue with Google
        </button>

        <div className="auth-divider"><span>or</span></div>

        <form onSubmit={handleSubmit} className="auth-form">
          <label className="field-label" htmlFor="email">email</label>
          <input id="email" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />

          <label className="field-label" htmlFor="password">password</label>
          <input
            id="password"
            type="password"
            autoComplete={mode === 'signin' ? 'current-password' : 'new-password'}
            minLength={8}
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />

          {error && <p className="error-text">{error}</p>}
          {notice && <p className="success-text">{notice}</p>}

          <button className="btn btn-teal" type="submit" disabled={isWorking}>
            {isWorking ? 'working…' : mode === 'signin' ? 'sign in' : 'create account'}
          </button>
        </form>

        <p className="auth-muted auth-switch">
          {mode === 'signin' ? 'New here?' : 'Already have an account?'}{' '}
          <button className="link-btn" type="button" onClick={() => { setMode(mode === 'signin' ? 'signup' : 'signin'); setError(null); setNotice(null) }}>
            {mode === 'signin' ? 'Create an account' : 'Sign in'}
          </button>
          {' · '}
          <Link to="/home">continue as guest</Link>
        </p>
      </div>
    </div>
  )
}

export default Login
