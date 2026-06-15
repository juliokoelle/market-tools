/**
 * Format-erkennender Dezimal-Parser.
 * - Punkt UND Komma -> deutsch: Punkt = Tausender, Komma = Dezimal.
 * - Nur Komma       -> Dezimal-Komma.
 * - Nur Punkt       -> Dezimal-Punkt (NICHT entfernen); bei mehreren Punkten
 *                      Heuristik: letzter Block <=2 Stellen = Dezimal, sonst Tausender.
 * - Keine Trenner   -> parseFloat.
 * Währungssymbole/Leerzeichen werden vor dem Parsen entfernt.
 */
export function parseNum(s: string | null | undefined): number {
  if (s == null) return NaN
  const t = String(s).replace(/[^0-9.,-]/g, '')
  if (!t || t === '-' || t === '.' || t === ',') return NaN

  const hasDot = t.includes('.')
  const hasComma = t.includes(',')

  if (hasDot && hasComma) {
    return parseFloat(t.replace(/\./g, '').replace(',', '.'))
  }
  if (hasComma) {
    return parseFloat(t.replace(',', '.'))
  }
  if (hasDot) {
    const dotCount = (t.match(/\./g) || []).length
    if (dotCount === 1) return parseFloat(t)
    const idx = t.lastIndexOf('.')
    const lastBlock = t.slice(idx + 1)
    if (lastBlock.length <= 2) {
      return parseFloat(t.slice(0, idx).replace(/\./g, '') + '.' + lastBlock)
    }
    return parseFloat(t.replace(/\./g, ''))
  }
  return parseFloat(t)
}
