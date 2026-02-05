import { useParams, Link } from 'react-router-dom'
import { useAnalysis } from '../hooks'
import { ResultsDisplay } from '../components'
import { Loading } from '../../../shared/components'

export function AnalysisResultScreen() {
  const { id } = useParams<{ id: string }>()
  const { analysis, loading, error } = useAnalysis(id || '')

  if (loading) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <Loading text="Loading analysis..." />
      </div>
    )
  }

  if (error || !analysis) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-16 text-center">
        <div className="text-6xl mb-4">❌</div>
        <h1 className="text-2xl font-bold mb-4">Analysis Not Found</h1>
        <p className="text-gray-400 mb-6">{error || 'Unable to load analysis results'}</p>
        <Link
          to="/upload"
          className="inline-flex px-6 py-3 bg-flame-600 hover:bg-flame-500 rounded-lg font-medium transition-colors"
        >
          Upload New Video
        </Link>
      </div>
    )
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-12">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-3xl font-bold">Analysis Results</h1>
        <Link
          to="/upload"
          className="px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm font-medium transition-colors"
        >
          Analyze Another
        </Link>
      </div>

      <ResultsDisplay analysis={analysis} />
    </div>
  )
}
