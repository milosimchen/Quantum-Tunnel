import { useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { useAuth } from './AuthContext'
import { useCopilot } from './CopilotContext'
import { loadCopilotThreads } from './progress'
import StudioCopilot from './copilot/StudioCopilot'
import ModuleThread from './copilot/ModuleThread'

const TABS = [
  { module: 'studio', label: 'Studio' },
  { module: 'study', label: 'Study' },
  { module: 'interview', label: 'Interview' },
  { module: 'jobs', label: 'Jobs' },
  { module: 'home', label: 'General' },
]

function moduleForPath(pathname) {
  if (pathname.startsWith('/studio')) return 'studio'
  if (pathname.startsWith('/study')) return 'study'
  if (pathname.startsWith('/interview')) return 'interview'
  if (pathname.startsWith('/jobs')) return 'jobs'
  return 'home'
}

// One copilot across the site, with a separate conversation thread per module.
// Each thread can still see the others (and the user's progress), so context
// carries across modules.
function CopilotDock() {
  const { user } = useAuth()
  const { isOpen, setIsOpen, activeModule, setActiveModule } = useCopilot()
  const location = useLocation()
  const [threads, setThreads] = useState({})

  useEffect(() => {
    loadCopilotThreads(user).then(setThreads)
  }, [user])

  // Follow the page the user is on, unless they've picked a tab since opening.
  useEffect(() => {
    if (!isOpen) setActiveModule(moduleForPath(location.pathname))
  }, [isOpen, location.pathname, setActiveModule])

  useEffect(() => {
    function onKey(event) {
      if (event.key === 'Escape') setIsOpen(false)
    }
    if (isOpen) window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [isOpen, setIsOpen])

  const module = activeModule || moduleForPath(location.pathname)

  return (
    <>
      {isOpen && <div className="copilot-overlay" onClick={() => setIsOpen(false)} />}

      <aside className={`copilot-dock ${isOpen ? 'copilot-dock-open' : ''}`} aria-hidden={!isOpen} aria-label="AI copilot">
        <div className="copilot-dock-header">
          <div className="ai-copilot-header">
            <span className="ai-dot"></span>
            <span className="ai-copilot-title">AI copilot</span>
          </div>
          <button className="copilot-close" onClick={() => setIsOpen(false)} aria-label="Close copilot">✕</button>
        </div>

        <div className="copilot-tabs" role="tablist">
          {TABS.map((tab) => (
            <button
              key={tab.module}
              role="tab"
              aria-selected={module === tab.module}
              className={`copilot-tab ${module === tab.module ? 'copilot-tab-active' : ''}`}
              onClick={() => setActiveModule(tab.module)}
            >
              {tab.label}
              {tab.module !== 'studio' && threads[tab.module]?.length > 0 && <span className="copilot-tab-dot" aria-hidden />}
            </button>
          ))}
        </div>

        {isOpen && (module === 'studio'
          ? <StudioCopilot />
          : <ModuleThread key={module} module={module} threads={threads} setThreads={setThreads} />)}
      </aside>
    </>
  )
}

export default CopilotDock
