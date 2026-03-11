import { useState, useCallback, useRef, useEffect } from 'react'
import { useAuth } from '../../auth/hooks/useAuth'
import {
  getSessions,
  getMessages as fetchMessages,
  deleteSession as deleteSessionApi,
  sendMessageSSE,
} from '../services/chatService'
import type { ChatSession, ChatMessageData, StreamingMessage } from '../types'

export function useChat() {
  const { session: authSession } = useAuth()
  const token = authSession?.access_token

  const [sessions, setSessions] = useState<ChatSession[]>([])
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<ChatMessageData[]>([])
  const [streamingMessage, setStreamingMessage] = useState<StreamingMessage | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isSending, setIsSending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastFailedMessage, setLastFailedMessage] = useState<string | null>(null)

  const abortControllerRef = useRef<AbortController | null>(null)

  // Load sessions on mount
  const loadSessions = useCallback(async () => {
    if (!token) return
    try {
      const data = await getSessions(token)
      setSessions(data)
    } catch (e) {
      console.error('Failed to load sessions:', e)
    }
  }, [token])

  useEffect(() => {
    loadSessions()
  }, [loadSessions])

  // Select a session — load its messages
  const selectSession = useCallback(
    async (id: string) => {
      if (!token) return
      // Abort any in-flight stream
      abortControllerRef.current?.abort()
      setStreamingMessage(null)
      setError(null)
      setLastFailedMessage(null)
      setActiveSessionId(id)
      setIsLoading(true)

      try {
        const msgs = await fetchMessages(token, id)
        setMessages(msgs)
      } catch (e) {
        console.error('Failed to load messages:', e)
        setError('Failed to load conversation history.')
      } finally {
        setIsLoading(false)
      }
    },
    [token],
  )

  // Start a new chat
  const startNewChat = useCallback(() => {
    abortControllerRef.current?.abort()
    setActiveSessionId(null)
    setMessages([])
    setStreamingMessage(null)
    setError(null)
    setLastFailedMessage(null)
  }, [])

  // Send a message
  const sendMessage = useCallback(
    async (text: string) => {
      if (!token || isSending) return

      setError(null)
      setLastFailedMessage(null)
      setIsSending(true)

      // Optimistic user message
      const tempUserMsg: ChatMessageData = {
        id: `temp-${Date.now()}`,
        session_id: activeSessionId || '',
        role: 'user',
        content: text,
        citations: null,
        created_at: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, tempUserMsg])

      // Init streaming message
      setStreamingMessage({
        role: 'assistant',
        content: '',
        citations: [],
        grounded: true,
        isStreaming: true,
      })

      const controller = new AbortController()
      abortControllerRef.current = controller

      let sessionIdForRequest = activeSessionId

      try {
        await sendMessageSSE(
          token,
          { message: text, session_id: activeSessionId || undefined },
          {
            onSession: (data) => {
              sessionIdForRequest = data.session_id
              setActiveSessionId(data.session_id)
              // Refresh sessions list (new session appeared)
              loadSessions()
            },
            onCitations: (data) => {
              setStreamingMessage((prev) =>
                prev ? { ...prev, citations: data.chunks, grounded: data.grounded } : prev,
              )
            },
            onData: (data) => {
              setStreamingMessage((prev) =>
                prev ? { ...prev, content: prev.content + data.text } : prev,
              )
            },
            onDone: (data) => {
              setStreamingMessage((prev) => {
                if (!prev) return null
                // Convert streaming message to a real message
                const finalMsg: ChatMessageData = {
                  id: data.message_id,
                  session_id: sessionIdForRequest || '',
                  role: 'assistant',
                  content: prev.content,
                  citations: prev.citations.length > 0 ? prev.citations : null,
                  created_at: new Date().toISOString(),
                }
                setMessages((msgs) => [...msgs, finalMsg])
                return null
              })
              setIsSending(false)
              // Re-fetch sessions after delay for auto-title
              setTimeout(() => loadSessions(), 3000)
            },
            onError: (data) => {
              setError(data.detail)
              setLastFailedMessage(text)
              setStreamingMessage((prev) =>
                prev ? { ...prev, isStreaming: false } : prev,
              )
              setIsSending(false)
            },
          },
          controller.signal,
        )
      } catch (e) {
        if ((e as Error).name === 'AbortError') return
        setError('Failed to connect to the server.')
        setLastFailedMessage(text)
        setStreamingMessage((prev) =>
          prev ? { ...prev, isStreaming: false } : prev,
        )
        setIsSending(false)
      }
    },
    [token, isSending, activeSessionId, loadSessions],
  )

  // Delete a session
  const deleteSession = useCallback(
    async (id: string) => {
      if (!token) return
      // Optimistic removal
      setSessions((prev) => prev.filter((s) => s.id !== id))
      if (activeSessionId === id) {
        startNewChat()
      }
      try {
        await deleteSessionApi(token, id)
      } catch (e) {
        console.error('Failed to delete session:', e)
        // Re-fetch to restore if delete failed
        loadSessions()
      }
    },
    [token, activeSessionId, startNewChat, loadSessions],
  )

  // Retry last failed message
  const retry = useCallback(() => {
    if (!lastFailedMessage) return
    // Remove the failed user message from the list
    setMessages((prev) => prev.slice(0, -1))
    setStreamingMessage(null)
    setError(null)
    const msg = lastFailedMessage
    setLastFailedMessage(null)
    sendMessage(msg)
  }, [lastFailedMessage, sendMessage])

  const clearError = useCallback(() => {
    setError(null)
  }, [])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort()
    }
  }, [])

  return {
    sessions,
    activeSessionId,
    messages,
    streamingMessage,
    isLoading,
    isSending,
    error,
    lastFailedMessage,
    loadSessions,
    selectSession,
    startNewChat,
    sendMessage,
    deleteSession,
    retry,
    clearError,
  }
}
