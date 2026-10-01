import { createContext, useCallback, useContext, useState } from 'react'

const CopilotContext = createContext(null)

export function useCopilot() {
  const context = useContext(CopilotContext)
  if (!context) {
    throw new Error('useCopilot must be used within a CopilotProvider')
  }
  return context
}

// Site-wide copilot state: whether the dock is open, which module's thread is
// showing, an optional pre-filled draft, and what the current page wants the
// copilot to know about (set by pages via useCopilotPage).
export function CopilotProvider({ children }) {
  const [isOpen, setIsOpen] = useState(false)
  const [activeModule, setActiveModule] = useState(null)
  const [draft, setDraft] = useState('')
  const [pageContext, setPageContext] = useState({ kind: 'home' })

  const openCopilot = useCallback((module = null, draftText = '') => {
    if (module) setActiveModule(module)
    if (draftText) setDraft(draftText)
    setIsOpen(true)
  }, [])

  const value = {
    isOpen, setIsOpen,
    activeModule, setActiveModule,
    draft, setDraft,
    pageContext, setPageContext,
    openCopilot,
  }

  return <CopilotContext.Provider value={value}>{children}</CopilotContext.Provider>
}
