import type { ExerciseType } from '../types'

interface ExerciseSelectorProps {
  value: ExerciseType
  onChange: (type: ExerciseType) => void
}

const exercises: { type: ExerciseType; label: string }[] = [
  { type: 'deadlift', label: 'Deadlift' },
  { type: 'squat', label: 'Squat' },
  { type: 'bench', label: 'Bench Press' },
]

export function ExerciseSelector({ value, onChange }: ExerciseSelectorProps) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-300 mb-2">
        Exercise Type
      </label>
      <div className="flex gap-3">
        {exercises.map(({ type, label }) => (
          <button
            key={type}
            type="button"
            onClick={() => onChange(type)}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              value === type
                ? 'bg-flame-600 text-white'
                : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
            }`}
          >
            {label}
          </button>
        ))}
      </div>
    </div>
  )
}
