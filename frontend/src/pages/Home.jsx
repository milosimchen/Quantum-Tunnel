import { Link } from 'react-router-dom'
import { useCopilotPage } from '../useCopilotPage'

const MODULES = [
  { path: '/study', title: 'Study', description: 'Quantum computing fundamentals — from intuition to the underlying math.' },
  { path: '/studio', title: 'Studio', description: 'Build, simplify, and verify quantum circuits with AI-assisted analysis.' },
  { path: '/jobs', title: 'Opportunities', description: 'Job listings and news from the quantum computing industry.' },
  { path: '/interview', title: 'Interview Prep', description: 'Practice canonical circuits and common interview questions.' },
]

function Home() {
  useCopilotPage({ kind: 'home' })
  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="brand">
          <div className="logo">QUANTUM <span>STUDIO</span></div>
          <div className="tagline">verified circuit analysis</div>
        </div>
      </header>

      <div className="module-grid">
        {MODULES.map((mod) => (
          <Link to={mod.path} className="module-card" key={mod.path}>
            <h2>{mod.title}</h2>
            <p>{mod.description}</p>
          </Link>
        ))}
      </div>
    </div>
  )
}

export default Home