import { useState, useEffect } from 'react'
import { analysisService } from '../services'
import { useAuth } from '../../auth/hooks'
import type { AnalysisResult } from '../types'

export function useAnalysis(id: string) {
  const { session } = useAuth()
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!id || !session) return

    setLoading(true)
    setError(null)

    analysisService
      .getAnalysis(id, session.access_token)
      .then(setAnalysis)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [id, session])

  return { analysis, loading, error }
}
