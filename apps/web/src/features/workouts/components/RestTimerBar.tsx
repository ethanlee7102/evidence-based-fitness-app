import { useState, useEffect, useRef } from 'react'

interface RestTimerBarProps {
  exerciseName: string
  durationSeconds: number
  onSkip: () => void
  onComplete: () => void
}

export function RestTimerBar({
  exerciseName,
  durationSeconds,
  onSkip,
  onComplete,
}: RestTimerBarProps) {
  const [remaining, setRemaining] = useState(durationSeconds)
  const onCompleteRef = useRef(onComplete)
  onCompleteRef.current = onComplete

  // Reset when a new timer starts (different exercise or duration)
  useEffect(() => {
    setRemaining(durationSeconds)
  }, [durationSeconds, exerciseName])

  useEffect(() => {
    const interval = setInterval(() => {
      setRemaining((prev) => {
        if (prev <= 1) {
          clearInterval(interval)
          setTimeout(() => onCompleteRef.current(), 0)
          return 0
        }
        return prev - 1
      })
    }, 1000)

    return () => clearInterval(interval)
  }, [durationSeconds, exerciseName])

  const mins = Math.floor(remaining / 60)
  const secs = remaining % 60
  const display = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`
  const isAlmostDone = remaining > 0 && remaining <= 3

  return (
    <div
      className={`fixed bottom-0 left-0 right-0 z-[55] bg-gray-800 border-t border-gray-700 px-4 py-3 flex items-center justify-between ${
        isAlmostDone ? 'animate-pulse' : ''
      }`}
    >
      <div className="min-w-0 flex-1">
        <p className="text-xs text-gray-400 truncate">Rest &mdash; {exerciseName}</p>
        <p className="text-2xl font-mono font-bold">{display}</p>
      </div>
      <button
        type="button"
        onClick={onSkip}
        className="px-4 py-2 text-sm font-medium text-gray-300 hover:text-white bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors"
      >
        Skip
      </button>
    </div>
  )
}
