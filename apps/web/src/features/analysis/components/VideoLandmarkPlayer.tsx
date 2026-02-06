import { useRef, useEffect, useState, useCallback } from 'react'
import type { FrameLandmarks, PhaseBoundary } from '../types'

interface VideoLandmarkPlayerProps {
  videoUrl: string
  landmarks: FrameLandmarks[]
  fps: number
  phaseBoundaries?: PhaseBoundary[]
}

// Skeleton connections between landmarks
const SKELETON_CONNECTIONS: [number, number][] = [
  // Torso
  [11, 12], // shoulders
  [11, 23], // left shoulder to left hip
  [12, 24], // right shoulder to right hip
  [23, 24], // hips
  // Left arm
  [11, 13], // shoulder to elbow
  [13, 15], // elbow to wrist
  // Right arm
  [12, 14],
  [14, 16],
  // Left leg
  [23, 25], // hip to knee
  [25, 27], // knee to ankle
  // Right leg
  [24, 26],
  [26, 28],
]

// Colors for different body parts
const LANDMARK_COLORS: Record<number, string> = {
  11: '#3B82F6', // left shoulder - blue
  12: '#3B82F6', // right shoulder - blue
  13: '#06B6D4', // left elbow - cyan
  14: '#06B6D4', // right elbow - cyan
  15: '#22C55E', // left wrist - green (bar tracking)
  16: '#22C55E', // right wrist - green
  23: '#F97316', // left hip - orange
  24: '#F97316', // right hip - orange
  25: '#EAB308', // left knee - yellow
  26: '#EAB308', // right knee - yellow
  27: '#EF4444', // left ankle - red
  28: '#EF4444', // right ankle - red
}

// Phase boundary colors
const PHASE_COLORS = ['#22C55E', '#EAB308', '#F97316'] // green, yellow, orange

