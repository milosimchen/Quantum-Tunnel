import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

function Landing() {
  const [dropping, setDropping] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    const pauseTimer = setTimeout(() => setDropping(true), 1800)
const navTimer = setTimeout(() => navigate('/home'), 2700)
    return () => {
      clearTimeout(pauseTimer)
      clearTimeout(navTimer)
    }
  }, [navigate])

  return (
    <div className={`landing ${dropping ? 'landing-drop' : ''}`}>
      <div className="landing-logo">
        QUANTUM <span>STUDIO</span>
      </div>
      <div className="landing-tagline">verified circuit analysis for quantum computing careers</div>
    </div>
  )
}

export default Landing