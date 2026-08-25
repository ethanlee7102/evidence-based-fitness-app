import { useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { useProfile } from '../../onboarding/hooks'
import { useWorkoutHistory } from '../../workouts/hooks/useWorkoutHistory'
import { formatVolume } from '../../workouts/utils/unitConversion'
import type { WorkoutSummary } from '../../workouts/types'

function StatTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-4">
      <p className="text-2xl font-semibold">{value}</p>
      <p className="text-sm text-gray-400 mt-1">{label}</p>
    </div>
  )
}

function relativeDate(iso: string): string {
  const then = new Date(iso)
  const days = Math.floor((Date.now() - then.getTime()) / 86_400_000)
  if (days <= 0) return 'Today'
  if (days === 1) return 'Yesterday'
  if (days < 7) return `${days} days ago`
  return then.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

export function HomeDashboardScreen() {
  const navigate = useNavigate()
  const { profile } = useProfile()
  const units = profile?.unitsPreference ?? 'metric'
  const { workouts, isLoading } = useWorkoutHistory()

  const completed = useMemo(
    () => workouts.filter((w: WorkoutSummary) => w.completed_at !== null),
    [workouts],
  )

  const stats = useMemo(() => {
    const totalSets = completed.reduce((s, w) => s + w.set_count, 0)
    const totalVolume = completed.reduce((s, w) => s + w.total_volume_kg, 0)
    return { count: completed.length, totalSets, totalVolume, last: completed[0]?.started_at }
  }, [completed])

  const recent = completed.slice(0, 5)
  const dash = isLoading ? '-' : undefined

  return (
    <div className="max-w-4xl mx-auto">
      <h1 className="text-3xl font-bold mb-2">
        Welcome{profile?.displayName ? `, ${profile.displayName}` : ''}!
      </h1>
      <p className="text-gray-400 mb-8">Your last 20 sessions at a glance.</p>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 mb-8">
        <StatTile label="Recent workouts" value={dash ?? String(stats.count)} />
        <StatTile label="Recent sets" value={dash ?? String(stats.totalSets)} />
        <StatTile label="Recent volume" value={dash ?? formatVolume(stats.totalVolume, units)} />
        <StatTile
          label="Last session"
          value={dash ?? (stats.last ? relativeDate(stats.last) : '-')}
        />
      </div>

      <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Recent Activity</h2>
          {recent.length > 0 && (
            <button
              onClick={() => navigate('/dashboard/workouts/history')}
              className="text-sm text-flame-400 hover:text-flame-300"
            >
              View all
            </button>
          )}
        </div>

        {isLoading ? (
          <p className="text-gray-400">Loading...</p>
        ) : recent.length === 0 ? (
          <p className="text-gray-400">No workouts logged yet. Start your first one!</p>
        ) : (
          <ul className="divide-y divide-gray-700">
            {recent.map((w) => (
              <li
                key={w.id}
                onClick={() => navigate('/dashboard/workouts/history')}
                className="py-3 -mx-2 px-2 rounded flex items-center justify-between cursor-pointer hover:bg-gray-700/30"
              >
                <div>
                  <p className="font-medium">
                    {new Date(w.started_at).toLocaleDateString(undefined, {
                      weekday: 'short',
                      month: 'short',
                      day: 'numeric',
                    })}
                  </p>
                  <p className="text-sm text-gray-400">
                    {w.exercise_count} exercises · {w.set_count} sets
                  </p>
                </div>
                <span className="text-sm text-gray-300">
                  {formatVolume(w.total_volume_kg, units)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="mt-8 text-center">
        <button
          type="button"
          onClick={() => navigate('/dashboard/workouts')}
          className="px-8 py-4 bg-flame-600 hover:bg-flame-500 rounded-xl font-medium text-lg transition-colors"
        >
          Log Workout
        </button>
      </div>
    </div>
  )
}
