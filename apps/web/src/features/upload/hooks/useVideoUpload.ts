import { useState, useCallback, useEffect, useRef } from 'react'
import { uploadService } from '../services'
import { useAuth } from '../../auth/hooks'
import type { ExerciseType, CameraSide, UploadState } from '../types'

export function useVideoUpload() {
  const { session } = useAuth()
  const [state, setState] = useState<UploadState>({
    file: null,
    preview: null,
    exerciseType: 'deadlift',
    cameraSide: 'left',
    uploading: false,
    analyzing: false,
    progress: 0,
    error: null,
  })

  // Track preview URL for cleanup on unmount
  const previewRef = useRef<string | null>(null)
  previewRef.current = state.preview

  useEffect(() => {
    return () => {
      if (previewRef.current) {
        URL.revokeObjectURL(previewRef.current)
      }
    }
  }, [])

  const setFile = useCallback((file: File | null) => {
    if (state.preview) {
      URL.revokeObjectURL(state.preview)
    }

    setState((prev) => ({
      ...prev,
      file,
      preview: file ? URL.createObjectURL(file) : null,
      error: null,
    }))
  }, [state.preview])

  const setExerciseType = useCallback((exerciseType: ExerciseType) => {
    setState((prev) => ({ ...prev, exerciseType }))
  }, [])

  const setCameraSide = useCallback((cameraSide: CameraSide) => {
    setState((prev) => ({ ...prev, cameraSide }))
  }, [])

  const reset = useCallback(() => {
    if (state.preview) {
      URL.revokeObjectURL(state.preview)
    }
    setState({
      file: null,
      preview: null,
      exerciseType: 'deadlift',
      cameraSide: 'left',
      uploading: false,
      analyzing: false,
      progress: 0,
      error: null,
    })
  }, [state.preview])

  const upload = useCallback(async (): Promise<string | null> => {
    if (!state.file || !session) {
      setState((prev) => ({ ...prev, error: 'No file selected or not authenticated' }))
      return null
    }

    setState((prev) => ({ ...prev, uploading: true, error: null, progress: 0 }))

    try {
      const { publicUrl } = await uploadService.uploadVideo(state.file, session.user.id)
      setState((prev) => ({ ...prev, progress: 50, uploading: false, analyzing: true }))

      const result = await uploadService.analyzeVideo(
        publicUrl,
        state.exerciseType,
        state.cameraSide,
        session.access_token
      )

      setState((prev) => ({ ...prev, progress: 100, analyzing: false }))
      return result.id
    } catch (err) {
      setState((prev) => ({
        ...prev,
        uploading: false,
        analyzing: false,
        error: err instanceof Error ? err.message : 'Upload failed',
      }))
      return null
    }
  }, [state.file, state.exerciseType, state.cameraSide, session])

  return {
    ...state,
    setFile,
    setExerciseType,
    setCameraSide,
    upload,
    reset,
  }
}
