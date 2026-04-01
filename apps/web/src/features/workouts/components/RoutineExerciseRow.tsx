import { ChevronUp, ChevronDown, Trash2, Plus, X } from 'lucide-react'
import type { RoutineExerciseInput, RoutineSetInput, SetType } from '../types'

interface RoutineExerciseRowProps {
  exercise: RoutineExerciseInput
  index: number
  total: number
  onRemove: () => void
  onMoveUp: () => void
  onMoveDown: () => void
  onUpdateExercise: (updates: Partial<RoutineExerciseInput>) => void
  onAddSet: () => void
  onRemoveSet: (setIndex: number) => void
  onUpdateSet: (setIndex: number, updates: Partial<RoutineSetInput>) => void
}

const REST_PRESETS = [30, 60, 90, 120, 180, 300]

function formatRest(seconds: number): string {
  if (seconds < 60) return `${seconds}s`
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return secs > 0 ? `${mins}m${secs}s` : `${mins}m`
}

export function RoutineExerciseRow({
  exercise,
  index,
  total,
  onRemove,
  onMoveUp,
  onMoveDown,
  onUpdateExercise,
  onAddSet,
  onRemoveSet,
  onUpdateSet,
}: RoutineExerciseRowProps) {
  const muscles = exercise.exercise.muscles
    ?.filter((m) => m.activation_level === 'maximum' || m.activation_level === 'high')
    .map((m) => m.muscle_group_name)
    .slice(0, 3)

  return (
    <div className="bg-gray-800/50 border border-gray-700 rounded-xl overflow-hidden">
      {/* Exercise header */}
      <div className="flex items-center justify-between p-3">
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-sm truncate">{exercise.exercise.name}</h3>
          {muscles && muscles.length > 0 && (
            <p className="text-xs text-gray-500">{muscles.join(', ')}</p>
          )}
        </div>

        <div className="flex items-center gap-0.5 ml-2">
          <button
            type="button"
            onClick={onMoveUp}
            disabled={index === 0}
            className="p-1 text-gray-500 hover:text-gray-300 disabled:opacity-30 disabled:cursor-default"
          >
            <ChevronUp className="w-4 h-4" />
          </button>
          <button
            type="button"
            onClick={onMoveDown}
            disabled={index === total - 1}
            className="p-1 text-gray-500 hover:text-gray-300 disabled:opacity-30 disabled:cursor-default"
          >
            <ChevronDown className="w-4 h-4" />
          </button>
          <button
            type="button"
            onClick={onRemove}
            className="p-1 text-gray-500 hover:text-red-400 transition-colors"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Rest timer */}
      <div className="px-3 pb-2">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs text-gray-500">Rest:</span>
          {REST_PRESETS.map((sec) => (
            <button
              key={sec}
              type="button"
              onClick={() =>
                onUpdateExercise({
                  rest_timer_seconds: exercise.rest_timer_seconds === sec ? null : sec,
                })
              }
              className={`text-xs px-2 py-0.5 rounded-full transition-colors ${
                exercise.rest_timer_seconds === sec
                  ? 'bg-flame-500/20 text-flame-400 border border-flame-500/40'
                  : 'bg-gray-700/50 text-gray-400 hover:bg-gray-700'
              }`}
            >
              {formatRest(sec)}
            </button>
          ))}
        </div>
      </div>

      {/* Sets table */}
      <div className="px-3 pb-3">
        {/* Header */}
        <div className="flex items-center gap-3 py-1 text-xs text-gray-500 font-medium">
          <div className="w-8 text-center">SET</div>
          <div className="flex-1 text-center">TARGET REPS</div>
          <div className="w-20 text-center">TYPE</div>
          <div className="w-6" />
        </div>

        {/* Set rows */}
        {exercise.sets.map((set, setIdx) => (
          <div key={setIdx} className="flex items-center gap-3 py-1.5">
            <div className="w-8 text-center text-xs text-gray-500 font-medium">
              {set.set_type !== 'normal' ? set.set_type.charAt(0).toUpperCase() : set.set_number}
            </div>
            <div className="flex-1 flex justify-center">
              <input
                type="number"
                inputMode="numeric"
                value={set.target_reps ?? ''}
                onChange={(e) => {
                  const val = e.target.value
                  onUpdateSet(setIdx, { target_reps: val === '' ? null : parseInt(val, 10) })
                }}
                placeholder="-"
                className="w-16 text-center bg-gray-700/50 border border-gray-600 rounded px-2 py-1 text-sm focus:outline-none focus:border-flame-500"
              />
            </div>
            <div className="w-20">
              <select
                value={set.set_type}
                onChange={(e) => onUpdateSet(setIdx, { set_type: e.target.value as SetType })}
                className="w-full text-xs bg-gray-700/50 border border-gray-600 rounded px-1.5 py-1 text-gray-300 focus:outline-none focus:border-flame-500"
              >
                <option value="normal">Normal</option>
                <option value="warmup">Warmup</option>
                <option value="dropset">Dropset</option>
                <option value="failure">Failure</option>
              </select>
            </div>
            <button
              type="button"
              onClick={() => onRemoveSet(setIdx)}
              className="w-6 text-gray-600 hover:text-red-400 transition-colors"
            >
              <X className="w-3.5 h-3.5 mx-auto" />
            </button>
          </div>
        ))}

        {/* Add set button */}
        <button
          type="button"
          onClick={onAddSet}
          className="flex items-center gap-1 text-xs text-flame-400 hover:text-flame-300 mt-1 px-1 py-0.5"
        >
          <Plus className="w-3 h-3" />
          Add Set
        </button>
      </div>
    </div>
  )
}
