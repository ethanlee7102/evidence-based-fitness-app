import { useReducer, useCallback, useRef, useEffect } from 'react'
import { useAuth } from '../../auth/hooks/useAuth'
import {
  startWorkout,
  getWorkout,
  addExerciseToWorkout,
  removeExerciseFromWorkout,
  addSet as addSetApi,
  updateSet as updateSetApi,
  deleteSet as deleteSetApi,
  finishWorkout,
  getPreviousSets,
  reorderExercises as reorderExercisesApi,
  updateWorkoutExercise,
} from '../services/workoutService'
import type {
  Exercise,
  FinishWorkoutRequest,
  PreviousSetData,
  Workout,
  WorkoutExercise,
  WorkoutSet,
} from '../types'

// --- State ---

interface ActiveWorkoutState {
  workout: Workout | null
  previousSets: Record<string, PreviousSetData[]> // keyed by exercise_id
  isLoading: boolean
  isSaving: boolean
  error: string | null
}

type Action =
  | { type: 'SET_LOADING'; loading: boolean }
  | { type: 'SET_SAVING'; saving: boolean }
  | { type: 'SET_ERROR'; error: string | null }
  | { type: 'SET_WORKOUT'; workout: Workout }
  | { type: 'ADD_EXERCISE_PENDING'; placeholderId: string; exercise: Exercise; sortOrder: number }
  | { type: 'ADD_EXERCISE'; placeholderId: string; exercise: WorkoutExercise }
  | { type: 'REMOVE_EXERCISE'; workoutExerciseId: string }
  | { type: 'REORDER_EXERCISES'; order: { id: string; sort_order: number }[] }
  | { type: 'ADD_SET'; workoutExerciseId: string; set: WorkoutSet }
  | { type: 'UPDATE_SET'; setId: string; updates: Partial<WorkoutSet> }
  | { type: 'DELETE_SET'; workoutExerciseId: string; setId: string }
  | { type: 'SET_PREVIOUS'; exerciseId: string; sets: PreviousSetData[] }
  | { type: 'UPDATE_EXERCISE'; workoutExerciseId: string; updates: { rest_timer_seconds?: number | null; notes?: string | null } }
  | { type: 'FINISH'; workout: Workout }

const initialState: ActiveWorkoutState = {
  workout: null,
  previousSets: {},
  isLoading: true,
  isSaving: false,
  error: null,
}

