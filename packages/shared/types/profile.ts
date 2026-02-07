export type Gender = 'male' | 'female' | 'other' | 'prefer_not_to_say'

export type ExperienceLevel = 'beginner' | 'intermediate' | 'advanced'

export type FitnessGoal = 'strength' | 'build_muscle' | 'lose_weight' | 'general_fitness' | 'cardio_endurance'

export type UnitsPreference = 'metric' | 'imperial'

export type DayOfWeek = 'monday' | 'tuesday' | 'wednesday' | 'thursday' | 'friday' | 'saturday' | 'sunday'

export interface OnboardingData {
  displayName: string
  birthday: string // ISO date string
  gender: Gender
  heightCm: number
  weightKg: number
  unitsPreference: UnitsPreference
  experienceLevel: ExperienceLevel
  goal: FitnessGoal
  workoutDaysPerWeek: number
  preferredDays?: DayOfWeek[]
  injuriesLimitations?: string
}

export interface UserProfile {
  id: string
  username?: string
  displayName?: string
  birthday?: string
  gender?: Gender
  heightCm?: number
  weightKg?: number
  unitsPreference: UnitsPreference
  experienceLevel?: ExperienceLevel
  goal?: FitnessGoal
  workoutDaysPerWeek?: number
  preferredDays?: DayOfWeek[]
  injuriesLimitations?: string
  onboardingCompleted: boolean
  onboardingCompletedAt?: string
  createdAt: string
}
