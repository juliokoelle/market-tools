import { useEffect, useRef, useState, useCallback } from 'react'
import { getPortfolio, savePortfolio, analyzePortfolio, getMarketPrices, getMarketNames, getStockDetail, searchTickers, getStockWatchlist, addStockToWatchlist, removeStockFromWatchlist, getAllocation, type Position, type PortfolioAnalysis, type StockDetail, type AllocationData, type AllocSlice } from '../services/api'
import { DonutSvg } from '../components/DonutSvg'
import { parseNum } from '../lib/parseNum'
import { normalizeTicker } from '../lib/ticker'

function isIsin(s: string) { return /^[A-Z]{2}[A-Z0-9]{9}[0-9]$/.test(s) }

function normalizeHeader(h: string) {
  return h.toLowerCase()
    .replace(/ø/g, 'o').replace(/ü/g, 'ue').replace(/ä/g, 'ae').replace(/ö/g, 'oe').replace(/ß/g, 'ss')
    .replace(/['"]/g, '').replace(/\s+/g, ' ').trim()
}

function parseTRCsv(text: string): { rows: Position[]; hasIsins: boolean; debugHeaders: string[] } {
  const clean = text.replace(/^﻿/, '').trim()
  const lines = clean.split(/\r?\n/)
  if (lines.length < 2) return { rows: [], hasIsins: false, debugHeaders: [] }
  const sep = lines[0].includes(';') ? ';' : ','
  const rawHeaders = lines[0].split(sep).map(h => h.replace(/^"|"$/g, '').trim())
  const headers = rawHeaders.map(normalizeHeader)

  const col = (names: string[]) => names.map(n => headers.indexOf(n)).find(i => i >= 0) ?? -1
  const colPartial = (frags: string[]) => { for (const f of frags) { const i = headers.findIndex(h => h.includes(f)); if (i >= 0) return i } return -1 }

  // TR transaction export: has category + type + symbol columns
  const categoryCol = col(['category'])
  const typeCol     = col(['type'])
  const symbolCol   = col(['symbol'])
  const nameCol     = col(['name', 'titel', 'wertpapier', 'bezeichnung', 'security', 'title'])
  const sharesCol   = col(['shares', 'menge', 'anzahl', 'quantity', 'stucke', 'stuck', 'stueck', 'stk'])
  const priceCol    = col(['price', 'kurs']) >= 0
    ? col(['price', 'kurs'])
    : colPartial(['einstandspreis', 'kaufkurs', 'kaufpreis', 'avg price'])

  const isTrTransactionFormat = categoryCol >= 0 && typeCol >= 0 && symbolCol >= 0

  if (isTrTransactionFormat) {
    type AggEntry = { name: string; totalShares: number; totalCost: number; buyShares: number }
    const agg: Record<string, AggEntry> = {}

    for (const line of lines.slice(1)) {
      if (!line.trim()) continue
      const cells    = line.split(sep).map(c => c.replace(/^"|"$/g, '').trim())
      const category = cells[categoryCol]?.toUpperCase() ?? ''
      const txType   = cells[typeCol]?.toUpperCase() ?? ''
      const isin     = cells[symbolCol]?.toUpperCase().replace(/\s/g, '') ?? ''

      if (!isin || !isIsin(isin)) continue // skip cash rows, BTC, etc.

      const isTrading            = category === 'TRADING' && (txType === 'BUY' || txType === 'SELL')
      const isShareCorpAction    = category === 'CORPORATE_ACTION' && cells[sharesCol]?.trim() !== ''
      if (!isTrading && !isShareCorpAction) continue

      const shares = parseNum(cells[sharesCol] ?? '')
      const price  = priceCol >= 0 ? parseNum(cells[priceCol] ?? '') : NaN
      if (isNaN(shares) || shares === 0) continue

      if (!agg[isin]) agg[isin] = { name: cells[nameCol] ?? isin, totalShares: 0, totalCost: 0, buyShares: 0 }
      agg[isin].totalShares += shares
      if (txType === 'BUY' && !isNaN(price) && shares > 0) {
        agg[isin].totalCost += shares * price
        agg[isin].buyShares += shares
      }
    }

    const rows: Position[] = Object.entries(agg)
      .filter(([, e]) => e.totalShares > 0.0001)
      .map(([isin, e]) => ({
        ticker:     isin,
        investment: parseFloat(e.totalCost.toFixed(2)),
        shares:     parseFloat(e.totalShares.toFixed(6)),
        avg_buy:    e.buyShares > 0 ? parseFloat((e.totalCost / e.buyShares).toFixed(4)) : undefined,
      }))

    return { rows, hasIsins: true, debugHeaders: rawHeaders }
  }

  // Fallback: snapshot format (one row = one position)
  const isinCol   = col(['isin', 'isin_code', 'wertpapier_id'])
  const investCol = col(['einstandswert', 'invested', 'investment', 'investiert', 'einstand'])
  const idCol     = isinCol >= 0 ? isinCol : (nameCol >= 0 ? nameCol : col(['ticker', 'symbol', 'wkn']))
  if (idCol < 0) return { rows: [], hasIsins: false, debugHeaders: rawHeaders }

  const rows = lines.slice(1).flatMap(line => {
    if (!line.trim()) return []
    const cells   = line.split(sep).map(c => c.replace(/^"|"$/g, '').trim())
    const ticker  = cells[idCol]?.toUpperCase().replace(/\s/g, '') ?? ''
    if (!ticker) return []
    const shares  = sharesCol >= 0 ? parseNum(cells[sharesCol] ?? '') : NaN
    const avg_buy = priceCol  >= 0 ? parseNum(cells[priceCol]  ?? '') : NaN
    const invest  = investCol >= 0 ? parseNum(cells[investCol] ?? '') : NaN
    const investment = !isNaN(invest) ? invest : (!isNaN(shares) && !isNaN(avg_buy) ? shares * avg_buy : 0)
    return [{ ticker, investment, shares: isNaN(shares) ? undefined : shares, avg_buy: isNaN(avg_buy) ? undefined : avg_buy }] as Position[]
  })

  return { rows, hasIsins: rows.some(r => isIsin(r.ticker)), debugHeaders: rawHeaders }
}

function LivePnlCard({ positions, prices }: { positions: Position[]; prices: Record<string, { price: number; change_pct: number }> }) {
  const rows = positions.filter(p => p.ticker && p.shares && p.avg_buy)
  if (!rows.length) return null
  let totalCost = 0, totalValue = 0
  const items = rows.map(p => {
    const cost = (p.shares ?? 0) * (p.avg_buy ?? 0)
    const curr = prices[p.ticker]?.price ?? 0
    const value = curr > 0 ? curr * (p.shares ?? 0) : cost
    totalCost += cost; totalValue += value
    const pnl = curr > 0 ? value - cost : 0
    const pnlPct = cost > 0 && curr > 0 ? (pnl / cost) * 100 : 0
    return { ticker: p.ticker, shares: p.shares ?? 0, avg_buy: p.avg_buy ?? 0, curr, value, pnl, pnlPct }
  })
  const totalPnl = totalValue - totalCost
  const totalPnlPct = totalCost > 0 ? (totalPnl / totalCost) * 100 : 0
  return (
    <div className="card" style={{ marginBottom: '1.5rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
        <h2 style={{ fontSize: '1rem', fontWeight: 700 }}>Live P&L</h2>
        <div style={{ textAlign: 'right' }}>
          <p style={{ fontSize: '1.3rem', fontWeight: 800, color: totalPnl >= 0 ? 'var(--positive)' : 'var(--negative)' }}>
            {totalPnl >= 0 ? '+' : ''}€{totalPnl.toLocaleString('de-DE', { maximumFractionDigits: 0 })}
          </p>
          <p style={{ fontSize: '.75rem', fontWeight: 600, color: totalPnlPct >= 0 ? 'var(--positive)' : 'var(--negative)' }}>
            {totalPnlPct >= 0 ? '+' : ''}{totalPnlPct.toFixed(2)}% · Depot €{totalValue.toLocaleString('de-DE', { maximumFractionDigits: 0 })}
          </p>
        </div>
      </div>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '.875rem' }}>
          <thead>
            <tr style={{ borderBottom: '2px solid var(--border)' }}>
              {['Ticker', 'Stück', 'Ø Kauf', 'Kurs', 'Wert', 'P&L', '+/-%'].map(h => (
                <th key={h} style={{ textAlign: 'left', padding: '.35rem .5rem', fontSize: '.65rem', fontWeight: 700, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '.04em' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {items.map(it => (
              <tr key={it.ticker} style={{ borderBottom: '1px solid var(--border)' }}>
                <td style={{ padding: '.45rem .5rem', fontWeight: 700, color: 'var(--teal)' }}>{it.ticker}</td>
                <td style={{ padding: '.45rem .5rem', color: 'var(--text-2)' }}>{it.shares}</td>
                <td style={{ padding: '.45rem .5rem', color: 'var(--text-2)' }}>€{it.avg_buy.toFixed(2)}</td>
                <td style={{ padding: '.45rem .5rem', fontWeight: 600 }}>{it.curr > 0 ? `$${it.curr.toFixed(2)}` : <span style={{ color: 'var(--text-3)' }}>···</span>}</td>
                <td style={{ padding: '.45rem .5rem' }}>{it.curr > 0 ? `€${it.value.toLocaleString('de-DE', { maximumFractionDigits: 0 })}` : '—'}</td>
                <td style={{ padding: '.45rem .5rem', fontWeight: 700, color: it.pnl >= 0 ? 'var(--positive)' : 'var(--negative)' }}>{it.curr > 0 ? `${it.pnl >= 0 ? '+' : ''}€${it.pnl.toFixed(0)}` : '—'}</td>
                <td style={{ padding: '.45rem .5rem', fontSize: '.8rem', fontWeight: 700, color: it.pnlPct >= 0 ? 'var(--positive)' : 'var(--negative)' }}>{it.curr > 0 ? `${it.pnlPct >= 0 ? '+' : ''}${it.pnlPct.toFixed(1)}%` : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

const UNIVERSE = [
  "AAPL","MSFT","NVDA","GOOG","META","AVGO","AMD","ORCL","CRM","ADBE",
  "INTC","QCOM","TXN","IBM","NOW","SNOW","PLTR","MU","AMAT","LRCX",
  "AMZN","TSLA","HD","MCD","NKE","SBUX","BKNG","LOW","TGT","ABNB",
  "EBAY","GM","F","UBER","LYFT","NFLX","DIS","CMCSA","T","VZ",
  "TMUS","SNAP","PINS","BRK-B","JPM","BAC","WFC","GS","MS","C",
  "AXP","BLK","SCHW","V","MA","PYPL","COF","JNJ","LLY","UNH",
  "PFE","ABBV","MRK","TMO","ABT","DHR","AMGN","GILD","ISRG","CVS",
  "HUM","CAT","HON","GE","BA","LMT","RTX","DE","UPS","FDX",
  "CSX","NSC","XOM","CVX","COP","SLB","EOG","PSX","MPC","PG",
  "KO","PEP","COST","WMT","PM","MO","CL","LIN","APD","FCX",
  "NEM","DOW","AMT","PLD","EQIX","SPG","NEE","DUK","SO","D",
  "VWCE.DE","4GLD.DE","ASML","SAP","BAYN.DE","BMW.DE","SIE.DE",
]

const PORTFOLIO_SEED: Position[] = [
  { ticker: "VWCE.DE", investment: 350 },
  { ticker: "NVDA",    investment: 180 },
  { ticker: "ASML",    investment: 180 },
  { ticker: "AVGO",    investment: 170 },
  { ticker: "GOOGL",   investment: 120 },
]

const SEED_KEY       = 'mt_portfolio_seed_seen'
const POSITIONS_KEY  = 'mt_portfolio_v2'

interface TickerSuggestion { ticker: string; name: string }

function TickerInput({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const [suggestions, setSuggestions] = useState<TickerSuggestion[]>([])
  const [activeIdx, setActiveIdx] = useState(-1)
  const ref = useRef<HTMLDivElement>(null)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const runSearch = useCallback((q: string) => {
    if (!q.trim()) { setSuggestions([]); setActiveIdx(-1); return }
    const upper = q.toUpperCase()
    const local = UNIVERSE
      .filter(t => t.startsWith(upper))
      .slice(0, 5)
      .map(t => ({ ticker: t, name: t }))
    setSuggestions(local)
    setActiveIdx(-1)

    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      searchTickers(q).then(results => {
        const remote = results.map(r => ({ ticker: r.ticker, name: r.name }))
        setSuggestions(prev => {
          const seen = new Set(prev.map(s => s.ticker))
          return [...prev, ...remote.filter(r => !seen.has(r.ticker))].slice(0, 8)
        })
      }).catch(() => {})
    }, 320)
  }, [])

  function pick(ticker: string) {
    onChange(ticker)
    setSuggestions([])
    setActiveIdx(-1)
  }

  useEffect(() => {
    function handler(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setSuggestions([])
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <input
        value={value}
        onChange={e => { onChange(e.target.value.toUpperCase().replace(/\s/g, '')); runSearch(e.target.value) }}
        onKeyDown={e => {
          if (!suggestions.length) return
          if (e.key === 'ArrowDown') { e.preventDefault(); setActiveIdx(i => Math.min(i + 1, suggestions.length - 1)) }
          else if (e.key === 'ArrowUp') { e.preventDefault(); setActiveIdx(i => Math.max(i - 1, -1)) }
          else if (e.key === 'Enter' && activeIdx >= 0) { e.preventDefault(); pick(suggestions[activeIdx].ticker) }
          else if (e.key === 'Escape') setSuggestions([])
        }}
        placeholder="Ticker or company name…"
        autoComplete="off"
        spellCheck={false}
        style={inputStyle}
      />
      {suggestions.length > 0 && (
        <ul className="dropdown-list" style={{
          position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 50,
          background: 'var(--surface)', border: '1px solid var(--border)',
          borderRadius: 'var(--radius-sm)', boxShadow: 'var(--shadow)',
          listStyle: 'none', margin: 0, padding: '.25rem 0',
        }}>
          {suggestions.map((s, i) => (
            <li key={s.ticker}
              onMouseDown={e => { e.preventDefault(); pick(s.ticker) }}
              style={{
                padding: '.4rem .75rem', fontSize: '.85rem', cursor: 'pointer',
                background: i === activeIdx ? 'var(--teal-light)' : 'transparent',
                color: i === activeIdx ? 'var(--teal)' : 'var(--text)',
                display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '.5rem',
              }}
            >
              <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: i === activeIdx ? 'var(--teal)' : 'var(--text-2)' }}>{s.name !== s.ticker ? s.name : ''}</span>
              <span style={{ fontWeight: 700, flexShrink: 0 }}>{s.ticker}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function SeedModal({ onAccept, onDecline }: { onAccept: () => void; onDecline: () => void }) {
  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,.5)', zIndex: 200, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '1rem' }}>
      <div className="card" style={{ width: '100%', maxWidth: 380 }}>
        <h3 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: '.4rem' }}>Start with a demo portfolio?</h3>
        <p style={{ fontSize: '.875rem', color: 'var(--text-2)', lineHeight: 1.6, marginBottom: '1.25rem' }}>
          Load a sample portfolio to explore the analysis features.
        </p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '.25rem', marginBottom: '1.25rem', fontSize: '.8rem' }}>
          {PORTFOLIO_SEED.map(p => (
            <div key={p.ticker} style={{ display: 'flex', justifyContent: 'space-between', padding: '.25rem 0', borderBottom: '1px solid var(--border)' }}>
              <span style={{ fontWeight: 700 }}>{p.ticker}</span>
              <span style={{ color: 'var(--text-2)' }}>€{p.investment}</span>
            </div>
          ))}
        </div>
        <div style={{ display: 'flex', gap: '.75rem' }}>
          <button onClick={onAccept} className="btn btn-primary" style={{ flex: 1, justifyContent: 'center' }}>Load demo</button>
          <button onClick={onDecline} className="btn btn-outline" style={{ flex: 1, justifyContent: 'center' }}>Skip</button>
        </div>
      </div>
    </div>
  )
}

function TransferModal({ ticker, price, onConfirm, onCancel }: {
  ticker: string; price: number
  onConfirm: (amount: number) => void; onCancel: () => void
}) {
  const [amount, setAmount] = useState('')
  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,.5)', zIndex: 200, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '1rem' }}>
      <div className="card" style={{ width: '100%', maxWidth: 340 }}>
        <h3 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: '.25rem' }}>Add {ticker} to Portfolio</h3>
        {price > 0 && (
          <p style={{ fontSize: '.8rem', color: 'var(--text-2)', marginBottom: '1rem' }}>
            Current price: ${price.toFixed(2)}
          </p>
        )}
        <label style={labelStyle}>Investment amount (€)</label>
        <input
          autoFocus
          type="number"
          min="1"
          value={amount}
          onChange={e => setAmount(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter') { const n = parseFloat(amount); if (n > 0) onConfirm(n) } }}
          placeholder="e.g. 500"
          style={{ ...inputStyle, marginTop: '.35rem', marginBottom: '1rem' }}
        />
        <div style={{ display: 'flex', gap: '.75rem' }}>
          <button
            onClick={() => { const n = parseFloat(amount); if (n > 0) onConfirm(n) }}
            className="btn btn-primary" style={{ flex: 1, justifyContent: 'center' }}
          >Add to Portfolio</button>
          <button onClick={onCancel} className="btn btn-outline" style={{ flex: 1, justifyContent: 'center' }}>Cancel</button>
        </div>
      </div>
    </div>
  )
}

function HoldingDetailModal({ ticker, onClose }: { ticker: string; onClose: () => void }) {
  const [detail, setDetail] = useState<StockDetail | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    getStockDetail(ticker).then(setDetail).catch(() => {}).finally(() => setLoading(false))
  }, [ticker])

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,.45)', zIndex: 200, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '1rem' }} onClick={onClose}>
      <div style={{ background: 'var(--surface)', borderRadius: 'var(--radius)', width: '100%', maxWidth: 480, padding: '1.5rem' }} onClick={e => e.stopPropagation()}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem' }}>
          <div>
            <h2 style={{ fontSize: '1.2rem', fontWeight: 700 }}>{ticker}</h2>
            {detail && <p style={{ fontSize: '.85rem', color: 'var(--text-3)' }}>{detail.name} · {detail.sector}</p>}
          </div>
          <button onClick={onClose} style={{ background: 'none', border: 'none', fontSize: '1.5rem', color: 'var(--text-3)', cursor: 'pointer' }}>×</button>
        </div>
        {loading && <p style={{ textAlign: 'center', color: 'var(--text-3)', fontSize: '.875rem', padding: '1.5rem 0' }}>Loading…</p>}
        {detail && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '.5rem' }}>
            {[
              { label: 'Price',      value: `$${detail.price.toFixed(2)}` },
              { label: 'Bull Score', value: String(detail.bull_score) },
              { label: 'Change',     value: `${detail.change_pct >= 0 ? '+' : ''}${detail.change_pct.toFixed(2)}%`, color: detail.change_pct >= 0 ? '#059669' : '#dc2626' },
              { label: 'P/E Ratio',  value: detail.pe_ratio?.toFixed(1) ?? '—' },
              { label: 'Market Cap', value: detail.market_cap ? `$${(detail.market_cap / 1e9).toFixed(1)}B` : '—' },
              { label: '52W High',   value: `$${detail.week_52_high?.toFixed(2) ?? '—'}` },
              { label: '52W Low',    value: `$${detail.week_52_low?.toFixed(2) ?? '—'}` },
              { label: 'Sector',     value: detail.sector ?? '—' },
            ].map(m => (
              <div key={m.label} style={{ padding: '.55rem .65rem', background: 'var(--surface-alt)', borderRadius: 6 }}>
                <p style={{ fontSize: '.68rem', color: 'var(--text-3)', marginBottom: '.1rem', textTransform: 'uppercase', letterSpacing: '.03em' }}>{m.label}</p>
                <p style={{ fontWeight: 700, fontSize: '.9rem', color: (m as any).color ?? 'var(--text)' }}>{m.value}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default function Portfolio() {
  const [tab, setTab] = useState<'holdings' | 'watchlist'>('holdings')

  // ── Holdings ──
  const [positions, setPositions] = useState<Position[]>(() => {
    try {
      const saved = localStorage.getItem(POSITIONS_KEY)
      if (saved) {
        const parsed = JSON.parse(saved)
        if (Array.isArray(parsed) && parsed.length > 0) return parsed
      }
    } catch {}
    return PORTFOLIO_SEED
  })
  const [analysis, setAnalysis]   = useState<PortfolioAnalysis | null>(() => {
    try { return JSON.parse(sessionStorage.getItem('mt_portfolio_analysis') ?? 'null') } catch { return null }
  })
  const [saving, setSaving]             = useState(false)
  const [analyzing, setAnalyzing]       = useState(false)
  const [csvResolving, setCsvResolving] = useState(false)
  const [showSeed, setShowSeed]         = useState(false)

  // ── Watchlist (backed by /stock-watchlist API) ──
  const [watchlist, setWatchlist] = useState<string[]>([])
  const [watchLoading, setWatchLoading] = useState(true)
  const [watchPrices, setWatchPrices] = useState<Record<string, { price: number; change_pct: number }>>({})
  const [watchNames, setWatchNames]   = useState<Record<string, string>>({})
  const [watchInput, setWatchInput]   = useState('')
  const watchInputRef = useRef<HTMLDivElement>(null)
  const [transferTicker, setTransferTicker] = useState<{ ticker: string; price: number } | null>(null)

  // ── Detail modal ──
  const [detailTicker, setDetailTicker] = useState<string | null>(null)

  // ── Allocation (by holding / sector / continent / market) ──
  const [alloc, setAlloc] = useState<AllocationData | null>(null)

  // ── Live holding prices (for P&L) ──
  const [holdingPrices, setHoldingPrices] = useState<Record<string, { price: number; change_pct: number }>>({})
  const csvInputRef = useRef<HTMLInputElement>(null)

  // ── Toast ──
  const [toast, setToast] = useState('')
  function showToast(msg: string, ms = 3000) { setToast(msg); setTimeout(() => setToast(''), ms) }

  // Persist + load positions
  useEffect(() => {
    if (positions.length > 0) localStorage.setItem(POSITIONS_KEY, JSON.stringify(positions))
  }, [positions])

  // Load live prices for holdings
  useEffect(() => {
    const tickers = positions.filter(p => p.ticker).map(p => p.ticker)
    if (!tickers.length) return
    getMarketPrices(tickers.join(',')).then(setHoldingPrices).catch(() => {})
  }, [positions])

  // Load allocation breakdown (weighted by invested €, consistent currency)
  useEffect(() => {
    const holdings = positions
      .filter(p => p.ticker && p.investment > 0)
      .map(p => ({ ticker: p.ticker, value: p.investment }))
    if (!holdings.length) { setAlloc(null); return }
    getAllocation(holdings).then(setAlloc).catch(() => setAlloc(null))
  }, [positions])

  // The GitHub-backed server store is the cross-device source of truth (written
  // on every Save). localStorage is only an offline cache / first-paint buffer —
  // it must NOT win over the server, otherwise updates from another device never
  // surface (was the "Daten nicht aktualisiert" bug).
  useEffect(() => {
    getPortfolio()
      .then(d => {
        if (d.positions?.length) {
          setPositions(d.positions)
          localStorage.setItem(POSITIONS_KEY, JSON.stringify(d.positions))
        } else if (!localStorage.getItem(POSITIONS_KEY) && !localStorage.getItem(SEED_KEY)) {
          setShowSeed(true)
        }
      })
      .catch(() => {
        if (!localStorage.getItem(POSITIONS_KEY) && !localStorage.getItem(SEED_KEY)) {
          setShowSeed(true)
        }
      })
  }, [])

  // Load watchlist from API on mount
  useEffect(() => {
    getStockWatchlist()
      .then(items => setWatchlist(items.map(i => i.ticker)))
      .catch(() => setWatchlist([]))
      .finally(() => setWatchLoading(false))
  }, [])

  useEffect(() => {
    if (!watchlist.length) return
    getMarketNames(watchlist).then(setWatchNames).catch(() => {})
  }, [watchlist])

  useEffect(() => {
    if (!watchlist.length) return
    const load = () => getMarketPrices(watchlist.join(',')).then(setWatchPrices).catch(() => {})
    load()
    const id = setInterval(load, 60_000)
    return () => clearInterval(id)
  }, [watchlist])

  // Holdings helpers
  function addRow()                                 { setPositions(p => [...p, { ticker: '', investment: 0 }]) }
  function removeRow(i: number)                     { setPositions(p => p.filter((_, j) => j !== i)) }
  function updateTicker(i: number, v: string)       { setPositions(p => p.map((r, j) => j === i ? { ...r, ticker: v } : r)) }
  function updateInvestment(i: number, v: number)   { setPositions(p => p.map((r, j) => j === i ? { ...r, investment: v } : r)) }
  function updateShares(i: number, raw: string) {
    const v = parseNum(raw)
    setPositions(p => p.map((r, j) => {
      if (j !== i) return r
      const shares = Number.isNaN(v) ? undefined : v
      const investment = shares != null && r.avg_buy != null
        ? parseFloat((shares * r.avg_buy).toFixed(2)) : r.investment
      return { ...r, shares, investment }
    }))
  }
  function updateAvgBuy(i: number, raw: string) {
    const v = parseNum(raw)
    setPositions(p => p.map((r, j) => {
      if (j !== i) return r
      const avg_buy = Number.isNaN(v) ? undefined : v
      const investment = avg_buy != null && r.shares != null
        ? parseFloat((avg_buy * r.shares).toFixed(2)) : r.investment
      return { ...r, avg_buy, investment }
    }))
  }

  function handleCsvImport(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = async ev => {
      const text = ev.target?.result as string
      const { rows, hasIsins, debugHeaders } = parseTRCsv(text)
      if (!rows.length) {
        const hint = debugHeaders.length ? ` (Spalten: ${debugHeaders.slice(0, 5).join(', ')})` : ''
        showToast(`CSV nicht erkannt${hint}`, 6000)
        return
      }
      if (hasIsins) {
        setCsvResolving(true)
        showToast(`ISINs erkannt — ${rows.length} Ticker werden aufgelöst…`, 10000)
        const resolved = await Promise.all(rows.map(async r => {
          if (!isIsin(r.ticker)) return r
          try {
            const results = await searchTickers(r.ticker)
            return results.length ? { ...r, ticker: results[0].ticker } : r
          } catch { return r }
        }))
        setCsvResolving(false)
        localStorage.setItem(SEED_KEY, '1')
        setPositions(resolved)
        const stillIsins = resolved.filter(r => isIsin(r.ticker)).length
        showToast(stillIsins
          ? `${resolved.length} Positionen importiert — ${stillIsins} ISINs nicht aufgelöst, bitte manuell korrigieren`
          : `${resolved.length} Positionen importiert`, 5000)
      } else {
        localStorage.setItem(SEED_KEY, '1')
        setPositions(rows)
        showToast(`${rows.length} Positionen importiert`)
      }
    }
    reader.readAsText(file, 'UTF-8')
    if (csvInputRef.current) csvInputRef.current.value = ''
  }

  function acceptSeed() {
    localStorage.setItem(SEED_KEY, '1')
    setShowSeed(false)
    setPositions(PORTFOLIO_SEED)
  }
  function declineSeed() {
    localStorage.setItem(SEED_KEY, '1')
    setShowSeed(false)
    setPositions([{ ticker: '', investment: 0 }])
  }

  async function handleSave() {
    setSaving(true)
    const cleaned = positions
      .filter(p => p.ticker)
      .map(p => ({ ...p, ticker: normalizeTicker(p.ticker) }))
    try {
      await savePortfolio(cleaned)
      setPositions(prev => prev.map(p => p.ticker ? { ...p, ticker: normalizeTicker(p.ticker) } : p))
      showToast('Portfolio saved')
    }
    catch { showToast('Save failed') }
    finally { setSaving(false) }
  }

  async function handleAnalyze() {
    const valid = positions.filter(p => p.ticker && p.investment > 0)
    if (!valid.length) { showToast('Add at least one ticker with an investment amount'); return }
    setAnalyzing(true)
    try {
      const result = await analyzePortfolio(valid)
      setAnalysis(result)
      sessionStorage.setItem('mt_portfolio_analysis', JSON.stringify(result))
    }
    catch (err) {
      const isNetwork = err instanceof TypeError
      showToast(isNetwork
        ? 'Backend is waking up — wait 30 s and try again'
        : 'Analysis failed — check your tickers and try again', isNetwork ? 6000 : 3000)
    }
    finally { setAnalyzing(false) }
  }

  // Watchlist helpers (API-backed)
  async function addToWatchlist(ticker: string) {
    const t = ticker.trim().toUpperCase()
    if (!t || watchlist.includes(t)) { setWatchInput(''); return }
    try {
      await addStockToWatchlist(t)
      setWatchlist(w => [...w, t])
    } catch { showToast('Failed to add ticker') }
    setWatchInput('')
  }

  async function removeFromWatchlist(ticker: string) {
    try {
      await removeStockFromWatchlist(ticker)
      setWatchlist(w => w.filter(t => t !== ticker))
    } catch { showToast('Failed to remove ticker') }
  }

  function confirmTransfer(amount: number) {
    if (!transferTicker) return
    const { ticker } = transferTicker
    setPositions(p => {
      const idx = p.findIndex(x => x.ticker === ticker)
      if (idx >= 0) return p.map((x, i) => i === idx ? { ...x, investment: x.investment + amount } : x)
      return [...p, { ticker, investment: amount }]
    })
    removeFromWatchlist(ticker)
    setTransferTicker(null)
    setTab('holdings')
    showToast(`${ticker} moved to portfolio`)
  }

  const portfolioTickers = new Set(positions.map(p => p.ticker))

  return (
    <main className="page page-enter">
      <div className="page-header">
        <h1 className="page-title">Portfolio</h1>
      </div>

      {/* Tabs */}
      <div className="tabs" style={{ marginBottom: '1.5rem' }}>
        <button className={`tab${tab === 'holdings' ? ' active' : ''}`} onClick={() => setTab('holdings')}>
          Holdings
        </button>
        <button className={`tab${tab === 'watchlist' ? ' active' : ''}`} onClick={() => setTab('watchlist')}>
          Watchlist
          {watchlist.length > 0 && (
            <span style={{ marginLeft: '.4rem', fontSize: '.65rem', fontWeight: 700, background: 'var(--teal-light)', color: 'var(--teal)', borderRadius: 999, padding: '.05rem .4rem' }}>
              {watchlist.length}
            </span>
          )}
        </button>
      </div>

      {/* ── Holdings tab ── */}
      {tab === 'holdings' && (
        <>
          <div className="card" style={{ marginBottom: '1.5rem' }}>
            <h2 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: '1rem' }}>Holdings</h2>

            <div style={{ overflowX: 'auto', marginBottom: '.75rem', WebkitOverflowScrolling: 'touch' }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 120px 110px 130px 28px 28px', gap: '.5rem .5rem', minWidth: 480 }}>
              <p style={labelStyle}>Ticker</p>
              <p style={labelStyle}>Stück</p>
              <p style={labelStyle}>Ø Kauf (€)</p>
              <p style={labelStyle}>Investment (€)</p>
              <span /><span />
              {positions.map((p, i) => (
                <>
                  <TickerInput key={`t${i}`} value={p.ticker} onChange={v => updateTicker(i, v)} />
                  <input
                    key={`s${i}`}
                    type="text"
                    inputMode="decimal"
                    defaultValue={p.shares ?? ''}
                    onBlur={e => updateShares(i, e.target.value)}
                    placeholder="z.B. 2,91"
                    style={inputStyle}
                  />
                  <input
                    key={`a${i}`}
                    type="text"
                    inputMode="decimal"
                    defaultValue={p.avg_buy ?? ''}
                    onBlur={e => updateAvgBuy(i, e.target.value)}
                    placeholder="z.B. 162,66"
                    style={inputStyle}
                  />
                  <input
                    key={`v${i}`}
                    type="number"
                    value={p.investment || ''}
                    onChange={e => updateInvestment(i, parseFloat(e.target.value) || 0)}
                    placeholder="5000"
                    style={inputStyle}
                  />
                  <button
                    key={`i${i}`}
                    onClick={() => p.ticker && setDetailTicker(p.ticker)}
                    title="View details"
                    style={{ background: 'none', border: 'none', color: p.ticker ? 'var(--teal)' : 'var(--text-3)', fontSize: '.85rem', cursor: p.ticker ? 'pointer' : 'default', display: 'flex', alignItems: 'center', justifyContent: 'center', opacity: p.ticker ? 1 : 0.3 }}
                  >↗</button>
                  <button
                    key={`d${i}`}
                    onClick={() => removeRow(i)}
                    style={{ background: 'none', border: 'none', color: 'var(--text-3)', fontSize: '1.1rem', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                  >×</button>
                </>
              ))}
            </div>
            </div>

            <div style={{ display: 'flex', gap: '.75rem', flexWrap: 'wrap' }}>
              <button onClick={addRow} className="btn btn-outline" style={{ fontSize: '.8rem' }}>+ Add row</button>
              <button onClick={handleSave} disabled={saving} className="btn btn-outline" style={{ fontSize: '.8rem' }}>
                {saving ? 'Saving…' : '↑ Save'}
              </button>
              <button onClick={() => csvInputRef.current?.click()} disabled={csvResolving} className="btn btn-outline" style={{ fontSize: '.8rem' }} title="CSV aus Trade Republic importieren">
                {csvResolving ? 'Auflösen…' : '↑ CSV Import (TR)'}
              </button>
              <button onClick={handleAnalyze} disabled={analyzing} className="btn btn-primary" style={{ fontSize: '.8rem' }}>
                {analyzing ? 'Analyzing…' : 'Analyze'}
              </button>
              <input ref={csvInputRef} type="file" accept=".csv,.txt" style={{ display: 'none' }} onChange={handleCsvImport} />
            </div>
            <p style={{ fontSize: '.72rem', color: 'var(--text-3)', marginTop: '.5rem' }}>
              TR: Depot → Exportieren → CSV. ISINs werden automatisch in Ticker aufgelöst.
            </p>
          </div>

          <LivePnlCard positions={positions} prices={holdingPrices} />

          {alloc && alloc.byHolding.length > 0 && (
            <div className="card" style={{ marginBottom: '1.5rem' }}>
              <h2 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: '1.25rem' }}>Allocation</h2>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.5rem 2rem' }}>
                <AllocBlock title="By Holding"   slices={alloc.byHolding} />
                <AllocBlock title="By Sector"    slices={alloc.bySector} />
                <AllocBlock title="By Continent" slices={alloc.byContinent} />
                <AllocBlock title="By Market"    slices={alloc.byMarket} />
              </div>

              {/* Regions strip — Developed / Emerging / Diversified / Other */}
              <div style={{ display: 'flex', gap: '2rem', flexWrap: 'wrap', marginTop: '1.5rem', borderTop: '1px solid var(--border)', paddingTop: '1.25rem' }}>
                {alloc.byMarket.map(m => (
                  <div key={m.label}>
                    <p style={{ fontSize: '1.4rem', fontWeight: 800, lineHeight: 1 }}>
                      {m.pct.toFixed(2)}<span style={{ fontSize: '.8rem', fontWeight: 600, color: 'var(--text-3)' }}> %</span>
                    </p>
                    <p style={{ fontSize: '.7rem', color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '.04em', marginTop: '.2rem' }}>{m.label}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {analyzing && (
            <div className="card" style={{ marginBottom: '1.5rem', padding: '2rem', textAlign: 'center' }}>
              <p style={{ color: 'var(--text-3)', fontSize: '.875rem' }}>Running portfolio analysis…</p>
            </div>
          )}

          {analysis && <AnalysisCard a={analysis} />}
        </>
      )}

      {/* ── Watchlist tab ── */}
      {tab === 'watchlist' && (
        <div>
          {/* Add ticker row */}
          <div className="card" style={{ marginBottom: '1rem', padding: '1rem 1.25rem' }}>
            <div style={{ display: 'flex', gap: '.75rem', alignItems: 'center' }}>
              <div ref={watchInputRef} style={{ position: 'relative', flex: 1 }}>
                <input
                  value={watchInput}
                  onChange={e => setWatchInput(e.target.value.toUpperCase().replace(/\s/g, ''))}
                  onKeyDown={e => { if (e.key === 'Enter') addToWatchlist(watchInput) }}
                  placeholder="Search ticker (e.g. AAPL)"
                  autoComplete="off"
                  spellCheck={false}
                  style={inputStyle}
                />
                {watchInput.length >= 1 && (() => {
                  const matches = UNIVERSE.filter(t => t.startsWith(watchInput)).slice(0, 6)
                  if (!matches.length) return null
                  return (
                    <ul className="dropdown-list" style={{
                      position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 50,
                      background: 'var(--surface)', border: '1px solid var(--border)',
                      borderRadius: 'var(--radius-sm)', boxShadow: 'var(--shadow)',
                      listStyle: 'none', margin: 0, padding: '.25rem 0',
                    }}>
                      {matches.map(s => (
                        <li key={s}
                          onMouseDown={e => { e.preventDefault(); addToWatchlist(s) }}
                          style={{ padding: '.4rem .75rem', fontSize: '.875rem', cursor: 'pointer', color: 'var(--text)' }}
                        >{s}</li>
                      ))}
                    </ul>
                  )
                })()}
              </div>
              <button onClick={() => addToWatchlist(watchInput)} className="btn btn-outline" style={{ fontSize: '.8rem', flexShrink: 0 }}>
                + Add
              </button>
            </div>
          </div>

          {/* Watchlist rows */}
          <div className="card table-scroll" style={{ padding: 0 }}>
            {watchLoading ? (
              <p style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-3)', fontSize: '.875rem' }}>Loading…</p>
            ) : watchlist.length === 0 ? (
              <p style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-3)', fontSize: '.875rem' }}>
                Your watchlist is empty. Search for a ticker above to add.
              </p>
            ) : (
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border)' }}>
                    {['Stock', 'Price', 'Change', ''].map(h => (
                      <th key={h} style={{ padding: '.75rem 1.25rem', textAlign: 'left', fontSize: '.65rem', fontWeight: 700, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '.06em' }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {watchlist.map((ticker, i) => {
                    const d = watchPrices[ticker]
                    const inPortfolio = portfolioTickers.has(ticker)
                    return (
                      <tr key={ticker} style={{ borderBottom: i < watchlist.length - 1 ? '1px solid var(--border)' : 'none' }}>
                        <td style={{ padding: '.85rem 1.25rem', fontWeight: 600, fontSize: '.875rem' }}>
                          <a href={`https://finance.yahoo.com/quote/${encodeURIComponent(ticker)}`} target="_blank" rel="noopener noreferrer" style={{ color: 'inherit', textDecoration: 'none' }}>
                            {watchNames[ticker] && watchNames[ticker] !== ticker
                              ? `${watchNames[ticker]} — ${ticker}`
                              : ticker}
                          </a>
                        </td>
                        <td style={{ padding: '.85rem 1.25rem', fontSize: '.9rem', color: 'var(--text-2)' }}>
                          {d ? `$${d.price.toFixed(2)}` : <span style={{ color: 'var(--text-3)' }}>···</span>}
                        </td>
                        <td style={{ padding: '.85rem 1.25rem' }}>
                          {d ? (
                            <span style={{ fontSize: '.8rem', fontWeight: 700, color: d.change_pct >= 0 ? 'var(--positive)' : 'var(--negative)' }}>
                              {d.change_pct >= 0 ? '+' : ''}{d.change_pct.toFixed(2)}%
                            </span>
                          ) : <span style={{ color: 'var(--text-3)', fontSize: '.8rem' }}>···</span>}
                        </td>
                        <td style={{ padding: '.85rem 1.25rem' }}>
                          <div style={{ display: 'flex', gap: '.5rem', justifyContent: 'flex-end' }}>
                            {inPortfolio ? (
                              <span className="badge badge-teal" style={{ fontSize: '.65rem' }}>In Portfolio</span>
                            ) : (
                              <button
                                onClick={() => setTransferTicker({ ticker, price: d?.price ?? 0 })}
                                className="btn btn-outline"
                                style={{ fontSize: '.75rem', padding: '.3rem .65rem' }}
                              >
                                → Portfolio
                              </button>
                            )}
                            <button
                              onClick={() => removeFromWatchlist(ticker)}
                              style={{ background: 'none', border: 'none', color: 'var(--text-3)', fontSize: '1rem', cursor: 'pointer', padding: '.2rem .4rem', borderRadius: 4 }}
                            >×</button>
                          </div>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}

      {detailTicker && <HoldingDetailModal ticker={detailTicker} onClose={() => setDetailTicker(null)} />}

      {showSeed && <SeedModal onAccept={acceptSeed} onDecline={declineSeed} />}

      {transferTicker && (
        <TransferModal
          ticker={transferTicker.ticker}
          price={transferTicker.price}
          onConfirm={confirmTransfer}
          onCancel={() => setTransferTicker(null)}
        />
      )}

      {toast && (
        <div className="toast-container">
          <div className="toast toast-info">{toast}</div>
        </div>
      )}
    </main>
  )
}

function AllocBlock({ title, slices }: { title: string; slices: AllocSlice[] }) {
  return (
    <div>
      <p style={{ ...labelStyle, marginBottom: '.75rem' }}>{title}</p>
      <DonutSvg slices={slices} />
    </div>
  )
}

function AnalysisCard({ a }: { a: PortfolioAnalysis }) {
  const ret    = (a.annualized_return ?? 0) * 100
  const vol    = (a.annualized_volatility ?? 0) * 100
  const div    = (a.diversification_score ?? 0) * 100
  const lgPos  = (a.largest_position ?? 0) * 100
  const riskLabel = vol < 15 ? 'Conservative' : vol < 25 ? 'Moderate' : 'Aggressive'
  const riskColor = vol < 15 ? 'var(--positive)' : vol < 25 ? 'var(--warn)' : 'var(--negative)'

  return (
    <div className="card">
      <h2 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: '1.25rem' }}>Analysis</h2>

      <div className="grid-4" style={{ marginBottom: '1rem' }}>
        {[
          { label: 'Total Value',   value: `€${(a.total_value ?? 0).toLocaleString('de-DE', { maximumFractionDigits: 0 })}`, color: undefined },
          { label: 'Annual Return', value: `${ret >= 0 ? '+' : ''}${ret.toFixed(1)}%`, color: ret >= 0 ? 'var(--positive)' : 'var(--negative)' },
          { label: 'Volatility',   value: `${vol.toFixed(1)}%`, color: undefined },
          { label: 'Risk Profile', value: riskLabel, color: riskColor },
        ].map(m => (
          <div key={m.label} style={{ padding: '.75rem', background: 'var(--surface-alt)', borderRadius: 8 }}>
            <p style={{ fontSize: '.75rem', color: 'var(--text-2)', marginBottom: '.25rem' }}>{m.label}</p>
            <p style={{ fontSize: '1.1rem', fontWeight: 700, color: m.color ?? 'var(--text)' }}>{m.value}</p>
          </div>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '.5rem', marginBottom: '1.25rem' }}>
        {[
          { label: 'Diversification', value: `${div.toFixed(0)}/100` },
          { label: 'Positions',       value: String(a.number_of_positions ?? 0) },
          { label: 'Largest Position', value: `${lgPos.toFixed(1)}%` },
        ].map(m => (
          <div key={m.label} style={{ padding: '.6rem .75rem', background: 'var(--surface-alt)', borderRadius: 8 }}>
            <p style={{ fontSize: '.7rem', color: 'var(--text-2)', marginBottom: '.2rem' }}>{m.label}</p>
            <p style={{ fontSize: '1rem', fontWeight: 700 }}>{m.value}</p>
          </div>
        ))}
      </div>

      {a.commentary && (
        <p style={{ fontSize: '.875rem', color: 'var(--text-2)', lineHeight: 1.7, marginBottom: '1.25rem', padding: '1rem', background: 'var(--teal-light)', borderRadius: 8, borderLeft: `3px solid var(--teal)` }}>
          {a.commentary}
        </p>
      )}

      {a.assets?.length > 0 && (
        <div>
          <p style={{ fontSize: '.75rem', fontWeight: 600, color: 'var(--text-3)', marginBottom: '.5rem', textTransform: 'uppercase', letterSpacing: '.04em' }}>Asset Breakdown</p>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '.875rem' }}>
              <thead>
                <tr>
                  {['Ticker', 'Weight', 'Exp. Return p.a.', 'Volatility p.a.'].map(h => (
                    <th key={h} style={{ textAlign: 'left', padding: '.35rem .5rem', fontSize: '.7rem', fontWeight: 600, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '.04em', borderBottom: '2px solid var(--border)' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {a.assets.map(asset => {
                  const assetRet = (asset.annual_return ?? 0) * 100
                  const assetVol = (asset.volatility ?? 0) * 100
                  return (
                    <tr key={asset.ticker}>
                      <td style={{ padding: '.4rem .5rem', fontWeight: 700, borderBottom: '1px solid var(--border)' }}>
                        <a href={`https://finance.yahoo.com/quote/${encodeURIComponent(asset.ticker)}`} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--teal)', textDecoration: 'none' }}>{asset.ticker}</a>
                      </td>
                      <td style={{ padding: '.4rem .5rem', color: 'var(--text-2)', borderBottom: '1px solid var(--border)' }}>{(asset.weight * 100).toFixed(1)}%</td>
                      <td style={{ padding: '.4rem .5rem', color: assetRet >= 0 ? 'var(--positive)' : 'var(--negative)', fontWeight: 600, borderBottom: '1px solid var(--border)' }}>
                        {assetRet >= 0 ? '+' : ''}{assetRet.toFixed(1)}%
                      </td>
                      <td style={{ padding: '.4rem .5rem', color: 'var(--text-2)', borderBottom: '1px solid var(--border)' }}>{assetVol.toFixed(1)}%</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}

const labelStyle: React.CSSProperties = {
  fontSize: '.75rem', fontWeight: 600, color: 'var(--text-3)',
  textTransform: 'uppercase', letterSpacing: '.04em',
}
const inputStyle: React.CSSProperties = {
  padding: '.45rem .6rem', border: '1px solid var(--border)',
  borderRadius: 6, fontSize: '.875rem', outline: 'none', width: '100%',
  background: 'var(--surface-alt)', color: 'var(--text)',
  fontFamily: 'inherit',
}
