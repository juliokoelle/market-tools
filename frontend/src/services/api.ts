import { mapHotStock, rankTabs, type RawHotStock } from '../components/market/hot-stocks/hot-data'

const BASE = import.meta.env.VITE_API_URL
  ?? (window.location.hostname === 'localhost'
    ? '/api'
    : 'https://api.juliokoelle.com')

async function get<T>(path: string): Promise<T> {
  const r = await fetch(`${BASE}${path}`)
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`)
  return r.json()
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`)
  return r.json()
}

// Market
export const getMarketPrices = (tickers: string) =>
  get<Record<string, { price: number; change: number; change_pct: number }>>(`/market/prices?tickers=${tickers}`)

export const getHotStocks = () =>
  get<{ stocks?: RawHotStock[] }>('/market/hot-stocks').then(d =>
    rankTabs((d.stocks ?? []).filter(s => s.price != null).map(mapHotStock))
  )

// Briefing
export const getBriefingPreview = () =>
  get<{ preview: string; date: string }>('/briefing/today/preview')

export const getBriefingList = () =>
  get<BriefingMeta[]>('/briefing/list')

export const getBriefing = (date: string) =>
  get<any>(`/briefing/${date}`).then((d: any) => ({
    date: d.date,
    content: d.markdown ?? d.content ?? '',
    html: d.html_render ?? d.html ?? '',
  }))

export const getBriefingCost = () =>
  get<{ monthly_total: number; budget: number; entries: CostEntry[] }>('/briefing/cost-summary')

export const searchTickers = (q: string) =>
  get<Array<{ ticker: string; name: string; exchange: string; type: string }>>(`/market/search-ticker?q=${encodeURIComponent(q)}`)

// Portfolio
export const getPortfolio = () =>
  get<any>('/portfolio').then((d: any) => ({
    positions: (d.positions ?? []).map((p: any): Position => ({
      ticker: p.ticker,
      investment: p.investment ?? p.amount_eur ?? 0,
      shares: p.shares ?? undefined,
      avg_buy: p.avg_buy ?? undefined,
    })),
    total_value: d.total_eur ?? d.total_value ?? 0,
    last_updated: d.last_updated ?? null,
  }))

export const savePortfolio = (positions: Position[]) =>
  post<{ ok: boolean }>('/portfolio', {
    positions: positions.map(p => ({
      ticker: p.ticker,
      amount_eur: p.investment,
      category: 'stock',
      note: '',
      shares: p.shares ?? null,
      avg_buy: p.avg_buy ?? null,
    })),
  })

export const analyzePortfolio = (holdings: Holding[]) =>
  post<PortfolioAnalysis>('/portfolio/analyze', { holdings })

// Allocation (by holding / sector / continent / market)
export interface AllocSlice { label: string; value: number; pct: number }
export interface AllocationData {
  total: number
  byHolding: AllocSlice[]
  bySector: AllocSlice[]
  byContinent: AllocSlice[]
  byMarket: AllocSlice[]
  byCountry: AllocSlice[]
}
export const getAllocation = (holdings: { ticker: string; value: number }[]) =>
  post<AllocationData>('/portfolio/allocation', { holdings })

// Performance — weighted equity curve vs S&P 500
export interface PerfPoint { date: string; value: number; benchmark?: number }
export interface PerfData { period: string; total: number; series: PerfPoint[] }
export const getPortfolioPerformance = (holdings: { ticker: string; value: number }[], period = '6mo') =>
  post<PerfData>('/portfolio/performance', { holdings, period })

// Stocks
export const getWatchlist = () =>
  get<any>('/watchlist').then((data: any): WatchlistCategory[] =>
    (data.categories ?? []).map((cat: any) => ({
      category: cat.name,
      stocks: (cat.tickers ?? []).map((t: any): StockDetail => ({
        ticker: t.ticker,
        name: t.name ?? t.ticker,
        price: t.price ?? 0,
        change_pct: t.change_pct ?? 0,
        bull_score: t.bull_score ?? 50,
        sector: '',
        market_cap: 0,
        pe_ratio: null,
        week_52_high: 0,
        week_52_low: 0,
        spark: t.spark ?? [],
        components: {
          momentum:  t.components?.momentum?.score  ?? 50,
          sentiment: t.components?.sentiment?.score ?? 50,
          valuation: t.components?.valuation?.score ?? 50,
          analyst:   t.components?.analyst?.score   ?? 50,
        },
      })),
    }))
  )

