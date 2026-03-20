import { useState, useCallback } from 'react'
import type { PreviousSetData, WorkoutExercise, WorkoutSet } from '../types'
import { SetRow } from './SetRow'
import { weightUnit } from '../utils/unitConversion'
import { useProfile } from '../../onboarding/hooks/useProfile'

const REST_PRESETS: { label: string; value: number | null }[] = [
  { label: '30s', value: 30 },
  { label: '1:00', value: 60 },
  { label: '1:30', value: 90 },
  { label: '2:00', value: 120 },
  { label: '3:00', value: 180 },
  { label: 'Off', value: null },
]

function formatRestTime(seconds: number): string {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  if (m > 0) return s > 0 ? `${m}:${String(s).padStart(2, '0')}` : `${m}:00`
  return `${s}s`
}

interface ExerciseCardProps {
  workoutExercise: WorkoutExercise
  previousSets: PreviousSetData[]
  onAddSet: (workoutExerciseId: string) => void
  onUpdateSet: (setId: string, updates: Partial<WorkoutSet>) => void
  onDeleteSet: (workoutExerciseId: string, setId: string) => void
  onRemoveExercise: (workoutExerciseId: string) => void
  onReorder: (workoutExerciseId: string, direction: 'up' | 'down') => void
  onUpdateExercise?: (workoutExerciseId: string, updates: { rest_timer_seconds?: number | null; notes?: string | null }) => void
  isFirst: boolean
  isLast: boolean
}

