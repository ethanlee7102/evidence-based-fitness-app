import { useState, useCallback, useEffect } from 'react'
import { useAuth } from '../../auth/hooks/useAuth'
import {
  listRoutines,
  deleteRoutine as deleteRoutineApi,
  duplicateRoutine as duplicateRoutineApi,
} from '../services/workoutService'
import type { RoutineSummary } from '../types'

export function useRoutines() {
  const { session: authSession } = useAuth()
  const token = authSession?.access_token

  const [routines, setRoutines] = useState<RoutineSummary[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadRoutines = useCallback(async () => {
    if (!token) return
    try {
      setIsLoading(true)
      setError(null)
      const data = await listRoutines(token)
      setRoutines(data)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load routines')
    } finally {
      setIsLoading(false)
    }
  }, [token])

  const deleteRoutine = useCallback(
    async (routineId: string) => {
      if (!token) return
      setRoutines((prev) => prev.filter((r) => r.id !== routineId))
      try {
        await deleteRoutineApi(token, routineId)
      } catch (e) {
        console.error('Failed to delete routine:', e)
        loadRoutines()
      }
    },
    [token, loadRoutines],
  )

  const duplicateRoutine = useCallback(
    async (routineId: string) => {
      if (!token) return
      try {
        await duplicateRoutineApi(token, routineId)
        loadRoutines()
      } catch (e) {
        console.error('Failed to duplicate routine:', e)
      }
    },
    [token, loadRoutines],
  )

  useEffect(() => {
    loadRoutines()
  }, [loadRoutines])

  return {
    routines,
    isLoading,
    error,
    loadRoutines,
    deleteRoutine,
    duplicateRoutine,
  }
}
