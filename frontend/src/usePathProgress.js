import { useEffect, useState } from 'react'
import { loadCompletedLessons, loadPracticeAttempts, summarizeAttempts } from './progress'
import { quizCorrectByTopic } from './paths'

// The user's saved progress in the shape paths.js expects. null while loading.
export function usePathProgress(user) {
  const [progress, setProgress] = useState(null)

  useEffect(() => {
    let cancelled = false
    Promise.all([loadCompletedLessons(user), loadPracticeAttempts(user)]).then(([lessons, attempts]) => {
      if (cancelled) return
      const circuitAttempts = attempts.filter((a) => !a.challenge_id.startsWith('quiz:'))
      setProgress({
        lessons,
        solved: summarizeAttempts(circuitAttempts).solved,
        quizCorrectByTopic: quizCorrectByTopic(attempts),
      })
    })
    return () => { cancelled = true }
  }, [user])

  return progress
}
