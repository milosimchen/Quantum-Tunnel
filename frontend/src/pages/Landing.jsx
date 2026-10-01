import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import BrandMark from '../BrandMark'

function Landing() {
  const [leaving, setLeaving] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    const pauseTimer = setTimeout(() => setLeaving(true), 1600)
    const navTimer = setTimeout(() => navigate('/home'), 2200)
    return () => {
      clearTimeout(pauseTimer)
      clearTimeout(navTimer)
    }
  }, [navigate])

  return (
    <div className={`landing ${leaving ? 'landing-drop' : ''}`}>
      <div className="landing-logo">
        <BrandMark size={56} />
        Quantum Tunnel
      </div>
      <div className="landing-tagline">verified practice for quantum computing careers</div>
    </div>
  )
}

export default Landing
