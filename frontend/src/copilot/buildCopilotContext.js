import { loadCompletedLessons, loadPracticeAttempts, loadSavedJobs, summarizeAttempts } from '../progress'
import { ALL_LESSONS } from '../study/lessons'

const LESSON_CATALOG = ALL_LESSONS.map((l) => ({ id: l.id, title: l.title, track: l.trackTitle }))

// Gathers what the copilot is allowed to know, fresh at send time. Everything
// here is the user's own saved data; the backend turns it into the facts the
// model must stick to (see backend/copilot.py).
export async function buildCopilotContext({ user, profile, pageContext, threads, activeModule }) {
  const [completedLessons, attempts, savedJobs] = await Promise.all([
    loadCompletedLessons(user),
    loadPracticeAttempts(user),
    loadSavedJobs(user),
  ])

  const circuitAttempts = attempts.filter((a) => !a.challenge_id.startsWith('quiz:'))
  const { solved, tried } = summarizeAttempts(circuitAttempts)

  // Latest answer per quiz question, tallied by topic.
  const latestQuiz = new Map()
  for (const a of attempts) {
    if (a.challenge_id.startsWith('quiz:') && !latestQuiz.has(a.challenge_id)) latestQuiz.set(a.challenge_id, a)
  }
  const quizByTopic = {}
  for (const a of latestQuiz.values()) {
    const topic = (quizByTopic[a.skill] ||= { answered: 0, correct: 0 })
    topic.answered += 1
    if (a.passed) topic.correct += 1
  }

  const otherThreads = Object.fromEntries(
    Object.entries(threads).filter(([module, messages]) => module !== activeModule && messages.length > 0)
  )

  return {
    signed_in: Boolean(user),
    profile: profile
      ? {
          display_name: profile.display_name,
          experience_level: profile.experience_level,
          goal: profile.goal,
          target_role: profile.target_role,
        }
      : {},
    progress: {
      lessons_completed: [...completedLessons],
      challenges_solved: [...solved],
      challenges_attempted: [...tried],
      quiz_by_topic: quizByTopic,
    },
    saved_jobs: savedJobs.map(({ job_id, title, company, status, description }) => ({ job_id, title, company, status, description })),
    page: pageContext,
    other_threads: otherThreads,
    lesson_catalog: LESSON_CATALOG,
  }
}
