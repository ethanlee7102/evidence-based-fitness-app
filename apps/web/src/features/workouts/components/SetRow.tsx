import { useCallback, useState, useEffect } from 'react'
import type { PreviousSetData, WorkoutSet } from '../types'
import { displayWeight, inputToKg, weightUnit } from '../utils/unitConversion'
import { useProfile } from '../../onboarding/hooks/useProfile'

interface SetRowProps {
  set: WorkoutSet
  previous: PreviousSetData | undefined
  onUpdate: (setId: string, updates: Partial<WorkoutSet>) => void
  onDelete: (setId: string) => void
}

export function SetRow({ set, previous, onUpdate, onDelete }: SetRowProps) {
  const { profile } = useProfile()
  const units = profile?.unitsPreference ?? 'metric'

  const [showOptions, setShowOptions] = useState(false)

  // Local string state for weight input — avoids kg↔lbs round-trip on every keystroke
  const [localWeight, setLocalWeight] = useState(() =>
    set.weight_kg != null ? String(displayWeight(set.weight_kg, units)) : '',
  )
  const [localReps, setLocalReps] = useState(() =>
    set.reps != null ? String(set.reps) : '',
  )
  const [localRpe, setLocalRpe] = useState(() =>
    set.rpe != null ? String(set.rpe) : '',
  )

  // Sync from parent when set changes externally (e.g. undo checkmark)
  useEffect(() => {
    setLocalWeight(
      set.weight_kg != null ? String(displayWeight(set.weight_kg, units)) : '',
    )
  }, [set.weight_kg, units])

  useEffect(() => {
    setLocalReps(set.reps != null ? String(set.reps) : '')
  }, [set.reps])

  useEffect(() => {
    setLocalRpe(set.rpe != null ? String(set.rpe) : '')
  }, [set.rpe])

  const prevDisplay =
    previous && previous.weight_kg != null && previous.reps != null
      ? `${displayWeight(previous.weight_kg, units)} x ${previous.reps}`
      : '-'

  const prevClickable =
    !!previous &&
    previous.weight_kg != null &&
    previous.reps != null &&
    !set.completed

  // Use local values so checkmark enables immediately after typing (before blur)
  const canComplete = localWeight !== '' && localReps !== ''

  const handlePrevTap = useCallback(() => {
    if (!previous || previous.weight_kg == null || previous.reps == null) return
    setLocalWeight(String(displayWeight(previous.weight_kg, units)))
    setLocalReps(String(previous.reps))
    onUpdate(set.id, { weight_kg: previous.weight_kg, reps: previous.reps })
  }, [previous, units, set.id, onUpdate])

  const handleWeightChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      setLocalWeight(e.target.value)
    },
    [],
  )

  const handleWeightBlur = useCallback(() => {
    if (localWeight === '') {
      onUpdate(set.id, { weight_kg: null })
      return
    }
    const num = parseFloat(localWeight)
    if (!isNaN(num)) {
      onUpdate(set.id, { weight_kg: inputToKg(num, units) })
    }
  }, [localWeight, set.id, onUpdate, units])

  const handleRepsChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      setLocalReps(e.target.value)
    },
    [],
  )

  const handleRepsBlur = useCallback(() => {
    if (localReps === '') {
      onUpdate(set.id, { reps: null })
      return
    }
    const num = parseInt(localReps, 10)
    if (!isNaN(num)) {
      onUpdate(set.id, { reps: num })
    }
  }, [localReps, set.id, onUpdate])

  const handleRpeChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      setLocalRpe(e.target.value)
    },
    [],
  )

  const handleRpeBlur = useCallback(() => {
    if (localRpe === '') {
      onUpdate(set.id, { rpe: null })
      return
    }
    const num = parseFloat(localRpe)
    if (!isNaN(num) && num >= 1 && num <= 10) {
      onUpdate(set.id, { rpe: num })
    }
  }, [localRpe, set.id, onUpdate])

  const handleToggleComplete = useCallback(() => {
    if (!canComplete && !set.completed) return
    // If completing, sync weight/reps/rpe from local state first
    if (!set.completed) {
      const weightNum = parseFloat(localWeight)
      const repsNum = parseInt(localReps, 10)
      if (!isNaN(weightNum) && !isNaN(repsNum)) {
        const updates: Partial<WorkoutSet> = {
          weight_kg: inputToKg(weightNum, units),
          reps: repsNum,
          completed: true,
        }
        if (localRpe !== '') {
          const rpeNum = parseFloat(localRpe)
          if (!isNaN(rpeNum) && rpeNum >= 1 && rpeNum <= 10) {
            updates.rpe = rpeNum
          }
        }
        onUpdate(set.id, updates)
        return
      }
    }
    onUpdate(set.id, { completed: !set.completed })
  }, [set.id, set.completed, canComplete, localWeight, localReps, localRpe, onUpdate, units])

  const setTypeLabel =
    set.set_type !== 'normal' ? set.set_type.charAt(0).toUpperCase() : ''

  return (
    <div
      className={`flex items-center gap-2 py-1.5 px-2 rounded-lg text-sm ${
        set.completed ? 'bg-green-900/20' : ''
      }`}
    >
      {/* Set number */}
      <div className="w-8 text-center text-gray-500 font-medium flex-shrink-0">
        {setTypeLabel || set.set_number}
      </div>

      {/* PREV — clickable when previous data exists and set not completed */}
      {prevClickable ? (
        <button
          type="button"
          onClick={handlePrevTap}
          className="w-24 text-center text-gray-500 text-xs flex-shrink-0 cursor-pointer hover:text-gray-300 hover:bg-gray-700/30 rounded py-0.5 transition-colors"
        >
          {prevDisplay}
        </button>
      ) : (
        <div className="w-24 text-center text-gray-500 text-xs flex-shrink-0">
          {prevDisplay}
        </div>
      )}

      {/* Weight input */}
      <div className="flex-1 min-w-0">
        <input
          type="number"
          inputMode="decimal"
          placeholder={weightUnit(units)}
          value={localWeight}
          onChange={handleWeightChange}
          onBlur={handleWeightBlur}
          disabled={set.completed}
          className="w-full bg-gray-700/50 border border-gray-600 rounded px-2 py-1 text-center text-sm
            focus:outline-none focus:border-flame-500 disabled:opacity-50 disabled:cursor-not-allowed
            [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
        />
      </div>

      {/* Reps input */}
      <div className="flex-1 min-w-0">
        <input
          type="number"
          inputMode="numeric"
          placeholder="Reps"
          value={localReps}
          onChange={handleRepsChange}
          onBlur={handleRepsBlur}
          disabled={set.completed}
          className="w-full bg-gray-700/50 border border-gray-600 rounded px-2 py-1 text-center text-sm
            focus:outline-none focus:border-flame-500 disabled:opacity-50 disabled:cursor-not-allowed
            [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
        />
      </div>

      {/* RPE input */}
      <div className="w-14 flex-shrink-0">
        <input
          type="number"
          inputMode="decimal"
          step={0.5}
          placeholder="RPE"
          value={localRpe}
          onChange={handleRpeChange}
          onBlur={handleRpeBlur}
          disabled={set.completed}
          className="w-full bg-gray-700/50 border border-gray-600 rounded px-1 py-1 text-center text-sm
            focus:outline-none focus:border-flame-500 disabled:opacity-50 disabled:cursor-not-allowed
            [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
        />
      </div>

      {/* Checkmark button */}
      <button
        type="button"
        aria-label={set.completed ? 'Uncheck set' : 'Complete set'}
        onClick={handleToggleComplete}
        disabled={!canComplete && !set.completed}
        className={`w-8 h-8 flex items-center justify-center rounded flex-shrink-0 transition-colors ${
          set.completed
            ? 'bg-green-600 text-white'
            : canComplete
              ? 'bg-gray-700 text-gray-400 hover:bg-gray-600'
              : 'bg-gray-800 text-gray-600 cursor-not-allowed'
        }`}
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          className="h-4 w-4"
          viewBox="0 0 20 20"
          fill="currentColor"
        >
          <path
            fillRule="evenodd"
            d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
            clipRule="evenodd"
          />
        </svg>
      </button>

      {/* Options (delete) */}
      <div className="relative flex-shrink-0">
        <button
          type="button"
          aria-label="Set options"
          onClick={() => setShowOptions(!showOptions)}
          className="text-gray-600 hover:text-gray-400 p-0.5"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
            <path d="M10 6a2 2 0 110-4 2 2 0 010 4zM10 12a2 2 0 110-4 2 2 0 010 4zM10 18a2 2 0 110-4 2 2 0 010 4z" />
          </svg>
        </button>
        {showOptions && (
          <>
            <div className="fixed inset-0 z-10" onClick={() => setShowOptions(false)} />
            <div className="absolute right-0 top-6 z-20 bg-gray-700 border border-gray-600 rounded-lg shadow-lg py-1 min-w-[120px]">
              <button
                type="button"
                className="w-full text-left px-3 py-1.5 text-sm text-red-400 hover:bg-gray-600"
                onClick={() => {
                  onDelete(set.id)
                  setShowOptions(false)
                }}
              >
                Delete Set
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
