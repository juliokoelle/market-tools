import { useState } from 'react'

interface Podcast {
  emoji: string
  name: string
  host: string
  category: string
  language: 'DE' | 'EN'
  description: string
  whyRelevant: string
  frequency: string
  url: string
  tags: string[]
}

const PODCASTS: Podcast[] = [
  {
    emoji: '💰',
    name: 'All-In Podcast',
    host: 'Chamath, Jason, Sacks, Friedberg',
    category: 'Finance & Tech',
    language: 'EN',
    description: 'Vier Tech-Investoren diskutieren wöchentlich Markets, Macro, Deals und globale Events mit Insider-Perspektive.',
    whyRelevant: 'Investment-Thesen, Macro-Outlook, Startup-Ökosystem — extrem dichte Informationsdichte pro Stunde.',
    frequency: 'Wöchentlich',
    url: 'https://www.allinpodcast.co',
    tags: ['Finance', 'VC', 'Macro', 'Tech'],
  },
  {
    emoji: '🏢',
    name: 'Acquired',
    host: 'Ben Gilbert & David Rosenthal',
    category: 'Business Deep Dives',
    language: 'EN',
    description: 'Mehrstündige Company Deep Dives: LVMH, Apple, NVIDIA, Amazon — wie Firmen wirklich groß werden.',
    whyRelevant: 'Für Investmententscheidungen: verstehe was eine Firma antreibt, bevor du investierst.',
    frequency: 'Ca. monatlich',
    url: 'https://www.acquired.fm',
    tags: ['Investing', 'Strategy', 'Business History'],
  },
  {
    emoji: '📊',
    name: 'Finanzfluss Podcast',
    host: 'Thomas & Nikolaus',
    category: 'Persönliche Finanzen',
    language: 'DE',
    description: 'ETF-Investing, Steuern, Altersvorsorge auf Deutsch. Evidence-based, keine Hotstock-Tipps.',
    whyRelevant: 'Steueroptimierung für dein ETF-Depot (VWCE), Holding-Struktur, GmbH-Themen — sehr praxisnah.',
    frequency: 'Wöchentlich',
    url: 'https://www.finanzfluss.de/podcast',
    tags: ['ETFs', 'Steuern', 'Deutschland', 'Geldanlage'],
  },
  {
    emoji: '🏠',
    name: 'Immocation Podcast',
    host: 'Alexander Raue',
    category: 'Immobilien',
    language: 'DE',
    description: 'Immobilien kaufen, finanzieren und verwalten in Deutschland. Cashflow, Steuer, Hausverwaltung.',
    whyRelevant: 'Direkt relevant für deine 300-Wohnungen-Holding: Hausverwaltung, 300er-Regel, steuerliche Strukturen.',
    frequency: 'Wöchentlich',
    url: 'https://immocation.de/podcast',
    tags: ['Immobilien', 'Holding', 'Hausverwaltung', 'Deutschland'],
  },
  {
    emoji: '💡',
    name: 'My First Million',
    host: 'Shaan Puri & Sam Parr',
    category: 'Entrepreneurship',
    language: 'EN',
    description: 'Business-Ideen brainstormen, Trends früh erkennen, Micro-SaaS und neue Märkte entdecken.',
    whyRelevant: 'Ideen für neue Apps, Monetarisierungsstrategien, Nischen-Opportunitäten — ideal für JK App Studio.',
    frequency: '3× pro Woche',
    url: 'https://www.mfmpod.com',
    tags: ['Startup', 'Ideas', 'Business Models'],
  },
  {
    emoji: '🎙️',
    name: 'OMR Podcast',
    host: 'Philipp Westermeyer',
    category: 'Business & Marketing',
    language: 'DE',
    description: 'Interviews mit deutschen und internationalen Unternehmern. Von Startup bis Mittelstand.',
    whyRelevant: 'Deutsches Business-Mindset, Expansion-Strategien, Marketing — relevant für KFZ-Expansion.',
    frequency: 'Wöchentlich',
    url: 'https://omr.com/de/podcasts/omr-podcast',
    tags: ['Marketing', 'Business', 'Deutschland', 'Growth'],
  },
  {
    emoji: '🏊',
    name: 'Triathlon Taren',
    host: 'Taren Gesell',
    category: 'Triathlon & Ironman',
    language: 'EN',
    description: 'Ironman-Training für Age-Grouper: Trainingsplanung, Ernährung, Race-Day-Strategie und Ausrüstung.',
    whyRelevant: 'Direkt für deine Ironman-Vorbereitung: Trainingsplan, Brick Workouts, Schwimm-Technik, Tapering.',
    frequency: '2× pro Woche',
    url: 'https://www.triathlontaren.com',
    tags: ['Ironman', 'Triathlon', 'Training', 'Wettkampf'],
  },
  {
    emoji: '🤖',
    name: 'Lex Fridman Podcast',
    host: 'Lex Fridman',
    category: 'Tech & Science',
    language: 'EN',
    description: 'Langform-Interviews mit führenden Köpfen aus AI, Business, Wissenschaft und Sport. Oft 3–5 Stunden.',
    whyRelevant: 'Deep dives auf AI-Entwicklung, Gründerphilosophien — für technologische Orientierung.',
    frequency: 'Unregelmäßig',
    url: 'https://lexfridman.com/podcast',
    tags: ['AI', 'Science', 'Tech', 'Philosophy'],
  },
  {
    emoji: '🏗️',
    name: 'How I Built This',
    host: 'Guy Raz (NPR)',
    category: 'Entrepreneurship',
    language: 'EN',
    description: 'Gründer-Interviews: Wie wurde Airbnb, Patagonia, Instagram aufgebaut? Die echten Geschichten.',
    whyRelevant: 'Inspiration für App Studio, Gründermentalität, Fehler die andere schon gemacht haben.',
    frequency: 'Wöchentlich',
    url: 'https://www.npr.org/series/490248027/how-i-built-this',
    tags: ['Startup', 'Founders', 'Inspiration'],
  },
  {
    emoji: '📈',
    name: 'Masters in Business',
    host: 'Barry Ritholtz (Bloomberg)',
    category: 'Investing',
    language: 'EN',
    description: 'Interviews mit den besten Portfolio-Managern, Ökonomen und Investoren der Welt.',
    whyRelevant: 'Investment-Philosophien, Risikomanagement, Portfolio-Konstruktion für dein eigenes Depot.',
    frequency: 'Wöchentlich',
    url: 'https://ritholtz.com/category/masters-in-business',
    tags: ['Investing', 'Finance', 'Bloomberg', 'Portfolio'],
  },
]

