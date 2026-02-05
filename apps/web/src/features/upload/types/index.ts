export type ExerciseType = 'deadlift' | 'squat' | 'bench'

export interface UploadState {
  file: File | null
  preview: string | null
  exerciseType: ExerciseType
  uploading: boolean
  analyzing: boolean
  progress: number
  error: string | null
}
