import { Link } from 'react-router-dom'
import { useCircuit } from './CircuitContext'

function PageHeader({ subtitle }) {
  const { isCopilotOpen, setIsCopilotOpen } = useCircuit()

  return (
    <header className="app-header">
      <div className="brand">
        <div className="logo">QUANTUM <span>STUDIO</span></div>
        <div className="tagline">{subtitle}</div>
      </div>
      <div className="header-actions">
        <Link to="/home" className="home-link">← home</Link>
        <button
          className="copilot-toggle"
          onClick={() => setIsCopilotOpen(!isCopilotOpen)}
          aria-label="Toggle AI Copilot"
        >
          ✦
        </button>
      </div>
    </header>
  )
}

export default PageHeader