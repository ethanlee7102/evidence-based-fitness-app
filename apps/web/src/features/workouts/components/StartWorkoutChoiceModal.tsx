import { Dumbbell, ClipboardList } from 'lucide-react'
import type { RoutineSummary } from '../types'

interface StartWorkoutChoiceModalProps {
  routines: RoutineSummary[]
  isStarting: boolean
  onStartEmpty: () => void
  onStartFromRoutine: (routineId: string) => void
  onClose: () => void
}

export function StartWorkoutChoiceModal({
  routines,
  isStarting,
  onStartEmpty,
  onStartFromRoutine,
  onClose,
}: StartWorkoutChoiceModalProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />

      {/* Modal */}
      <div className="relative z-10 bg-gray-900 border border-gray-700 rounded-2xl w-full max-w-sm mx-4 overflow-hidden">
        <div className="p-4 border-b border-gray-700">
          <h2 className="text-lg font-semibold text-center">Start Workout</h2>
        </div>

        <div className="p-4 space-y-3">
          {/* Empty workout option */}
          <button
            type="button"
            onClick={onStartEmpty}
            disabled={isStarting}
            className="w-full flex items-center gap-3 p-4 bg-gray-800/50 border border-gray-700 rounded-xl hover:bg-gray-800 hover:border-gray-600 transition-colors disabled:opacity-50"
          >
            <div className="w-10 h-10 bg-gray-700 rounded-lg flex items-center justify-center">
              <Dumbbell className="w-5 h-5 text-gray-400" />
            </div>
            <div className="text-left">
              <p className="font-medium">Empty Workout</p>
              <p className="text-xs text-gray-500">Start from scratch</p>
            </div>
          </button>

          {/* Divider */}
          <div className="flex items-center gap-3 text-xs text-gray-500">
            <div className="flex-1 border-t border-gray-700" />
            <span>or choose a routine</span>
            <div className="flex-1 border-t border-gray-700" />
          </div>

          {/* Routine list */}
          <div className="space-y-2 max-h-60 overflow-y-auto">
            {routines.map((r) => (
              <button
                key={r.id}
                type="button"
                onClick={() => onStartFromRoutine(r.id)}
                disabled={isStarting}
                className="w-full flex items-center gap-3 p-3 bg-gray-800/30 border border-gray-700/50 rounded-xl hover:bg-gray-800/50 hover:border-gray-600 transition-colors disabled:opacity-50"
              >
                <div className="w-10 h-10 bg-flame-500/10 rounded-lg flex items-center justify-center">
                  <ClipboardList className="w-5 h-5 text-flame-400" />
                </div>
                <div className="text-left flex-1 min-w-0">
                  <p className="font-medium text-sm truncate">{r.name}</p>
                  <p className="text-xs text-gray-500">
                    {r.exercise_count} exercises &middot; {r.total_sets} sets
                  </p>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Cancel */}
        <div className="p-4 pt-0">
          <button
            type="button"
            onClick={onClose}
            className="w-full text-sm text-gray-400 hover:text-gray-300 py-2"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  )
}
