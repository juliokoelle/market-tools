import { useState, useRef, useEffect } from 'react'
import { NavLink, Link, useLocation } from 'react-router-dom'
import { useTheme } from '../hooks/useTheme'

const marketLinks = [
  { to: '/market',            label: 'Dashboard',      end: true },
  { to: '/market/briefing',   label: 'Briefing',       end: false },
  { to: '/market/portfolio',  label: 'Portfolio',      end: false },
  { to: '/market/hot-stocks', label: 'Hot Stocks',     end: false },
  { to: '/market/analyzer',   label: 'Stock Analyzer', end: false },
]

const ideaLinks = [
  { to: '/ideas', label: 'All Ideas', end: false },
]

function Dropdown({ label, links, isActive }: {
  label: string
  links: { to: string; label: string; end: boolean }[]
  isActive: boolean
}) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handler(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <button
        className={`nav-btn${isActive ? ' nav-btn--active' : ''}`}
        onClick={() => setOpen(o => !o)}
        aria-expanded={open}
      >
        {label}
        <svg width="11" height="11" viewBox="0 0 12 12" fill="none"
          style={{ marginLeft: 2, transition: 'transform .15s', transform: open ? 'rotate(180deg)' : 'none' }}>
          <path d="M2 4l4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      </button>
      {open && (
        <div className="nav-dropdown" onClick={() => setOpen(false)}>
          {links.map(l => (
            <NavLink
              key={l.to}
              to={l.to}
              end={l.end}
              className={({ isActive }) => `nav-dropdown-item${isActive ? ' active' : ''}`}
            >
              {l.label}
            </NavLink>
          ))}
        </div>
      )}
    </div>
  )
}

function SunIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/>
      <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
      <line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/>
      <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
    </svg>
  )
}

function MoonIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
    </svg>
  )
}

export default function Navigation() {
  const location = useLocation()
  const { theme, toggle } = useTheme()
  const isMarket = location.pathname.startsWith('/market')
  const isIdeas  = location.pathname.startsWith('/ideas')

  return (
    <>
      <nav className="nav">
        <div className="nav-inner">
          <Link to="/" className="nav-logo">JK</Link>

          <div className="nav-links">
            <Dropdown label="Market Tools" links={marketLinks} isActive={isMarket} />
            <Dropdown label="Ideas"        links={ideaLinks}   isActive={isIdeas} />
          </div>

          <button
            onClick={toggle}
            className="theme-toggle"
            title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
          >
            {theme === 'dark' ? <SunIcon /> : <MoonIcon />}
            <span style={{ fontSize: '.75rem' }}>{theme === 'dark' ? 'Light' : 'Dark'}</span>
          </button>
        </div>
      </nav>

      <style>{`
        .nav {
          position: sticky; top: 0; z-index: 100;
          background: rgba(var(--nav-bg, 255,255,255), .92);
          backdrop-filter: blur(12px);
          border-bottom: 1px solid var(--border);
        }
        [data-theme="dark"] .nav { background: rgba(10,10,10,.92); }

        .nav-inner {
          max-width: 1200px; margin: 0 auto; padding: 0 1.5rem;
          height: 52px; display: flex; align-items: center; gap: 1rem;
        }
        .nav-logo {
          font-size: 1rem; font-weight: 800; color: var(--accent);
          letter-spacing: -.5px; margin-right: .5rem;
        }
        .nav-links { display: flex; align-items: center; gap: .15rem; flex: 1; }

        .nav-btn {
          display: flex; align-items: center; gap: .3rem;
          padding: .35rem .7rem; border-radius: var(--radius-sm);
          font-size: .875rem; font-weight: 500;
          background: none; border: none;
          color: var(--text-secondary);
          transition: background .14s, color .14s;
        }
        .nav-btn:hover    { background: var(--bg-tertiary); color: var(--text-primary); }
        .nav-btn--active  { color: var(--accent); }

        .nav-dropdown {
          position: absolute; top: calc(100% + .5rem); left: 0;
          background: var(--bg-elevated);
          border: 1px solid var(--border);
          border-radius: var(--radius-sm);
          box-shadow: var(--shadow);
          min-width: 180px; overflow: hidden;
          animation: fadeIn .15s ease;
        }
        .nav-dropdown-item {
          display: block; padding: .6rem 1rem;
          font-size: .875rem; color: var(--text-secondary);
          transition: background .1s, color .1s;
        }
        .nav-dropdown-item:hover { background: var(--bg-tertiary); color: var(--text-primary); }
        .nav-dropdown-item.active { color: var(--accent); font-weight: 600; background: var(--accent-lt); }

        .theme-toggle {
          display: flex; align-items: center; gap: .35rem;
          padding: .35rem .7rem; border-radius: var(--radius-sm);
          background: none; border: 1px solid var(--border);
          color: var(--text-secondary); font-size: .8rem;
          transition: border-color .14s, color .14s;
          white-space: nowrap;
        }
        .theme-toggle:hover { color: var(--accent); border-color: var(--accent); }
      `}</style>
    </>
  )
}
