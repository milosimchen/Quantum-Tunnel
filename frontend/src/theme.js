// Theme preference: 'system' (follow the device), 'light' or 'dark'.
// index.html applies a saved explicit choice before first paint; this keeps
// it in sync afterwards. Tokens for both themes live in index.css.
const KEY = 'qt.theme'

export function getThemePreference() {
  try {
    const value = localStorage.getItem(KEY)
    return value === 'light' || value === 'dark' ? value : 'system'
  } catch {
    return 'system'
  }
}

export function setThemePreference(preference) {
  const root = document.documentElement
  if (preference === 'system') delete root.dataset.theme
  else root.dataset.theme = preference
  try {
    if (preference === 'system') localStorage.removeItem(KEY)
    else localStorage.setItem(KEY, preference)
  } catch {
    // Private mode: the choice lasts for this visit only.
  }
}
