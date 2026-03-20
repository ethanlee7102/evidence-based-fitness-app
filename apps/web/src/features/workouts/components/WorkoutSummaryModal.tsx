import { useState, useCallback } from 'react'
import type { Workout, FinishWorkoutRequest } from '../types'
import { formatDuration, formatVolume, displayWeight, weightUnit } from '../utils/unitConversion'
import { useProfile } from '../../onboarding/hooks/useProfile'
import { Button } from '../../../shared/components/Button'

interface WorkoutSummaryModalProps {
  workout: Workout
  elapsed: number
  onFinish: (data: FinishWorkoutRequest) => Promise<void>
  onCancel: () => void
  isSaving: boolean
}

export function WorkoutSummaryModal({
  workout,
  elapsed,
  onFinish,
  onCancel,
  isSaving,
}: WorkoutSummaryModalProps) {
  const { profile } = useProfile()
  const units = profile?.unitsPreference ?? 'metric'

  const [rating, setRating] = useState<number>(0)
  const [bodyWeight, setBodyWeight] = useState('')
  const [notes, setNotes] = useState('')

  // Calculate stats
  const completedSets = workout.exercises.flatMap((we) =>
    we.sets.filter((s) => s.completed),
  )
  const totalVolume = completedSets.reduce(
    (sum, s) => sum + (s.weight_kg || 0) * (s.reps || 0),
    0,
  )
  const exerciseCount = workout.exercises.length
  const setCount = completedSets.length

  const uncheckedSets = workout.exercises.flatMap((we) =>
    we.sets.filter((s) => !s.completed),
  )

  const handleFinish = useCallback(async () => {
    const data: FinishWorkoutRequest = {}
    if (rating > 0) data.rating = rating
    if (bodyWeight) {
      const bw = parseFloat(bodyWeight)
      if (!isNaN(bw)) {
        data.body_weight_kg = units === 'imperial' ? bw * 0.453592 : bw
      }
    }
    if (notes.trim()) data.notes = notes.trim()

    await onFinish(data)
  }, [rating, bodyWeight, notes, units, onFinish])

  return (
    <div className="fixed inset-0 z-[70] bg-gray-900/95 flex items-center justify-center p-4">
      <div className="bg-gray-800 border border-gray-700 rounded-2xl max-w-md w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <h2 className="text-xl font-bold mb-4">Finish Workout</h2>

          {/* Warning for unchecked sets */}
          {uncheckedSets.length > 0 && (
            <div className="bg-yellow-900/30 border border-yellow-700/50 rounded-lg p-3 mb-4 text-sm text-yellow-300">
              {uncheckedSets.length} unchecked set{uncheckedSets.length !== 1 ? 's' : ''} will not be counted.
            </div>
          )}

          {/* Stats */}
          <div className="grid grid-cols-3 gap-4 mb-6">
            <div className="text-center">
              <p className="text-2xl font-bold">{formatDuration(elapsed)}</p>
              <p className="text-xs text-gray-500">Duration</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold">{exerciseCount}</p>
              <p className="text-xs text-gray-500">Exercises</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold">{setCount}</p>
              <p className="text-xs text-gray-500">Sets</p>
            </div>
          </div>

          <div className="text-center mb-6">
            <p className="text-lg font-semibold">{formatVolume(totalVolume, units)}</p>
            <p className="text-xs text-gray-500">Total Volume</p>
          </div>

          {/* Exercise summary */}
          <div className="space-y-2 mb-6">
            {workout.exercises.map((we) => {
              const completed = we.sets.filter((s) => s.completed)
              const bestSet = completed.reduce(
                (best, s) => {
                  const vol = (s.weight_kg || 0) * (s.reps || 0)
                  return vol > best.vol ? { vol, set: s } : best
                },
                { vol: 0, set: null as typeof completed[0] | null },
              )
              return (
                <div
                  key={we.id}
                  className="flex items-center justify-between text-sm"
                >
                  <span className="text-gray-300">{we.exercise.name}</span>
                  <span className="text-gray-500">
                    {completed.length} set{completed.length !== 1 ? 's' : ''}
                    {bestSet.set && (
                      <>
                        {' \u2014 '}
                        {displayWeight(bestSet.set.weight_kg || 0, units)} {weightUnit(units)} x {bestSet.set.reps}
                      </>
                    )}
                  </span>
                </div>
              )
            })}
          </div>

          {/* Rating */}
          <div className="mb-4">
            <label className="text-sm text-gray-400 mb-2 block">
              How was this workout?
            </label>
            <div className="flex gap-2 justify-center">
              {[1, 2, 3, 4, 5].map((star) => (
                <button
                  key={star}
                  type="button"
                  onClick={() => setRating(rating === star ? 0 : star)}
                  className={`p-1 transition-colors ${
                    star <= rating ? 'text-yellow-400' : 'text-gray-600'
                  }`}
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    className="h-8 w-8"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                  >
                    <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                  </svg>
                </button>
              ))}
            </div>
          </div>

          {/* Body weight */}
          <div className="mb-4">
            <label className="text-sm text-gray-400 mb-1 block">
              Body Weight ({weightUnit(units)}) — optional
            </label>
            <input
              type="number"
              inputMode="decimal"
              value={bodyWeight}
              onChange={(e) => setBodyWeight(e.target.value)}
              placeholder={`e.g. ${units === 'imperial' ? '180' : '82'}`}
              className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-sm
                focus:outline-none focus:border-flame-500
                [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
            />
          </div>

          {/* Notes */}
          <div className="mb-6">
            <label className="text-sm text-gray-400 mb-1 block">
              Notes — optional
            </label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="How did it feel?"
              rows={2}
              className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-sm
                focus:outline-none focus:border-flame-500 resize-none"
            />
          </div>

          {/* Buttons */}
          <div className="flex gap-3">
            <Button
              variant="secondary"
              className="flex-1"
              onClick={onCancel}
              disabled={isSaving}
            >
              Cancel
            </Button>
            <Button
              className="flex-1"
              onClick={handleFinish}
              disabled={isSaving}
            >
              {isSaving ? 'Saving...' : 'Finish Workout'}
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
