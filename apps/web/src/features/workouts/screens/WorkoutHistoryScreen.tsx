import { useState, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { ChevronLeft } from 'lucide-react'
import { useWorkoutHistory } from '../hooks/useWorkoutHistory'
import { WorkoutHistoryList } from '../components/WorkoutHistoryList'
import { WorkoutFilterBar } from '../components/WorkoutFilterBar'
import { WorkoutDetailModal } from '../components/WorkoutDetailModal'
import { ActiveWorkoutModal } from '../components/ActiveWorkoutModal'

export function WorkoutHistoryScreen() {
  const {
    workouts,
    isLoading,
    isLoadingMore,
    hasMore,
    error,
    filters,
    setFilters,
    activeFilterCount,
    loadWorkouts,
    loadMore,
    deleteWorkout,
  } = useWorkoutHistory()

  const [viewWorkoutId, setViewWorkoutId] = useState<string | null>(null)
  const [resumeWorkoutId, setResumeWorkoutId] = useState<string | null>(null)
  const [showActiveWorkout, setShowActiveWorkout] = useState(false)

  const handleViewWorkout = useCallback((workoutId: string) => {
    setViewWorkoutId(workoutId)
  }, [])

  const handleResumeWorkout = useCallback((workoutId: string) => {
    setResumeWorkoutId(workoutId)
    setShowActiveWorkout(true)
  }, [])

  const handleDeleteWorkout = useCallback(
    (workoutId: string) => {
      if (window.confirm('Delete this workout? This cannot be undone.')) {
        deleteWorkout(workoutId)
      }
    },
    [deleteWorkout],
  )

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

  return (
    <div className="max-w-4xl mx-auto">
      <Link
        to="/dashboard/workouts"
        className="inline-flex items-center text-sm text-gray-400 hover:text-gray-200 mb-4"
      >
        <ChevronLeft className="w-4 h-4 mr-1" />
        Back to Workouts
      </Link>

      <h1 className="text-3xl font-bold mb-6">Workout History</h1>

      <WorkoutFilterBar
        filters={filters}
        onFiltersChange={setFilters}
        activeFilterCount={activeFilterCount}
      />

      {error && (
        <div className="bg-red-900/30 border border-red-700 rounded-lg p-3 mb-4 text-sm text-red-300">
          {error}
        </div>
      )}

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-flame-500" />
        </div>
      ) : workouts.length === 0 ? (
        <p className="text-gray-400">
          {activeFilterCount > 0
            ? 'No workouts match your filters.'
            : 'No workouts logged yet.'}
        </p>
      ) : (
        <WorkoutHistoryList
          workouts={workouts}
          isLoadingMore={isLoadingMore}
          hasMore={hasMore}
          onLoadMore={loadMore}
          onView={handleViewWorkout}
          onResume={handleResumeWorkout}
          onDelete={handleDeleteWorkout}
        />
      )}

      {viewWorkoutId && (
        <WorkoutDetailModal
          workoutId={viewWorkoutId}
          onClose={() => setViewWorkoutId(null)}
        />
      )}

      {showActiveWorkout && (
        <ActiveWorkoutModal
          resumeWorkoutId={resumeWorkoutId}
          onComplete={handleWorkoutComplete}
          onClose={handleCloseWorkout}
        />
      )}
    </div>
  )
}
