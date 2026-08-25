import type { WorkoutSummary } from '../types'
import { formatDuration, formatVolume } from '../utils/unitConversion'
import { useProfile } from '../../onboarding/hooks/useProfile'
import { useAuth, useIsGuest } from '../../auth/hooks'

interface WorkoutHistoryCardProps {
  workout: WorkoutSummary
  onView: (id: string) => void
  onResume: (id: string) => void
  onDelete: (id: string) => void
}

export function WorkoutHistoryCard({ workout, onView, onResume, onDelete }: WorkoutHistoryCardProps) {
  const { profile } = useProfile()
  const units = profile?.unitsPreference ?? 'metric'
  const { user } = useAuth()
  const isGuest = useIsGuest()
  // Guests may delete their OWN logged workouts, but the seeded demo history is
  // owned by the demo athlete, so hide delete there (it would 404 anyway).
  const canDelete = !isGuest || workout.user_id === user?.id

  const date = new Date(workout.started_at)
  const dateStr = date.toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
  })
  const timeStr = date.toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
  })

  const isComplete = workout.completed_at !== null

  return (
    <div
      className="bg-gray-800/50 border border-gray-700 rounded-xl p-4 hover:border-gray-600 transition-colors cursor-pointer"
      onClick={() => (isComplete ? onView(workout.id) : onResume(workout.id))}
    >
      <div className="flex items-start justify-between mb-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-semibold">{dateStr}</span>
            <span
              className={`text-xs px-2 py-0.5 rounded-full ${
                isComplete
                  ? 'bg-green-900/50 text-green-400'
                  : 'bg-yellow-900/50 text-yellow-400'
              }`}
            >
              {isComplete ? 'Completed' : 'In Progress'}
            </span>
          </div>
          <p className="text-sm text-gray-400">{timeStr}</p>
        </div>

        <div className="flex items-center gap-1">
          {!isComplete && (
            <button
              type="button"
              className="text-sm font-medium text-flame-400 hover:text-flame-300 px-3 py-1 rounded-lg hover:bg-flame-400/10 transition-colors"
              onClick={(e) => {
                e.stopPropagation()
                onResume(workout.id)
              }}
            >
              Resume
            </button>
          )}
          {canDelete && (
            <button
              type="button"
              className="text-gray-500 hover:text-red-400 transition-colors p-1"
              aria-label="Delete workout"
              onClick={(e) => {
                e.stopPropagation()
                onDelete(workout.id)
              }}
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                <path
                  fillRule="evenodd"
                  d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z"
                  clipRule="evenodd"
                />
              </svg>
            </button>
          )}
        </div>
      </div>

      <div className="flex items-center gap-4 text-sm text-gray-400">
        <div className="flex items-center gap-1">
          <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
            <path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.429A1 1 0 009 15.571V11a1 1 0 112 0v4.571a1 1 0 00.725.962l5 1.428a1 1 0 001.17-1.408l-7-14z" />
          </svg>
          <span>{workout.exercise_count} exercises</span>
        </div>
        <div className="flex items-center gap-1">
          <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
          </svg>
          <span>
            {workout.duration_seconds
              ? formatDuration(workout.duration_seconds)
              : '--:--'}
          </span>
        </div>
        <div className="flex items-center gap-1">
          <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M3 3a1 1 0 000 2v8a2 2 0 002 2h2.586l-1.293 1.293a1 1 0 101.414 1.414L10 15.414l2.293 2.293a1 1 0 001.414-1.414L12.414 15H15a2 2 0 002-2V5a1 1 0 100-2H3zm11 4a1 1 0 10-2 0v4a1 1 0 102 0V7zm-3 1a1 1 0 10-2 0v3a1 1 0 102 0V8zM8 9a1 1 0 00-2 0v2a1 1 0 102 0V9z" clipRule="evenodd" />
          </svg>
          <span>{formatVolume(workout.total_volume_kg, units)}</span>
        </div>
        {workout.set_count > 0 && (
          <span>{workout.set_count} sets</span>
        )}
        {workout.rating && (
          <div className="flex items-center gap-0.5">
            {Array.from({ length: workout.rating }, (_, i) => (
              <svg key={i} xmlns="http://www.w3.org/2000/svg" className="h-3.5 w-3.5 text-yellow-400" viewBox="0 0 20 20" fill="currentColor">
                <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
              </svg>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
