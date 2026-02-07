import type { DayOfWeek, ExperienceLevel, FitnessGoal, Gender, UnitsPreference } from '@flame-fitness/shared'

export interface OnboardingFormData {
  // Step 1: Basic Info
  displayName: string
  birthday: string
  gender: Gender | ''

  // Step 2: Physical Stats
  heightCm: number | ''
  weightKg: number | ''
  unitsPreference: UnitsPreference

  // Step 3: Fitness Profile
  experienceLevel: ExperienceLevel | ''
  goal: FitnessGoal | ''

  // Step 4: Schedule
  workoutDaysPerWeek: number
  preferredDays: DayOfWeek[]
  injuriesLimitations: string
}

export const INITIAL_FORM_DATA: OnboardingFormData = {
  displayName: '',
  birthday: '',
  gender: '',
  heightCm: '',
  weightKg: '',
  unitsPreference: 'imperial',
  experienceLevel: '',
  goal: '',
  workoutDaysPerWeek: 3,
  preferredDays: [],
  injuriesLimitations: '',
}

export const ONBOARDING_STEPS = [
  { title: 'Basic Info', description: 'Tell us about yourself' },
  { title: 'Physical Stats', description: 'Your measurements' },
  { title: 'Fitness Profile', description: 'Your experience and goals' },
  { title: 'Schedule', description: 'Plan your week' },
] as const

export type OnboardingStep = 0 | 1 | 2 | 3
