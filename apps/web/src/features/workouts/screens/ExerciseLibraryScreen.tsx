import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { useExerciseSearch } from '../hooks/useExerciseSearch'
import { ExerciseDetailModal } from '../components/ExerciseDetailModal'
import { MUSCLE_CATEGORIES, EQUIPMENT_OPTIONS } from '../types'

export function ExerciseLibraryScreen() {
  const {
    query, setQuery,
    equipment, setEquipment,
    muscleCategory, setMuscleCategory,
    results,
    recentExercises,
    isLoading,
    hasActiveFilters,
  } = useExerciseSearch()

  const [selectedExerciseId, setSelectedExerciseId] = useState<string | null>(null)

  const displayList = results

  return (
    <div className="max-w-4xl mx-auto">
      <Link
        to="/dashboard/workouts"
        className="inline-flex items-center text-sm text-gray-400 hover:text-gray-200 mb-4"
      >
        <ChevronLeft className="w-4 h-4 mr-1" />
        Back to Workouts
      </Link>

      <h1 className="text-3xl font-bold mb-6">Exercise Library</h1>

      {/* Search + Filters */}
      <div className="space-y-3 mb-6">
        <input
          type="text"
          placeholder="Search exercises..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-sm
            placeholder-gray-500 focus:outline-none focus:border-flame-500"
        />

        <div className="flex gap-2">
          <select
            value={muscleCategory}
            onChange={(e) => setMuscleCategory(e.target.value)}
            className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-gray-300"
          >
            <option value="">All Muscles</option>
            {MUSCLE_CATEGORIES.map((cat) => (
              <option key={cat} value={cat}>
                {cat}
              </option>
            ))}
          </select>

          <select
            value={equipment}
            onChange={(e) => setEquipment(e.target.value)}
            className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-gray-300"
          >
            <option value="">All Equipment</option>
            {EQUIPMENT_OPTIONS.map((eq) => (
              <option key={eq} value={eq}>
                {eq.charAt(0).toUpperCase() + eq.slice(1)}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Recent section */}
      {!hasActiveFilters && recentExercises.length > 0 && !isLoading && (
        <div className="mb-4">
          <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">Recent</h3>
          <div className="space-y-1">
            {recentExercises.slice(0, 5).map((exercise) => {
              const primaryMuscles = exercise.muscles
                ?.filter(
                  (m) =>
                    m.activation_level === 'maximum' ||
                    m.activation_level === 'high',
                )
                .map((m) => m.muscle_group_name)
                .slice(0, 3)

              return (
                <button
                  key={`recent-${exercise.id}`}
                  type="button"
                  onClick={() => setSelectedExerciseId(exercise.id)}
                  className="w-full text-left p-3 rounded-lg hover:bg-gray-800 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium text-sm">{exercise.name}</p>
                      <div className="flex items-center gap-2 text-xs text-gray-500">
                        {exercise.equipment && (
                          <span className="capitalize">{exercise.equipment}</span>
                        )}
                        {primaryMuscles && primaryMuscles.length > 0 && (
                          <span>{primaryMuscles.join(', ')}</span>
                        )}
                      </div>
                    </div>
                    <ChevronRight className="w-5 h-5 text-gray-600" />
                  </div>
                </button>
              )
            })}
          </div>
          <div className="border-b border-gray-700 mt-3 mb-3" />
          <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">All Exercises</h3>
        </div>
      )}

      {/* Results */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-flame-500" />
        </div>
      ) : displayList.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-gray-500">No exercises found</p>
        </div>
      ) : (
        <div className="space-y-1">
          {displayList.map((exercise) => {
            const primaryMuscles = exercise.muscles
              ?.filter(
                (m) =>
                  m.activation_level === 'maximum' ||
                  m.activation_level === 'high',
              )
              .map((m) => m.muscle_group_name)
              .slice(0, 3)

            return (
              <button
                key={exercise.id}
                type="button"
                onClick={() => setSelectedExerciseId(exercise.id)}
                className="w-full text-left p-3 rounded-lg hover:bg-gray-800 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-sm">{exercise.name}</p>
                    <div className="flex items-center gap-2 text-xs text-gray-500">
                      {exercise.equipment && (
                        <span className="capitalize">{exercise.equipment}</span>
                      )}
                      {primaryMuscles && primaryMuscles.length > 0 && (
                        <span>{primaryMuscles.join(', ')}</span>
                      )}
                    </div>
                  </div>
                  <ChevronRight className="w-5 h-5 text-gray-600" />
                </div>
              </button>
            )
          })}
        </div>
      )}

      {/* Exercise detail modal */}
      {selectedExerciseId && (
        <ExerciseDetailModal
          exerciseId={selectedExerciseId}
          onClose={() => setSelectedExerciseId(null)}
        />
      )}
    </div>
  )
}