export const getStockDetail = (ticker: string) =>
  get<any>(`/stock/${ticker}/detail`).then((d: any): StockDetail => ({
    ticker: d.ticker,
    name: d.name ?? d.company_name ?? d.ticker,
    price: d.price ?? 0,
    change_pct: d.change_pct ?? 0,
    bull_score: d.bull_score ?? 50,
    sector: d.sector ?? '',
    market_cap: d.market_cap ?? 0,
    pe_ratio: d.pe_ratio ?? null,
    week_52_high: d.week_52_high ?? 0,
    week_52_low: d.week_52_low ?? 0,
    native_currency: d.native_currency ?? null,
    currency: d.currency ?? 'EUR',
    beta: d.beta ?? null,
    rel_volume: d.rel_volume ?? null,
    components: {
      momentum:  d.components?.momentum?.score  ?? 50,
      sentiment: d.components?.sentiment?.score ?? 50,
      valuation: d.components?.valuation?.score ?? 50,
      analyst:   d.components?.analyst?.score   ?? 50,
    },
  }))

export const getMarketNames = (tickers: string[]) =>
  get<Record<string, string>>(`/market/names?tickers=${tickers.join(',')}`)

export const getStockChart = (ticker: string, period: string) =>
  get<any>(`/stock/${ticker}/chart?period=${period}`).then((d: any): ChartData => ({
    currency: d.currency ?? 'EUR',
    points: (d.ohlcv ?? []) as ChartPoint[],
  }))

export const getStockAiSummary = (ticker: string) =>
  get<{ summary: string }>(`/stock/${ticker}/ai-summary`)

export const getStockFinancials = (ticker: string) =>
  get<StockFinancials>(`/stock/${ticker}/financials`)

export const getStockPeers = (ticker: string) =>
  get<PeersResponse>(`/stock/${ticker}/peers`).then(d => d.peers ?? [])

export const getTickerProfile = (ticker: string) =>
  get<TickerProfile>(`/ticker/${ticker}/profile`)

// Personal Watchlist (Portfolio page — backed by /stock-watchlist API)
export interface WatchlistEntry { ticker: string; company: string; notes: string; added: string }

export const getStockWatchlist = () =>
  get<WatchlistEntry[]>('/stock-watchlist')

export const addStockToWatchlist = (ticker: string, company = '') =>
  post<WatchlistEntry[]>('/stock-watchlist', { ticker, company, notes: '', added: '' })

export const removeStockFromWatchlist = (ticker: string) =>
  fetch(`${BASE}/stock-watchlist/${encodeURIComponent(ticker)}`, { method: 'DELETE' })
    .then(r => { if (!r.ok) throw new Error(`${r.status}`); return r.json() as Promise<WatchlistEntry[]> })

// Types
export interface StockRow { ticker: string; name: string; price: number; change_pct: number; bull_score?: number }
export interface BriefingMeta { date: string; has_pdf: boolean }
export interface CostEntry { date: string; provider: string; cost: number }
export interface Position { ticker: string; investment: number; shares?: number; avg_buy?: number }
export interface Holding { ticker: string; investment: number; shares?: number; avg_buy?: number }
export interface PortfolioAnalysis {
  total_value: number
  annualized_return: number
  annualized_volatility: number
  diversification_score: number
  largest_position_usd: number
  largest_position: number
  number_of_positions: number
  assets: Array<{ ticker: string; weight: number; annual_return: number; volatility: number }>
  positions: Record<string, { investment: number; weight: number; current_price: number; shares: number }>
  commentary: string
  correlation_matrix: Record<string, Record<string, number>>
}
export interface WatchlistCategory { category: string; stocks: StockDetail[] }
export interface StockDetail {
  ticker: string; name: string; price: number; change_pct: number
  bull_score: number; sector: string; market_cap: number
  pe_ratio: number | null; week_52_high: number; week_52_low: number
  native_currency?: string | null; currency?: string
  beta?: number | null; rel_volume?: number | null
  spark?: number[]
  components: { momentum: number; sentiment: number; valuation: number; analyst: number }
}
export interface ChartPoint { date: string; open: number; high: number; low: number; close: number; volume: number }
export interface ChartData { currency: string; points: ChartPoint[] }
export interface TickerProfile {
  ticker: string; name: string; sector: string; industry: string
  market_cap: number; description: string; website: string
  employees: number; country: string
}
export interface FinancialsRow { year: number | string; revenue: number | null; ebitda: number | null; net_income: number | null }
export interface StockFinancials { ticker: string; currency: string; fx_ok: boolean; rows: FinancialsRow[] }
export interface PeerRow { ticker: string; name: string; bull_score: number; price: number | null; change_pct: number | null }
export interface PeersResponse { ticker: string; sector: string | null; peers: PeerRow[] }
