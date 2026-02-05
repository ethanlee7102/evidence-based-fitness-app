import { apiRequest } from '../../../lib/api'
import type { AnalysisResult } from '../types'

export const analysisService = {
  async getAnalysis(id: string, token: string): Promise<AnalysisResult> {
    return apiRequest<AnalysisResult>(`/analysis/${id}`, { token })
  },
}
