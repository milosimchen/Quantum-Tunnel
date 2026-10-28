// Prints every lesson as JSON for the copilot's retrieval index
// (backend/ingest_rag.py). Run with: node scripts/export-lessons.mjs
import { ALL_LESSONS } from '../src/study/lessons.js'

process.stdout.write(JSON.stringify(ALL_LESSONS.map(({ id, title, trackTitle, blocks }) => ({ id, title, trackTitle, blocks }))))
