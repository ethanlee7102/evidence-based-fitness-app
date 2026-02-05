interface ScoreCardProps {
  score: number
}

export function ScoreCard({ score }: ScoreCardProps) {
  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-400'
    if (score >= 60) return 'text-yellow-400'
    return 'text-red-400'
  }

  const getScoreLabel = (score: number) => {
    if (score >= 90) return 'Excellent'
    if (score >= 80) return 'Good'
    if (score >= 70) return 'Decent'
    if (score >= 60) return 'Needs Work'
    return 'Needs Improvement'
  }

  return (
    <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-6 text-center">
      <div className="text-6xl font-bold mb-2">
        <span className={getScoreColor(score)}>{score}</span>
      </div>
      <p className="text-gray-400 text-sm">Technique Score</p>
      <p className={`mt-2 font-medium ${getScoreColor(score)}`}>
        {getScoreLabel(score)}
      </p>
    </div>
  )
}
