import type { OnboardingData, UserProfile } from '@flame-fitness/shared'
import { apiRequest } from '../../../lib/api'

interface ProfileApiResponse {
  id: string
  username?: string
  display_name?: string
  birthday?: string
  gender?: string
  height_cm?: number
  weight_kg?: number
  units_preference: string
  experience_level?: string
  goal?: string
  workout_days_per_week?: number
  preferred_days?: string[]
  injuries_limitations?: string
  onboarding_completed: boolean
  onboarding_completed_at?: string
  created_at: string
}

function mapProfileResponse(data: ProfileApiResponse): UserProfile {
  return {
    id: data.id,
    username: data.username,
    displayName: data.display_name,
    birthday: data.birthday,
    gender: data.gender as UserProfile['gender'],
    heightCm: data.height_cm,
    weightKg: data.weight_kg,
    unitsPreference: (data.units_preference || 'metric') as UserProfile['unitsPreference'],
    experienceLevel: data.experience_level as UserProfile['experienceLevel'],
    goal: data.goal as UserProfile['goal'],
    workoutDaysPerWeek: data.workout_days_per_week,
    preferredDays: data.preferred_days as UserProfile['preferredDays'],
    injuriesLimitations: data.injuries_limitations,
    onboardingCompleted: data.onboarding_completed,
    onboardingCompletedAt: data.onboarding_completed_at,
    createdAt: data.created_at,
  }
}

export async function getProfile(token: string): Promise<UserProfile> {
  const data = await apiRequest<ProfileApiResponse>('/profile/me', { token })
  return mapProfileResponse(data)
}

export async function completeOnboarding(
  token: string,
  data: OnboardingData
): Promise<UserProfile> {
  // Convert camelCase to snake_case for API
  const payload = {
    display_name: data.displayName,
    birthday: data.birthday,
    gender: data.gender,
    height_cm: data.heightCm,
    weight_kg: data.weightKg,
    units_preference: data.unitsPreference,
    experience_level: data.experienceLevel,
    goal: data.goal,
    workout_days_per_week: data.workoutDaysPerWeek,
    preferred_days: data.preferredDays,
    injuries_limitations: data.injuriesLimitations,
  }

  const response = await apiRequest<ProfileApiResponse>('/profile/onboarding', {
    method: 'POST',
    body: JSON.stringify(payload),
    token,
  })
  return mapProfileResponse(response)
}
