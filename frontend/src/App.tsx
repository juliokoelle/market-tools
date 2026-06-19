import { useEffect } from 'react'
import { Routes, Route } from 'react-router-dom'
import Navigation from './components/Navigation'
import TickerBanner from './components/TickerBanner'
import PasswordGate from './components/PasswordGate'
import Today from './pages/Today'
import LandingPage from './pages/LandingPage'
import Dashboard from './pages/Dashboard'
import Briefing from './pages/Briefing'
import Portfolio from './pages/Portfolio'
import HotStocks from './pages/HotStocks'
import Analyzer from './pages/Analyzer'
import AnalyzerDetail from './pages/AnalyzerDetail'
import Ideas from './pages/Ideas'
import Training from './pages/Training'
import Podcasts from './pages/Podcasts'

const BACKEND = import.meta.env.VITE_API_URL ?? 'https://api.178-104-138-156.sslip.io'

export default function App() {
  useEffect(() => {
    const saved = localStorage.getItem('mt_theme') || 'light'
    document.documentElement.dataset.theme = saved
    fetch(`${BACKEND}/market/prices?tickers=%5EGSPC`).catch(() => {})
  }, [])

  return (
    <PasswordGate>
      <div className="app-with-ticker">
        <TickerBanner />
        <div className="app-shell">
          <Navigation />
          <div className="main-content">
            <Routes>
              <Route path="/" element={<Today />} />
              <Route path="/about" element={<LandingPage />} />
              <Route path="/market" element={<Dashboard />} />
              <Route path="/market/briefing" element={<Briefing />} />
              <Route path="/market/portfolio" element={<Portfolio />} />
              <Route path="/market/hot-stocks" element={<HotStocks />} />
              <Route path="/market/analyzer" element={<Analyzer />} />
              <Route path="/market/analyzer/:symbol" element={<AnalyzerDetail />} />
              <Route path="/ideas" element={<Ideas />} />
              <Route path="/life/training" element={<Training />} />
              <Route path="/life/podcasts" element={<Podcasts />} />
            </Routes>
          </div>
        </div>
      </div>
    </PasswordGate>
  )
}
