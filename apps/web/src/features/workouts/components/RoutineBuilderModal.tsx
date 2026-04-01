import { useState, useReducer, useCallback } from 'react'
import { Plus } from 'lucide-react'
import { useAuth } from '../../auth/hooks/useAuth'
import { createRoutine, updateRoutine } from '../services/workoutService'
import { ExerciseSearchModal } from './ExerciseSearchModal'
import { CreateExerciseForm } from './CreateExerciseForm'
import { RoutineExerciseRow } from './RoutineExerciseRow'
import type { Routine, RoutineExerciseInput, RoutineSetInput, Exercise } from '../types'

interface RoutineBuilderModalProps {
  routine?: Routine | null
  initialExercises?: RoutineExerciseInput[]
  onSave: () => void
  onClose: () => void
}

// --- State ---

interface BuilderState {
  name: string
  exercises: RoutineExerciseInput[]
  isSaving: boolean
  error: string | null
}

type BuilderAction =
  | { type: 'SET_NAME'; name: string }
  | { type: 'ADD_EXERCISE'; exercise: Exercise }
  | { type: 'REMOVE_EXERCISE'; index: number }
  | { type: 'MOVE_EXERCISE'; index: number; direction: 'up' | 'down' }
  | { type: 'UPDATE_EXERCISE'; index: number; updates: Partial<RoutineExerciseInput> }
  | { type: 'ADD_SET'; exerciseIndex: number }
  | { type: 'REMOVE_SET'; exerciseIndex: number; setIndex: number }
  | { type: 'UPDATE_SET'; exerciseIndex: number; setIndex: number; updates: Partial<RoutineSetInput> }
  | { type: 'SET_SAVING'; isSaving: boolean }
  | { type: 'SET_ERROR'; error: string | null }

function reindex(exercises: RoutineExerciseInput[]): RoutineExerciseInput[] {
  return exercises.map((ex, i) => ({
    ...ex,
    sort_order: i,
    sets: ex.sets.map((s, j) => ({ ...s, set_number: j + 1 })),
  }))
}

function builderReducer(state: BuilderState, action: BuilderAction): BuilderState {
  switch (action.type) {
    case 'SET_NAME':
      return { ...state, name: action.name }

    case 'ADD_EXERCISE': {
      const newExercise: RoutineExerciseInput = {
        exercise_id: action.exercise.id,
        exercise: action.exercise,
        sort_order: state.exercises.length,
        rest_timer_seconds: null,
        notes: null,
        sets: [{ set_number: 1, target_reps: null, set_type: 'normal' }],
      }
      return { ...state, exercises: [...state.exercises, newExercise] }
    }

    case 'REMOVE_EXERCISE': {
      const updated = [...state.exercises]
      updated.splice(action.index, 1)
      return { ...state, exercises: reindex(updated) }
    }

    case 'MOVE_EXERCISE': {
      const arr = [...state.exercises]
      const from = action.index
      const to = action.direction === 'up' ? from - 1 : from + 1
      if (to < 0 || to >= arr.length) return state
      ;[arr[from], arr[to]] = [arr[to], arr[from]]
      return { ...state, exercises: reindex(arr) }
    }

    case 'UPDATE_EXERCISE': {
      const exercises = [...state.exercises]
      exercises[action.index] = { ...exercises[action.index], ...action.updates }
      return { ...state, exercises }
    }

    case 'ADD_SET': {
      const exercises = [...state.exercises]
      const ex = { ...exercises[action.exerciseIndex] }
      ex.sets = [
        ...ex.sets,
        {
          set_number: ex.sets.length + 1,
          target_reps: ex.sets.length > 0 ? ex.sets[ex.sets.length - 1].target_reps : null,
          set_type: 'normal' as const,
        },
      ]
      exercises[action.exerciseIndex] = ex
      return { ...state, exercises }
    }

    case 'REMOVE_SET': {
      const exercises = [...state.exercises]
      const ex = { ...exercises[action.exerciseIndex] }
      const sets = [...ex.sets]
      sets.splice(action.setIndex, 1)
      ex.sets = sets.map((s, i) => ({ ...s, set_number: i + 1 }))
      exercises[action.exerciseIndex] = ex
      return { ...state, exercises }
    }

    case 'UPDATE_SET': {
      const exercises = [...state.exercises]
      const ex = { ...exercises[action.exerciseIndex] }
      const sets = [...ex.sets]
      sets[action.setIndex] = { ...sets[action.setIndex], ...action.updates }
      ex.sets = sets
      exercises[action.exerciseIndex] = ex
      return { ...state, exercises }
    }

    case 'SET_SAVING':
      return { ...state, isSaving: action.isSaving }

    case 'SET_ERROR':
      return { ...state, error: action.error }

    default:
      return state
  }
}

function buildInitialState(routine?: Routine | null, initialExercises?: RoutineExerciseInput[]): BuilderState {
  if (routine) {
    return {
      name: routine.name,
      exercises: routine.exercises.map((re) => ({
        exercise_id: re.exercise_id,
        exercise: re.exercise,
        sort_order: re.sort_order,
        rest_timer_seconds: re.rest_timer_seconds,
        notes: re.notes,
        sets: re.sets.map((s) => ({
          set_number: s.set_number,
          target_reps: s.target_reps,
          set_type: s.set_type,
        })),
      })),
      isSaving: false,
      error: null,
    }
  }

  if (initialExercises) {
    return {
      name: '',
      exercises: initialExercises,
      isSaving: false,
      error: null,
    }
  }

  return { name: '', exercises: [], isSaving: false, error: null }
}

