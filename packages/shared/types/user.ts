export interface UserProfile {
  id: string
  username?: string
  createdAt: string
}

export interface Video {
  id: string
  userId: string
  storagePath: string
  exerciseType: 'squat' | 'bench' | 'deadlift'
  durationSeconds?: number
  uploadedAt: string
}
