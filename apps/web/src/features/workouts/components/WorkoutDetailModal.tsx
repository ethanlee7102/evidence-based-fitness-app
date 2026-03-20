import { useState, useEffect } from 'react'
import { useAuth } from '../../auth/hooks/useAuth'
import { getWorkout } from '../services/workoutService'
import { formatDuration, formatVolume, displayWeight, weightUnit } from '../utils/unitConversion'
import { useProfile } from '../../onboarding/hooks/useProfile'
import type { Workout } from '../types'

interface WorkoutDetailModalProps {
  workoutId: string
  onClose: () => void
}

export function WorkoutDetailModal({ workoutId, onClose }: WorkoutDetailModalProps) {
  const { session: authSession } = useAuth()
  const token = authSession?.access_token
  const { profile } = useProfile()
  const units = profile?.unitsPreference ?? 'metric'

  const [workout, setWorkout] = useState<Workout | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!token) return
    setIsLoading(true)
    getWorkout(token, workoutId)
      .then(setWorkout)
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load workout'))
      .finally(() => setIsLoading(false))
  }, [token, workoutId])

  // Compute stats
  let completedSets = 0
  let totalVolume = 0

  if (workout) {
    for (const we of workout.exercises) {
      for (const s of we.sets) {
        if (s.completed) {
          completedSets++
          totalVolume += (s.weight_kg ?? 0) * (s.reps ?? 0)
        }
      }
    }
  }

  if (isLoading) {
    return (
      <div className="fixed inset-0 z-50 bg-gray-900 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-flame-500" />
      </div>
    )
  }

  if (error || !workout) {
    return (
      <div className="fixed inset-0 z-50 bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-400 mb-4">{error || 'Workout not found'}</p>
          <button
            type="button"
            onClick={onClose}
            className="text-flame-400 hover:text-flame-300"
          >
            Go Back
          </button>
        </div>
      </div>
    )
  }

  const date = new Date(workout.started_at)
  const dateStr = date.toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  })
  const timeStr = date.toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
  })

  return (
    <div className="fixed inset-0 z-50 bg-gray-900 flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-700">
        <button type="button" onClick={onClose} className="text-gray-400 hover:text-gray-200">
          <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
          </svg>
        </button>
        <div className="text-center">
          <h2 className="font-semibold">{dateStr}</h2>
          <p className="text-sm text-gray-400">{timeStr}</p>
        </div>
        <div className="w-6" />
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 max-w-2xl mx-auto w-full">
        {/* Stats grid */}
        <div className="grid grid-cols-4 gap-3">
          <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-3 text-center">
            <p className="text-lg font-bold">
              {workout.duration_seconds != null ? formatDuration(workout.duration_seconds) : '-'}
            </p>
            <p className="text-xs text-gray-500">Duration</p>
          </div>
          <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-3 text-center">
            <p className="text-lg font-bold">{workout.exercises.length}</p>
            <p className="text-xs text-gray-500">Exercises</p>
          </div>
          <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-3 text-center">
            <p className="text-lg font-bold">{completedSets}</p>
            <p className="text-xs text-gray-500">Sets</p>
          </div>
          <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-3 text-center">
            <p className="text-lg font-bold">{formatVolume(totalVolume, units)}</p>
            <p className="text-xs text-gray-500">Volume</p>
          </div>
        </div>

        {/* Metadata */}
        {(workout.rating != null || workout.body_weight_kg != null || workout.notes) && (
          <div className="space-y-2">
            {workout.rating != null && (
              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-400">Rating:</span>
                <div className="flex gap-0.5">
                  {[1, 2, 3, 4, 5].map((star) => (
                    <svg
                      key={star}
                      xmlns="http://www.w3.org/2000/svg"
                      className={`h-5 w-5 ${star <= workout.rating! ? 'text-yellow-400' : 'text-gray-600'}`}
                      viewBox="0 0 20 20"
                      fill="currentColor"
                    >
                      <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                    </svg>
                  ))}
                </div>
              </div>
            )}
            {workout.body_weight_kg != null && (
              <p className="text-sm text-gray-400">
                Body weight: {displayWeight(workout.body_weight_kg, units)} {weightUnit(units)}
              </p>
            )}
            {workout.notes && (
              <p className="text-sm text-gray-400 italic">{workout.notes}</p>
            )}
          </div>
        )}

        {/* Exercise list */}
        {workout.exercises.map((we) => {
          const muscles = we.exercise.muscles
            ?.filter((m) => m.activation_level === 'maximum' || m.activation_level === 'high')
            .map((m) => m.muscle_group_name)
            .slice(0, 3)

          const hasRpe = we.sets.some((s) => s.rpe != null)

          return (
            <div key={we.id} className="bg-gray-800/50 border border-gray-700 rounded-xl overflow-hidden">
              <div className="p-3">
                <h3 className="font-semibold text-sm">{we.exercise.name}</h3>
                {muscles && muscles.length > 0 && (
                  <p className="text-xs text-gray-500">{muscles.join(', ')}</p>
                )}
              </div>

              <div className="px-3 pb-3">
                {/* Header */}
                <div className="flex items-center gap-3 py-1 text-xs text-gray-500 font-medium">
                  <div className="w-8 text-center">SET</div>
                  <div className="flex-1 text-center">{weightUnit(units).toUpperCase()}</div>
                  <div className="flex-1 text-center">REPS</div>
                  {hasRpe && <div className="w-12 text-center">RPE</div>}
                  <div className="w-16 text-center">TYPE</div>
                </div>

                {/* Sets */}
                {we.sets.map((s) => (
                  <div
                    key={s.id}
                    className={`flex items-center gap-3 py-1.5 text-sm ${
                      s.completed ? 'text-gray-200' : 'text-gray-500'
                    }`}
                  >
                    <div className="w-8 text-center text-gray-500 font-medium">
                      {s.set_type !== 'normal' ? s.set_type.charAt(0).toUpperCase() : s.set_number}
                    </div>
                    <div className="flex-1 text-center">
                      {s.weight_kg != null ? displayWeight(s.weight_kg, units) : '-'}
                    </div>
                    <div className="flex-1 text-center">
                      {s.reps != null ? s.reps : '-'}
                    </div>
                    {hasRpe && (
                      <div className="w-12 text-center">
                        {s.rpe != null ? s.rpe : '-'}
                      </div>
                    )}
                    <div className="w-16 text-center">
                      {s.set_type !== 'normal' && (
                        <span className="text-xs px-1.5 py-0.5 rounded bg-gray-700 text-gray-400 capitalize">
                          {s.set_type}
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
