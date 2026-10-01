import { Routes, Route } from 'react-router-dom'
import Landing from './pages/Landing'
import Home from './pages/Home'
import Studio from './pages/Studio'
import Study from './pages/Study'
import Jobs from './pages/Jobs'
import InterviewPrep from './pages/InterviewPrep'
import CopilotDock from './CopilotDock'
import MathDeepDive from './MathDeepDive'

function App() {
  return (
    <>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/home" element={<Home />} />
        <Route path="/studio" element={<Studio />} />
        <Route path="/study" element={<Study />} />
        <Route path="/jobs" element={<Jobs />} />
        <Route path="/interview" element={<InterviewPrep />} />
      </Routes>
      <CopilotDock />
      <MathDeepDive />
    </>
  )
}

export default App