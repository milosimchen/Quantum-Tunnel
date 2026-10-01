import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../AuthContext'
import { useCopilot } from '../CopilotContext'
import { apiUrl } from '../api'
import { appendCopilotMessages, clearCopilotThread } from '../progress'
import { buildCopilotContext } from './buildCopilotContext'

const STARTERS = {
  study: ['Explain this lesson more simply', 'What should I study next?', 'Quiz me on what I just read'],
  interview: ['Give me a hint', 'What am I weakest at so far?', 'Ask me an interview question'],
  jobs: ['Make interview questions for a job I saved', 'Which saved job fits my progress best?', 'What skills do these roles want?'],
  home: ['Where should I start?', 'Summarize my progress', 'Make me a study plan for this week'],
}

function ModuleThread({ module, threads, setThreads }) {
  const { user, profile } = useAuth()
  const { pageContext, draft, setDraft } = useCopilot()
  const [input, setInput] = useState('')
  const [isSending, setIsSending] = useState(false)
  const [error, setError] = useState(null)
  const scrollRef = useRef(null)

  const messages = threads[module] || []

  // A draft handed over by a page ("ask the copilot for a hint") lands in the input box.
  useEffect(() => {
    if (draft) {
      setInput(draft)
      setDraft('')
    }
  }, [draft, setDraft])

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages.length, isSending])

  async function send(text) {
    const message = text.trim()
    if (!message || isSending) return
    setInput('')
    setError(null)
    setIsSending(true)

    const history = messages.map(({ role, content }) => ({ role, content }))
    setThreads((current) => ({ ...current, [module]: [...(current[module] || []), { role: 'user', content: message }] }))

    try {
      const context = await buildCopilotContext({ user, profile, pageContext, threads, activeModule: module })
      const response = await fetch(apiUrl('/copilot'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ module, message, history, context }),
      })
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || `status ${response.status}`)

      const reply = { role: 'assistant', content: data.answer, links: data.links }
      setThreads((current) => ({ ...current, [module]: [...(current[module] || []), reply] }))
      appendCopilotMessages(user, module, [{ role: 'user', content: message }, reply])
    } catch (e) {
      setError(`The copilot couldn't answer: ${e.message}`)
      // Put the unanswered message back so it isn't lost.
      setThreads((current) => ({ ...current, [module]: (current[module] || []).slice(0, -1) }))
      setInput(message)
    } finally {
      setIsSending(false)
    }
  }

  async function clearThread() {
    setThreads((current) => ({ ...current, [module]: [] }))
    await clearCopilotThread(user, module)
  }

  return (
    <>
      <div className="ai-scroll-area" ref={scrollRef}>
        {messages.length === 0 ? (
          <div className="copilot-empty">
            <p className="empty-state">
              Ask anything about quantum computing or your prep. The copilot can see your profile, progress, saved jobs
              and what's on this page.
            </p>
            <div className="copilot-starters">
              {(STARTERS[module] || STARTERS.home).map((starter) => (
                <button key={starter} className="filter-chip" onClick={() => send(starter)} disabled={isSending}>{starter}</button>
              ))}
            </div>
          </div>
        ) : (
          <div className="chat-log">
            {messages.map((entry, i) => (
              entry.role === 'user' ? (
                <div key={i} className="chat-q">{entry.content}</div>
              ) : (
                <div key={i} className="chat-a-block">
                  <div className="chat-a">{entry.content}</div>
                  {entry.links?.length > 0 && (
                    <div className="copilot-links">
                      {entry.links.map((link) => (
                        <Link key={`${link.kind}-${link.id}`} to={link.path} className="filter-chip">{link.title} →</Link>
                      ))}
                    </div>
                  )}
                </div>
              )
            ))}
            {isSending && <div className="chat-a thinking-dots" aria-label="Copilot is thinking">thinking…</div>}
          </div>
        )}
      </div>

      {error && <p className="error-text">{error}</p>}
      <p className="caveat copilot-caveat">
        AI-generated. Facts about your progress come from your saved data, but explanations aren't verified. Only Check answer and Scan verify circuits.
        {messages.length > 0 && <> · <button className="link-btn" onClick={clearThread}>clear this thread</button></>}
      </p>

      <form className="chat-input-row" onSubmit={(e) => { e.preventDefault(); send(input) }}>
        <input type="text" value={input} onChange={(e) => setInput(e.target.value)} placeholder="Ask the copilot…" disabled={isSending} aria-label="Message the copilot" />
        <button className="btn btn-primary" type="submit" disabled={isSending || !input.trim()}>{isSending ? '…' : 'ask'}</button>
      </form>
    </>
  )
}

export default ModuleThread
