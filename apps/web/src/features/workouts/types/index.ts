// Workout feature types — snake_case matching backend wire format

export type Equipment =
  | 'barbell'
  | 'dumbbell'
  | 'cable'
  | 'machine'
  | 'bodyweight'
  | 'band'
  | 'kettlebell'
  | 'other'

export type SetType = 'normal' | 'warmup' | 'dropset' | 'failure'

export interface MuscleGroup {
  id: string
  name: string
  category: string
  display_order: number
}

export interface ExerciseMuscle {
  muscle_group_id: string
  muscle_group_name: string
  muscle_group_category: string
  activation_level: 'maximum' | 'high' | 'medium' | 'partial'
}

export interface Exercise {
  id: string
  name: string
  aliases: string[]
  equipment: Equipment | null
  movement_pattern: string | null
  force_type: string | null
  body_region: 'upper' | 'lower' | 'full' | null
  laterality: 'bilateral' | 'unilateral'
  is_compound: boolean
  instructions: string[]
  video_url: string | null
  is_global: boolean
  muscles: ExerciseMuscle[]
}

export interface WorkoutSet {
  id: string
  workout_exercise_id: string
  set_number: number
  weight_kg: number | null
  reps: number | null
  rpe: number | null
  set_type: SetType
  duration_seconds: number | null
  rest_seconds: number | null
  is_to_failure: boolean
  completed: boolean
  completed_at: string | null
  created_at: string
}

export interface WorkoutExercise {
  id: string
  workout_id: string
  exercise_id: string
  exercise: Exercise
  sort_order: number
  superset_group: number | null
  rest_timer_seconds: number | null
  notes: string | null
  sets: WorkoutSet[]
}

export interface Workout {
  id: string
  user_id: string
  started_at: string
  completed_at: string | null
  duration_seconds: number | null
  body_weight_kg: number | null
  rating: number | null
  notes: string | null
  created_at: string
  exercises: WorkoutExercise[]
}

export interface WorkoutSummary {
  id: string
  user_id: string
  started_at: string
  completed_at: string | null
  duration_seconds: number | null
  rating: number | null
  notes: string | null
  exercise_count: number
  set_count: number
  total_volume_kg: number
}

export interface PreviousSetData {
  set_number: number
  weight_kg: number | null
  reps: number | null
}

export interface CreateExerciseRequest {
  name: string
  equipment?: Equipment | null
  movement_pattern?: string | null
  force_type?: string | null
  body_region?: 'upper' | 'lower' | 'full' | null
  laterality?: 'bilateral' | 'unilateral'
  is_compound?: boolean
  instructions?: string[]
  muscle_group_ids?: string[]
}

export interface FinishWorkoutRequest {
  rating?: number | null
  body_weight_kg?: number | null
  notes?: string | null
  duration_seconds?: number | null
}

// --- Exercise Stats ---

export interface ExerciseSetHistory {
  date: string
  weight_kg: number | null
  reps: number | null
  rpe: number | null
  set_type: SetType
  volume: number
}

export interface ExerciseVolumePoint {
  date: string
  volume: number
  sets: number
}

export interface ExerciseStats {
  exercise_id: string
  recent_sets: ExerciseSetHistory[]
  volume_history: ExerciseVolumePoint[]
}

// Muscle categories for filters
export const MUSCLE_CATEGORIES = [
  'Chest',
  'Back',
  'Shoulders',
  'Biceps',
  'Triceps',
  'Forearms',
  'Quads',
  'Hamstrings',
  'Glutes',
  'Calves',
  'Abs',
] as const

export const EQUIPMENT_OPTIONS: Equipment[] = [
  'barbell',
  'dumbbell',
  'cable',
  'machine',
  'bodyweight',
  'band',
  'kettlebell',
  'other',
]

// --- Routines ---

export interface RoutineSet {
  id: string
  routine_exercise_id: string
  set_number: number
  target_reps: number | null
  set_type: SetType
}

export interface RoutineExercise {
  id: string
  routine_id: string
  exercise_id: string
  exercise: Exercise
  sort_order: number
  rest_timer_seconds: number | null
  notes: string | null
  sets: RoutineSet[]
}

export interface Routine {
  id: string
  user_id: string
  name: string
  last_used_at: string | null
  use_count: number
  created_at: string
  updated_at: string
  exercises: RoutineExercise[]
}

export interface RoutineSummary {
  id: string
  name: string
  exercise_count: number
  total_sets: number
  last_used_at: string | null
  use_count: number
}

export interface RoutineExerciseInput {
  exercise_id: string
  exercise: Exercise
  sort_order: number
  rest_timer_seconds: number | null
  notes: string | null
  sets: RoutineSetInput[]
}

export interface RoutineSetInput {
  set_number: number
  target_reps: number | null
  set_type: SetType
}

// Workout history filter types
export type DatePreset = 'week' | 'month' | '3months' | 'all'

export interface WorkoutFilters {
  datePreset: DatePreset
  dateFrom: string | null
  dateTo: string | null
  minRating: number | null
  exerciseId: string | null
  exerciseName: string | null
}
