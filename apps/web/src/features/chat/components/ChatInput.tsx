import { useRef, useCallback } from 'react'
import { ArrowUp } from 'lucide-react'

interface ChatInputProps {
  onSend: (text: string) => void
  isSending: boolean
}

export function ChatInput({ onSend, isSending }: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const resetHeight = useCallback(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
  }, [])

  const handleInput = useCallback(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${el.scrollHeight}px`
  }, [])

  const handleSend = useCallback(() => {
    const el = textareaRef.current
    if (!el) return
    const text = el.value.trim()
    if (!text || isSending) return
    onSend(text)
    el.value = ''
    resetHeight()
  }, [onSend, isSending, resetHeight])

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        handleSend()
      }
    },
    [handleSend],
  )

  return (
    <div className="border-t border-gray-800 px-4 py-3">
      <div className="flex items-end gap-2 max-w-3xl mx-auto">
        <textarea
          ref={textareaRef}
          onInput={handleInput}
          onKeyDown={handleKeyDown}
          disabled={isSending}
          placeholder={isSending ? 'Thinking...' : 'Ask about exercise science...'}
          rows={1}
          className="flex-1 bg-gray-800/50 border border-gray-700 rounded-xl px-4 py-3 text-white placeholder-gray-500 resize-none max-h-[200px] overflow-y-auto focus:outline-none focus:border-flame-500 transition-colors disabled:opacity-50"
        />
        <button
          onClick={handleSend}
          disabled={isSending}
          className="flex-shrink-0 w-10 h-10 rounded-full bg-flame-600 hover:bg-flame-500 disabled:bg-gray-700 disabled:opacity-50 flex items-center justify-center text-white transition-colors"
        >
          <ArrowUp className="w-5 h-5" />
        </button>
      </div>
    </div>
  )
}
