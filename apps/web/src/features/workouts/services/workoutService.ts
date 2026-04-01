import { apiRequest } from '../../../lib/api'
import type {
  CreateExerciseRequest,
  Exercise,
  ExerciseStats,
  FinishWorkoutRequest,
  MuscleGroup,
  PreviousSetData,
  Routine,
  RoutineExerciseInput,
  RoutineSummary,
  Workout,
  WorkoutSet,
  WorkoutSummary,
} from '../types'

// --- Muscle Groups ---

export async function getMuscleGroups(token: string): Promise<MuscleGroup[]> {
  return apiRequest<MuscleGroup[]>('/workouts/muscle-groups', { token })
}

// --- Exercises ---

export async function searchExercises(
  token: string,
  params?: { q?: string; equipment?: string; muscle_category?: string },
): Promise<Exercise[]> {
  const searchParams = new URLSearchParams()
  if (params?.q) searchParams.set('q', params.q)
  if (params?.equipment) searchParams.set('equipment', params.equipment)
  if (params?.muscle_category) searchParams.set('muscle_category', params.muscle_category)
  const qs = searchParams.toString()
  return apiRequest<Exercise[]>(`/workouts/exercises${qs ? `?${qs}` : ''}`, { token })
}

export async function getExercise(token: string, exerciseId: string): Promise<Exercise> {
  return apiRequest<Exercise>(`/workouts/exercises/${exerciseId}`, { token })
}

export async function createExercise(
  token: string,
  data: CreateExerciseRequest,
): Promise<Exercise> {
  return apiRequest<Exercise>('/workouts/exercises', {
    method: 'POST',
    token,
    body: JSON.stringify(data),
  })
}

export async function getPreviousSets(
  token: string,
  exerciseId: string,
): Promise<PreviousSetData[]> {
  return apiRequest<PreviousSetData[]>(`/workouts/exercises/${exerciseId}/previous`, { token })
}

export async function getExerciseStats(
  token: string,
  exerciseId: string,
): Promise<ExerciseStats> {
  return apiRequest<ExerciseStats>(`/workouts/exercises/${exerciseId}/stats`, { token })
}

export async function getRecentExercises(
  token: string,
  limit: number = 10,
): Promise<Exercise[]> {
  return apiRequest<Exercise[]>(`/workouts/exercises/recent?limit=${limit}`, { token })
}

// --- Workouts ---

export async function startWorkout(token: string): Promise<Workout> {
  return apiRequest<Workout>('/workouts', { method: 'POST', token })
}

export async function listWorkouts(
  token: string,
  params?: {
    limit?: number
    offset?: number
    date_from?: string
    date_to?: string
    min_rating?: number
    exercise_id?: string
  },
): Promise<WorkoutSummary[]> {
  const searchParams = new URLSearchParams()
  if (params?.limit) searchParams.set('limit', String(params.limit))
  if (params?.offset) searchParams.set('offset', String(params.offset))
  if (params?.date_from) searchParams.set('date_from', params.date_from)
  if (params?.date_to) searchParams.set('date_to', params.date_to)
  if (params?.min_rating) searchParams.set('min_rating', String(params.min_rating))
  if (params?.exercise_id) searchParams.set('exercise_id', params.exercise_id)
  const qs = searchParams.toString()
  return apiRequest<WorkoutSummary[]>(`/workouts${qs ? `?${qs}` : ''}`, { token })
}

export async function getInProgressWorkout(token: string): Promise<Workout | null> {
  return apiRequest<Workout | null>('/workouts/in-progress', { token })
}

export async function getWorkout(token: string, workoutId: string): Promise<Workout> {
  return apiRequest<Workout>(`/workouts/${workoutId}`, { token })
}

export async function finishWorkout(
  token: string,
  workoutId: string,
  data: FinishWorkoutRequest,
): Promise<Workout> {
  return apiRequest<Workout>(`/workouts/${workoutId}/finish`, {
    method: 'PATCH',
    token,
    body: JSON.stringify(data),
  })
}

export async function deleteWorkout(token: string, workoutId: string): Promise<void> {
  await apiRequest(`/workouts/${workoutId}`, { method: 'DELETE', token })
}

// --- Workout Exercises ---

