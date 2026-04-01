import { useState } from 'react'
import { SlidersHorizontal, Star, X } from 'lucide-react'
import type { WorkoutFilters, DatePreset, Exercise } from '../types'
import { ExerciseSearchModal } from './ExerciseSearchModal'

interface WorkoutFilterBarProps {
  filters: WorkoutFilters
  onFiltersChange: (filters: WorkoutFilters) => void
  activeFilterCount: number
}

const DATE_PRESETS: { value: DatePreset | 'custom'; label: string }[] = [
  { value: 'week', label: 'This Week' },
  { value: 'month', label: 'This Month' },
  { value: '3months', label: 'Last 3 Mo' },
  { value: 'all', label: 'All Time' },
]

export function WorkoutFilterBar({
  filters,
  onFiltersChange,
  activeFilterCount,
}: WorkoutFilterBarProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [showExerciseSearch, setShowExerciseSearch] = useState(false)
  const [showCustomRange, setShowCustomRange] = useState(
    filters.datePreset === 'all' && (filters.dateFrom !== null || filters.dateTo !== null),
  )

  const handlePresetClick = (preset: DatePreset) => {
    setShowCustomRange(false)
    onFiltersChange({
      ...filters,
      datePreset: preset,
      dateFrom: null,
      dateTo: null,
    })
  }

  const handleCustomClick = () => {
    setShowCustomRange(true)
    onFiltersChange({
      ...filters,
      datePreset: 'all',
      dateFrom: filters.dateFrom,
      dateTo: filters.dateTo,
    })
  }

  const handleCustomDate = (field: 'dateFrom' | 'dateTo', value: string) => {
    onFiltersChange({
      ...filters,
      datePreset: 'all',
      [field]: value || null,
    })
  }

  const handleStarClick = (rating: number) => {
    onFiltersChange({
      ...filters,
      minRating: filters.minRating === rating ? null : rating,
    })
  }

  const handleExerciseSelect = (exercise: Exercise) => {
    onFiltersChange({
      ...filters,
      exerciseId: exercise.id,
      exerciseName: exercise.name,
    })
    setShowExerciseSearch(false)
  }

  const handleClearExercise = () => {
    onFiltersChange({
      ...filters,
      exerciseId: null,
      exerciseName: null,
    })
  }

  const handleClearAll = () => {
    setShowCustomRange(false)
    onFiltersChange({
      datePreset: 'all',
      dateFrom: null,
      dateTo: null,
      minRating: null,
      exerciseId: null,
      exerciseName: null,
    })
  }

  return (
    <div className="mb-4">
      {/* Toggle row */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="inline-flex items-center gap-2 text-sm text-gray-400 hover:text-gray-200 transition-colors"
        >
          <SlidersHorizontal className="w-4 h-4" />
          <span>Filters</span>
          {activeFilterCount > 0 && (
            <span className="bg-flame-500 text-white text-xs font-medium rounded-full w-5 h-5 flex items-center justify-center">
              {activeFilterCount}
            </span>
          )}
        </button>
        {activeFilterCount > 0 && (
          <button
            onClick={handleClearAll}
            className="text-xs text-gray-500 hover:text-gray-300 transition-colors"
          >
            Clear All
          </button>
        )}
      </div>

      {/* Filter panel */}
      {isOpen && (
        <div className="mt-3 space-y-4 bg-gray-800/50 border border-gray-700 rounded-lg p-4">
          {/* Date range */}
          <div>
            <label className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-2 block">
              Date Range
            </label>
            <div className="flex flex-wrap gap-2">
              {DATE_PRESETS.map(({ value, label }) => (
                <button
                  key={value}
                  onClick={() => handlePresetClick(value as DatePreset)}
                  className={`px-3 py-1.5 text-xs rounded-lg border transition-colors ${
                    filters.datePreset === value && !showCustomRange
                      ? 'bg-flame-600 border-flame-600 text-white'
                      : 'bg-gray-800 border-gray-600 text-gray-300 hover:border-gray-500'
                  }`}
                >
                  {label}
                </button>
              ))}
              <button
                onClick={handleCustomClick}
                className={`px-3 py-1.5 text-xs rounded-lg border transition-colors ${
                  showCustomRange
                    ? 'bg-flame-600 border-flame-600 text-white'
                    : 'bg-gray-800 border-gray-600 text-gray-300 hover:border-gray-500'
                }`}
              >
                Custom
              </button>
            </div>
            {showCustomRange && (
              <div className="flex items-center gap-2 mt-2">
                <input
                  type="date"
                  value={filters.dateFrom || ''}
                  onChange={(e) => handleCustomDate('dateFrom', e.target.value)}
                  className="bg-gray-800 border border-gray-600 rounded-lg px-3 py-1.5 text-xs text-gray-200 focus:border-flame-500 focus:outline-none"
                />
                <span className="text-xs text-gray-500">to</span>
                <input
                  type="date"
                  value={filters.dateTo || ''}
                  onChange={(e) => handleCustomDate('dateTo', e.target.value)}
                  className="bg-gray-800 border border-gray-600 rounded-lg px-3 py-1.5 text-xs text-gray-200 focus:border-flame-500 focus:outline-none"
                />
              </div>
            )}
          </div>

          {/* Star rating */}
          <div>
            <label className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-2 block">
              Min Rating
            </label>
            <div className="flex gap-1">
              {[1, 2, 3, 4, 5].map((star) => (
                <button
                  key={star}
                  onClick={() => handleStarClick(star)}
                  className="p-0.5 transition-colors"
                >
                  <Star
                    className={`w-5 h-5 ${
                      filters.minRating && star <= filters.minRating
                        ? 'fill-yellow-400 text-yellow-400'
                        : 'text-gray-600 hover:text-gray-400'
                    }`}
                  />
                </button>
              ))}
              {filters.minRating && (
                <span className="text-xs text-gray-500 ml-2 self-center">
                  {filters.minRating}+ stars
                </span>
              )}
            </div>
          </div>

          {/* Exercise filter */}
          <div>
            <label className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-2 block">
              Exercise
            </label>
            {filters.exerciseName ? (
              <div className="inline-flex items-center gap-2 bg-gray-800 border border-gray-600 rounded-lg px-3 py-1.5">
                <span className="text-sm text-gray-200">{filters.exerciseName}</span>
                <button
                  onClick={handleClearExercise}
                  className="text-gray-500 hover:text-gray-300 transition-colors"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            ) : (
              <button
                onClick={() => setShowExerciseSearch(true)}
                className="text-sm text-gray-400 hover:text-gray-200 bg-gray-800 border border-gray-600 rounded-lg px-3 py-1.5 transition-colors"
              >
                Any Exercise
              </button>
            )}
          </div>
        </div>
      )}

      {/* Exercise search modal */}
      {showExerciseSearch && (
        <ExerciseSearchModal
          onSelect={handleExerciseSelect}
          onClose={() => setShowExerciseSearch(false)}
          onCreateCustom={() => {}}
        />
      )}
    </div>
  )
}
