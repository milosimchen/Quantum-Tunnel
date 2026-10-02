import { ALL_LESSONS } from './study/lessons'
import { QUIZ_STEP_TARGET } from './paths'

const LESSONS_BY_ID = Object.fromEntries(ALL_LESSONS.map((l) => [l.id, l]))

// Title, route and kind label for a path step. challengeTitles comes from /practice/challenges.
export function describeStep(step, challengeTitles = {}) {
  if (step.kind === 'lesson') {
    const lesson = LESSONS_BY_ID[step.id]
    return { label: 'Read', title: lesson?.title || step.id, path: `/study/${step.id}`, meta: lesson ? `${lesson.minutes} min` : '' }
  }
  if (step.kind === 'challenge') {
    return { label: 'Build', title: challengeTitles[step.id] || step.id, path: `/interview/challenge/${step.id}`, meta: '' }
  }
  return {
    label: 'Quiz',
    title: `${step.id} questions`,
    path: `/interview?tab=concepts&topic=${encodeURIComponent(step.id)}`,
    meta: `${QUIZ_STEP_TARGET} correct`,
  }
}