function reducer(state: ActiveWorkoutState, action: Action): ActiveWorkoutState {
  switch (action.type) {
    case 'SET_LOADING':
      return { ...state, isLoading: action.loading }

    case 'SET_SAVING':
      return { ...state, isSaving: action.saving }

    case 'SET_ERROR':
      return { ...state, error: action.error }

    case 'SET_WORKOUT':
      return { ...state, workout: action.workout, isLoading: false }

    case 'ADD_EXERCISE_PENDING': {
      if (!state.workout) return state
      const placeholder: WorkoutExercise = {
        id: action.placeholderId,
        workout_id: state.workout.id,
        exercise_id: action.exercise.id,
        exercise: action.exercise,
        sort_order: action.sortOrder,
        superset_group: null,
        rest_timer_seconds: null,
        notes: null,
        sets: [],
        _loading: true,
      } as WorkoutExercise & { _loading: true }
      return {
        ...state,
        workout: {
          ...state.workout,
          exercises: [...state.workout.exercises, placeholder],
        },
      }
    }

    case 'ADD_EXERCISE': {
      if (!state.workout) return state
      return {
        ...state,
        workout: {
          ...state.workout,
          exercises: state.workout.exercises.map((we) =>
            we.id === action.placeholderId ? action.exercise : we,
          ),
        },
      }
    }

    case 'REMOVE_EXERCISE': {
      if (!state.workout) return state
      return {
        ...state,
        workout: {
          ...state.workout,
          exercises: state.workout.exercises.filter(
            (we) => we.id !== action.workoutExerciseId,
          ),
        },
      }
    }

    case 'REORDER_EXERCISES': {
      if (!state.workout) return state
      const orderMap = new Map(action.order.map((o) => [o.id, o.sort_order]))
      const sorted = [...state.workout.exercises]
        .map((we) => ({
          ...we,
          sort_order: orderMap.get(we.id) ?? we.sort_order,
        }))
        .sort((a, b) => a.sort_order - b.sort_order)
      return {
        ...state,
        workout: { ...state.workout, exercises: sorted },
      }
    }

    case 'ADD_SET': {
      if (!state.workout) return state
      return {
        ...state,
        workout: {
          ...state.workout,
          exercises: state.workout.exercises.map((we) =>
            we.id === action.workoutExerciseId
              ? { ...we, sets: [...we.sets, action.set] }
              : we,
          ),
        },
      }
    }

    case 'UPDATE_SET': {
      if (!state.workout) return state
      return {
        ...state,
        workout: {
          ...state.workout,
          exercises: state.workout.exercises.map((we) => ({
            ...we,
            sets: we.sets.map((s) =>
              s.id === action.setId ? { ...s, ...action.updates } : s,
            ),
          })),
        },
      }
    }

    case 'DELETE_SET': {
      if (!state.workout) return state
      return {
        ...state,
        workout: {
          ...state.workout,
          exercises: state.workout.exercises.map((we) =>
            we.id === action.workoutExerciseId
              ? { ...we, sets: we.sets.filter((s) => s.id !== action.setId) }
              : we,
          ),
        },
      }
    }

    case 'SET_PREVIOUS':
      return {
        ...state,
        previousSets: {
          ...state.previousSets,
          [action.exerciseId]: action.sets,
        },
      }

    case 'UPDATE_EXERCISE': {
      if (!state.workout) return state
      return {
        ...state,
        workout: {
          ...state.workout,
          exercises: state.workout.exercises.map((we) =>
            we.id === action.workoutExerciseId
              ? { ...we, ...action.updates }
              : we,
          ),
        },
      }
    }

    case 'FINISH':
      return { ...state, workout: action.workout }

    default:
      return state
  }
}

// --- Hook ---

