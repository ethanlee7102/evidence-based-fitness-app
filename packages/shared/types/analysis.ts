export type ExerciseType = 'squat' | 'bench' | 'deadlift'

export type IssueSeverity = 'minor' | 'moderate' | 'major'

export interface FormIssue {
  issue: string
  severity: IssueSeverity
  description: string
  frames?: number[]
}

export interface BarPathPoint {
  x: number
  y: number
  frame: number
}

export interface AnalysisResult {
  id: string
  techniqueScore: number
  issues: FormIssue[]
  barPath?: BarPathPoint[]
  landmarksData?: Record<string, unknown>
}

export interface Analysis {
  id: string
  videoId: string
  techniqueScore: number
  issues: FormIssue[]
  landmarksData?: Record<string, unknown>
  barPath?: BarPathPoint[]
  processedAt: string
}

export interface Landmark {
  x: number
  y: number
  z: number
  visibility: number
}

export interface PoseFrame {
  frameNumber: number
  timestamp: number
  landmarks: Record<number, Landmark>
}

export const LANDMARK_INDICES = {
  LEFT_SHOULDER: 11,
  RIGHT_SHOULDER: 12,
  LEFT_ELBOW: 13,
  RIGHT_ELBOW: 14,
  LEFT_WRIST: 15,
  RIGHT_WRIST: 16,
  LEFT_HIP: 23,
  RIGHT_HIP: 24,
  LEFT_KNEE: 25,
  RIGHT_KNEE: 26,
  LEFT_ANKLE: 27,
  RIGHT_ANKLE: 28,
} as const
