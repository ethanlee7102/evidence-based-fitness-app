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

export interface LandmarkPoint {
  x: number
  y: number
  visibility: number
}

export interface FrameLandmarks {
  frame: number
  points: Record<number, LandmarkPoint>
}

export interface PhaseBoundary {
  y: number
  between_phases: [number, number]
}

export interface AnalysisResult {
  id: string
  techniqueScore: number
  issues: FormIssue[]
  barPath?: BarPathPoint[]
  videoUrl?: string
  landmarks?: FrameLandmarks[]
  fps?: number
  phaseBoundaries?: PhaseBoundary[]
}
