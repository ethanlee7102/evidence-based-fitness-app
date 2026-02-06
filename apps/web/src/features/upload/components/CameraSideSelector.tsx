import type { CameraSide } from '../types'

interface CameraSideSelectorProps {
  value: CameraSide
  onChange: (side: CameraSide) => void
}

const sides: { side: CameraSide; label: string }[] = [
  { side: 'left', label: 'Left side' },
  { side: 'right', label: 'Right side' },
]

export function CameraSideSelector({ value, onChange }: CameraSideSelectorProps) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-300 mb-2">
        Which side is facing the camera?
      </label>
      <div className="flex gap-3">
        {sides.map(({ side, label }) => (
          <button
            key={side}
            type="button"
            onClick={() => onChange(side)}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              value === side
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
