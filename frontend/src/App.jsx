import { Routes, Route } from 'react-router-dom'
import Landing from './pages/Landing'
import Home from './pages/Home'
import Studio from './pages/Studio'
import Study from './pages/Study'
import Jobs from './pages/Jobs'
import InterviewPrep from './pages/InterviewPrep'
import Login from './pages/Login'
import Lesson from './pages/Lesson'
import PathPage from './pages/PathPage'
import MockInterview from './pages/MockInterview'
import Portfolio from './pages/Portfolio'
import PublicPortfolio from './pages/PublicPortfolio'
import PracticeChallenge from './pages/PracticeChallenge'
import Account from './pages/Account'
import CopilotDock from './CopilotDock'
import MathDeepDive from './MathDeepDive'
import AuthRedirects from './AuthRedirects'

function App() {
  return (
    <>
      <AuthRedirects />
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/home" element={<Home />} />
        <Route path="/studio" element={<Studio />} />
        <Route path="/study" element={<Study />} />
        <Route path="/study/:lessonId" element={<Lesson />} />
        <Route path="/jobs" element={<Jobs />} />
        <Route path="/interview" element={<InterviewPrep />} />
        <Route path="/interview/mock" element={<MockInterview />} />
        <Route path="/interview/challenge/:challengeId" element={<PracticeChallenge />} />
        <Route path="/path" element={<PathPage />} />
        <Route path="/portfolio" element={<Portfolio />} />
        <Route path="/u/:slug" element={<PublicPortfolio />} />
        <Route path="/login" element={<Login />} />
        <Route path="/account" element={<Account />} />
      </Routes>
      <CopilotDock />
      <MathDeepDive />
    </>
  )
}

export default App