const LANG_OPTIONS = ['Alle', 'DE', 'EN'] as const
const CAT_FILTERS = ['Finance & Tech', 'Immobilien', 'Triathlon & Ironman', 'Entrepreneurship'] as const

export default function Podcasts() {
  const [lang, setLang] = useState<string>('Alle')
  const [cat, setCat] = useState<string>('Alle')

  const shown = PODCASTS.filter(p => {
    if (lang !== 'Alle' && p.language !== lang) return false
    if (cat !== 'Alle' && p.category !== cat) return false
    return true
  })

  return (
    <main className="page page-enter">
      <div className="page-header">
        <div>
          <h1 className="page-title">Podcasts</h1>
          <p className="page-subtitle">Kuratierte Shows für Finance, Immobilien, Triathlon & Business</p>
        </div>
        <span className="badge badge-gray">{PODCASTS.length} Shows</span>
      </div>

      {/* Filters */}
      <div style={{ display: 'flex', gap: '.4rem', flexWrap: 'wrap', marginBottom: '1.5rem', alignItems: 'center' }}>
        {LANG_OPTIONS.map(l => (
          <button
            key={l}
            onClick={() => setLang(l)}
            style={{
              padding: '.3rem .7rem', borderRadius: 20, fontSize: '.8rem', fontWeight: 600, cursor: 'pointer',
              border: `1px solid ${lang === l ? 'var(--teal)' : 'var(--border)'}`,
              background: lang === l ? 'var(--teal-light)' : 'transparent',
              color: lang === l ? 'var(--teal)' : 'var(--text-3)',
            }}
          >
            {l === 'Alle' ? 'Alle Sprachen' : l === 'DE' ? '🇩🇪 Deutsch' : '🇺🇸 English'}
          </button>
        ))}
        <div style={{ width: 1, height: 18, background: 'var(--border)', margin: '0 .15rem' }} />
        {CAT_FILTERS.map(c => (
          <button
            key={c}
            onClick={() => setCat(cat === c ? 'Alle' : c)}
            style={{
              padding: '.3rem .7rem', borderRadius: 20, fontSize: '.8rem', fontWeight: 600, cursor: 'pointer',
              border: `1px solid ${cat === c ? 'var(--teal)' : 'var(--border)'}`,
              background: cat === c ? 'var(--teal-light)' : 'transparent',
              color: cat === c ? 'var(--teal)' : 'var(--text-3)',
            }}
          >
            {c}
          </button>
        ))}
      </div>

      {/* Grid */}
      {shown.length === 0 ? (
        <p style={{ textAlign: 'center', color: 'var(--text-3)', padding: '3rem 0' }}>
          Keine Podcasts für diesen Filter.
        </p>
      ) : (
        <div className="grid-3">
          {shown.map(p => (
            <div key={p.name} className="card" style={{ display: 'flex', flexDirection: 'column', gap: '.75rem' }}>
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '.5rem' }}>
                <span style={{ fontSize: '2rem', lineHeight: 1 }}>{p.emoji}</span>
                <div style={{ display: 'flex', gap: '.3rem', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
                  <span className="badge badge-gray" style={{ fontSize: '.63rem' }}>
                    {p.language === 'DE' ? '🇩🇪 DE' : '🇺🇸 EN'}
                  </span>
                  <span className="badge badge-gray" style={{ fontSize: '.63rem' }}>{p.frequency}</span>
                </div>
              </div>

              <div>
                <h2 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: '.15rem' }}>{p.name}</h2>
                <p style={{ fontSize: '.78rem', color: 'var(--text-3)', marginBottom: '.5rem' }}>{p.host}</p>
                <p style={{ fontSize: '.875rem', color: 'var(--text-2)', lineHeight: 1.6 }}>{p.description}</p>
              </div>

              <div style={{ padding: '.6rem .75rem', background: 'var(--teal-light)', borderRadius: 8, borderLeft: '3px solid var(--teal)' }}>
                <p style={{ fontSize: '.78rem', color: 'var(--text-2)', lineHeight: 1.55 }}>
                  <strong style={{ color: 'var(--teal)' }}>Warum relevant:</strong> {p.whyRelevant}
                </p>
              </div>

              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '.3rem' }}>
                {p.tags.map(t => <span key={t} className="badge badge-gray" style={{ fontSize: '.63rem' }}>{t}</span>)}
              </div>

              <a
                href={p.url}
                target="_blank"
                rel="noopener noreferrer"
                className="btn btn-outline"
                style={{ marginTop: 'auto', justifyContent: 'center', fontSize: '.85rem' }}
              >
                Podcast öffnen →
              </a>
            </div>
          ))}
        </div>
      )}
    </main>
  )
}
