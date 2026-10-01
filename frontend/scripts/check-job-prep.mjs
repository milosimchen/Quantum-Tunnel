// Verifies every lesson / challenge / quiz topic referenced by jobs/jobPrep.js
// exists, so a renamed lesson can't silently break job prep links.
// Run with: npm run check:lessons (runs both checks)
import { readFileSync } from 'node:fs'
import { ALL_LESSONS } from '../src/study/lessons.js'
import { prepForJob } from '../src/jobs/jobPrep.js'

const lessonIds = new Set(ALL_LESSONS.map((l) => l.id))
const practiceSrc = readFileSync(new URL('../../backend/practice.py', import.meta.url), 'utf8')
const challengeIds = new Set([...practiceSrc.matchAll(/"id": "([a-z0-9_]+)"/g)].map((m) => m[1]))
const quizSrc = readFileSync(new URL('../../backend/interview_questions.py', import.meta.url), 'utf8')
const quizTopics = new Set([...quizSrc.matchAll(/"topic": "([A-Za-z ]+)"/g)].map((m) => m[1]))

// Every keyword area is reachable by its own first keyword; the fallback by empty text.
const src = readFileSync(new URL('../src/jobs/jobPrep.js', import.meta.url), 'utf8')
const firstKeywords = [...src.matchAll(/keywords: \['([^']+)'/g)].map((m) => m[1])
const areas = [...firstKeywords.map((k) => prepForJob({ title: k })[0]), prepForJob({ title: '' })[0]]

let bad = 0
for (const area of areas) {
  for (const id of area.lessons) if (!lessonIds.has(id)) { bad++; console.log(`${area.id}: unknown lesson ${id}`) }
  for (const id of area.challenges) if (!challengeIds.has(id)) { bad++; console.log(`${area.id}: unknown challenge ${id}`) }
  for (const t of area.quizTopics) if (!quizTopics.has(t)) { bad++; console.log(`${area.id}: unknown quiz topic ${t}`) }
}
console.log(areas.length, 'job-prep areas checked,', bad, 'problems')
if (bad) process.exit(1)
