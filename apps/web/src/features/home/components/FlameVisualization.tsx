interface FlameVisualizationProps {
  score?: number
  size?: 'sm' | 'md' | 'lg'
  animated?: boolean
}

export function FlameVisualization({
  score = 50,
  size = 'md',
  animated = true,
}: FlameVisualizationProps) {
  const sizeClasses = {
    sm: 'w-12 h-12',
    md: 'w-24 h-24',
    lg: 'w-40 h-40',
  }

  const getFlameColors = (score: number) => {
    if (score >= 90) {
      return { outer: '#22c55e', middle: '#4ade80', inner: '#86efac' }
    }
    if (score >= 70) {
      return { outer: '#f97316', middle: '#fb923c', inner: '#fde047' }
    }
    if (score >= 50) {
      return { outer: '#ef4444', middle: '#f97316', inner: '#fbbf24' }
    }
    return { outer: '#6b7280', middle: '#9ca3af', inner: '#d1d5db' }
  }

  const colors = getFlameColors(score)
  const intensity = score >= 90 ? 1.2 : score >= 70 ? 1.0 : score >= 50 ? 0.8 : 0.6

  return (
    <div className={`relative ${sizeClasses[size]}`}>
      <svg
        viewBox="0 0 100 120"
        className={`w-full h-full ${animated ? 'animate-flame-flicker' : ''}`}
        style={{ transform: `scale(${intensity})` }}
      >
        <defs>
          <linearGradient id={`flame-grad-${score}`} x1="50%" y1="100%" x2="50%" y2="0%">
            <stop offset="0%" stopColor={colors.outer} />
            <stop offset="50%" stopColor={colors.middle} />
            <stop offset="100%" stopColor={colors.inner} />
          </linearGradient>
          <filter id="flame-glow">
            <feGaussianBlur stdDeviation="3" result="coloredBlur" />
            <feMerge>
              <feMergeNode in="coloredBlur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        <path
          d="M50 10 C30 40 20 60 25 80 C28 95 40 105 50 105 C60 105 72 95 75 80 C80 60 70 40 50 10 Z"
          fill={`url(#flame-grad-${score})`}
          filter="url(#flame-glow)"
        />

        <path
          d="M50 35 C40 55 35 70 40 85 C43 92 47 97 50 97 C53 97 57 92 60 85 C65 70 60 55 50 35 Z"
          fill={colors.inner}
          opacity="0.9"
        />

        {score >= 70 && <circle cx="50" cy="75" r="8" fill="white" opacity="0.4" />}
      </svg>

      {score >= 90 && animated && (
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="absolute w-full h-full bg-green-400/20 rounded-full animate-ping" />
        </div>
      )}
    </div>
  )
}
