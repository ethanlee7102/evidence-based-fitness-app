import { Link } from 'react-router-dom'

export function HistoryScreen() {
  return (
    <div className="max-w-3xl mx-auto px-4 py-12">
      <h1 className="text-3xl font-bold mb-8">Analysis History</h1>

      <div className="text-center py-16 bg-gray-800/50 rounded-xl border border-gray-700">
        <div className="text-5xl mb-4">📊</div>
        <p className="text-gray-400 mb-6">
          Your analysis history will appear here.
        </p>
        <Link
          to="/upload"
          className="inline-flex px-6 py-3 bg-flame-600 hover:bg-flame-500 rounded-lg font-medium transition-colors"
        >
          Analyze Your First Video
        </Link>
      </div>
    </div>
  )
}
