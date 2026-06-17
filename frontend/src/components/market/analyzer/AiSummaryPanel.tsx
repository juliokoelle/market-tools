import { useEffect, useState } from 'react'
import { Panel, SectionHeader } from '../primitives'
import { getStockAiSummary } from '../../../services/api'

export function AiSummaryPanel({ ticker }: { ticker: string }) {
  const [summary, setSummary] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    getStockAiSummary(ticker)
      .then(d => { if (active) setSummary(d.summary) })
      .catch(() => { if (active) setSummary('') })
    return () => { active = false }
  }, [ticker])

  if (summary === null) return null   // lädt
  if (!summary) return null           // kein Inhalt: Panel ausblenden

  return (
    <Panel>
      <SectionHeader title="AI-Zusammenfassung" />
      <p style={{ marginTop: '.75rem', fontSize: '.85rem', lineHeight: 1.6, color: 'var(--text-2)', whiteSpace: 'pre-wrap' }}>
        {summary}
      </p>
    </Panel>
  )
}
