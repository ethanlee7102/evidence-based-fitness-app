import type { Citation } from '../types'

const CATEGORY_COLORS: Record<string, string> = {
  hypertrophy: 'bg-purple-500/20 text-purple-300',
  strength: 'bg-blue-500/20 text-blue-300',
  nutrition: 'bg-green-500/20 text-green-300',
  endurance: 'bg-yellow-500/20 text-yellow-300',
  recovery: 'bg-teal-500/20 text-teal-300',
  mobility: 'bg-orange-500/20 text-orange-300',
  programming: 'bg-indigo-500/20 text-indigo-300',
  general: 'bg-gray-500/20 text-gray-300',
}

interface GroupedCitation {
  title: string
  authors: string
  year: number
  category: string
  doi: string | null
  sections: { section: string | null; page_start: number | null; page_end: number | null }[]
}

/** Normalize to "surname::year" for matching inline citations to cards. */
export function normalizeCiteKey(authors: string, year: string | number): string {
  const surname = authors.split(/[\s,]/)[0].toLowerCase()
  return `${surname}::${year}`
}

/** Strip leading numbers like "5. Discussion" or "5 Discussion" → "Discussion",
 *  and deduplicate repeated names like "5. Conclusion 5. Conclusion" → "Conclusion". */
function cleanSection(raw: string): string {
  // Strip all leading "number." or "number " prefixes (handles "5. Conclusion 5. Conclusion")
  const cleaned = raw.replace(/\d+\.?\s*/g, '').trim()
  // Deduplicate repeated words (e.g. "Conclusions Conclusions" → "Conclusions")
  const words = cleaned.split(/\s+/)
  const mid = Math.ceil(words.length / 2)
  const first = words.slice(0, mid).join(' ')
  const second = words.slice(mid).join(' ')
  if (first && first === second) return first
  return cleaned
}

/** Group raw citations by paper title, deduplicating sections. */
export function groupCitations(citations: Citation[]): GroupedCitation[] {
  const map = new Map<string, GroupedCitation>()

  for (const c of citations) {
    const key = `${c.title}::${c.year}`
    const existing = map.get(key)

    const section = c.section ? cleanSection(c.section) : null

    if (existing) {
      // Only add if this section+page combo isn't already listed
      const isDupe = existing.sections.some(
        (s) => s.section === section && s.page_start === c.page_start && s.page_end === c.page_end,
      )
      if (!isDupe) {
        existing.sections.push({ section, page_start: c.page_start, page_end: c.page_end })
      }
    } else {
      map.set(key, {
        title: c.title,
        authors: c.authors,
        year: c.year,
        category: c.category,
        doi: c.doi,
        sections: [{ section, page_start: c.page_start, page_end: c.page_end }],
      })
    }
  }

  return Array.from(map.values())
}

interface CitationCardProps {
  citation: GroupedCitation
}

export function CitationCard({ citation }: CitationCardProps) {
  const categoryColor = CATEGORY_COLORS[citation.category] || CATEGORY_COLORS.general

  const titleElement = citation.doi ? (
    <a
      href={`https://doi.org/${citation.doi}`}
      target="_blank"
      rel="noopener noreferrer"
      className="text-flame-400 hover:text-flame-300 text-sm font-medium line-clamp-1 transition-colors"
    >
      {citation.title}
    </a>
  ) : (
    <span className="text-gray-200 text-sm font-medium line-clamp-1">{citation.title}</span>
  )

  const citeKey = normalizeCiteKey(citation.authors, citation.year)

  return (
    <div
      data-cite-key={citeKey}
      className="bg-gray-800/60 border border-gray-700/50 rounded-lg px-3 py-2 min-w-0 transition-all duration-300"
    >
      {titleElement}
      <p className="text-gray-400 text-xs mt-0.5 truncate">
        {citation.authors} ({citation.year})
      </p>
      <div className="flex items-center gap-1.5 mt-1">
        <span className={`text-xs px-1.5 py-0.5 rounded ${categoryColor}`}>
          {citation.category}
        </span>
      </div>
      {citation.sections.length > 0 && (
        <div className="flex flex-wrap gap-x-3 gap-y-0.5 mt-1.5 pt-1.5 border-t border-gray-700/40">
          {citation.sections.map((s, i) => (
            <span key={i} className="text-xs text-gray-500">
              {s.section && <span>{s.section}</span>}
              {s.section && s.page_start != null && ' · '}
              {s.page_start != null && (
                <span className="text-gray-400">
                  p.{s.page_start}{s.page_end != null && s.page_end !== s.page_start && `–${s.page_end}`}
                </span>
              )}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}
