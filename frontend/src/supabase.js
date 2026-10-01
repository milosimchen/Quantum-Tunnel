import { createClient } from '@supabase/supabase-js'

// Both values come from Supabase: Project Settings -> API. The anon key is
// designed to be public; row-level security (supabase/schema.sql) is what
// protects each user's data.
const url = import.meta.env.VITE_SUPABASE_URL
const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

// When not configured, the app runs in guest-only mode: everything works,
// but nothing is saved between visits.
export const supabase = url && anonKey ? createClient(url, anonKey) : null
export const accountsEnabled = Boolean(supabase)
