import { useRef, useMemo, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { Components } from 'react-markdown'
import { CitationCard, groupCitations, normalizeCiteKey } from './CitationCard'
import type { Citation } from '../types'

interface ChatMessageProps {
  role: 'user' | 'assistant'
  content: string
  citations?: Citation[] | null
  grounded?: boolean
  isStreaming?: boolean
}

/**
 * Pre-process markdown to turn citation patterns into cite:// links.
 * Handles:
 *   [Author et al., 2020, p. 14]
 *   [Author & Author, 2020]
 *   [Carroll et al., 2018, cited in Thompson et al., 2020, p. 14]
 *
 * Avoids matching existing markdown links [text](url) via negative lookahead.
 */
function processCitations(content: string): string {
  return content.replace(
    /\[([^[\]]+?,\s*(\d{4})[^[\]]*)\](?!\()/g,
    (_match, fullCitation: string, year: string) => {
      // "cited in" pattern — link to the paper we actually have
      const citedInMatch = fullCitation.match(/cited\s+in\s+(.+?),\s*(\d{4})/i)

      let targetAuthors: string
      let targetYear: string

      if (citedInMatch) {
        targetAuthors = citedInMatch[1].trim()
        targetYear = citedInMatch[2]
      } else {
        const authorsMatch = fullCitation.match(/^(.+?),\s*\d{4}/)
        targetAuthors = authorsMatch ? authorsMatch[1].trim() : ''
        targetYear = year
      }

      const key = normalizeCiteKey(targetAuthors, targetYear)
      return `[${fullCitation}](#cite::${encodeURIComponent(key)})`
    },
  )
}

function highlightCard(card: Element) {
  card.classList.add('ring-2', 'ring-flame-500/70')
  setTimeout(() => card.classList.remove('ring-2', 'ring-flame-500/70'), 1500)
}

export function ChatMessage({ role, content, citations, grounded, isStreaming }: ChatMessageProps) {
  const isUser = role === 'user'
  const citationsRef = useRef<HTMLDivElement>(null)

  const handleCiteClick = useCallback((key: string) => {
    const card = citationsRef.current?.querySelector(`[data-cite-key="${key}"]`)
    if (card) {
      card.scrollIntoView({ behavior: 'smooth', block: 'center' })
      highlightCard(card)
    }
  }, [])

  const markdownComponents = useMemo<Components>(
    () => ({
      p: ({ children }) => <p className="mb-3 last:mb-0">{children}</p>,
      ul: ({ children }) => <ul className="list-disc list-inside mb-3 space-y-1">{children}</ul>,
      ol: ({ children }) => <ol className="list-decimal list-inside mb-3 space-y-1">{children}</ol>,
      li: ({ children }) => <li className="text-gray-200">{children}</li>,
      strong: ({ children }) => <strong className="font-semibold text-white">{children}</strong>,
      code: ({ children, className }) => {
        const isBlock = className?.includes('language-')
        if (isBlock) {
          return (
            <code className={`${className} block bg-gray-900 rounded-lg p-3 text-sm overflow-x-auto mb-3`}>
              {children}
            </code>
          )
        }
        return (
          <code className="bg-gray-700/50 text-flame-300 px-1.5 py-0.5 rounded text-sm">
            {children}
          </code>
        )
      },
      pre: ({ children }) => <pre className="mb-3">{children}</pre>,
      a: ({ href, children }) => {
        if (href?.startsWith('#cite::')) {
          const key = decodeURIComponent(href.slice(7))
          return (
            <button
              type="button"
              onClick={() => handleCiteClick(key)}
              className="text-flame-400 hover:text-flame-300 font-medium cursor-pointer transition-colors"
            >
              [{children}]
            </button>
          )
        }
        return (
          <a
            href={href}
            target="_blank"
            rel="noopener noreferrer"
            className="text-flame-400 hover:text-flame-300 underline transition-colors"
          >
            {children}
          </a>
        )
      },
      h1: ({ children }) => <h1 className="text-xl font-bold text-white mb-2 mt-4 first:mt-0">{children}</h1>,
      h2: ({ children }) => <h2 className="text-lg font-bold text-white mb-2 mt-3 first:mt-0">{children}</h2>,
      h3: ({ children }) => <h3 className="text-base font-semibold text-white mb-1 mt-3 first:mt-0">{children}</h3>,
      blockquote: ({ children }) => (
        <blockquote className="border-l-2 border-gray-600 pl-3 italic text-gray-300 mb-3">{children}</blockquote>
      ),
    }),
    [handleCiteClick],
  )

  const processedContent = useMemo(() => processCitations(content), [content])

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} px-4 py-2`}>
      <div className={`max-w-[85%] md:max-w-[75%] ${isUser ? '' : 'w-full'}`}>
        <div
          className={`rounded-2xl px-4 py-3 ${
            isUser
              ? 'bg-flame-600/20 text-white rounded-tr-sm'
              : 'bg-gray-800/50 text-gray-200 rounded-tl-sm'
          }`}
        >
          {isUser ? (
            <p className="whitespace-pre-wrap">{content}</p>
          ) : (
            <div className="prose-invert max-w-none text-sm leading-relaxed">
              <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                {processedContent}
              </ReactMarkdown>
              {isStreaming && (
                <span className="inline-block w-2 h-4 bg-flame-400 ml-0.5 animate-pulse" />
              )}
            </div>
          )}

          {grounded === false && !isUser && (
            <p className="text-amber-400 text-xs mt-2 pt-2 border-t border-gray-700/50">
              No relevant research found — this response is based on general knowledge.
            </p>
          )}
        </div>

        {citations && citations.length > 0 && (
          <div ref={citationsRef} className="mt-2 border-t border-gray-700/30 pt-2">
            <p className="text-xs text-gray-500 mb-1.5">Sources</p>
            <div className="flex flex-wrap gap-2">
              {groupCitations(citations).map((g) => (
                <CitationCard key={`${g.title}::${g.year}`} citation={g} />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
