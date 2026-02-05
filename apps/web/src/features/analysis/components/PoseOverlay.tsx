import type { BarPathPoint } from '../types'

interface PoseOverlayProps {
  barPath?: BarPathPoint[]
  width: number
  height: number
}

export function PoseOverlay({ barPath, width, height }: PoseOverlayProps) {
  if (!barPath || barPath.length < 2) {
    return null
  }

  const pathData = barPath
    .map((point, i) => {
      const x = point.x * width
      const y = point.y * height
      return `${i === 0 ? 'M' : 'L'} ${x} ${y}`
    })
    .join(' ')

  return (
    <svg
      width={width}
      height={height}
      className="absolute top-0 left-0 pointer-events-none"
    >
      <path
        d={pathData}
        fill="none"
        stroke="#f97316"
        strokeWidth="3"
        strokeLinecap="round"
        strokeLinejoin="round"
        opacity="0.8"
      />
      {barPath.map((point, i) => (
        <circle
          key={i}
          cx={point.x * width}
          cy={point.y * height}
          r="4"
          fill="#f97316"
          opacity="0.6"
        />
      ))}
    </svg>
  )
}
