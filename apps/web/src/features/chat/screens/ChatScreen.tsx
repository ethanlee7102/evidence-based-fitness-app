export function ChatScreen() {
  return (
    <div className="max-w-4xl mx-auto">
      <h1 className="text-3xl font-bold mb-2">Chat</h1>
      <p className="text-gray-400 mb-8">Your AI fitness assistant.</p>

      <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-8 text-center">
        <div className="text-5xl mb-4">💬</div>
        <h2 className="text-xl font-semibold mb-2">AI Assistant</h2>
        <p className="text-gray-400 mb-6">
          Ask questions about your training, get workout suggestions, or discuss your fitness goals.
        </p>
        <div className="max-w-md mx-auto">
          <input
            type="text"
            placeholder="Ask me anything about fitness..."
            className="w-full px-4 py-3 bg-gray-900 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-flame-500"
            disabled
          />
        </div>
        <p className="text-gray-500 text-sm mt-4">Coming soon</p>
      </div>
    </div>
  )
}
