import { useState, useCallback, useRef } from 'react'
import { useActiveWorkout } from '../hooks/useActiveWorkout'
import { WorkoutTimer } from './WorkoutTimer'
import { ExerciseCard } from './ExerciseCard'
import { ExerciseSearchModal } from './ExerciseSearchModal'
import { WorkoutSummaryModal } from './WorkoutSummaryModal'
import { CreateExerciseForm } from './CreateExerciseForm'
import { RestTimerBar } from './RestTimerBar'
import { Button } from '../../../shared/components/Button'
import type { WorkoutSet } from '../types'

const ELAPSED_KEY_PREFIX = 'flame_workout_elapsed_'

interface ActiveWorkoutModalProps {
  resumeWorkoutId: string | null
  onComplete: () => void
  onClose: () => void
}

export function ActiveWorkoutModal({
  resumeWorkoutId,
  onComplete,
  onClose,
}: ActiveWorkoutModalProps) {
  const {
    workout,
    previousSets,
    isLoading,
    isSaving,
    error,
    addExercise,
    removeExercise,
    reorderExercises,
    addSetToExercise,
    updateSetLocal,
    deleteSet,
    finishWorkout,
    updateExercise,
    clearError,
  } = useActiveWorkout(resumeWorkoutId)

  // Restore saved elapsed time for resumed workouts (pauses timer across close/resume)
  const [initialElapsed] = useState(() => {
    if (!resumeWorkoutId) return 0
    const saved = localStorage.getItem(`${ELAPSED_KEY_PREFIX}${resumeWorkoutId}`)
    return saved ? parseInt(saved, 10) : 0
  })
  const elapsedRef = useRef(initialElapsed)

  const [showExerciseSearch, setShowExerciseSearch] = useState(false)
  const [showSummary, setShowSummary] = useState(false)
  const [showCreateExercise, setShowCreateExercise] = useState(false)
  const [restTimer, setRestTimer] = useState<{ exerciseName: string; durationSeconds: number } | null>(null)

  const handleFinish = useCallback(async () => {
    setShowSummary(true)
  }, [])

  const handleConfirmFinish = useCallback(
    async (data: Parameters<typeof finishWorkout>[0]) => {
      const result = await finishWorkout({
        ...data,
        duration_seconds: elapsedRef.current,
      })
      if (result) {
        localStorage.removeItem(`${ELAPSED_KEY_PREFIX}${result.id}`)
        onComplete()
      }
    },
    [finishWorkout, onComplete],
  )

  const handleDiscard = useCallback(() => {
    if (window.confirm('Close workout? You can resume it later.')) {
      if (workout) {
        localStorage.setItem(
          `${ELAPSED_KEY_PREFIX}${workout.id}`,
          String(elapsedRef.current),
        )
      }
      onClose()
    }
  }, [onClose, workout])

  // Wrapper that auto-starts rest timer on set completion
  const handleUpdateSet = useCallback(
    (setId: string, updates: Partial<WorkoutSet>) => {
      updateSetLocal(setId, updates)

      if (updates.completed && workout) {
        for (const we of workout.exercises) {
          if (we.sets.some((s) => s.id === setId) && we.rest_timer_seconds) {
            setRestTimer({
              exerciseName: we.exercise.name,
              durationSeconds: we.rest_timer_seconds,
            })
            break
          }
        }
      }
    },
    [updateSetLocal, workout],
  )

  if (isLoading) {
    return (
      <div className="fixed inset-0 z-50 bg-gray-900 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-flame-500" />
      </div>
    )
  }

  if (!workout) {
    return (
      <div className="fixed inset-0 z-50 bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-400 mb-4">Failed to start workout</p>
          <Button onClick={onClose}>Go Back</Button>
        </div>
      </div>
    )
  }

  return (
    <>
      <div className="fixed inset-0 z-50 bg-gray-900 flex flex-col">
        {/* Top bar */}
        <div className="flex items-center justify-between p-4 border-b border-gray-700">
          <button
            type="button"
            onClick={handleDiscard}
            className="text-gray-400 hover:text-gray-200 text-sm"
          >
            Close
          </button>

          <WorkoutTimer
            startedAt={workout.started_at}
            initialElapsed={initialElapsed}
            elapsedRef={elapsedRef}
          />

          <Button size="sm" onClick={handleFinish}>
            Finish
          </Button>
        </div>

        {/* Error banner */}
        {error && (
          <div className="mx-4 mt-2 bg-red-900/30 border border-red-700 rounded-lg p-2 text-sm text-red-300 flex items-center justify-between">
            <span>{error}</span>
            <button
              type="button"
              onClick={clearError}
              className="text-red-400 hover:text-red-300 ml-2"
            >
              &times;
            </button>
          </div>
        )}

        {/* Exercise list */}
        <div className={`flex-1 overflow-y-auto p-4 space-y-3 max-w-2xl mx-auto w-full ${restTimer ? 'pb-24' : ''}`}>
          {workout.exercises.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-gray-500 mb-4">
                No exercises yet. Add one to get started.
              </p>
            </div>
          ) : (
            workout.exercises.map((we, idx) =>
              we.id.startsWith('pending-') ? (
                // Skeleton card while exercise is being added — matches ExerciseCard layout
                <div
                  key={we.id}
                  className="bg-gray-800/50 border border-gray-700 rounded-xl overflow-hidden animate-pulse"
                >
                  <div className="flex items-center justify-between p-3">
                    <div className="flex-1 min-w-0">
                      <div className="h-5 w-36 bg-gray-700 rounded" />
                      <div className="h-4 w-24 bg-gray-700/60 rounded mt-0.5" />
                    </div>
                    <div className="flex items-center gap-1 flex-shrink-0">
                      <div className="h-4 w-14 bg-gray-700/50 rounded" />
                      <div className="h-6 w-6 bg-gray-700/40 rounded" />
                      <div className="h-7 w-7 bg-gray-700/40 rounded" />
                      <div className="h-5 w-5 bg-gray-700/40 rounded" />
                    </div>
                  </div>
                  <div className="px-3 pb-3">
                    <div className="flex items-center gap-2 py-1">
                      <div className="w-8 h-4 bg-gray-700/40 rounded" />
                      <div className="w-24 h-4 bg-gray-700/40 rounded" />
                      <div className="flex-1 h-4 bg-gray-700/40 rounded" />
                      <div className="flex-1 h-4 bg-gray-700/40 rounded" />
                      <div className="w-14 h-4 bg-gray-700/40 rounded" />
                      <div className="w-8 h-4" />
                      <div className="w-5 h-4" />
                    </div>
                    <div className="flex items-center gap-2 py-1.5 px-2">
                      <div className="w-8 h-7 bg-gray-700/30 rounded" />
                      <div className="w-24 h-7 bg-gray-700/30 rounded" />
                      <div className="flex-1 h-7 bg-gray-700/30 rounded" />
                      <div className="flex-1 h-7 bg-gray-700/30 rounded" />
                      <div className="w-14 h-7 bg-gray-700/30 rounded" />
                      <div className="w-8 h-8 bg-gray-700/30 rounded" />
                      <div className="w-5 h-4" />
                    </div>
                    <div className="h-8 mt-2 bg-gray-700/20 rounded-lg" />
                  </div>
                </div>
              ) : (
                <ExerciseCard
                  key={we.id}
                  workoutExercise={we}
                  previousSets={previousSets[we.exercise_id] || []}
                  onAddSet={addSetToExercise}
                  onUpdateSet={handleUpdateSet}
                  onDeleteSet={deleteSet}
                  onRemoveExercise={removeExercise}
                  onReorder={reorderExercises}
                  onUpdateExercise={updateExercise}
                  isFirst={idx === 0}
                  isLast={idx === workout.exercises.length - 1}
                />
              ),
            )
          )}

          {/* Add exercise button */}
          <button
            type="button"
            onClick={() => setShowExerciseSearch(true)}
            className="w-full py-3 border-2 border-dashed border-gray-700 rounded-xl text-gray-400
              hover:border-flame-600 hover:text-flame-400 transition-colors text-sm font-medium"
          >
            + Add Exercise
          </button>
        </div>
      </div>

      {/* Rest timer bar */}
      {restTimer && (
        <RestTimerBar
          exerciseName={restTimer.exerciseName}
          durationSeconds={restTimer.durationSeconds}
          onSkip={() => setRestTimer(null)}
          onComplete={() => setRestTimer(null)}
        />
      )}

      {/* Exercise search modal */}
      {showExerciseSearch && (
        <ExerciseSearchModal
          onSelect={addExercise}
          onClose={() => setShowExerciseSearch(false)}
          onCreateCustom={() => {
            setShowExerciseSearch(false)
            setShowCreateExercise(true)
          }}
        />
      )}

      {/* Create custom exercise */}
      {showCreateExercise && (
        <CreateExerciseForm
          onCreated={(exercise) => {
            addExercise(exercise)
            setShowCreateExercise(false)
          }}
          onClose={() => setShowCreateExercise(false)}
        />
      )}

      {/* Summary/finish modal */}
      {showSummary && (
        <WorkoutSummaryModal
          workout={workout}
          elapsed={elapsedRef.current}
          onFinish={handleConfirmFinish}
          onCancel={() => setShowSummary(false)}
          isSaving={isSaving}
        />
      )}
    </>
  )
}
