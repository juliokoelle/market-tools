import { describe, it, expect } from 'vitest'
import { parseNum } from './parseNum'

describe('parseNum', () => {
  it('dezimal-Punkt bleibt erhalten (Bug-Regression)', () => {
    expect(parseNum('162.66')).toBeCloseTo(162.66, 4)
    expect(parseNum('2.9131980000')).toBeCloseTo(2.913198, 6)
  })
  it('deutsches Format: Punkt = Tausender, Komma = Dezimal', () => {
    expect(parseNum('1.234,56')).toBeCloseTo(1234.56, 2)
    expect(parseNum('1.000.000,00')).toBeCloseTo(1000000, 2)
  })
  it('nur Komma = Dezimal-Komma', () => {
    expect(parseNum('162,66')).toBeCloseTo(162.66, 2)
  })
  it('mehrfache Punkte: letzter Block >2 Stellen = Tausender', () => {
    expect(parseNum('1.234.567')).toBeCloseTo(1234567, 0)
  })
  it('mehrfache Punkte: letzter Block <=2 Stellen = Dezimal', () => {
    expect(parseNum('1.234.56')).toBeCloseTo(1234.56, 2)
  })
  it('keine Trenner = parseFloat', () => {
    expect(parseNum('5000')).toBe(5000)
  })
  it('Währungssymbole/Leerzeichen werden ignoriert', () => {
    expect(parseNum('€ 1.626,58')).toBeCloseTo(1626.58, 2)
  })
  it('negativ', () => {
    expect(parseNum('-162.66')).toBeCloseTo(-162.66, 2)
  })
  it('leer/Müll = NaN', () => {
    expect(Number.isNaN(parseNum(''))).toBe(true)
    expect(Number.isNaN(parseNum('abc'))).toBe(true)
  })
})