export function VideoLandmarkPlayer({ videoUrl, landmarks, fps, phaseBoundaries }: VideoLandmarkPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [showPhaseBoundaries, setShowPhaseBoundaries] = useState(true)

  // Debug: log phase boundaries
  console.log('Phase boundaries:', phaseBoundaries)

  // Find the closest frame landmarks for the current time
  const getCurrentLandmarks = useCallback(
    (time: number): FrameLandmarks | null => {
      if (!landmarks.length) return null

      const frameNumber = Math.floor(time * fps)

      // Find the closest frame (landmarks are sampled, so we need to find nearest)
      let closest = landmarks[0]
      let minDiff = Math.abs(closest.frame - frameNumber)

      for (const lm of landmarks) {
        const diff = Math.abs(lm.frame - frameNumber)
        if (diff < minDiff) {
          minDiff = diff
          closest = lm
        }
      }

      return closest
    },
    [landmarks, fps]
  )

  // Draw landmarks on canvas
  const drawLandmarks = useCallback(
    (frameLandmarks: FrameLandmarks | null) => {
      const canvas = canvasRef.current
      const video = videoRef.current
      if (!canvas || !video) return

      const ctx = canvas.getContext('2d')
      if (!ctx) return

      // Match canvas size to video display size
      const rect = video.getBoundingClientRect()
      canvas.width = rect.width
      canvas.height = rect.height

      // Clear canvas
      ctx.clearRect(0, 0, canvas.width, canvas.height)

      // Draw phase boundary lines
      if (showPhaseBoundaries && phaseBoundaries && phaseBoundaries.length > 0) {
        for (let i = 0; i < phaseBoundaries.length; i++) {
          const boundary = phaseBoundaries[i]
          const y = boundary.y * canvas.height
          const color = PHASE_COLORS[i] || '#FFFFFF'

          // Draw dashed line
          ctx.beginPath()
          ctx.setLineDash([8, 4])
          ctx.strokeStyle = color
          ctx.lineWidth = 2
          ctx.moveTo(0, y)
          ctx.lineTo(canvas.width, y)
          ctx.stroke()
          ctx.setLineDash([])

          // Draw phase label on left side
          ctx.font = 'bold 12px sans-serif'
          ctx.fillStyle = color
          ctx.textAlign = 'left'
          ctx.fillText(`P${boundary.between_phases[0]}/P${boundary.between_phases[1]}`, 8, y - 4)
        }
      }

      if (!frameLandmarks) return

      const { points } = frameLandmarks

      // Draw skeleton connections
      ctx.lineWidth = 2
      ctx.lineCap = 'round'

      for (const [start, end] of SKELETON_CONNECTIONS) {
        const p1 = points[start]
        const p2 = points[end]

        if (p1 && p2 && p1.visibility > 0.5 && p2.visibility > 0.5) {
          ctx.beginPath()
          ctx.strokeStyle = 'rgba(255, 255, 255, 0.6)'
          ctx.moveTo(p1.x * canvas.width, p1.y * canvas.height)
          ctx.lineTo(p2.x * canvas.width, p2.y * canvas.height)
          ctx.stroke()
        }
      }

      // Draw landmark points
      for (const [indexStr, point] of Object.entries(points)) {
        const index = parseInt(indexStr)
        if (point.visibility < 0.5) continue

        const x = point.x * canvas.width
        const y = point.y * canvas.height
        const color = LANDMARK_COLORS[index] || '#FFFFFF'

        // Draw outer circle
        ctx.beginPath()
        ctx.arc(x, y, 6, 0, Math.PI * 2)
        ctx.fillStyle = color
        ctx.fill()

        // Draw inner circle
        ctx.beginPath()
        ctx.arc(x, y, 3, 0, Math.PI * 2)
        ctx.fillStyle = '#FFFFFF'
        ctx.fill()
      }
    },
    [showPhaseBoundaries, phaseBoundaries]
  )

  // Update canvas on time change or when phase boundaries toggle
  useEffect(() => {
    const frameLandmarks = getCurrentLandmarks(currentTime)
    drawLandmarks(frameLandmarks)
  }, [currentTime, getCurrentLandmarks, drawLandmarks, showPhaseBoundaries])

  // Handle video time updates
  const handleTimeUpdate = () => {
    if (videoRef.current) {
      setCurrentTime(videoRef.current.currentTime)
    }
  }

  const handleLoadedMetadata = () => {
    if (videoRef.current) {
      setDuration(videoRef.current.duration)
    }
  }

  const handlePlayPause = () => {
    if (videoRef.current) {
      if (isPlaying) {
        videoRef.current.pause()
      } else {
        videoRef.current.play()
      }
      setIsPlaying(!isPlaying)
    }
  }

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const time = parseFloat(e.target.value)
    if (videoRef.current) {
      videoRef.current.currentTime = time
      setCurrentTime(time)
    }
  }

  const handleStepFrame = (direction: number) => {
    if (videoRef.current && fps > 0) {
      const frameTime = 1 / fps
      const newTime = Math.max(0, Math.min(duration, currentTime + direction * frameTime))
      videoRef.current.currentTime = newTime
      setCurrentTime(newTime)
    }
  }

  const formatTime = (time: number) => {
    const mins = Math.floor(time / 60)
    const secs = Math.floor(time % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  return (
    <div className="bg-gray-800/50 border border-gray-700 rounded-xl overflow-hidden">
      <div className="relative">
        <video
          ref={videoRef}
          src={videoUrl}
          className="w-full"
          onTimeUpdate={handleTimeUpdate}
          onLoadedMetadata={handleLoadedMetadata}
          onPlay={() => setIsPlaying(true)}
          onPause={() => setIsPlaying(false)}
          playsInline
        />
        <canvas
          ref={canvasRef}
          className="absolute top-0 left-0 w-full h-full pointer-events-none"
        />
      </div>

      {/* Controls */}
      <div className="p-4 space-y-3">
        {/* Progress bar */}
        <input
          type="range"
          min={0}
          max={duration || 1}
          step={0.01}
          value={currentTime}
          onChange={handleSeek}
          className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-flame-500"
        />

        <div className="flex items-center justify-between">
          {/* Left: Time */}
          <span className="text-sm text-gray-400 font-mono">
            {formatTime(currentTime)} / {formatTime(duration)}
          </span>

          {/* Center: Controls */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => handleStepFrame(-1)}
              className="p-2 hover:bg-gray-700 rounded-lg transition-colors"
              title="Previous frame"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12.066 11.2a1 1 0 000 1.6l5.334 4A1 1 0 0019 16V8a1 1 0 00-1.6-.8l-5.333 4zM4.066 11.2a1 1 0 000 1.6l5.334 4A1 1 0 0011 16V8a1 1 0 00-1.6-.8l-5.334 4z" />
              </svg>
            </button>

            <button
              onClick={handlePlayPause}
              className="p-3 bg-flame-600 hover:bg-flame-500 rounded-full transition-colors"
            >
              {isPlaying ? (
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 9v6m4-6v6" />
                </svg>
              ) : (
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                </svg>
              )}
            </button>

            <button
              onClick={() => handleStepFrame(1)}
              className="p-2 hover:bg-gray-700 rounded-lg transition-colors"
              title="Next frame"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11.933 12.8a1 1 0 000-1.6L6.6 7.2A1 1 0 005 8v8a1 1 0 001.6.8l5.333-4zM19.933 12.8a1 1 0 000-1.6l-5.333-4A1 1 0 0013 8v8a1 1 0 001.6.8l5.333-4z" />
              </svg>
            </button>
          </div>

          {/* Right: Frame info + Phase toggle */}
          <div className="flex items-center gap-3">
            {phaseBoundaries && phaseBoundaries.length > 0 && (
              <button
                onClick={() => setShowPhaseBoundaries(!showPhaseBoundaries)}
                className={`px-2 py-1 text-xs rounded transition-colors ${
                  showPhaseBoundaries
                    ? 'bg-flame-600 text-white'
                    : 'bg-gray-700 text-gray-400'
                }`}
              >
                Phases
              </button>
            )}
            <span className="text-sm text-gray-400">
              Frame {Math.floor(currentTime * fps)}
            </span>
          </div>
        </div>

        {/* Legend */}
        <div className="flex flex-wrap gap-3 pt-2 border-t border-gray-700 text-xs">
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 rounded-full bg-blue-500" /> Shoulders
          </span>
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 rounded-full bg-green-500" /> Wrists (Bar)
          </span>
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 rounded-full bg-orange-500" /> Hips
          </span>
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 rounded-full bg-yellow-500" /> Knees
          </span>
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 rounded-full bg-red-500" /> Ankles
          </span>
          {showPhaseBoundaries && phaseBoundaries && phaseBoundaries.length > 0 && (
            <span className="flex items-center gap-1">
              <span className="w-4 h-0.5 bg-green-500" style={{ borderTop: '2px dashed' }} /> Phase Lines
            </span>
          )}
        </div>
      </div>
    </div>
  )
}
