import { supabase } from './supabase'

// Progress storage. Signed-in users save to Supabase (follows them across
// devices); guests save to this browser's localStorage so a refresh doesn't
// wipe their work. Every function takes the current user (or null).

const GUEST_ATTEMPTS_KEY = 'qs.guest.practiceAttempts'
const GUEST_LESSONS_KEY = 'qs.guest.lessonProgress'

function readGuest(key) {
  try {
    return JSON.parse(localStorage.getItem(key)) || []
  } catch {
    return []
  }
}

function writeGuest(key, rows) {
  try {
    localStorage.setItem(key, JSON.stringify(rows))
  } catch {
    // Storage full or blocked (private mode): progress just won't persist.
  }
}

// ---- Interview Prep ---------------------------------------------------------

// attempt: { challenge_id, skill, difficulty, passed, gate_count }
// Quiz answers use challenge_id "quiz:<question id>" and the topic as skill.
export async function recordPracticeAttempt(user, attempt) {
  if (user && supabase) {
    const { error } = await supabase.from('practice_attempts').insert({ ...attempt, user_id: user.id })
    if (error) console.error('Failed to save attempt:', error.message)
    return
  }
  const rows = readGuest(GUEST_ATTEMPTS_KEY)
  rows.push({ ...attempt, created_at: new Date().toISOString() })
  writeGuest(GUEST_ATTEMPTS_KEY, rows.slice(-500))
}

export async function loadPracticeAttempts(user) {
  if (user && supabase) {
    const { data, error } = await supabase
      .from('practice_attempts')
      .select('challenge_id, skill, difficulty, passed, gate_count, created_at')
      .order('created_at', { ascending: false })
      .limit(1000)
    if (error) {
      console.error('Failed to load attempts:', error.message)
      return []
    }
    return data
  }
  return readGuest(GUEST_ATTEMPTS_KEY).reverse()
}

// Summaries the UI (and later the copilot) can use without re-deriving them.
export function summarizeAttempts(attempts) {
  const solved = new Set()
  const tried = new Set()
  for (const attempt of attempts) {
    tried.add(attempt.challenge_id)
    if (attempt.passed) solved.add(attempt.challenge_id)
  }
  return { solved, tried }
}

// ---- Study ------------------------------------------------------------------

export async function loadCompletedLessons(user) {
  if (user && supabase) {
    const { data, error } = await supabase.from('lesson_progress').select('lesson_id, completed_at')
    if (error) {
      console.error('Failed to load lesson progress:', error.message)
      return new Set()
    }
    return new Set(data.map((row) => row.lesson_id))
  }
  return new Set(readGuest(GUEST_LESSONS_KEY))
}

export async function setLessonComplete(user, lessonId, complete) {
  if (user && supabase) {
    const query = complete
      ? supabase.from('lesson_progress').upsert({ user_id: user.id, lesson_id: lessonId })
      : supabase.from('lesson_progress').delete().eq('lesson_id', lessonId)
    const { error } = await query
    if (error) console.error('Failed to update lesson progress:', error.message)
    return
  }
  const lessons = new Set(readGuest(GUEST_LESSONS_KEY))
  if (complete) lessons.add(lessonId)
  else lessons.delete(lessonId)
  writeGuest(GUEST_LESSONS_KEY, [...lessons])
}

// ---- Jobs -------------------------------------------------------------------

const GUEST_JOBS_KEY = 'qs.guest.savedJobs'

export const JOB_STATUSES = [
  { value: 'saved', label: 'Saved' },
  { value: 'applied', label: 'Applied' },
  { value: 'interviewing', label: 'Interviewing' },
  { value: 'offer', label: 'Offer' },
  { value: 'closed', label: 'Closed' },
]

export async function loadSavedJobs(user) {
  if (user && supabase) {
    const { data, error } = await supabase.from('saved_jobs').select('*').order('saved_at', { ascending: false })
    if (error) {
      console.error('Failed to load saved jobs:', error.message)
      return []
    }
    return data
  }
  return readGuest(GUEST_JOBS_KEY)
}

// job: a listing from /jobs_search. Only the fields worth keeping are stored.
export async function saveJob(user, job) {
  const row = {
    job_id: job.id,
    title: job.title,
    company: job.company,
    location: job.location,
    apply_url: job.apply_url,
    description: job.description,
    status: 'saved',
    notes: '',
    saved_at: new Date().toISOString(),
  }
  if (user && supabase) {
    const { data, error } = await supabase.from('saved_jobs').upsert({ ...row, user_id: user.id }).select().single()
    if (error) {
      console.error('Failed to save job:', error.message)
      return null
    }
    return data
  }
  const rows = readGuest(GUEST_JOBS_KEY).filter((r) => r.job_id !== job.id)
  writeGuest(GUEST_JOBS_KEY, [row, ...rows])
  return row
}

export async function updateSavedJob(user, jobId, fields) {
  const changes = { ...fields, updated_at: new Date().toISOString() }
  if (user && supabase) {
    const { error } = await supabase.from('saved_jobs').update(changes).eq('job_id', jobId)
    if (error) console.error('Failed to update job:', error.message)
    return
  }
  writeGuest(GUEST_JOBS_KEY, readGuest(GUEST_JOBS_KEY).map((r) => (r.job_id === jobId ? { ...r, ...changes } : r)))
}

export async function removeSavedJob(user, jobId) {
  if (user && supabase) {
    const { error } = await supabase.from('saved_jobs').delete().eq('job_id', jobId)
    if (error) console.error('Failed to remove job:', error.message)
    return
  }
  writeGuest(GUEST_JOBS_KEY, readGuest(GUEST_JOBS_KEY).filter((r) => r.job_id !== jobId))
}
