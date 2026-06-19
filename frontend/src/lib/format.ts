// Formatierungs-Helfer für die Market-UI. Keine Backend-Kopplung — überall nutzbar.
// Durchgängig EUR + deutsches Zahlenformat (Komma-Dezimal, Punkt-Tausender).

/** Währung in EUR. Ab 1.000 ohne Nachkommastellen, darunter mit 2. */
export const fmtCurrency = (n: number) =>
  new Intl.NumberFormat('de-DE', {
    style: 'currency',
    currency: 'EUR',
    maximumFractionDigits: Math.abs(n) >= 1000 ? 0 : 2,
  }).format(n)

/** Währung in EUR, immer 2 Nachkommastellen. */
export const fmtCurrencyExact = (n: number) =>
  new Intl.NumberFormat('de-DE', {
    style: 'currency',
    currency: 'EUR',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(n)

/**
 * Geldbetrag in beliebiger Währung (Backend liefert Analyzer-Werte in
 * Heimatwährung — USD bei US-Titeln). Ungültige/Nicht-ISO-Codes (z.B. "GBp")
 * fallen sauber auf "<Zahl> <Code>" zurück statt zu werfen.
 */
export const fmtMoney = (n: number, code = 'EUR') => {
  try {
    return new Intl.NumberFormat('de-DE', {
      style: 'currency', currency: code,
      maximumFractionDigits: Math.abs(n) >= 1000 ? 0 : 2,
    }).format(n)
  } catch {
    return `${fmtNumber(n, Math.abs(n) >= 1000 ? 0 : 2)} ${code}`
  }
}

/** Geldbetrag in beliebiger Währung, immer 2 Nachkommastellen. */
export const fmtMoneyExact = (n: number, code = 'EUR') => {
  try {
    return new Intl.NumberFormat('de-DE', {
      style: 'currency', currency: code,
      minimumFractionDigits: 2, maximumFractionDigits: 2,
    }).format(n)
  } catch {
    return `${fmtPrice(n)} ${code}`
  }
}

/** Währungssymbol/-code für Labels (z.B. Achsen). */
export const currencyLabel = (code = 'EUR') =>
  ({ USD: '$', EUR: '€', GBP: '£', GBp: 'p', CHF: 'CHF', JPY: '¥', CAD: 'C$', AUD: 'A$', HKD: 'HK$' } as Record<string, string>)[code] ?? code

/** Reine Zahl mit 2 Nachkommastellen (z.B. Kurse). */
export const fmtPrice = (n: number) =>
  new Intl.NumberFormat('de-DE', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(n)

/** Zahl, frei in den Nachkommastellen. */
export const fmtNumber = (n: number, max = 2) =>
  new Intl.NumberFormat('de-DE', { maximumFractionDigits: max }).format(n)

/** Kompaktnotation (1,2 Mio. / 3,4 Mrd.). */
export const fmtCompact = (n: number) =>
  new Intl.NumberFormat('de-DE', { notation: 'compact', maximumFractionDigits: 2 }).format(n)

/** Prozent mit Vorzeichen, deutsches Komma. */
export const fmtPct = (n: number, digits = 2) =>
  `${n >= 0 ? '+' : ''}${n.toFixed(digits).replace('.', ',')}%`

/**
 * Marktkapitalisierung. yfinance liefert sie in der Heimatwährung des Wertpapiers
 * (USD für US-Titel) — daher Währung explizit übergeben statt EUR zu erzwingen.
 */
export const fmtMarketCap = (n: number, currency: 'USD' | 'EUR' = 'USD') =>
  `${currency === 'EUR' ? '' : '$'}${fmtCompact(n)}${currency === 'EUR' ? ' €' : ''}`

/** Score-Ton: <45 low, 45–69 mid, ≥70 high. */
export const scoreTone = (score: number): 'low' | 'mid' | 'high' =>
  score >= 70 ? 'high' : score >= 45 ? 'mid' : 'low'

/** Relative Zeit auf Deutsch ("vor 3 Min", "vor 2 Std"). */
export const relativeTime = (iso: string) => {
  const diffMs = Date.now() - new Date(iso).getTime()
  const m = Math.round(diffMs / 60000)
  if (m < 1) return 'gerade eben'
  if (m < 60) return `vor ${m} Min`
  const h = Math.round(m / 60)
  if (h < 24) return `vor ${h} Std`
  return `vor ${Math.round(h / 24)} Tg`
}
