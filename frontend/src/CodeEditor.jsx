// A plain, accessible code box for OpenQASM. Tab inserts two spaces instead of
// leaving the field (Esc then Tab still moves focus on, for keyboard users).
function CodeEditor({ id, value, onChange, rows = 12, label }) {
  function handleKeyDown(event) {
    if (event.key === 'Tab' && !event.shiftKey && !event.target.dataset.escaped) {
      event.preventDefault()
      const { selectionStart, selectionEnd } = event.target
      const next = value.slice(0, selectionStart) + '  ' + value.slice(selectionEnd)
      onChange(next)
      requestAnimationFrame(() => {
        event.target.selectionStart = event.target.selectionEnd = selectionStart + 2
      })
    }
    if (event.key === 'Escape') event.target.dataset.escaped = '1'
  }

  return (
    <div className="code-editor">
      <label className="field-label" htmlFor={id}>{label}</label>
      <textarea
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKeyDown}
        onBlur={(e) => delete e.target.dataset.escaped}
        rows={rows}
        spellCheck={false}
        autoCapitalize="off"
        autoComplete="off"
        autoCorrect="off"
        aria-describedby={`${id}-help`}
      />
      <span id={`${id}-help`} className="caveat">OpenQASM 2 or 3. Tab indents; press Esc then Tab to leave the editor.</span>
    </div>
  )
}

export default CodeEditor
