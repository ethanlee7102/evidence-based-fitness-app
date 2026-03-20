// Chat feature types — snake_case matching backend wire format

export interface Citation {
  chunk_id: string
  title: string
  authors: string
  year: number
  category: string
  similarity: number
  journal: string | null
  doi: string | null
  section: string | null
  page_start: number | null
  page_end: number | null
}

export interface ChatSession {
  id: string
  user_id: string
  title: string | null
  created_at: string
  updated_at: string
}

export interface ChatMessageData {
  id: string
  session_id: string
  role: 'user' | 'assistant'
  content: string
  citations: Citation[] | null
  created_at: string
}

export interface StreamingMessage {
  role: 'assistant'
  content: string
  citations: Citation[]
  grounded: boolean
  isStreaming: boolean
}

export interface SendMessageRequest {
  message: string
  session_id?: string
  category?: string
}

export interface SSECallbacks {
  onSession: (data: { session_id: string; title: string | null }) => void
  onCitations: (data: { chunks: Citation[]; grounded: boolean }) => void
  onData: (data: { text: string }) => void
  onDone: (data: { message_id: string }) => void
  onError: (data: { detail: string }) => void
}

export const SUGGESTED_QUESTIONS = [
  'What rep range is best for muscle hypertrophy?',
  'How does protein timing affect muscle growth?',
  'Is periodized resistance training necessary for maximizing hypertrophy, and how do linear vs undulating compare?',
  'How does blood flow restriction training compare to heavy lifting for muscle and strength?',
  'How should I warm up before squats and bench press for the best performance?',
  'Can long-term stretching programs actually increase muscle strength or size?',
  'What is rate of force development and how can it be trained?',
  'What are supersets and are they as effective as traditional sets for building muscle?',
] as const
