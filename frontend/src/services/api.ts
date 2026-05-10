const BASE = import.meta.env.VITE_API_URL ?? '/api'

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
  get<{ gainers: StockRow[]; losers: StockRow[]; bull_high: StockRow[]; bull_low: StockRow[] }>('/market/hot-stocks')

// Briefing
export const getBriefingPreview = () =>
  get<{ preview: string; date: string }>('/briefing/today/preview')

export const getBriefingList = () =>
  get<BriefingMeta[]>('/briefing/list')

export const getBriefing = (date: string) =>
  get<{ date: string; content: string; html: string }>(`/briefing/${date}`)

export const getBriefingCost = () =>
  get<{ monthly_total: number; budget: number; entries: CostEntry[] }>('/briefing/cost-summary')

// Portfolio
export const getPortfolio = () =>
  get<{ positions: Position[]; total_value: number }>('/portfolio')

export const savePortfolio = (positions: Position[]) =>
  post<{ ok: boolean }>('/portfolio', { positions })

export const analyzePortfolio = (holdings: Holding[]) =>
  post<PortfolioAnalysis>('/portfolio/analyze', { holdings })

// Stocks
export const getWatchlist = () =>
  get<WatchlistCategory[]>('/watchlist')

export const getStockDetail = (ticker: string) =>
  get<StockDetail>(`/stock/${ticker}/detail`)

export const getStockChart = (ticker: string, period: string) =>
  get<ChartPoint[]>(`/stock/${ticker}/chart?period=${period}`)

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
  annual_return: number
  volatility: number
  diversification: number
  insight: string
  positions: Array<{ ticker: string; value: number; gain_pct: number }>
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
