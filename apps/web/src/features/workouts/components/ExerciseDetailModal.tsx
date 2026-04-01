import { useState, useEffect } from 'react'
import { X } from 'lucide-react'
import { useAuth } from '../../auth/hooks/useAuth'
import { getExercise, getExerciseStats } from '../services/workoutService'
import type { Exercise, ExerciseStats } from '../types'
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts'

interface ExerciseDetailModalProps {
  exerciseId: string
  onClose: () => void
}

const ACTIVATION_CONFIG: Record<string, { label: string; color: string; dot: string }> = {
  maximum: { label: 'Maximum', color: 'text-orange-400', dot: 'bg-orange-400' },
  high: { label: 'High', color: 'text-amber-400', dot: 'bg-amber-400' },
  medium: { label: 'Medium', color: 'text-yellow-400', dot: 'bg-yellow-400' },
  partial: { label: 'Partial', color: 'text-gray-400', dot: 'bg-gray-500' },
}

const ACTIVATION_ORDER = ['maximum', 'high', 'medium', 'partial']

export function ExerciseDetailModal({ exerciseId, onClose }: ExerciseDetailModalProps) {
  const { session: authSession } = useAuth()
  const token = authSession?.access_token

  const [exercise, setExercise] = useState<Exercise | null>(null)
  const [stats, setStats] = useState<ExerciseStats | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    if (!token) return

    setIsLoading(true)
    Promise.all([
      getExercise(token, exerciseId),
      getExerciseStats(token, exerciseId),
    ])
      .then(([ex, st]) => {
        setExercise(ex)
        setStats(st)
      })
      .catch(console.error)
      .finally(() => setIsLoading(false))
  }, [token, exerciseId])

  // Group muscles by activation level
  const muscleGroups = exercise
    ? ACTIVATION_ORDER.map((level) => ({
        level,
        config: ACTIVATION_CONFIG[level],
        muscles: exercise.muscles
          .filter((m) => m.activation_level === level)
          .map((m) => m.muscle_group_name),
      })).filter((g) => g.muscles.length > 0)
    : []

  const metadataItems = exercise
    ? [
        { label: 'Equipment', value: exercise.equipment },
        { label: 'Movement', value: exercise.movement_pattern },
        { label: 'Body Region', value: exercise.body_region },
        { label: 'Force Type', value: exercise.force_type },
        { label: 'Laterality', value: exercise.laterality },
        { label: 'Type', value: exercise.is_compound ? 'Compound' : 'Isolation' },
      ].filter((item) => item.value != null)
    : []

  return (
    <div className="fixed inset-0 z-[60] bg-gray-900/95 flex justify-center">
      <div className="flex flex-col w-full max-w-2xl">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-700">
          <button
            type="button"
            onClick={onClose}
            className="text-gray-400 hover:text-gray-200 p-1"
          >
            <X className="w-6 h-6" />
          </button>
          <h2 className="text-lg font-semibold truncate px-4">
            {exercise?.name || 'Loading...'}
          </h2>
          <div className="w-8" />
        </div>

        {/* Content */}
        {isLoading ? (
          <div className="flex items-center justify-center flex-1">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-flame-500" />
          </div>
        ) : exercise ? (
          <div className="flex-1 overflow-y-auto p-4 space-y-6 [&::-webkit-scrollbar]:w-2 [&::-webkit-scrollbar-track]:bg-transparent [&::-webkit-scrollbar-thumb]:bg-gray-700 [&::-webkit-scrollbar-thumb]:rounded-full">
            {/* Metadata grid */}
            {metadataItems.length > 0 && (
              <div className="grid grid-cols-3 gap-2">
                {metadataItems.map((item) => (
                  <div
                    key={item.label}
                    className="bg-gray-800/50 border border-gray-700 rounded-lg p-3"
                  >
                    <p className="text-xs text-gray-500 mb-0.5">{item.label}</p>
                    <p className="text-sm font-medium capitalize">{item.value}</p>
                  </div>
                ))}
              </div>
            )}

            {/* Muscles worked */}
            {muscleGroups.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-gray-300 mb-3">Muscles Worked</h3>
                <div className="space-y-3">
                  {muscleGroups.map((group) => (
                    <div key={group.level}>
                      <div className="flex items-center gap-2 mb-1.5">
                        <div className={`w-2 h-2 rounded-full ${group.config.dot}`} />
                        <span className={`text-xs font-medium ${group.config.color}`}>
                          {group.config.label}
                        </span>
                      </div>
                      <div className="flex flex-wrap gap-1.5 ml-4">
                        {group.muscles.map((name) => (
                          <span
                            key={name}
                            className="bg-gray-800 rounded-full px-3 py-1 text-xs text-gray-300"
                          >
                            {name}
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Instructions */}
            <div>
              <h3 className="text-sm font-semibold text-gray-300 mb-3">Instructions</h3>
              {exercise.instructions.length > 0 ? (
                <div className="space-y-2.5">
                  {exercise.instructions.map((step, i) => (
                    <div key={i} className="flex gap-3">
                      <div className="w-6 h-6 rounded-full bg-gray-800 text-xs flex items-center justify-center text-gray-400 shrink-0 mt-0.5">
                        {i + 1}
                      </div>
                      <p className="text-sm text-gray-300 leading-relaxed">{step}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-gray-600">No instructions available.</p>
              )}
            </div>

            {/* Your Stats */}
            <div>
              <h3 className="text-sm font-semibold text-gray-300 mb-3">Your Stats</h3>

              {stats && stats.recent_sets.length > 0 ? (
                <div className="space-y-4">
                  {/* Recent sets table */}
                  <div>
                    <p className="text-xs text-gray-500 mb-2">Recent Sets</p>
                    <div className="bg-gray-800/50 border border-gray-700 rounded-lg overflow-hidden">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b border-gray-700 text-xs text-gray-500">
                            <th className="text-left py-2 px-3 font-medium">Date</th>
                            <th className="text-right py-2 px-3 font-medium">Weight</th>
                            <th className="text-right py-2 px-3 font-medium">Reps</th>
                            <th className="text-right py-2 px-3 font-medium">RPE</th>
                            <th className="text-right py-2 px-3 font-medium">Volume</th>
                          </tr>
                        </thead>
                        <tbody>
                          {stats.recent_sets.map((set, i) => (
                            <tr
                              key={i}
                              className={i < stats.recent_sets.length - 1 ? 'border-b border-gray-700/50' : ''}
                            >
                              <td className="py-2 px-3 text-gray-400">{set.date}</td>
                              <td className="py-2 px-3 text-right text-gray-300">
                                {set.weight_kg != null ? `${set.weight_kg} kg` : '-'}
                              </td>
                              <td className="py-2 px-3 text-right text-gray-300">
                                {set.reps ?? '-'}
                              </td>
                              <td className="py-2 px-3 text-right text-gray-300">
                                {set.rpe ?? '-'}
                              </td>
                              <td className="py-2 px-3 text-right text-gray-300">
                                {set.volume > 0 ? `${set.volume}` : '-'}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>

                  {/* Volume chart */}
                  {stats.volume_history.length > 1 && (
                    <div>
                      <p className="text-xs text-gray-500 mb-2">Volume Over Time</p>
                      <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-3">
                        <ResponsiveContainer width="100%" height={200}>
                          <LineChart data={stats.volume_history}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                            <XAxis
                              dataKey="date"
                              tick={{ fontSize: 11, fill: '#6b7280' }}
                              tickLine={false}
                              axisLine={{ stroke: '#374151' }}
                            />
                            <YAxis
                              tick={{ fontSize: 11, fill: '#6b7280' }}
                              tickLine={false}
                              axisLine={{ stroke: '#374151' }}
                              width={50}
                            />
                            <Tooltip
                              contentStyle={{
                                backgroundColor: '#1f2937',
                                border: '1px solid #374151',
                                borderRadius: '0.5rem',
                                fontSize: '0.75rem',
                              }}
                              labelStyle={{ color: '#9ca3af' }}
                              formatter={(value) => [`${value} kg`, 'Volume']}
                            />
                            <Line
                              type="monotone"
                              dataKey="volume"
                              stroke="#f97316"
                              strokeWidth={2}
                              dot={{ r: 4, fill: '#f97316' }}
                              activeDot={{ r: 6 }}
                            />
                          </LineChart>
                        </ResponsiveContainer>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="bg-gray-800/30 border border-dashed border-gray-700 rounded-xl p-6 text-center">
                  <p className="text-sm text-gray-600">
                    No stats yet. Start logging this exercise to see your progress.
                  </p>
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-center flex-1">
            <p className="text-gray-500">Exercise not found.</p>
          </div>
        )}
      </div>
    </div>
  )
}
