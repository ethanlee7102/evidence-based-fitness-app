export type ExerciseType = 'deadlift' | 'squat' | 'bench'
export type CameraSide = 'left' | 'right'

export interface UploadState {
  file: File | null
  preview: string | null
  exerciseType: ExerciseType
  cameraSide: CameraSide
  uploading: boolean
  analyzing: boolean
  progress: number
  error: string | null
}
