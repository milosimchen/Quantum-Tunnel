// Sanity-checks lesson content after edits: every formula renders in KaTeX and
// every quick-check answer index is valid. Run with: npm run check:lessons
import katex from 'katex'
import { ALL_LESSONS } from '../src/study/lessons.js'
let n = 0, bad = 0
const tex = []
for (const l of ALL_LESSONS) for (const b of l.blocks) {
  if (b.type === 'math') tex.push([l.id, b.tex, true])
  for (const t of [b.text, b.question].filter(Boolean)) for (const m of t.matchAll(/\$([^$]+)\$/g)) tex.push([l.id, m[1], false])
  if (b.type === 'check' && (b.answer < 0 || b.answer >= b.choices.length)) { console.log('BAD ANSWER INDEX', l.id); bad++ }
}
for (const [id, t, d] of tex) { n++; try { katex.renderToString(t, { displayMode: d, throwOnError: true }) } catch (e) { bad++; console.log(id, '::', t, '::', e.message) } }
console.log(n, 'formulas checked,', bad, 'problems')
if (bad) process.exit(1)
