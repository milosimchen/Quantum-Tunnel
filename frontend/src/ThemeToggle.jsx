import { useState } from 'react'
import { getThemePreference, setThemePreference } from './theme'

const NEXT = { system: 'light', light: 'dark', dark: 'system' }
const LABELS = { system: 'Theme: matches your device', light: 'Theme: light', dark: 'Theme: dark' }

function ThemeIcon({ preference }) {
  if (preference === 'light') {
    return (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden="true">
        <circle cx="12" cy="12" r="4" />
        <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
      </svg>
    )
  }
  if (preference === 'dark') {
    return (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M20 14.5A8 8 0 019.5 4a8 8 0 1010.5 10.5z" />
      </svg>
    )
  }
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden="true">
      <circle cx="12" cy="12" r="8" />
      <path d="M12 4a8 8 0 010 16z" fill="currentColor" stroke="none" />
    </svg>
  )
}

// Cycles: device setting → light → dark → device setting.
function ThemeToggle() {
  const [preference, setPreference] = useState(getThemePreference)

  function cycle() {
    const next = NEXT[preference]
    setThemePreference(next)
    setPreference(next)
  }

  return (
    <button className="icon-btn" onClick={cycle} aria-label={`${LABELS[preference]}. Click to change.`} title={LABELS[preference]}>
      <ThemeIcon preference={preference} />
    </button>
  )
}

export default ThemeToggle
