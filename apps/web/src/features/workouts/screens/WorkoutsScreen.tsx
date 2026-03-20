import { useState, useCallback } from 'react'
import { Button } from '../../../shared/components/Button'
import { useWorkoutHistory } from '../hooks/useWorkoutHistory'
import { WorkoutHistoryList } from '../components/WorkoutHistoryList'
import { ActiveWorkoutModal } from '../components/ActiveWorkoutModal'
import { WorkoutDetailModal } from '../components/WorkoutDetailModal'

export function WorkoutsScreen() {
  const {
    workouts,
    isLoading,
    isLoadingMore,
    hasMore,
    error,
    loadWorkouts,
    loadMore,
    deleteWorkout,
  } = useWorkoutHistory()

  const [showActiveWorkout, setShowActiveWorkout] = useState(false)
  const [resumeWorkoutId, setResumeWorkoutId] = useState<string | null>(null)
  const [viewWorkoutId, setViewWorkoutId] = useState<string | null>(null)

  const handleStartWorkout = useCallback(() => {
    setResumeWorkoutId(null)
    setShowActiveWorkout(true)
  }, [])

  const handleResumeWorkout = useCallback((workoutId: string) => {
    setResumeWorkoutId(workoutId)
    setShowActiveWorkout(true)
  }, [])

  const handleWorkoutComplete = useCallback(() => {
    setShowActiveWorkout(false)
    setResumeWorkoutId(null)
    loadWorkouts()
  }, [loadWorkouts])

  const handleCloseWorkout = useCallback(() => {
    setShowActiveWorkout(false)
    setResumeWorkoutId(null)
    loadWorkouts()
  }, [loadWorkouts])

  const handleViewWorkout = useCallback((workoutId: string) => {
    setViewWorkoutId(workoutId)
  }, [])

  const handleDeleteWorkout = useCallback(
    (workoutId: string) => {
      if (window.confirm('Delete this workout? This cannot be undone.')) {
        deleteWorkout(workoutId)
      }
    },
    [deleteWorkout],
  )

  if (isLoading) {
    return (
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold mb-2">Workouts</h1>
        <p className="text-gray-400 mb-8">Log and view your workout history.</p>
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-flame-500" />
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold mb-1">Workouts</h1>
          <p className="text-gray-400">Log and view your workout history.</p>
        </div>
        <Button size="lg" onClick={handleStartWorkout}>
          Start Workout
        </Button>
      </div>

      {error && (
        <div className="bg-red-900/30 border border-red-700 rounded-lg p-3 mb-4 text-sm text-red-300">
          {error}
        </div>
      )}

      {/* Empty state */}
      {workouts.length === 0 && (
        <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-8 text-center">
          <div className="text-5xl mb-4">&#127947;&#65039;</div>
          <h2 className="text-xl font-semibold mb-2">No Workouts Yet</h2>
          <p className="text-gray-400 mb-6">
            Start logging your workouts to track your progress.
          </p>
          <Button size="lg" onClick={handleStartWorkout}>
            Log Your First Workout
          </Button>
        </div>
      )}

      {/* Workout history */}
      <WorkoutHistoryList
        workouts={workouts}
        isLoadingMore={isLoadingMore}
        hasMore={hasMore}
        onLoadMore={loadMore}
        onView={handleViewWorkout}
        onResume={handleResumeWorkout}
        onDelete={handleDeleteWorkout}
      />

      {/* Active workout modal */}
      {showActiveWorkout && (
        <ActiveWorkoutModal
          resumeWorkoutId={resumeWorkoutId}
          onComplete={handleWorkoutComplete}
          onClose={handleCloseWorkout}
        />
      )}

      {/* Workout detail modal */}
      {viewWorkoutId && (
        <WorkoutDetailModal
          workoutId={viewWorkoutId}
          onClose={() => setViewWorkoutId(null)}
        />
      )}
    </div>
  )
}
