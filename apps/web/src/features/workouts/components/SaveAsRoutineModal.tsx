import { useState, useCallback } from 'react'
import { useAuth } from '../../auth/hooks/useAuth'
import { saveWorkoutAsRoutine } from '../services/workoutService'

interface SaveAsRoutineModalProps {
  workoutId: string
  onSaved: () => void
  onClose: () => void
}

export function SaveAsRoutineModal({ workoutId, onSaved, onClose }: SaveAsRoutineModalProps) {
  const { session: authSession } = useAuth()
  const token = authSession?.access_token

  const [name, setName] = useState('')
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSave = useCallback(async () => {
    if (!token || !name.trim()) {
      setError('Enter a routine name')
      return
    }

    setIsSaving(true)
    setError(null)

    try {
      await saveWorkoutAsRoutine(token, workoutId, name.trim())
      onSaved()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to save routine')
    } finally {
      setIsSaving(false)
    }
  }, [token, workoutId, name, onSaved])

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />

      <div className="relative z-10 bg-gray-900 border border-gray-700 rounded-2xl w-full max-w-sm mx-4 p-6">
        <h2 className="text-lg font-semibold mb-4">Save as Routine</h2>

        {error && (
          <div className="bg-red-900/30 border border-red-700 rounded-lg p-2 mb-3 text-xs text-red-300">
            {error}
          </div>
        )}

        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Routine name (e.g. Push Day)"
          maxLength={100}
          autoFocus
          className="w-full bg-gray-800/50 border border-gray-700 rounded-lg px-4 py-2.5 text-sm placeholder-gray-600 focus:outline-none focus:border-flame-500 mb-4"
          onKeyDown={(e) => {
            if (e.key === 'Enter') handleSave()
          }}
        />

        <div className="flex gap-3">
          <button
            type="button"
            onClick={onClose}
            className="flex-1 py-2 text-sm text-gray-400 hover:text-gray-300 border border-gray-700 rounded-lg transition-colors"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSave}
            disabled={isSaving || !name.trim()}
            className="flex-1 py-2 text-sm font-medium bg-flame-500 hover:bg-flame-600 text-white rounded-lg transition-colors disabled:opacity-50"
          >
            {isSaving ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  )
}
