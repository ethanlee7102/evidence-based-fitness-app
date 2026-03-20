import { useState, useCallback, useEffect } from 'react'
import { useAuth } from '../../auth/hooks/useAuth'
import { listWorkouts, deleteWorkout as deleteWorkoutApi } from '../services/workoutService'
import type { WorkoutSummary } from '../types'

const PAGE_SIZE = 20

export function useWorkoutHistory() {
  const { session: authSession } = useAuth()
  const token = authSession?.access_token

  const [workouts, setWorkouts] = useState<WorkoutSummary[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isLoadingMore, setIsLoadingMore] = useState(false)
  const [hasMore, setHasMore] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadWorkouts = useCallback(async () => {
    if (!token) return
    try {
      setIsLoading(true)
      setError(null)
      const history = await listWorkouts(token, { limit: PAGE_SIZE, offset: 0 })
      setWorkouts(history)
      setHasMore(history.length >= PAGE_SIZE)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load workouts')
    } finally {
      setIsLoading(false)
    }
  }, [token])

  const loadMore = useCallback(async () => {
    if (!token || isLoadingMore || !hasMore) return
    try {
      setIsLoadingMore(true)
      const more = await listWorkouts(token, {
        limit: PAGE_SIZE,
        offset: workouts.length,
      })
      setWorkouts((prev) => [...prev, ...more])
      setHasMore(more.length >= PAGE_SIZE)
    } catch (e) {
      console.error('Failed to load more workouts:', e)
    } finally {
      setIsLoadingMore(false)
    }
  }, [token, isLoadingMore, hasMore, workouts.length])

  const deleteWorkout = useCallback(
    async (workoutId: string) => {
      if (!token) return
      // Optimistic removal
      setWorkouts((prev) => prev.filter((w) => w.id !== workoutId))
      try {
        await deleteWorkoutApi(token, workoutId)
      } catch (e) {
        console.error('Failed to delete workout:', e)
        loadWorkouts() // Re-fetch on error
      }
    },
    [token, loadWorkouts],
  )

  useEffect(() => {
    loadWorkouts()
  }, [loadWorkouts])

  return {
    workouts,
    isLoading,
    isLoadingMore,
    hasMore,
    error,
    loadWorkouts,
    loadMore,
    deleteWorkout,
  }
}
