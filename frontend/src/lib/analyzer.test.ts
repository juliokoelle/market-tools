import { describe, it, expect } from 'vitest'
import { range52Position, fmtRelVolume, financialsToBars, sortPeers } from './analyzer'

describe('range52Position', () => {
  it('Mitte der Spanne -> 50', () => {
    expect(range52Position(100, 200, 150)).toBe(50)
  })
  it('clamps unter Low / über High', () => {
    expect(range52Position(100, 200, 80)).toBe(0)
    expect(range52Position(100, 200, 260)).toBe(100)
  })
  it('degenerierte Spanne (high<=low) -> 0', () => {
    expect(range52Position(200, 200, 200)).toBe(0)
    expect(range52Position(200, 100, 150)).toBe(0)
  })
})

describe('fmtRelVolume', () => {
  it('null/undefined -> Strich', () => {
    expect(fmtRelVolume(null)).toBe('—')
    expect(fmtRelVolume(undefined)).toBe('—')
  })
  it('Faktor mit ×-Suffix, deutsches Komma', () => {
    expect(fmtRelVolume(1.5)).toBe('1,5×')
    expect(fmtRelVolume(2)).toBe('2×')
  })
})

describe('financialsToBars', () => {
  it('mappt rows auf recharts-Reihen (Mio. EUR)', () => {
    const rows = [{ year: 2023, revenue: 2_000_000_000, ebitda: 800_000_000, net_income: 500_000_000 }]
    expect(financialsToBars(rows)).toEqual([
      { year: '2023', Revenue: 2000, EBITDA: 800, 'Net Income': 500 },
    ])
  })
  it('null-Werte -> 0', () => {
    expect(financialsToBars([{ year: 2022, revenue: null, ebitda: null, net_income: null }]))
      .toEqual([{ year: '2022', Revenue: 0, EBITDA: 0, 'Net Income': 0 }])
  })
})

describe('sortPeers', () => {
  it('absteigend nach bull_score, ohne Mutation', () => {
    const input = [
      { ticker: 'A', name: 'A', bull_score: 40, price: 1, change_pct: 0 },
      { ticker: 'B', name: 'B', bull_score: 80, price: 1, change_pct: 0 },
    ]
    const out = sortPeers(input)
    expect(out.map(p => p.ticker)).toEqual(['B', 'A'])
    expect(input.map(p => p.ticker)).toEqual(['A', 'B'])
  })
})
