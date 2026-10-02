import { useEffect } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from './AuthContext'

const FRIENDLY_AUTH_ERRORS = {
  otp_expired: 'That link has expired or was already used. If you already confirmed your email, just sign in below. Otherwise, sign up again to get a new link.',
  access_denied: 'That sign-in link didn\'t work. Please try signing in again.',
}

// Handles the two places Supabase sends people back into the app:
// - failed email/OAuth links arrive as "#error=...&error_code=..." on any page
// - a freshly signed-in user who hasn't set up their profile yet
function AuthRedirects() {
  const { user, profile } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()

  useEffect(() => {
    if (!location.hash.includes('error=')) return
    const params = new URLSearchParams(location.hash.slice(1))
    const code = params.get('error_code') || params.get('error')
    const message = FRIENDLY_AUTH_ERRORS[code] || params.get('error_description') || 'Sign-in failed. Please try again.'
    navigate('/login', { replace: true, state: { authError: message } })
  }, [location.hash, navigate])

  useEffect(() => {
    const exempt = ['/', '/login', '/account']
    // Public portfolio pages are for visitors; never redirect them to onboarding.
    if (location.pathname.startsWith('/u/')) return
    if (user && profile && !profile.onboarded && !exempt.includes(location.pathname)) {
      navigate('/account', { replace: true })
    }
  }, [user, profile, location.pathname, navigate])

  return null
}

export default AuthRedirects
