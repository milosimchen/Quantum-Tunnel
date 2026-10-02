import { lazy, Suspense } from 'react'
import { Routes, Route } from 'react-router-dom'
import Landing from './pages/Landing'
import Home from './pages/Home'
import CopilotDock from './CopilotDock'
import MathDeepDive from './MathDeepDive'
import AuthRedirects from './AuthRedirects'

// Pages load on first visit, so the first page isn't held up by KaTeX, Supabase, etc.
const Studio = lazy(() => import('./pages/Studio'))
const Study = lazy(() => import('./pages/Study'))
const Jobs = lazy(() => import('./pages/Jobs'))
const InterviewPrep = lazy(() => import('./pages/InterviewPrep'))
const Login = lazy(() => import('./pages/Login'))
const Lesson = lazy(() => import('./pages/Lesson'))
const PathPage = lazy(() => import('./pages/PathPage'))
const MockInterview = lazy(() => import('./pages/MockInterview'))
const Portfolio = lazy(() => import('./pages/Portfolio'))
const PublicPortfolio = lazy(() => import('./pages/PublicPortfolio'))
const PracticeChallenge = lazy(() => import('./pages/PracticeChallenge'))
const Account = lazy(() => import('./pages/Account'))

function App() {
  return (
    <>
      <AuthRedirects />
      <Suspense fallback={<div className="app-shell"><p className="empty-state page-loading">Loading…</p></div>}>
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
      </Suspense>
      <CopilotDock />
      <MathDeepDive />
    </>
  )
}

export default App