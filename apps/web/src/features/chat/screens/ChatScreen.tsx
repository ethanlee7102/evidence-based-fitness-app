import { useState } from 'react'
import { ChevronRight, X } from 'lucide-react'
import { useChat } from '../hooks/useChat'
import { ChatMessageList } from '../components/ChatMessageList'
import { ChatInput } from '../components/ChatInput'
import { SessionSidebar } from '../components/SessionSidebar'

export function ChatScreen() {
  const {
    sessions,
    activeSessionId,
    messages,
    streamingMessage,
    isLoading,
    isSending,
    error,
    lastFailedMessage,
    selectSession,
    startNewChat,
    sendMessage,
    deleteSession,
    retry,
    clearError,
  } = useChat()

  const [sidebarOpen, setSidebarOpen] = useState(() => window.innerWidth >= 768)

  return (
    <div className="flex h-screen -m-6">
      <SessionSidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        isOpen={sidebarOpen}
        onToggle={() => setSidebarOpen((prev) => !prev)}
        onNewChat={startNewChat}
        onSelectSession={selectSession}
        onDeleteSession={deleteSession}
      />

      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <div className="flex items-center gap-3 px-4 py-2 border-b border-gray-800">
          {!sidebarOpen && (
            <button
              onClick={() => setSidebarOpen(true)}
              className="text-gray-400 hover:text-white transition-colors"
              title="Expand sidebar"
            >
              <ChevronRight className="w-5 h-5" />
            </button>
          )}
          <h1 className="text-sm font-medium text-gray-300 truncate">
            {activeSessionId
              ? sessions.find((s) => s.id === activeSessionId)?.title || 'New Chat'
              : 'New Chat'}
          </h1>
        </div>

        {/* Error banner */}
        {error && (
          <div className="flex items-center gap-3 px-4 py-2 bg-red-500/10 border-b border-red-500/20">
            <p className="flex-1 text-sm text-red-400">{error}</p>
            <div className="flex items-center gap-2">
              {lastFailedMessage && (
                <button
                  onClick={retry}
                  className="text-xs text-red-300 hover:text-white bg-red-500/20 hover:bg-red-500/30 px-3 py-1 rounded-md transition-colors"
                >
                  Retry
                </button>
              )}
              <button onClick={clearError} className="text-red-400 hover:text-red-300">
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}

        {/* Loading overlay for session switch */}
        {isLoading ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="w-6 h-6 border-2 border-flame-500 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : (
          <ChatMessageList
            messages={messages}
            streamingMessage={streamingMessage}
            isSending={isSending}
            onSelectQuestion={sendMessage}
          />
        )}

        <ChatInput onSend={sendMessage} isSending={isSending} />
      </div>
    </div>
  )
}
