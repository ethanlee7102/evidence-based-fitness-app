import { supabase } from '../../../lib/supabase'
import { apiRequest } from '../../../lib/api'
import type { ExerciseType } from '../types'
import type { AnalysisResult } from '../../analysis/types'

export interface UploadResult {
  storagePath: string
  publicUrl: string
}

export type { AnalysisResult }

export const uploadService = {
  async uploadVideo(file: File, userId: string): Promise<UploadResult> {
    const fileName = `${userId}/${Date.now()}-${file.name}`

    const { error } = await supabase.storage
      .from('videos')
      .upload(fileName, file, {
        cacheControl: '3600',
        upsert: false,
      })

    if (error) throw error

    const { data: { publicUrl } } = supabase.storage
      .from('videos')
      .getPublicUrl(fileName)

    return {
      storagePath: fileName,
      publicUrl,
    }
  },

  async analyzeVideo(
    videoUrl: string,
    exerciseType: ExerciseType,
    token: string
  ): Promise<AnalysisResult> {
    return apiRequest<AnalysisResult>('/analysis/analyze', {
      method: 'POST',
      token,
      body: JSON.stringify({
        video_url: videoUrl,
        exercise_type: exerciseType,
      }),
    })
  },
}
