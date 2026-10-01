import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { CircuitProvider } from './CircuitContext'
import { AuthProvider } from './AuthContext'
import { CopilotProvider } from './CopilotContext'
import './index.css'
import './App.css'
import App from './App.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <CircuitProvider>
          <CopilotProvider>
            <App />
          </CopilotProvider>
        </CircuitProvider>
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
)