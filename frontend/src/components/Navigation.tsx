import { NavLink, Link } from 'react-router-dom'
import { useState } from 'react'
import { useTheme } from '../hooks/useTheme'

function IconDashboard() {
  return <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="7" height="9"/><rect x="14" y="3" width="7" height="5"/><rect x="14" y="12" width="7" height="9"/><rect x="3" y="16" width="7" height="5"/></svg>
}
function IconBriefing() {
  return <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
}
function IconPortfolio() {
  return <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
}
function IconHot() {
  return <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M8.5 14.5A2.5 2.5 0 0011 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 11-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 002.5 2.5z"/></svg>
}
function IconAnalyzer() {
  return <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/><line x1="2" y1="20" x2="22" y2="20"/></svg>
}
function IconIdeas() {
  return <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
}
function IconSun() {
  return <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/></svg>
}
function IconMoon() {
  return <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z"/></svg>
}
function IconChevron({ collapsed }: { collapsed: boolean }) {
  return <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ transition: 'transform .2s', transform: collapsed ? 'rotate(180deg)' : 'none' }}><polyline points="15 18 9 12 15 6"/></svg>
}

const NAV_MARKET = [
  { to: '/market',            label: 'Dashboard',      icon: <IconDashboard />, end: true },
  { to: '/market/briefing',   label: 'Briefing',       icon: <IconBriefing />,  end: false },
  { to: '/market/portfolio',  label: 'Portfolio',      icon: <IconPortfolio />, end: false },
  { to: '/market/hot-stocks', label: 'Hot Stocks',     icon: <IconHot />,       end: false },
  { to: '/market/analyzer',   label: 'Stock Analyzer', icon: <IconAnalyzer />,  end: false },
]

export default function Navigation() {
  const { theme, toggle } = useTheme()
  const [collapsed, setCollapsed] = useState(false)

  return (
    <>
      <aside className={`sidebar${collapsed ? ' sidebar--collapsed' : ''}`}>
        {/* Logo */}
        <Link to="/" className="sidebar-logo" style={{ textDecoration: 'none' }}>
          <div className="sidebar-logo-mark">JK</div>
          {!collapsed && <span className="sidebar-logo-name">Intelligence OS</span>}
        </Link>

        {/* Market section */}
        <div className="sidebar-section">
          {!collapsed && <p className="sidebar-section-label">Market</p>}
          {NAV_MARKET.map(l => (
            <NavLink
              key={l.to}
              to={l.to}
              end={l.end}
              title={collapsed ? l.label : undefined}
              className={({ isActive }) => `sidebar-item${isActive ? ' active' : ''}`}
            >
              <span className="sidebar-item-icon">{l.icon}</span>
              {!collapsed && l.label}
            </NavLink>
          ))}
        </div>

        <div className="sidebar-divider" />

        {/* Capture section */}
        <div className="sidebar-section">
          {!collapsed && <p className="sidebar-section-label">Capture</p>}
          <NavLink
            to="/ideas"
            title={collapsed ? 'Ideas' : undefined}
            className={({ isActive }) => `sidebar-item${isActive ? ' active' : ''}`}
          >
            <span className="sidebar-item-icon"><IconIdeas /></span>
            {!collapsed && 'Ideas'}
          </NavLink>
        </div>

        {/* Footer */}
        <div className="sidebar-footer">
          <button className="theme-toggle" onClick={toggle} title={theme === 'dark' ? 'Light mode' : 'Dark mode'}>
            {theme === 'dark' ? <IconSun /> : <IconMoon />}
            {!collapsed && <span>{theme === 'dark' ? 'Light mode' : 'Dark mode'}</span>}
          </button>
        </div>
      </aside>

      {/* Collapse toggle tab */}
      <button
        className="sidebar-collapse-btn"
        onClick={() => setCollapsed(c => !c)}
        title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        style={{ left: collapsed ? 'calc(var(--sidebar-collapsed-w) - 1px)' : 'calc(var(--sidebar-w) - 1px)' }}
      >
        <IconChevron collapsed={collapsed} />
      </button>
    </>
  )
}
