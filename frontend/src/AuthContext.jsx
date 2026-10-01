import { createContext, useContext, useEffect, useState, useCallback } from 'react'
import { supabase, accountsEnabled } from './supabase'

const AuthContext = createContext(null)

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

export function AuthProvider({ children }) {
  const [session, setSession] = useState(null)
  const [profile, setProfile] = useState(null)
  // Guest mode has nothing to load, so it starts ready.
  const [isLoading, setIsLoading] = useState(accountsEnabled)

  const loadProfile = useCallback(async (userId) => {
    if (!supabase || !userId) {
      setProfile(null)
      return
    }
    const { data, error } = await supabase
      .from('profiles')
      .select('*')
      .eq('id', userId)
      .maybeSingle()
    if (error) {
      console.error('Failed to load profile:', error.message)
    }
    setProfile(data || null)
  }, [])

  useEffect(() => {
    if (!supabase) return

    supabase.auth.getSession().then(async ({ data }) => {
      setSession(data.session)
      await loadProfile(data.session?.user?.id)
      setIsLoading(false)
    })

    const { data: listener } = supabase.auth.onAuthStateChange((_event, newSession) => {
      setSession(newSession)
      // Deferred so the Supabase client isn't re-entered from inside its own callback.
      setTimeout(() => loadProfile(newSession?.user?.id), 0)
    })

    return () => listener.subscription.unsubscribe()
  }, [loadProfile])

  async function signInWithEmail(email, password) {
    const { error } = await supabase.auth.signInWithPassword({ email, password })
    return error?.message || null
  }

  async function signUpWithEmail(email, password) {
    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: { emailRedirectTo: `${window.location.origin}/home` },
    })
    if (error) return { error: error.message }
    // With email confirmation on, there's a user but no session until they click the link.
    return { error: null, needsConfirmation: !data.session }
  }

  async function signInWithGoogle() {
    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: { redirectTo: `${window.location.origin}/home` },
    })
    return error?.message || null
  }

  async function signOut() {
    await supabase.auth.signOut()
    setProfile(null)
  }

  async function updateProfile(fields) {
    if (!supabase || !session) return 'Not signed in.'
    const { data, error } = await supabase
      .from('profiles')
      .update({ ...fields, updated_at: new Date().toISOString() })
      .eq('id', session.user.id)
      .select()
      .single()
    if (error) return error.message
    setProfile(data)
    return null
  }

  const value = {
    accountsEnabled,
    isLoading,
    session,
    user: session?.user || null,
    profile,
    signInWithEmail,
    signUpWithEmail,
    signInWithGoogle,
    signOut,
    updateProfile,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
