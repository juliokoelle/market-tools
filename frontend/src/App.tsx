import { useEffect } from 'react'
import { Routes, Route } from 'react-router-dom'
import Navigation from './components/Navigation'
import PasswordGate from './components/PasswordGate'
import LandingPage from './pages/LandingPage'
import Dashboard from './pages/Dashboard'
import Briefing from './pages/Briefing'
import Portfolio from './pages/Portfolio'
import HotStocks from './pages/HotStocks'
import Analyzer from './pages/Analyzer'
import Ideas from './pages/Ideas'

export default function App() {
  // Apply saved theme before first paint
  useEffect(() => {
    const saved = localStorage.getItem('mt_theme') || 'light'
    document.documentElement.dataset.theme = saved
  }, [])

  return (
    <PasswordGate>
      <Navigation />
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/market" element={<Dashboard />} />
        <Route path="/market/briefing" element={<Briefing />} />
        <Route path="/market/portfolio" element={<Portfolio />} />
        <Route path="/market/hot-stocks" element={<HotStocks />} />
        <Route path="/market/analyzer" element={<Analyzer />} />
        <Route path="/ideas" element={<Ideas />} />
      </Routes>
    </PasswordGate>
  )
}
