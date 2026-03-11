import { Flame } from 'lucide-react'
import { SUGGESTED_QUESTIONS } from '../types'

interface SuggestedQuestionsProps {
  onSelect: (question: string) => void
}

export function SuggestedQuestions({ onSelect }: SuggestedQuestionsProps) {
  return (
    <div className="flex flex-col items-center justify-center h-full px-4">
      <div className="flex items-center gap-2 mb-2">
        <Flame className="w-8 h-8 text-flame-500" />
        <h2 className="text-2xl font-bold text-white">Ask about exercise science</h2>
      </div>
      <p className="text-gray-400 mb-8 text-center">
        Get research-backed answers with cited sources
      </p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 w-full max-w-2xl">
        {SUGGESTED_QUESTIONS.map((question) => (
          <button
            key={question}
            onClick={() => onSelect(question)}
            className="text-left bg-gray-800/50 hover:bg-gray-800 border border-gray-700/50 hover:border-gray-600 rounded-xl px-4 py-3 text-sm text-gray-300 hover:text-white transition-colors"
          >
            {question}
          </button>
        ))}
      </div>
    </div>
  )
}
