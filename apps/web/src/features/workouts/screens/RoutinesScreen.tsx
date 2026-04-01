import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Plus } from 'lucide-react'
import { useAuth } from '../../auth/hooks/useAuth'
import { useRoutines } from '../hooks/useRoutines'
import { RoutineCard } from '../components/RoutineCard'
import { RoutineBuilderModal } from '../components/RoutineBuilderModal'
import { startWorkoutFromRoutine, getRoutine } from '../services/workoutService'
import { ActiveWorkoutModal } from '../components/ActiveWorkoutModal'
import type { Routine } from '../types'

export function RoutinesScreen() {
  const { session: authSession } = useAuth()
  const token = authSession?.access_token
  const navigate = useNavigate()

  const { routines, isLoading, error, loadRoutines, deleteRoutine, duplicateRoutine } = useRoutines()

  const [showBuilder, setShowBuilder] = useState(false)
  const [editRoutine, setEditRoutine] = useState<Routine | null>(null)
  const [showActiveWorkout, setShowActiveWorkout] = useState(false)
  const [resumeWorkoutId, setResumeWorkoutId] = useState<string | null>(null)
  const [startingRoutineId, setStartingRoutineId] = useState<string | null>(null)

  const handleNewRoutine = useCallback(() => {
    setEditRoutine(null)
    setShowBuilder(true)
  }, [])

  const handleEditRoutine = useCallback(async (routineId: string) => {
    if (!token) return
    try {
      const full = await getRoutine(token, routineId)
      setEditRoutine(full)
      setShowBuilder(true)
    } catch (e) {
      console.error('Failed to load routine:', e)
    }
  }, [token])

  const handleDeleteRoutine = useCallback((routineId: string) => {
    if (window.confirm('Delete this routine? This cannot be undone.')) {
      deleteRoutine(routineId)
    }
  }, [deleteRoutine])

  const handleStartFromRoutine = useCallback(async (routineId: string) => {
    if (!token) return
    try {
      setStartingRoutineId(routineId)
      const workout = await startWorkoutFromRoutine(token, routineId)
      setResumeWorkoutId(workout.id)
      setShowActiveWorkout(true)
    } catch (e) {
      console.error('Failed to start workout from routine:', e)
    } finally {
      setStartingRoutineId(null)
    }
  }, [token])

  const handleWorkoutDone = useCallback(() => {
    setShowActiveWorkout(false)
    setResumeWorkoutId(null)
    loadRoutines()
  }, [loadRoutines])

  if (isLoading) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center gap-3 mb-6">
          <button type="button" onClick={() => navigate('/dashboard/workouts')} className="text-gray-400 hover:text-gray-200">
            <ArrowLeft className="w-5 h-5" />
          </button>
          <h1 className="text-2xl font-bold">Routines</h1>
        </div>
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-flame-500" />
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <button type="button" onClick={() => navigate('/dashboard/workouts')} className="text-gray-400 hover:text-gray-200">
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-2xl font-bold">Routines</h1>
            <p className="text-sm text-gray-400">Create and manage workout templates</p>
          </div>
        </div>
        <button
          type="button"
          onClick={handleNewRoutine}
          className="flex items-center gap-2 bg-flame-500 hover:bg-flame-600 text-white px-4 py-2 rounded-lg font-medium text-sm transition-colors"
        >
          <Plus className="w-4 h-4" />
          New Routine
        </button>
      </div>

      {error && (
        <div className="bg-red-900/30 border border-red-700 rounded-lg p-3 mb-4 text-sm text-red-300">
          {error}
        </div>
      )}

      {routines.length === 0 ? (
        <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-8 text-center">
          <h2 className="text-xl font-semibold mb-2">No Routines Yet</h2>
          <p className="text-gray-400 mb-6">
            Create a routine to save your favorite workout templates.
          </p>
          <button
            type="button"
            onClick={handleNewRoutine}
            className="bg-flame-500 hover:bg-flame-600 text-white px-6 py-2.5 rounded-lg font-medium transition-colors"
          >
            Create Your First Routine
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {routines.map((r) => (
            <RoutineCard
              key={r.id}
              routine={r}
              onStart={handleStartFromRoutine}
              onEdit={handleEditRoutine}
              onDuplicate={duplicateRoutine}
              onDelete={handleDeleteRoutine}
            />
          ))}
        </div>
      )}

      {startingRoutineId && (
        <div className="fixed inset-0 z-40 bg-gray-900/50 flex items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-flame-500" />
        </div>
      )}

      {showBuilder && (
        <RoutineBuilderModal
          routine={editRoutine}
          onSave={() => {
            setShowBuilder(false)
            setEditRoutine(null)
            loadRoutines()
          }}
          onClose={() => {
            setShowBuilder(false)
            setEditRoutine(null)
          }}
        />
      )}

      {showActiveWorkout && (
        <ActiveWorkoutModal
          resumeWorkoutId={resumeWorkoutId}
          onComplete={handleWorkoutDone}
          onClose={handleWorkoutDone}
        />
      )}
    </div>
  )
}
