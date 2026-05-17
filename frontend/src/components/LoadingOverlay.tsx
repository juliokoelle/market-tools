import { useEffect, useRef, useState } from 'react'

interface Orb {
  x: number; y: number
  vx: number; vy: number
  r: number
  color: [number, number, number]
  factor: number
  ox: number; oy: number
}

const COLORS: Array<[number, number, number]> = [
  [20, 184, 166],   // teal
  [99, 102, 241],   // indigo
  [244, 63, 94],    // rose
  [139, 92, 246],   // violet
  [6, 182, 212],    // cyan
  [245, 158, 11],   // amber
  [34, 197, 94],    // green
  [249, 115, 22],   // orange
]

function makeOrbs(w: number, h: number): Orb[] {
  return COLORS.map(color => ({
    x: Math.random() * w,
    y: Math.random() * h,
    vx: (Math.random() - 0.5) * 0.6,
    vy: (Math.random() - 0.5) * 0.6,
    r: 80 + Math.random() * 100,
    color,
    factor: 0.025 + Math.random() * 0.04,
    ox: (Math.random() - 0.5) * w * 0.6,
    oy: (Math.random() - 0.5) * h * 0.6,
  }))
}

export function LoadingOverlay({ visible }: { visible: boolean }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const mouse = useRef<{ x: number; y: number } | null>(null)
  const orbsRef = useRef<Orb[]>([])
  const rafRef = useRef(0)
  const [mounted, setMounted] = useState(false)
  const [show, setShow] = useState(false)

  useEffect(() => {
    if (visible) {
      setMounted(true)
      // allow mount to happen, then fade in
      const t = requestAnimationFrame(() => setShow(true))
      return () => cancelAnimationFrame(t)
    } else {
      setShow(false)
      const t = setTimeout(() => setMounted(false), 450)
      return () => clearTimeout(t)
    }
  }, [visible])

  useEffect(() => {
    if (!mounted) return

    const canvas = canvasRef.current
    if (!canvas) return
    const cv = canvas  // stable non-null ref for closures
    const ctx = cv.getContext('2d')!

    function resize() {
      cv.width = window.innerWidth
      cv.height = window.innerHeight
      if (!orbsRef.current.length)
        orbsRef.current = makeOrbs(cv.width, cv.height)
    }
    resize()
    window.addEventListener('resize', resize)

    function onMouse(e: MouseEvent) {
      mouse.current = { x: e.clientX, y: e.clientY }
    }
    window.addEventListener('mousemove', onMouse)

    function tick() {
      const W = cv.width, H = cv.height
      ctx.clearRect(0, 0, W, H)

      for (const orb of orbsRef.current) {
        if (mouse.current) {
          const tx = mouse.current.x + orb.ox
          const ty = mouse.current.y + orb.oy
          orb.x += (tx - orb.x) * orb.factor
          orb.y += (ty - orb.y) * orb.factor
        } else {
          // autonomous drift
          orb.vx += (Math.random() - 0.5) * 0.03
          orb.vy += (Math.random() - 0.5) * 0.03
          orb.vx = Math.max(-0.8, Math.min(0.8, orb.vx))
          orb.vy = Math.max(-0.8, Math.min(0.8, orb.vy))
          orb.x += orb.vx
          orb.y += orb.vy
          if (orb.x < -orb.r) orb.x = W + orb.r
          if (orb.x > W + orb.r) orb.x = -orb.r
          if (orb.y < -orb.r) orb.y = H + orb.r
          if (orb.y > H + orb.r) orb.y = -orb.r
        }

        const [r, g, b] = orb.color
        const g2 = ctx.createRadialGradient(orb.x, orb.y, 0, orb.x, orb.y, orb.r)
        g2.addColorStop(0, `rgba(${r},${g},${b},0.55)`)
        g2.addColorStop(0.5, `rgba(${r},${g},${b},0.18)`)
        g2.addColorStop(1, `rgba(${r},${g},${b},0)`)

        ctx.save()
        ctx.globalCompositeOperation = 'screen'
        ctx.fillStyle = g2
        ctx.beginPath()
        ctx.arc(orb.x, orb.y, orb.r, 0, Math.PI * 2)
        ctx.fill()
        ctx.restore()
      }

      rafRef.current = requestAnimationFrame(tick)
    }
    tick()

    return () => {
      window.removeEventListener('resize', resize)
      window.removeEventListener('mousemove', onMouse)
      cancelAnimationFrame(rafRef.current)
      orbsRef.current = []
    }
  }, [mounted])

  if (!mounted) return null

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 1000,
      background: 'rgba(4, 7, 14, 0.93)',
      opacity: show ? 1 : 0,
      transition: 'opacity 0.35s ease',
      pointerEvents: visible ? 'all' : 'none',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
    }}>
      <canvas ref={canvasRef} style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }} />
      <div style={{ position: 'relative', textAlign: 'center', userSelect: 'none' }}>
        <div style={{
          display: 'inline-block', width: 32, height: 32,
          border: '2px solid rgba(255,255,255,0.15)',
          borderTopColor: 'rgba(20,184,166,0.8)',
          borderRadius: '50%',
          animation: 'spin 0.9s linear infinite',
        }} />
        <p style={{
          marginTop: '.75rem', color: 'rgba(255,255,255,0.35)',
          fontSize: '.7rem', letterSpacing: '.12em', textTransform: 'uppercase',
        }}>Loading</p>
      </div>
    </div>
  )
}
