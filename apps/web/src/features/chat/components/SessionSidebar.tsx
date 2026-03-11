import { ChevronLeft, Plus, Trash2 } from 'lucide-react'
import type { ChatSession } from '../types'

interface SessionSidebarProps {
  sessions: ChatSession[]
  activeSessionId: string | null
  isOpen: boolean
  onToggle: () => void
  onNewChat: () => void
  onSelectSession: (id: string) => void
  onDeleteSession: (id: string) => void
}

export function SessionSidebar({
  sessions,
  activeSessionId,
  isOpen,
  onToggle,
  onNewChat,
  onSelectSession,
  onDeleteSession,
}: SessionSidebarProps) {
  if (!isOpen) return null

  return (
    <div className="w-72 flex-shrink-0 bg-gray-900 border-r border-gray-800 flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800">
        <button
          onClick={onNewChat}
          className="flex items-center gap-2 text-sm text-gray-300 hover:text-white transition-colors"
        >
          <Plus className="w-4 h-4" />
          New Chat
        </button>
        <button
          onClick={onToggle}
          className="text-gray-400 hover:text-white transition-colors"
          title="Collapse sidebar"
        >
          <ChevronLeft className="w-4 h-4" />
        </button>
      </div>

      {/* Session list */}
      <div className="flex-1 overflow-y-auto py-2">
        {sessions.length === 0 ? (
          <p className="text-gray-500 text-sm text-center py-4">No conversations yet</p>
        ) : (
          sessions.map((session) => {
            const isActive = session.id === activeSessionId
            return (
              <div
                key={session.id}
                className={`group flex items-center gap-2 px-3 py-2 mx-2 rounded-lg cursor-pointer transition-colors ${
                  isActive
                    ? 'bg-flame-600/20 text-flame-400'
                    : 'text-gray-300 hover:bg-gray-800/50 hover:text-white'
                }`}
                onClick={() => onSelectSession(session.id)}
              >
                <span className="flex-1 text-sm truncate">
                  {session.title || 'New Chat'}
                </span>
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    onDeleteSession(session.id)
                  }}
                  className="opacity-0 group-hover:opacity-100 text-gray-500 hover:text-red-400 transition-all flex-shrink-0"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