export function ExerciseCard({
  workoutExercise,
  previousSets,
  onAddSet,
  onUpdateSet,
  onDeleteSet,
  onRemoveExercise,
  onReorder,
  onUpdateExercise,
  isFirst,
  isLast,
}: ExerciseCardProps) {
  const { profile } = useProfile()
  const units = profile?.unitsPreference ?? 'metric'
  const [collapsed, setCollapsed] = useState(false)
  const [showMenu, setShowMenu] = useState(false)
  const [showRestMenu, setShowRestMenu] = useState(false)

  const exercise = workoutExercise.exercise
  const sets = workoutExercise.sets
  const restTimerSeconds = workoutExercise.rest_timer_seconds

  const handleDelete = useCallback(
    (setId: string) => {
      onDeleteSet(workoutExercise.id, setId)
    },
    [workoutExercise.id, onDeleteSet],
  )

  const handleRestSelect = useCallback(
    (value: number | null) => {
      onUpdateExercise?.(workoutExercise.id, { rest_timer_seconds: value })
      setShowRestMenu(false)
    },
    [workoutExercise.id, onUpdateExercise],
  )

  const muscles = exercise.muscles
    ?.filter((m) => m.activation_level === 'maximum' || m.activation_level === 'high')
    .map((m) => m.muscle_group_name)
    .slice(0, 3)

  return (
    <div className="bg-gray-800/50 border border-gray-700 rounded-xl overflow-hidden">
      {/* Header */}
      <div
        className="flex items-center justify-between p-3 cursor-pointer"
        onClick={() => setCollapsed(!collapsed)}
      >
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-sm truncate">{exercise.name}</h3>
          {muscles && muscles.length > 0 && (
            <p className="text-xs text-gray-500 truncate">{muscles.join(', ')}</p>
          )}
        </div>

        <div className="flex items-center gap-1 flex-shrink-0">
          {/* Rest time display */}
          {restTimerSeconds != null && (
            <span className="text-xs text-flame-400 mr-1">
              {formatRestTime(restTimerSeconds)}
            </span>
          )}

          <span className="text-xs text-gray-500 mr-1">
            {sets.filter((s) => s.completed).length}/{sets.length} sets
          </span>

          {/* Clock icon for rest timer config */}
          {onUpdateExercise && (
            <div className="relative">
              <button
                type="button"
                aria-label="Rest timer"
                onClick={(e) => {
                  e.stopPropagation()
                  setShowRestMenu(!showRestMenu)
                }}
                className={`p-1 ${restTimerSeconds != null ? 'text-flame-400' : 'text-gray-500'} hover:text-gray-300`}
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
                </svg>
              </button>
              {showRestMenu && (
                <>
                  <div className="fixed inset-0 z-10" onClick={(e) => { e.stopPropagation(); setShowRestMenu(false) }} />
                  <div className="absolute right-0 top-8 z-20 bg-gray-700 border border-gray-600 rounded-lg shadow-lg py-1 min-w-[100px]">
                    {REST_PRESETS.map((preset) => (
                      <button
                        key={preset.label}
                        type="button"
                        className={`w-full text-left px-3 py-1.5 text-sm hover:bg-gray-600 ${
                          restTimerSeconds === preset.value ? 'text-flame-400' : 'text-gray-300'
                        }`}
                        onClick={(e) => {
                          e.stopPropagation()
                          handleRestSelect(preset.value)
                        }}
                      >
                        {preset.label}
                      </button>
                    ))}
                  </div>
                </>
              )}
            </div>
          )}

          {/* Three-dot menu */}
          <div className="relative">
            <button
              type="button"
              aria-label="Exercise options"
              onClick={(e) => {
                e.stopPropagation()
                setShowMenu(!showMenu)
              }}
              className="p-1 text-gray-500 hover:text-gray-300"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                <path d="M10 6a2 2 0 110-4 2 2 0 010 4zM10 12a2 2 0 110-4 2 2 0 010 4zM10 18a2 2 0 110-4 2 2 0 010 4z" />
              </svg>
            </button>
            {showMenu && (
              <>
                <div className="fixed inset-0 z-10" onClick={() => setShowMenu(false)} />
                <div className="absolute right-0 top-8 z-20 bg-gray-700 border border-gray-600 rounded-lg shadow-lg py-1 min-w-[140px]">
                  {!isFirst && (
                    <button
                      type="button"
                      className="w-full text-left px-3 py-1.5 text-sm text-gray-300 hover:bg-gray-600"
                      onClick={(e) => {
                        e.stopPropagation()
                        onReorder(workoutExercise.id, 'up')
                        setShowMenu(false)
                      }}
                    >
                      Move Up
                    </button>
                  )}
                  {!isLast && (
                    <button
                      type="button"
                      className="w-full text-left px-3 py-1.5 text-sm text-gray-300 hover:bg-gray-600"
                      onClick={(e) => {
                        e.stopPropagation()
                        onReorder(workoutExercise.id, 'down')
                        setShowMenu(false)
                      }}
                    >
                      Move Down
                    </button>
                  )}
                  <button
                    type="button"
                    className="w-full text-left px-3 py-1.5 text-sm text-red-400 hover:bg-gray-600"
                    onClick={(e) => {
                      e.stopPropagation()
                      if (window.confirm(`Remove ${exercise.name}?`)) {
                        onRemoveExercise(workoutExercise.id)
                      }
                      setShowMenu(false)
                    }}
                  >
                    Remove Exercise
                  </button>
                </div>
              </>
            )}
          </div>

          {/* Collapse arrow */}
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className={`h-5 w-5 text-gray-500 transition-transform ${collapsed ? '' : 'rotate-180'}`}
            viewBox="0 0 20 20"
            fill="currentColor"
          >
            <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
          </svg>
        </div>
      </div>

      {/* Sets table */}
      {!collapsed && (
        <div className="px-3 pb-3">
          {/* Header row */}
          <div className="flex items-center gap-2 py-1 text-xs text-gray-500 font-medium">
            <div className="w-8 text-center">SET</div>
            <div className="w-24 text-center">PREV</div>
            <div className="flex-1 text-center">{weightUnit(units).toUpperCase()}</div>
            <div className="flex-1 text-center">REPS</div>
            <div className="w-14 text-center">RPE</div>
            <div className="w-8" /> {/* checkmark space */}
            <div className="w-5" /> {/* menu space */}
          </div>

          {/* Set rows */}
          {sets.map((set) => (
            <SetRow
              key={set.id}
              set={set}
              previous={previousSets.find((p) => p.set_number === set.set_number)}
              onUpdate={onUpdateSet}
              onDelete={handleDelete}
            />
          ))}

          {/* Add set button */}
          <button
            type="button"
            onClick={() => onAddSet(workoutExercise.id)}
            className="w-full mt-2 py-1.5 text-sm text-gray-400 hover:text-gray-300 hover:bg-gray-700/50 rounded-lg transition-colors"
          >
            + Add Set
          </button>
        </div>
      )}
    </div>
  )
}
