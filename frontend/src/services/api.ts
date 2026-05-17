const BASE = import.meta.env.VITE_API_URL
  ?? (window.location.hostname === 'localhost'
    ? '/api'
    : 'https://market-tools-backend-my0v.onrender.com')

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
  get<any>('/market/hot-stocks').then((d: any) => {
    const stocks: StockRow[] = (d.stocks ?? [])
      .filter((s: any) => s.price != null)
      .map((s: any): StockRow => ({
        ticker: s.ticker,
        name: s.name ?? s.ticker,
        price: s.price ?? 0,
        change_pct: s.change_pct ?? 0,
        bull_score: s.bull_score ?? 50,
      }))
    const byChange = [...stocks].sort((a, b) => b.change_pct - a.change_pct)
    const byBull   = [...stocks].sort((a, b) => (b.bull_score ?? 50) - (a.bull_score ?? 50))
    return {
      gainers:  byChange.slice(0, 5),
      losers:   byChange.slice(-5).reverse(),
      bull_high: byBull.slice(0, 5),
      bull_low:  byBull.slice(-5).reverse(),
    }
  })

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
  get<{ positions: Position[]; total_value: number }>('/portfolio')

export const savePortfolio = (positions: Position[]) =>
  post<{ ok: boolean }>('/portfolio', { positions })

export const analyzePortfolio = (holdings: Holding[]) =>
  post<PortfolioAnalysis>('/portfolio/analyze', { holdings })

// Stocks
export const getWatchlist = () =>
  get<any>('/watchlist').then((data: any): WatchlistCategory[] =>
    (data.categories ?? []).map((cat: any) => ({
      category: cat.name,
      stocks: (cat.tickers ?? []).map((t: any): StockDetail => ({
        ticker: t.ticker,
        name: t.ticker,
        price: t.components?.momentum?.details?.price ?? 0,
        change_pct: 0,
        bull_score: t.bull_score ?? 50,
        sector: '',
        market_cap: 0,
        pe_ratio: null,
        week_52_high: 0,
        week_52_low: 0,
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
    components: {
      momentum:  d.components?.momentum?.score  ?? 50,
      sentiment: d.components?.sentiment?.score ?? 50,
      valuation: d.components?.valuation?.score ?? 50,
      analyst:   d.components?.analyst?.score   ?? 50,
    },
  }))

export const getStockChart = (ticker: string, period: string) =>
  get<any>(`/stock/${ticker}/chart?period=${period}`).then((d: any): ChartPoint[] => d.ohlcv ?? [])

export const getStockAiSummary = (ticker: string) =>
  get<{ summary: string }>(`/stock/${ticker}/ai-summary`)

export const getTickerProfile = (ticker: string) =>
  get<TickerProfile>(`/ticker/${ticker}/profile`)

// Types
export interface StockRow { ticker: string; name: string; price: number; change_pct: number; bull_score?: number }
export interface BriefingMeta { date: string; has_pdf: boolean }
export interface CostEntry { date: string; provider: string; cost: number }
export interface Position { ticker: string; investment: number }
export interface Holding { ticker: string; investment: number }
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
  components: { momentum: number; sentiment: number; valuation: number; analyst: number }
}
export interface ChartPoint { date: string; open: number; high: number; low: number; close: number; volume: number }
export interface TickerProfile {
  ticker: string; name: string; sector: string; industry: string
  market_cap: number; description: string; website: string
  employees: number; country: string
}
