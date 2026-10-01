import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { CircuitProvider } from './CircuitContext'
import { AuthProvider } from './AuthContext'
import './App.css'
import App from './App.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <CircuitProvider>
          <App />
        </CircuitProvider>
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
)