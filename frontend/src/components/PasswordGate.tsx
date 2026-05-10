import { useState, useEffect, type ReactNode } from 'react'

const STORAGE_KEY = 'mt_auth'
const PASSWORD    = 'Bookrun2026'

export default function PasswordGate({ children }: { children: ReactNode }) {
  const [unlocked, setUnlocked] = useState(false)
  const [input, setInput]       = useState('')
  const [error, setError]       = useState(false)
  const [shake, setShake]       = useState(false)

  useEffect(() => {
    if (localStorage.getItem(STORAGE_KEY) === '1') setUnlocked(true)
  }, [])

  function submit(e: React.FormEvent) {
    e.preventDefault()
    if (input === PASSWORD) {
      localStorage.setItem(STORAGE_KEY, '1')
      setUnlocked(true)
    } else {
      setError(true)
      setShake(true)
      setTimeout(() => setShake(false), 500)
    }
  }

  if (unlocked) return <>{children}</>

  return (
    <div style={{
      minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'var(--bg-secondary)', padding: '1rem',
    }}>
      <div className="card" style={{ width: '100%', maxWidth: 360, textAlign: 'center' }}>
        <p style={{ fontSize: '2rem', marginBottom: '.75rem' }}>🔒</p>
        <h1 style={{ fontSize: '1.15rem', fontWeight: 700, marginBottom: '.35rem' }}>Private Access</h1>
        <p style={{ fontSize: '.875rem', color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
          Enter password to continue.
        </p>

        <form onSubmit={submit} style={{ display: 'flex', flexDirection: 'column', gap: '.75rem' }}>
          <input
            type="password"
            value={input}
            onChange={e => { setInput(e.target.value); setError(false) }}
            placeholder="Password"
            autoFocus
            style={{
              padding: '.6rem .8rem',
              border: `1px solid ${error ? 'var(--negative)' : 'var(--border)'}`,
              borderRadius: 'var(--radius-sm)',
              fontSize: '1rem',
              outline: 'none',
              background: 'var(--bg-tertiary)',
              color: 'var(--text-primary)',
              animation: shake ? 'shake .4s ease' : 'none',
              textAlign: 'center',
            }}
          />
          {error && <p style={{ fontSize: '.8rem', color: 'var(--negative)' }}>Incorrect password</p>}
          <button type="submit" className="btn btn-primary" style={{ justifyContent: 'center' }}>
            Unlock
          </button>
        </form>
      </div>

      <style>{`
        @keyframes shake {
          0%,100% { transform: translateX(0); }
          20%,60%  { transform: translateX(-6px); }
          40%,80%  { transform: translateX(6px); }
        }
      `}</style>
    </div>
  )
}
