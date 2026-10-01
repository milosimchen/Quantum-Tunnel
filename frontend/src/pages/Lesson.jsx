import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import PageHeader from '../PageHeader'
import { useCopilotPage } from '../useCopilotPage'
import { useCopilot } from '../CopilotContext'
import { useAuth } from '../AuthContext'
import { apiUrl } from '../api'
import { loadCompletedLessons, setLessonComplete } from '../progress'
import { findLesson } from '../study/lessons'
import LessonBlocks from '../study/LessonBlocks'

function Lesson() {
  const { lessonId } = useParams()
  const { user } = useAuth()
  const found = findLesson(lessonId)
  const [isComplete, setIsComplete] = useState(false)
  const [challengeTitles, setChallengeTitles] = useState({})
  const { openCopilot } = useCopilot()
  useCopilotPage({ kind: 'lesson', lesson_id: lessonId })

  useEffect(() => {
    loadCompletedLessons(user).then((done) => setIsComplete(done.has(lessonId)))
  }, [user, lessonId])

  useEffect(() => {
    window.scrollTo(0, 0)
  }, [lessonId])

  useEffect(() => {
    fetch(apiUrl('/practice/challenges'))
      .then((response) => response.json())
      .then((data) => setChallengeTitles(Object.fromEntries(data.challenges.map((c) => [c.id, c.title]))))
      .catch(() => {})
  }, [])

  if (!found) {
    return (
      <div className="app-shell">
        <PageHeader subtitle="study" />
        <p className="empty-state">That lesson doesn't exist. <Link to="/study">Back to Study</Link></p>
      </div>
    )
  }

  const { lesson, previous, next } = found

  async function toggleComplete() {
    const newValue = !isComplete
    setIsComplete(newValue)
    await setLessonComplete(user, lesson.id, newValue)
  }

  return (
    <div className="app-shell">
      <PageHeader subtitle="study" />
      <article className="lesson">
        <Link to="/study" className="back-link">← {lesson.trackTitle}</Link>
        <h1 className="module-title">{lesson.title}</h1>
        <p className="lesson-meta">
          {lesson.minutes} min read ·{' '}
          <button className="link-btn" onClick={() => openCopilot('study', `I'm reading "${lesson.title}". `)}>ask the copilot about this lesson</button>
        </p>

        <LessonBlocks blocks={lesson.blocks} challengeTitles={challengeTitles} />

        <div className="lesson-footer">
          <button className={`btn ${isComplete ? '' : 'btn-teal'}`} onClick={toggleComplete}>
            {isComplete ? '✓ completed (undo)' : 'mark as complete'}
          </button>
          <nav className="lesson-nav">
            {previous ? <Link to={`/study/${previous.id}`}>← {previous.title}</Link> : <span />}
            {next ? <Link to={`/study/${next.id}`}>{next.title} →</Link> : <Link to="/study">back to all lessons</Link>}
          </nav>
        </div>
      </article>
    </div>
  )
}

export default Lesson