export function RoutineBuilderModal({ routine, initialExercises, onSave, onClose }: RoutineBuilderModalProps) {
  const { session: authSession } = useAuth()
  const token = authSession?.access_token

  const [state, dispatch] = useReducer(builderReducer, buildInitialState(routine, initialExercises))
  const [showExerciseSearch, setShowExerciseSearch] = useState(false)
  const [showCreateExercise, setShowCreateExercise] = useState(false)

  const isEditing = !!routine

  const handleSave = useCallback(async () => {
    if (!token) return
    if (!state.name.trim()) {
      dispatch({ type: 'SET_ERROR', error: 'Routine name is required' })
      return
    }
    if (state.exercises.length === 0) {
      dispatch({ type: 'SET_ERROR', error: 'Add at least one exercise' })
      return
    }

    dispatch({ type: 'SET_SAVING', isSaving: true })
    dispatch({ type: 'SET_ERROR', error: null })

    try {
      const payload = {
        name: state.name.trim(),
        exercises: state.exercises.map((ex) => ({
          exercise_id: ex.exercise_id,
          sort_order: ex.sort_order,
          rest_timer_seconds: ex.rest_timer_seconds,
          notes: ex.notes,
          sets: ex.sets,
        })),
      }

      if (isEditing && routine) {
        await updateRoutine(token, routine.id, payload)
      } else {
        await createRoutine(token, payload)
      }

      onSave()
    } catch (e) {
      dispatch({
        type: 'SET_ERROR',
        error: e instanceof Error ? e.message : 'Failed to save routine',
      })
    } finally {
      dispatch({ type: 'SET_SAVING', isSaving: false })
    }
  }, [token, state.name, state.exercises, isEditing, routine, onSave])

  const handleAddExercise = useCallback((exercise: Exercise) => {
    dispatch({ type: 'ADD_EXERCISE', exercise })
  }, [])

  return (
    <div className="fixed inset-0 z-50 bg-gray-900 flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-700">
        <button
          type="button"
          onClick={onClose}
          className="text-gray-400 hover:text-gray-200 text-sm font-medium"
        >
          Cancel
        </button>
        <h2 className="font-semibold">{isEditing ? 'Edit Routine' : 'New Routine'}</h2>
        <button
          type="button"
          onClick={handleSave}
          disabled={state.isSaving}
          className="text-flame-400 hover:text-flame-300 text-sm font-medium disabled:opacity-50"
        >
          {state.isSaving ? 'Saving...' : 'Save'}
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 max-w-2xl mx-auto w-full">
        {state.error && (
          <div className="bg-red-900/30 border border-red-700 rounded-lg p-3 mb-4 text-sm text-red-300">
            {state.error}
          </div>
        )}

        {/* Name input */}
        <input
          type="text"
          value={state.name}
          onChange={(e) => dispatch({ type: 'SET_NAME', name: e.target.value })}
          placeholder="Routine name (e.g. Push Day)"
          maxLength={100}
          className="w-full bg-gray-800/50 border border-gray-700 rounded-lg px-4 py-3 text-lg font-semibold placeholder-gray-600 focus:outline-none focus:border-flame-500 mb-4"
        />

        {/* Exercise list */}
        <div className="space-y-3 mb-4">
          {state.exercises.map((ex, i) => (
            <RoutineExerciseRow
              key={`${ex.exercise_id}-${i}`}
              exercise={ex}
              index={i}
              total={state.exercises.length}
              onRemove={() => dispatch({ type: 'REMOVE_EXERCISE', index: i })}
              onMoveUp={() => dispatch({ type: 'MOVE_EXERCISE', index: i, direction: 'up' })}
              onMoveDown={() => dispatch({ type: 'MOVE_EXERCISE', index: i, direction: 'down' })}
              onUpdateExercise={(updates) =>
                dispatch({ type: 'UPDATE_EXERCISE', index: i, updates })
              }
              onAddSet={() => dispatch({ type: 'ADD_SET', exerciseIndex: i })}
              onRemoveSet={(setIndex) =>
                dispatch({ type: 'REMOVE_SET', exerciseIndex: i, setIndex })
              }
              onUpdateSet={(setIndex, updates) =>
                dispatch({ type: 'UPDATE_SET', exerciseIndex: i, setIndex, updates })
              }
            />
          ))}
        </div>

        {/* Add exercise button */}
        <button
          type="button"
          onClick={() => setShowExerciseSearch(true)}
          className="w-full flex items-center justify-center gap-2 py-3 border-2 border-dashed border-gray-700 rounded-xl text-gray-400 hover:text-gray-300 hover:border-gray-600 transition-colors"
        >
          <Plus className="w-5 h-5" />
          Add Exercise
        </button>
      </div>

      {/* Exercise search modal */}
      {showExerciseSearch && (
        <ExerciseSearchModal
          onSelect={handleAddExercise}
          onClose={() => setShowExerciseSearch(false)}
          onCreateCustom={() => {
            setShowExerciseSearch(false)
            setShowCreateExercise(true)
          }}
        />
      )}

      {/* Create exercise form */}
      {showCreateExercise && (
        <div className="fixed inset-0 z-[65] bg-gray-900/95 flex items-start justify-center pt-12 overflow-y-auto">
          <div className="w-full max-w-lg p-4">
            <CreateExerciseForm
              onCreated={(exercise) => {
                handleAddExercise(exercise)
                setShowCreateExercise(false)
              }}
              onClose={() => setShowCreateExercise(false)}
            />
          </div>
        </div>
      )}
    </div>
  )
}
