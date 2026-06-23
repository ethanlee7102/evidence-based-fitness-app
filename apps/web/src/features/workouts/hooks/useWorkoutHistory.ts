import { useState, useCallback, useEffect, useMemo } from 'react'
import { useAuth } from '../../auth/hooks/useAuth'
import { listWorkouts, deleteWorkout as deleteWorkoutApi } from '../services/workoutService'
import type { WorkoutSummary, WorkoutFilters } from '../types'

const PAGE_SIZE = 20

const DEFAULT_FILTERS: WorkoutFilters = {
  datePreset: 'all',
  dateFrom: null,
  dateTo: null,
  minRating: null,
  exerciseId: null,
  exerciseName: null,
}

function computeDateRange(filters: WorkoutFilters): {
  date_from?: string
  date_to?: string
} {
  if (filters.datePreset === 'week' || filters.datePreset === 'month' || filters.datePreset === '3months') {
    const now = new Date()
    let from: Date
    if (filters.datePreset === 'week') {
      from = new Date(now)
      from.setDate(now.getDate() - 7)
    } else if (filters.datePreset === 'month') {
      from = new Date(now)
      from.setMonth(now.getMonth() - 1)
    } else {
      from = new Date(now)
      from.setMonth(now.getMonth() - 3)
    }
    return { date_from: from.toISOString().split('T')[0] }
  }

  // 'all' preset or custom range — check for explicit date bounds
  const result: { date_from?: string; date_to?: string } = {}
  if (filters.dateFrom) result.date_from = filters.dateFrom
  if (filters.dateTo) result.date_to = filters.dateTo
  return result
}

export function useWorkoutHistory() {
  const { session: authSession } = useAuth()
  const token = authSession?.access_token

  const [workouts, setWorkouts] = useState<WorkoutSummary[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isLoadingMore, setIsLoadingMore] = useState(false)
  const [hasMore, setHasMore] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filters, setFilters] = useState<WorkoutFilters>(DEFAULT_FILTERS)

  const activeFilterCount = useMemo(() => {
    let count = 0
    if (filters.datePreset !== 'all' || filters.dateFrom || filters.dateTo) count++
    if (filters.minRating) count++
    if (filters.exerciseId) count++
    return count
  }, [filters])

  const buildParams = useCallback(
    (offset: number) => {
      const dateRange = computeDateRange(filters)
      return {
        limit: PAGE_SIZE,
        offset,
        ...dateRange,
        ...(filters.minRating ? { min_rating: filters.minRating } : {}),
        ...(filters.exerciseId ? { exercise_id: filters.exerciseId } : {}),
      }
    },
    [filters],
  )

  const loadWorkouts = useCallback(async () => {
    if (!token) return
    try {
      setIsLoading(true)
      setError(null)
      const history = await listWorkouts(token, buildParams(0))
      setWorkouts(history)
      setHasMore(history.length >= PAGE_SIZE)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load workouts')
    } finally {
      setIsLoading(false)
    }
  }, [token, buildParams])

  const loadMore = useCallback(async () => {
    if (!token || isLoadingMore || !hasMore) return
    try {
      setIsLoadingMore(true)
      const more = await listWorkouts(token, buildParams(workouts.length))
      setWorkouts((prev) => [...prev, ...more])
      setHasMore(more.length >= PAGE_SIZE)
    } catch (e) {
      console.error('Failed to load more workouts:', e)
    } finally {
      setIsLoadingMore(false)
    }
  }, [token, isLoadingMore, hasMore, workouts.length, buildParams])

  const deleteWorkout = useCallback(
    async (workoutId: string) => {
      if (!token) return
      setWorkouts((prev) => prev.filter((w) => w.id !== workoutId))
      try {
        await deleteWorkoutApi(token, workoutId)
      } catch (e) {
        console.error('Failed to delete workout:', e)
        loadWorkouts()
      }
    },
    [token, loadWorkouts],
  )

  // Re-fetch when token or filters change
  useEffect(() => {
    loadWorkouts()
  }, [loadWorkouts])

  return {
    workouts,
    isLoading,
    isLoadingMore,
    hasMore,
    error,
    filters,
    setFilters,
    activeFilterCount,
    loadWorkouts,
    loadMore,
    deleteWorkout,
  }
}
