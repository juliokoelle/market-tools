/** Bekannte Falsch-Ticker -> gültiges Yahoo-Symbol. */
export const TICKER_ALIASES: Record<string, string> = {
  TELEKOM: 'DTE.DE',
}

export function normalizeTicker(raw: string): string {
  const t = (raw ?? '').trim().toUpperCase()
  return TICKER_ALIASES[t] ?? t
}
