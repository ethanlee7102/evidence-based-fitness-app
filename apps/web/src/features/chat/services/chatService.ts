import { apiRequest } from '../../../lib/api'
import type { ChatMessageData, ChatSession, SendMessageRequest, SSECallbacks } from '../types'

const API_BASE = import.meta.env.VITE_API_URL || '/api'

export async function getSessions(token: string): Promise<ChatSession[]> {
  return apiRequest<ChatSession[]>('/chat/sessions', { token })
}

export async function getSession(token: string, sessionId: string): Promise<ChatSession> {
  return apiRequest<ChatSession>(`/chat/sessions/${sessionId}`, { token })
}

export async function getMessages(token: string, sessionId: string): Promise<ChatMessageData[]> {
  return apiRequest<ChatMessageData[]>(`/chat/sessions/${sessionId}/messages`, { token })
}

export async function deleteSession(token: string, sessionId: string): Promise<void> {
  await apiRequest(`/chat/sessions/${sessionId}`, { method: 'DELETE', token })
}

export async function sendMessageSSE(
  token: string,
  request: SendMessageRequest,
  callbacks: SSECallbacks,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch(`${API_BASE}/chat/message`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(request),
    signal,
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }))
    callbacks.onError({ detail: error.detail || 'Request failed' })
    return
  }

  const reader = response.body?.getReader()
  if (!reader) {
    callbacks.onError({ detail: 'No response stream available' })
    return
  }

  const decoder = new TextDecoder()
  let buffer = ''

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })

      // Split on double newline to find complete SSE events
      const parts = buffer.split('\n\n')
      // Last part may be incomplete — keep it in buffer
      buffer = parts.pop() || ''

      for (const part of parts) {
        if (!part.trim()) continue

        let eventName = ''
        let eventData = ''

        for (const line of part.split('\n')) {
          if (line.startsWith('event: ')) {
            eventName = line.slice(7)
          } else if (line.startsWith('data: ')) {
            eventData = line.slice(6)
          }
        }

        if (!eventName || !eventData) continue

        try {
          const parsed = JSON.parse(eventData)

          switch (eventName) {
            case 'session':
              callbacks.onSession(parsed)
              break
            case 'citations':
              callbacks.onCitations(parsed)
              break
            case 'data':
              callbacks.onData(parsed)
              break
            case 'done':
              callbacks.onDone(parsed)
              break
            case 'error':
              callbacks.onError(parsed)
              break
          }
        } catch {
          // Skip malformed JSON
        }
      }
    }
  } finally {
    reader.releaseLock()
  }
}
