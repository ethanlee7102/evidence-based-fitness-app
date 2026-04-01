import { useState, useEffect, useRef } from 'react'
import { useAuth } from '../../auth/hooks/useAuth'
import { searchExercises, getRecentExercises } from '../services/workoutService'
import type { Exercise } from '../types'

export function useExerciseSearch() {
  const { session: authSession } = useAuth()
  const token = authSession?.access_token

  const [query, setQuery] = useState('')
  const [equipment, setEquipment] = useState<string>('')
  const [muscleCategory, setMuscleCategory] = useState<string>('')
  const [results, setResults] = useState<Exercise[]>([])
  const [recentExercises, setRecentExercises] = useState<Exercise[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const debounceRef = useRef<ReturnType<typeof setTimeout>>()

  const hasActiveFilters = !!(query || equipment || muscleCategory)

  // Fetch recent exercises on mount
  useEffect(() => {
    if (!token) return
    getRecentExercises(token, 10)
      .then(setRecentExercises)
      .catch(() => {})
  }, [token])

  // Search with debounce
  useEffect(() => {
    if (!token) return

    if (debounceRef.current) clearTimeout(debounceRef.current)

    debounceRef.current = setTimeout(async () => {
      setIsLoading(true)
      try {
        const data = await searchExercises(token, {
          q: query || undefined,
          equipment: equipment || undefined,
          muscle_category: muscleCategory || undefined,
        })
        // Sort: names starting with query first, then alphabetical
        if (query) {
          const q = query.toLowerCase()
          data.sort((a, b) => {
            const aStarts = a.name.toLowerCase().startsWith(q)
            const bStarts = b.name.toLowerCase().startsWith(q)
            if (aStarts && !bStarts) return -1
            if (!aStarts && bStarts) return 1
            return a.name.localeCompare(b.name)
          })
        }
        setResults(data)
      } catch (e) {
        console.error('Search failed:', e)
      } finally {
        setIsLoading(false)
      }
    }, 300)

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
  }, [token, query, equipment, muscleCategory])

  return {
    query,
    setQuery,
    equipment,
    setEquipment,
    muscleCategory,
    setMuscleCategory,
    results,
    recentExercises,
    isLoading,
    hasActiveFilters,
  }
}
