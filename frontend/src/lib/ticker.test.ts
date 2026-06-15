import { describe, it, expect } from 'vitest'
import { normalizeTicker } from './ticker'

describe('normalizeTicker', () => {
  it('TELEKOM -> DTE.DE', () => {
    expect(normalizeTicker('TELEKOM')).toBe('DTE.DE')
    expect(normalizeTicker(' telekom ')).toBe('DTE.DE')
  })
  it('unbekannte Ticker bleiben (getrimmt, upper)', () => {
    expect(normalizeTicker('vwce.de')).toBe('VWCE.DE')
  })
})
