import { useState, useEffect, useRef } from 'react'
import { formatDuration } from '../utils/unitConversion'

interface WorkoutTimerProps {
  startedAt: string
  /** Seconds already elapsed from previous sessions (for pause/resume). */
  initialElapsed?: number
  /** Ref updated every second with the current elapsed value. */
  elapsedRef?: React.MutableRefObject<number>
}

export function WorkoutTimer({ initialElapsed = 0, elapsedRef }: WorkoutTimerProps) {
  // "Virtual start" = now minus whatever time was already accumulated
  const virtualStart = useRef(Date.now() - initialElapsed * 1000)
  const [elapsed, setElapsed] = useState(initialElapsed)

  useEffect(() => {
    const update = () => {
      const secs = Math.floor((Date.now() - virtualStart.current) / 1000)
      setElapsed(secs)
      if (elapsedRef) elapsedRef.current = secs
    }
    update()
    const interval = setInterval(update, 1000)
    return () => clearInterval(interval)
  }, [elapsedRef])

  return (
    <span className="text-lg font-mono tabular-nums text-gray-300">
      {formatDuration(elapsed)}
    </span>
  )
}
