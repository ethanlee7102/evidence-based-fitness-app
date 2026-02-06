import type { AnalysisResult } from '../types'
import { ScoreCard } from './ScoreCard'
import { IssuesList } from './IssuesList'
import { VideoLandmarkPlayer } from './VideoLandmarkPlayer'

interface ResultsDisplayProps {
  analysis: AnalysisResult
}

export function ResultsDisplay({ analysis }: ResultsDisplayProps) {
  console.log('=== ANALYSIS DATA ===', JSON.stringify(analysis, null, 2))
  const hasVideoData = analysis.videoUrl && analysis.landmarks && analysis.fps
  console.log('hasVideoData:', hasVideoData, 'phaseBoundaries:', analysis.phaseBoundaries)

  return (
    <div className="space-y-8">
      {/* Video with landmark overlay */}
      {hasVideoData && (
        <div>
          <h2 className="text-xl font-semibold mb-4">Pose Analysis</h2>
          <VideoLandmarkPlayer
            videoUrl={analysis.videoUrl!}
            landmarks={analysis.landmarks!}
            fps={analysis.fps!}
            phaseBoundaries={analysis.phaseBoundaries}
          />
        </div>
      )}

      <div className="grid md:grid-cols-3 gap-6">
        <div className="md:col-span-1">
          <ScoreCard score={analysis.techniqueScore} />
        </div>

        <div className="md:col-span-2 bg-gray-800/50 border border-gray-700 rounded-xl p-6">
          <h2 className="font-semibold mb-4">Score Breakdown</h2>
          <div className="space-y-3">
            <ScoreBar label="Bar Path" value={Math.min(100, analysis.techniqueScore + 5)} />
            <ScoreBar label="Back Position" value={Math.min(100, analysis.techniqueScore - 3)} />
            <ScoreBar label="Hip Hinge" value={analysis.techniqueScore} />
          </div>
        </div>
      </div>

      <div>
        <h2 className="text-xl font-semibold mb-4">Identified Issues</h2>
        <IssuesList issues={analysis.issues} />
      </div>

      <Recommendations score={analysis.techniqueScore} issues={analysis.issues} />
    </div>
  )
}

function ScoreBar({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span className="text-gray-400">{label}</span>
        <span>{value}%</span>
      </div>
      <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
        <div className="h-full bg-flame-500" style={{ width: `${value}%` }} />
      </div>
    </div>
  )
}

function Recommendations({
  score,
  issues,
}: {
  score: number
  issues: AnalysisResult['issues']
}) {
  const recommendations: string[] = []

  if (score < 80) {
    recommendations.push(
      'Focus on keeping the bar close to your body throughout the lift. The bar should travel in a straight vertical path.'
    )
  }

  if (issues.some((i) => i.issue.includes('back'))) {
    recommendations.push(
      'Practice maintaining a neutral spine. Consider using lighter weight to ingrain proper back position.'
    )
  }

  recommendations.push(
    'Continue to record and analyze your lifts regularly to track improvement over time.'
  )

  return (
    <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-6">
      <h2 className="font-semibold mb-4">Recommendations</h2>
      <ul className="space-y-3">
        {recommendations.map((rec, index) => (
          <li key={index} className="flex items-start gap-3">
            <span className="text-flame-500">•</span>
            <span className="text-gray-300">{rec}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}