export async function addExerciseToWorkout(
  token: string,
  workoutId: string,
  exerciseId: string,
  sortOrder: number,
): Promise<unknown> {
  return apiRequest(`/workouts/${workoutId}/exercises`, {
    method: 'POST',
    token,
    body: JSON.stringify({ exercise_id: exerciseId, sort_order: sortOrder }),
  })
}

export async function removeExerciseFromWorkout(
  token: string,
  workoutId: string,
  workoutExerciseId: string,
): Promise<void> {
  await apiRequest(`/workouts/${workoutId}/exercises/${workoutExerciseId}`, {
    method: 'DELETE',
    token,
  })
}

export async function updateWorkoutExercise(
  token: string,
  workoutId: string,
  workoutExerciseId: string,
  data: { rest_timer_seconds?: number | null; notes?: string | null },
): Promise<unknown> {
  return apiRequest(`/workouts/${workoutId}/exercises/${workoutExerciseId}`, {
    method: 'PATCH',
    token,
    body: JSON.stringify(data),
  })
}

export async function reorderExercises(
  token: string,
  workoutId: string,
  order: { workout_exercise_id: string; sort_order: number }[],
): Promise<void> {
  await apiRequest(`/workouts/${workoutId}/exercises/reorder`, {
    method: 'PATCH',
    token,
    body: JSON.stringify({ order }),
  })
}

// --- Sets ---

export async function addSet(
  token: string,
  workoutId: string,
  workoutExerciseId: string,
  data: { set_number: number; weight_kg?: number | null; reps?: number | null; set_type?: string },
): Promise<WorkoutSet> {
  return apiRequest<WorkoutSet>(
    `/workouts/${workoutId}/exercises/${workoutExerciseId}/sets`,
    { method: 'POST', token, body: JSON.stringify(data) },
  )
}

export async function updateSet(
  token: string,
  workoutId: string,
  setId: string,
  data: Partial<{
    weight_kg: number | null
    reps: number | null
    rpe: number | null
    set_type: string
    completed: boolean
    is_to_failure: boolean
  }>,
): Promise<WorkoutSet> {
  return apiRequest<WorkoutSet>(`/workouts/${workoutId}/sets/${setId}`, {
    method: 'PATCH',
    token,
    body: JSON.stringify(data),
  })
}

export async function deleteSet(
  token: string,
  workoutId: string,
  setId: string,
): Promise<void> {
  await apiRequest(`/workouts/${workoutId}/sets/${setId}`, { method: 'DELETE', token })
}

// --- Routines ---

export async function listRoutines(token: string): Promise<RoutineSummary[]> {
  return apiRequest<RoutineSummary[]>('/routines', { token })
}

export async function getRoutine(token: string, routineId: string): Promise<Routine> {
  return apiRequest<Routine>(`/routines/${routineId}`, { token })
}

export async function createRoutine(
  token: string,
  data: { name: string; exercises: Omit<RoutineExerciseInput, 'exercise'>[] },
): Promise<Routine> {
  return apiRequest<Routine>('/routines', {
    method: 'POST',
    token,
    body: JSON.stringify(data),
  })
}

export async function updateRoutine(
  token: string,
  routineId: string,
  data: { name: string; exercises: Omit<RoutineExerciseInput, 'exercise'>[] },
): Promise<Routine> {
  return apiRequest<Routine>(`/routines/${routineId}`, {
    method: 'PUT',
    token,
    body: JSON.stringify(data),
  })
}

export async function deleteRoutine(token: string, routineId: string): Promise<void> {
  await apiRequest(`/routines/${routineId}`, { method: 'DELETE', token })
}

export async function duplicateRoutine(token: string, routineId: string): Promise<Routine> {
  return apiRequest<Routine>(`/routines/${routineId}/duplicate`, { method: 'POST', token })
}

export async function startWorkoutFromRoutine(
  token: string,
  routineId: string,
): Promise<Workout> {
  return apiRequest<Workout>(`/routines/${routineId}/start-workout`, { method: 'POST', token })
}

export async function saveWorkoutAsRoutine(
  token: string,
  workoutId: string,
  name: string,
): Promise<Routine> {
  return apiRequest<Routine>(`/routines/from-workout/${workoutId}`, {
    method: 'POST',
    token,
    body: JSON.stringify({ name }),
  })
}
