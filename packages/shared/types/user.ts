// UserProfile is now exported from profile.ts with full onboarding fields
export type { UserProfile } from './profile'

export interface Video {
  id: string
  userId: string
  storagePath: string
  exerciseType: 'squat' | 'bench' | 'deadlift'
  durationSeconds?: number
  uploadedAt: string
}
