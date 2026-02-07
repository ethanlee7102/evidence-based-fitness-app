import type { OnboardingData, UserProfile } from '@flame-fitness/shared'
import { apiRequest } from '../../../lib/api'

export async function getProfile(token: string): Promise<UserProfile> {
  return apiRequest<UserProfile>('/profile/me', { token })
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

  return apiRequest<UserProfile>('/profile/onboarding', {
    method: 'POST',
    body: JSON.stringify(payload),
    token,
  })
}
