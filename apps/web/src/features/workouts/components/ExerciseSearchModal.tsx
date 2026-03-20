import { useState, useCallback, useEffect, useRef } from 'react'
import { useAuth } from '../../auth/hooks/useAuth'
import { searchExercises, getRecentExercises } from '../services/workoutService'
import type { Exercise } from '../types'
import { MUSCLE_CATEGORIES, EQUIPMENT_OPTIONS } from '../types'

interface ExerciseSearchModalProps {
  onSelect: (exercise: Exercise) => void
  onClose: () => void
  onCreateCustom: () => void
}

export function ExerciseSearchModal({
  onSelect,
  onClose,
  onCreateCustom,
}: ExerciseSearchModalProps) {
  const { session: authSession } = useAuth()
  const token = authSession?.access_token

  const [query, setQuery] = useState('')
  const [equipment, setEquipment] = useState<string>('')
  const [muscleCategory, setMuscleCategory] = useState<string>('')
  const [results, setResults] = useState<Exercise[]>([])
  const [recentExercises, setRecentExercises] = useState<Exercise[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const debounceRef = useRef<ReturnType<typeof setTimeout>>()

  // Focus search input on mount
  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  // Fetch recent exercises on mount
  useEffect(() => {
    if (!token) return
    getRecentExercises(token, 10)
      .then(setRecentExercises)
      .catch(() => {})
  }, [token])

  // Search with debounce
  useEffect(() => {
    if (!token) return

    if (debounceRef.current) clearTimeout(debounceRef.current)

    debounceRef.current = setTimeout(async () => {
      setIsLoading(true)
      try {
        const data = await searchExercises(token, {
          q: query || undefined,
          equipment: equipment || undefined,
          muscle_category: muscleCategory || undefined,
        })
        setResults(data)
      } catch (e) {
        console.error('Search failed:', e)
      } finally {
        setIsLoading(false)
      }
    }, 300)

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
  }, [token, query, equipment, muscleCategory])

  const handleSelect = useCallback(
    (exercise: Exercise) => {
      onSelect(exercise)
      onClose()
    },
    [onSelect, onClose],
  )

  return (
    <div className="fixed inset-0 z-[60] bg-gray-900/95 flex justify-center">
      <div className="flex flex-col w-full max-w-2xl">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-700">
        <h2 className="text-lg font-semibold">Add Exercise</h2>
        <button
          type="button"
          onClick={onClose}
          className="text-gray-400 hover:text-gray-200 p-1"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
          </svg>
        </button>
      </div>

      {/* Search bar */}
      <div className="p-4 space-y-3">
        <input
          ref={inputRef}
          type="text"
          placeholder="Search exercises..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-sm
            placeholder-gray-500 focus:outline-none focus:border-flame-500"
        />

        {/* Filters */}
        <div className="flex gap-2">
          <select
            value={muscleCategory}
            onChange={(e) => setMuscleCategory(e.target.value)}
            className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-gray-300"
          >
            <option value="">All Muscles</option>
            {MUSCLE_CATEGORIES.map((cat) => (
              <option key={cat} value={cat}>
                {cat}
              </option>
            ))}
          </select>

          <select
            value={equipment}
            onChange={(e) => setEquipment(e.target.value)}
            className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-gray-300"
          >
            <option value="">All Equipment</option>
            {EQUIPMENT_OPTIONS.map((eq) => (
              <option key={eq} value={eq}>
                {eq.charAt(0).toUpperCase() + eq.slice(1)}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Results */}
      <div className="flex-1 overflow-y-auto px-4 pb-4 [&::-webkit-scrollbar]:w-2 [&::-webkit-scrollbar-track]:bg-transparent [&::-webkit-scrollbar-thumb]:bg-gray-700 [&::-webkit-scrollbar-thumb]:rounded-full">
        {/* Recent exercises — shown when no search/filters active */}
        {!query && !equipment && !muscleCategory && recentExercises.length > 0 && !isLoading && (
          <div className="mb-4">
            <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">Recent</h3>
            <div className="space-y-1">
              {recentExercises.map((exercise) => {
                const primaryMuscles = exercise.muscles
                  ?.filter(
                    (m) =>
                      m.activation_level === 'maximum' ||
                      m.activation_level === 'high',
                  )
                  .map((m) => m.muscle_group_name)
                  .slice(0, 3)

                return (
                  <button
                    key={`recent-${exercise.id}`}
                    type="button"
                    onClick={() => handleSelect(exercise)}
                    className="w-full text-left p-3 rounded-lg hover:bg-gray-800 transition-colors"
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium text-sm">{exercise.name}</p>
                        <div className="flex items-center gap-2 text-xs text-gray-500">
                          {exercise.equipment && (
                            <span className="capitalize">{exercise.equipment}</span>
                          )}
                          {primaryMuscles && primaryMuscles.length > 0 && (
                            <span>{primaryMuscles.join(', ')}</span>
                          )}
                        </div>
                      </div>
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        className="h-5 w-5 text-gray-600"
                        viewBox="0 0 20 20"
                        fill="currentColor"
                      >
                        <path
                          fillRule="evenodd"
                          d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z"
                          clipRule="evenodd"
                        />
                      </svg>
                    </div>
                  </button>
                )
              })}
            </div>
            <div className="border-b border-gray-700 mt-3" />
          </div>
        )}

        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-flame-500" />
          </div>
        ) : results.length === 0 ? (
          <div className="text-center py-8">
            <p className="text-gray-500 mb-4">No exercises found</p>
            <button
              type="button"
              onClick={onCreateCustom}
              className="text-flame-400 hover:text-flame-300 text-sm font-medium"
            >
              Create Custom Exercise
            </button>
          </div>
        ) : (
          <div className="space-y-1">
            {results.map((exercise) => {
              const primaryMuscles = exercise.muscles
                ?.filter(
                  (m) =>
                    m.activation_level === 'maximum' ||
                    m.activation_level === 'high',
                )
                .map((m) => m.muscle_group_name)
                .slice(0, 3)

              return (
                <button
                  key={exercise.id}
                  type="button"
                  onClick={() => handleSelect(exercise)}
                  className="w-full text-left p-3 rounded-lg hover:bg-gray-800 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium text-sm">{exercise.name}</p>
                      <div className="flex items-center gap-2 text-xs text-gray-500">
                        {exercise.equipment && (
                          <span className="capitalize">{exercise.equipment}</span>
                        )}
                        {primaryMuscles && primaryMuscles.length > 0 && (
                          <span>{primaryMuscles.join(', ')}</span>
                        )}
                      </div>
                    </div>
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      className="h-5 w-5 text-gray-600"
                      viewBox="0 0 20 20"
                      fill="currentColor"
                    >
                      <path
                        fillRule="evenodd"
                        d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z"
                        clipRule="evenodd"
                      />
                    </svg>
                  </div>
                </button>
              )
            })}

            {/* Create custom at bottom */}
            <button
              type="button"
              onClick={onCreateCustom}
              className="w-full text-left p-3 rounded-lg hover:bg-gray-800 transition-colors border border-dashed border-gray-700"
            >
              <p className="text-sm text-flame-400 font-medium">
                + Create Custom Exercise
              </p>
            </button>
          </div>
        )}
      </div>
      </div>
    </div>
  )
}
