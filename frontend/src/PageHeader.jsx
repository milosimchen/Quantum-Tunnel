import { Link, NavLink } from 'react-router-dom'
import { useCopilot } from './CopilotContext'
import { useAuth } from './AuthContext'
import BrandMark from './BrandMark'
import ThemeToggle from './ThemeToggle'
import SparkleIcon from './SparkleIcon'

const NAV = [
  { to: '/study', label: 'Study' },
  { to: '/studio', label: 'Studio' },
  { to: '/interview', label: 'Interview Prep' },
  { to: '/jobs', label: 'Opportunities' },
]

function PageHeader() {
  const { isOpen, setIsOpen } = useCopilot()
  const { accountsEnabled, user, profile } = useAuth()

  return (
    <header className="app-header">
      <Link to="/home" className="brand">
        <BrandMark />
        Quantum Tunnel
      </Link>
      <nav className="site-nav" aria-label="Modules">
        {NAV.map((item) => (
          <NavLink key={item.to} to={item.to} className={({ isActive }) => (isActive ? 'active' : '')}>
            {item.label}
          </NavLink>
        ))}
      </nav>
      <div className="header-actions">
        <button className="copilot-toggle" onClick={() => setIsOpen(!isOpen)} aria-expanded={isOpen} aria-label="Ask the copilot">
          <SparkleIcon />
          <span className="copilot-toggle-label">Ask the copilot</span>
        </button>
        <ThemeToggle />
        {accountsEnabled && (
          user ? (
            <Link to="/account" className="account-link" title="Your profile">
              {profile?.display_name || user.email}
            </Link>
          ) : (
            <Link to="/login" className="home-link">Sign in</Link>
          )
        )}
      </div>
    </header>
  )
}

export default PageHeader
