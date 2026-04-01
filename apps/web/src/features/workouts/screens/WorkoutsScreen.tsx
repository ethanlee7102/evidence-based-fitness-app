import { useState, useCallback, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { BookOpen, ClipboardList } from 'lucide-react'
import { Button } from '../../../shared/components/Button'
import { useAuth } from '../../auth/hooks/useAuth'
import { useWorkoutHistory } from '../hooks/useWorkoutHistory'
import { WorkoutHistoryList } from '../components/WorkoutHistoryList'
import { ActiveWorkoutModal } from '../components/ActiveWorkoutModal'
import { WorkoutDetailModal } from '../components/WorkoutDetailModal'
import { StartWorkoutChoiceModal } from '../components/StartWorkoutChoiceModal'
import { listRoutines, startWorkoutFromRoutine } from '../services/workoutService'
import type { RoutineSummary } from '../types'

const RECENT_LIMIT = 3

export function WorkoutsScreen() {
  const { session: authSession } = useAuth()
  const token = authSession?.access_token

  const {
    workouts,
    isLoading,
    error,
    loadWorkouts,
    deleteWorkout,
  } = useWorkoutHistory()

  const [showActiveWorkout, setShowActiveWorkout] = useState(false)
  const [resumeWorkoutId, setResumeWorkoutId] = useState<string | null>(null)
  const [viewWorkoutId, setViewWorkoutId] = useState<string | null>(null)
  const [routines, setRoutines] = useState<RoutineSummary[]>([])
  const [showStartChoice, setShowStartChoice] = useState(false)
  const [isStartingFromRoutine, setIsStartingFromRoutine] = useState(false)

  // Load routines for start-workout choice
  useEffect(() => {
    if (!token) return
    listRoutines(token).then(setRoutines).catch(() => {})
  }, [token])

  const handleStartWorkout = useCallback(() => {
    if (routines.length > 0) {
      setShowStartChoice(true)
    } else {
      setResumeWorkoutId(null)
      setShowActiveWorkout(true)
    }
  }, [routines.length])

  const handleStartEmpty = useCallback(() => {
    setShowStartChoice(false)
    setResumeWorkoutId(null)
    setShowActiveWorkout(true)
  }, [])

  const handleStartFromRoutine = useCallback(async (routineId: string) => {
    if (!token) return
    try {
      setIsStartingFromRoutine(true)
      const workout = await startWorkoutFromRoutine(token, routineId)
      setShowStartChoice(false)
      setResumeWorkoutId(workout.id)
      setShowActiveWorkout(true)
    } catch (e) {
      console.error('Failed to start workout from routine:', e)
    } finally {
      setIsStartingFromRoutine(false)
    }
  }, [token])

  const handleResumeWorkout = useCallback((workoutId: string) => {
    setResumeWorkoutId(workoutId)
    setShowActiveWorkout(true)
  }, [])

  const handleWorkoutComplete = useCallback(() => {
    setShowActiveWorkout(false)
    setResumeWorkoutId(null)
    loadWorkouts()
    // Refresh routines (usage stats may have changed)
    if (token) listRoutines(token).then(setRoutines).catch(() => {})
  }, [loadWorkouts, token])

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

      {/* Recent workouts (top 3) */}
      <WorkoutHistoryList
        workouts={workouts.slice(0, RECENT_LIMIT)}
        isLoadingMore={false}
        hasMore={false}
        onLoadMore={() => {}}
        onView={handleViewWorkout}
        onResume={handleResumeWorkout}
        onDelete={handleDeleteWorkout}
      />

      {workouts.length > RECENT_LIMIT && (
        <div className="text-center pt-3">
          <Link
            to="/dashboard/workouts/history"
            className="text-sm text-flame-400 hover:text-flame-300 font-medium"
          >
            See All History
          </Link>
        </div>
      )}

      {/* Quick access tiles */}
      <div className="grid grid-cols-2 gap-4 mt-8">
        <Link
          to="/dashboard/workouts/exercises"
          className="bg-gray-800/50 border border-gray-700 rounded-xl p-6 hover:bg-gray-800 hover:border-gray-600 transition-colors group aspect-[2/1] flex flex-col items-center justify-center text-center"
        >
          <BookOpen className="w-10 h-10 text-flame-400 mb-3 group-hover:text-flame-300 transition-colors" />
          <h3 className="font-semibold text-lg mb-1">Exercise Library</h3>
          <p className="text-sm text-gray-500">Browse all exercises</p>
        </Link>

        <Link
          to="/dashboard/workouts/routines"
          className="bg-gray-800/50 border border-gray-700 rounded-xl p-6 hover:bg-gray-800 hover:border-gray-600 transition-colors group aspect-[2/1] flex flex-col items-center justify-center text-center"
        >
          <ClipboardList className="w-10 h-10 text-flame-400 mb-3 group-hover:text-flame-300 transition-colors" />
          <h3 className="font-semibold text-lg mb-1">Routines</h3>
          <p className="text-sm text-gray-500">Manage workout templates</p>
        </Link>
      </div>

      {/* Start workout choice modal */}
      {showStartChoice && (
        <StartWorkoutChoiceModal
          routines={routines}
          isStarting={isStartingFromRoutine}
          onStartEmpty={handleStartEmpty}
          onStartFromRoutine={handleStartFromRoutine}
          onClose={() => setShowStartChoice(false)}
        />
      )}

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
