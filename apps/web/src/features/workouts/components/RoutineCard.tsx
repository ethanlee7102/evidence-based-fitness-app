import { useState } from 'react'
import { Play, Pencil, Copy, Trash2, MoreVertical } from 'lucide-react'
import type { RoutineSummary } from '../types'

interface RoutineCardProps {
  routine: RoutineSummary
  onStart: (id: string) => void
  onEdit: (id: string) => void
  onDuplicate: (id: string) => void
  onDelete: (id: string) => void
}

function formatRelativeTime(dateStr: string | null): string {
  if (!dateStr) return 'Never used'
  const diff = Date.now() - new Date(dateStr).getTime()
  const days = Math.floor(diff / 86400000)
  if (days === 0) return 'Today'
  if (days === 1) return 'Yesterday'
  if (days < 7) return `${days} days ago`
  if (days < 30) return `${Math.floor(days / 7)} weeks ago`
  return `${Math.floor(days / 30)} months ago`
}

export function RoutineCard({ routine, onStart, onEdit, onDuplicate, onDelete }: RoutineCardProps) {
  const [showMenu, setShowMenu] = useState(false)

  return (
    <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-4 hover:border-gray-600 transition-colors">
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-base truncate">{routine.name}</h3>
          <p className="text-sm text-gray-400 mt-0.5">
            {routine.exercise_count} exercises &middot; {routine.total_sets} sets
          </p>
        </div>

        <div className="flex items-center gap-1 ml-2">
          <button
            type="button"
            onClick={() => onStart(routine.id)}
            className="flex items-center gap-1.5 text-sm font-medium text-flame-400 hover:text-flame-300 px-3 py-1.5 rounded-lg hover:bg-flame-400/10 transition-colors"
          >
            <Play className="w-3.5 h-3.5" />
            Start
          </button>

          <div className="relative">
            <button
              type="button"
              onClick={() => setShowMenu(!showMenu)}
              className="text-gray-500 hover:text-gray-300 p-1.5 rounded-lg hover:bg-gray-700/50 transition-colors"
            >
              <MoreVertical className="w-4 h-4" />
            </button>

            {showMenu && (
              <>
                <div className="fixed inset-0 z-10" onClick={() => setShowMenu(false)} />
                <div className="absolute right-0 top-full mt-1 z-20 bg-gray-800 border border-gray-700 rounded-lg shadow-xl py-1 min-w-[140px]">
                  <button
                    type="button"
                    className="flex items-center gap-2 w-full px-3 py-2 text-sm text-gray-300 hover:bg-gray-700/50 transition-colors"
                    onClick={() => { onEdit(routine.id); setShowMenu(false) }}
                  >
                    <Pencil className="w-3.5 h-3.5" />
                    Edit
                  </button>
                  <button
                    type="button"
                    className="flex items-center gap-2 w-full px-3 py-2 text-sm text-gray-300 hover:bg-gray-700/50 transition-colors"
                    onClick={() => { onDuplicate(routine.id); setShowMenu(false) }}
                  >
                    <Copy className="w-3.5 h-3.5" />
                    Duplicate
                  </button>
                  <button
                    type="button"
                    className="flex items-center gap-2 w-full px-3 py-2 text-sm text-red-400 hover:bg-gray-700/50 transition-colors"
                    onClick={() => { onDelete(routine.id); setShowMenu(false) }}
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                    Delete
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      </div>

      <div className="flex items-center gap-3 text-xs text-gray-500">
        <span>{formatRelativeTime(routine.last_used_at)}</span>
        {routine.use_count > 0 && (
          <span>&middot; Used {routine.use_count} time{routine.use_count !== 1 ? 's' : ''}</span>
        )}
      </div>
    </div>
  )
}
