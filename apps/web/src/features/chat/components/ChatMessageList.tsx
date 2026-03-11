import { useRef, useEffect, useCallback } from 'react'
import { ChatMessage } from './ChatMessage'
import { TypingIndicator } from './TypingIndicator'
import { SuggestedQuestions } from './SuggestedQuestions'
import type { ChatMessageData, StreamingMessage } from '../types'

interface ChatMessageListProps {
  messages: ChatMessageData[]
  streamingMessage: StreamingMessage | null
  isSending: boolean
  onSelectQuestion: (question: string) => void
}

export function ChatMessageList({
  messages,
  streamingMessage,
  isSending,
  onSelectQuestion,
}: ChatMessageListProps) {
  const scrollContainerRef = useRef<HTMLDivElement>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  const isNearBottom = useCallback(() => {
    const el = scrollContainerRef.current
    if (!el) return true
    return el.scrollTop + el.clientHeight >= el.scrollHeight - 100
  }, [])

  // Auto-scroll on new content
  useEffect(() => {
    if (!isNearBottom()) return
    bottomRef.current?.scrollIntoView({
      behavior: streamingMessage?.isStreaming ? 'auto' : 'smooth',
    })
  }, [messages, streamingMessage?.content, streamingMessage?.isStreaming, isNearBottom])

  const isEmpty = messages.length === 0 && !streamingMessage && !isSending

  return (
    <div ref={scrollContainerRef} className="flex-1 overflow-y-auto">
      {isEmpty ? (
        <SuggestedQuestions onSelect={onSelectQuestion} />
      ) : (
        <div className="max-w-3xl mx-auto py-4">
          {messages.map((msg) => (
            <ChatMessage
              key={msg.id}
              role={msg.role}
              content={msg.content}
              citations={msg.citations}
            />
          ))}

          {streamingMessage && (
            streamingMessage.content ? (
              <ChatMessage
                role="assistant"
                content={streamingMessage.content}
                citations={streamingMessage.citations.length > 0 ? streamingMessage.citations : null}
                grounded={streamingMessage.grounded}
                isStreaming={streamingMessage.isStreaming}
              />
            ) : streamingMessage.isStreaming ? (
              <TypingIndicator />
            ) : null
          )}

          <div ref={bottomRef} />
        </div>
      )}
    </div>
  )
}