export function useActiveWorkout(resumeWorkoutId: string | null) {
  const { session: authSession } = useAuth()
  const token = authSession?.access_token

  const [state, dispatch] = useReducer(reducer, initialState)
  const debounceTimers = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map())
  const initRef = useRef(false)

  // Initialize workout
  useEffect(() => {
    if (!token || initRef.current) return
    initRef.current = true

    const init = async () => {
      try {
        dispatch({ type: 'SET_LOADING', loading: true })

        let workout: Workout
        if (resumeWorkoutId) {
          workout = await getWorkout(token, resumeWorkoutId)
        } else {
          workout = await startWorkout(token)
        }
        dispatch({ type: 'SET_WORKOUT', workout })

        // Load previous sets for all exercises in resumed workout
        if (resumeWorkoutId && workout.exercises.length > 0) {
          for (const we of workout.exercises) {
            getPreviousSets(token, we.exercise_id)
              .then((sets) =>
                dispatch({ type: 'SET_PREVIOUS', exerciseId: we.exercise_id, sets }),
              )
              .catch(() => {})
          }
        }
      } catch (e) {
        dispatch({
          type: 'SET_ERROR',
          error: e instanceof Error ? e.message : 'Failed to start workout',
        })
        dispatch({ type: 'SET_LOADING', loading: false })
      }
    }
    init()

    // Flush pending updates and cleanup debounce timers on unmount
    return () => {
      debounceTimers.current.forEach((timer) => clearTimeout(timer))
      debounceTimers.current.clear()
      // Flush any pending debounced updates
      pendingUpdates.current.forEach((updates, setId) => {
        syncRef.current(setId, updates)
      })
      pendingUpdates.current.clear()
    }
  }, [token, resumeWorkoutId])

  // Add exercise — show skeleton immediately, replace when server responds
  const addExercise = useCallback(
    async (exercise: Exercise) => {
      if (!token || !state.workout) return
      const sortOrder = state.workout.exercises.length
      const placeholderId = `pending-${Date.now()}`

      // Optimistic: show skeleton card right away
      dispatch({ type: 'ADD_EXERCISE_PENDING', placeholderId, exercise, sortOrder })

      try {
        const result = await addExerciseToWorkout(
          token,
          state.workout.id,
          exercise.id,
          sortOrder,
        )

        const weId = (result as { id: string }).id

        // Auto-create first set
        const firstSet = await addSetApi(token, state.workout.id, weId, {
          set_number: 1,
        })

        // Replace placeholder with real data
        const we: WorkoutExercise = {
          id: weId,
          workout_id: state.workout.id,
          exercise_id: exercise.id,
          exercise,
          sort_order: sortOrder,
          superset_group: null,
          rest_timer_seconds: null,
          notes: null,
          sets: [firstSet],
        }
        dispatch({ type: 'ADD_EXERCISE', placeholderId, exercise: we })

        // Fetch previous sets
        getPreviousSets(token, exercise.id)
          .then((sets) =>
            dispatch({ type: 'SET_PREVIOUS', exerciseId: exercise.id, sets }),
          )
          .catch(() => {})
      } catch (e) {
        // Remove the placeholder on error
        dispatch({ type: 'REMOVE_EXERCISE', workoutExerciseId: placeholderId })
        dispatch({
          type: 'SET_ERROR',
          error: e instanceof Error ? e.message : 'Failed to add exercise',
        })
      }
    },
    [token, state.workout],
  )

  // Remove exercise
  const removeExercise = useCallback(
    async (workoutExerciseId: string) => {
      if (!token || !state.workout) return

      dispatch({ type: 'REMOVE_EXERCISE', workoutExerciseId })

      try {
        await removeExerciseFromWorkout(token, state.workout.id, workoutExerciseId)
      } catch (e) {
        console.error('Failed to remove exercise:', e)
        // Re-fetch workout on error
        const workout = await getWorkout(token, state.workout.id)
        dispatch({ type: 'SET_WORKOUT', workout })
      }
    },
    [token, state.workout],
  )

  // Reorder exercises
  const reorderExercises = useCallback(
    async (workoutExerciseId: string, direction: 'up' | 'down') => {
      if (!token || !state.workout) return

      const exercises = [...state.workout.exercises]
      const idx = exercises.findIndex((we) => we.id === workoutExerciseId)
      if (idx === -1) return
      if (direction === 'up' && idx === 0) return
      if (direction === 'down' && idx === exercises.length - 1) return

      const swapIdx = direction === 'up' ? idx - 1 : idx + 1
      const order = exercises.map((we, i) => {
        if (i === idx) return { id: we.id, sort_order: swapIdx }
        if (i === swapIdx) return { id: we.id, sort_order: idx }
        return { id: we.id, sort_order: i }
      })

      dispatch({ type: 'REORDER_EXERCISES', order })

      try {
        await reorderExercisesApi(
          token,
          state.workout.id,
          order.map((o) => ({
            workout_exercise_id: o.id,
            sort_order: o.sort_order,
          })),
        )
      } catch (e) {
        console.error('Failed to reorder:', e)
      }
    },
    [token, state.workout],
  )

  // Add set
  const addSetToExercise = useCallback(
    async (workoutExerciseId: string) => {
      if (!token || !state.workout) return

      const we = state.workout.exercises.find((e) => e.id === workoutExerciseId)
      if (!we) return

      const setNumber = we.sets.length + 1

      try {
        const newSet = await addSetApi(token, state.workout.id, workoutExerciseId, {
          set_number: setNumber,
        })
        dispatch({ type: 'ADD_SET', workoutExerciseId, set: newSet })
      } catch (e) {
        dispatch({
          type: 'SET_ERROR',
          error: e instanceof Error ? e.message : 'Failed to add set',
        })
      }
    },
    [token, state.workout],
  )

  // Server sync via ref to avoid stale closures in debounce timers
  const syncSetToServer = useCallback(
    async (setId: string, updates: Partial<WorkoutSet>) => {
      if (!token || !state.workout) return
      try {
        const serverUpdates: Record<string, unknown> = {}
        if (updates.weight_kg !== undefined) serverUpdates.weight_kg = updates.weight_kg
        if (updates.reps !== undefined) serverUpdates.reps = updates.reps
        if (updates.rpe !== undefined) serverUpdates.rpe = updates.rpe
        if (updates.set_type !== undefined) serverUpdates.set_type = updates.set_type
        if (updates.completed !== undefined) serverUpdates.completed = updates.completed
        if (updates.is_to_failure !== undefined) serverUpdates.is_to_failure = updates.is_to_failure

        if (Object.keys(serverUpdates).length > 0) {
          await updateSetApi(token, state.workout.id, setId, serverUpdates)
        }
      } catch (e) {
        console.error('Failed to sync set:', e)
        dispatch({
          type: 'SET_ERROR',
          error: 'Failed to save set. Check your connection.',
        })
      }
    },
    [token, state.workout?.id],
  )

  // Ref always points to latest syncSetToServer to avoid stale closures in setTimeout
  const syncRef = useRef(syncSetToServer)
  useEffect(() => { syncRef.current = syncSetToServer }, [syncSetToServer])

  // Track pending updates so we can flush on unmount
  const pendingUpdates = useRef<Map<string, Partial<WorkoutSet>>>(new Map())

  // Update set (optimistic + debounced server sync)
  const updateSetLocal = useCallback(
    (setId: string, updates: Partial<WorkoutSet>) => {
      dispatch({ type: 'UPDATE_SET', setId, updates })

      // Debounce server sync (except for 'completed' which should be immediate)
      if (updates.completed !== undefined) {
        // Cancel any pending debounce timer to prevent stale partial updates racing
        const existing = debounceTimers.current.get(setId)
        if (existing) {
          clearTimeout(existing)
          debounceTimers.current.delete(setId)
        }
        pendingUpdates.current.delete(setId)
        syncRef.current(setId, updates)
      } else {
        pendingUpdates.current.set(setId, updates)
        const existing = debounceTimers.current.get(setId)
        if (existing) clearTimeout(existing)

        const timer = setTimeout(() => {
          syncRef.current(setId, updates)
          debounceTimers.current.delete(setId)
          pendingUpdates.current.delete(setId)
        }, 500)
        debounceTimers.current.set(setId, timer)
      }
    },
    [],
  )

  // Delete set
  const deleteSet = useCallback(
    async (workoutExerciseId: string, setId: string) => {
      if (!token || !state.workout) return

      dispatch({ type: 'DELETE_SET', workoutExerciseId, setId })

      try {
        await deleteSetApi(token, state.workout.id, setId)
      } catch (e) {
        console.error('Failed to delete set:', e)
      }
    },
    [token, state.workout],
  )

  // Finish workout
  const handleFinishWorkout = useCallback(
    async (data: FinishWorkoutRequest) => {
      if (!token || !state.workout) return null

      try {
        dispatch({ type: 'SET_SAVING', saving: true })
        const result = await finishWorkout(token, state.workout.id, data)
        dispatch({ type: 'FINISH', workout: result })
        return result
      } catch (e) {
        dispatch({
          type: 'SET_ERROR',
          error: e instanceof Error ? e.message : 'Failed to finish workout',
        })
        return null
      } finally {
        dispatch({ type: 'SET_SAVING', saving: false })
      }
    },
    [token, state.workout],
  )

  // Update exercise (rest timer, notes)
  const updateExercise = useCallback(
    async (workoutExerciseId: string, updates: { rest_timer_seconds?: number | null; notes?: string | null }) => {
      if (!token || !state.workout) return

      dispatch({ type: 'UPDATE_EXERCISE', workoutExerciseId, updates })

      try {
        await updateWorkoutExercise(token, state.workout.id, workoutExerciseId, updates)
      } catch (e) {
        console.error('Failed to update exercise:', e)
      }
    },
    [token, state.workout],
  )

  const clearError = useCallback(() => {
    dispatch({ type: 'SET_ERROR', error: null })
  }, [])

  return {
    workout: state.workout,
    previousSets: state.previousSets,
    isLoading: state.isLoading,
    isSaving: state.isSaving,
    error: state.error,
    addExercise,
    removeExercise,
    reorderExercises,
    addSetToExercise,
    updateSetLocal,
    deleteSet,
    finishWorkout: handleFinishWorkout,
    updateExercise,
    clearError,
  }
}
