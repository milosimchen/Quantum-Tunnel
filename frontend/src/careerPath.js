import { supabase } from './supabase'
import { PATHS_BY_ID } from './paths'

// ---- Storing the choice -------------------------------------------------------
// Saved on the profile when signed in; also kept in this browser, so the
// choice survives if the profile column hasn't been added yet (migration 002).

const LOCAL_KEY = 'qt.careerPath'

export function getCareerPath(profile) {
  if (profile?.career_path && PATHS_BY_ID[profile.career_path]) return profile.career_path
  try {
    const local = localStorage.getItem(LOCAL_KEY)
    return PATHS_BY_ID[local] ? local : null
  } catch {
    return null
  }
}

// Returns null on success, or a message if the account couldn't store it.
export async function saveCareerPath(user, pathId, updateProfile) {
  try {
    if (pathId) localStorage.setItem(LOCAL_KEY, pathId)
    else localStorage.removeItem(LOCAL_KEY)
  } catch {
    // Private mode: the account copy (if any) still works.
  }
  if (!user || !supabase) return null
  const error = await updateProfile({ career_path: pathId })
  if (error && /career_path/.test(error)) {
    return 'Saved in this browser. To save it to your account, run supabase/migrations/002_career_path.sql in Supabase.'
  }
  return error
}
