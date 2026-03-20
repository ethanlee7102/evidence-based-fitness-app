import { useState, useCallback, useEffect } from 'react'
import { useAuth } from '../../auth/hooks/useAuth'
import { createExercise, getMuscleGroups } from '../services/workoutService'
import type { Exercise, MuscleGroup, Equipment } from '../types'
import { EQUIPMENT_OPTIONS } from '../types'
import { Button } from '../../../shared/components/Button'

interface CreateExerciseFormProps {
  onCreated: (exercise: Exercise) => void
  onClose: () => void
}

export function CreateExerciseForm({ onCreated, onClose }: CreateExerciseFormProps) {
  const { session: authSession } = useAuth()
  const token = authSession?.access_token

  const [name, setName] = useState('')
  const [equipment, setEquipment] = useState<Equipment | ''>('')
  const [bodyRegion, setBodyRegion] = useState<'upper' | 'lower' | 'full' | ''>('')
  const [selectedMuscles, setSelectedMuscles] = useState<Set<string>>(new Set())
  const [muscleGroups, setMuscleGroups] = useState<MuscleGroup[]>([])
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Load muscle groups
  useEffect(() => {
    if (!token) return
    getMuscleGroups(token).then(setMuscleGroups).catch(() => {})
  }, [token])

  const toggleMuscle = useCallback((id: string) => {
    setSelectedMuscles((prev) => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }, [])

  const handleSubmit = useCallback(async () => {
    if (!token || !name.trim()) return
    setIsSubmitting(true)
    setError(null)

    try {
      const exercise = await createExercise(token, {
        name: name.trim(),
        equipment: equipment || undefined,
        body_region: bodyRegion || undefined,
        muscle_group_ids: Array.from(selectedMuscles),
      })
      onCreated(exercise)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to create exercise')
    } finally {
      setIsSubmitting(false)
    }
  }, [token, name, equipment, bodyRegion, selectedMuscles, onCreated])

  // Group muscles by category
  const musclesByCategory = muscleGroups.reduce(
    (acc, mg) => {
      if (!acc[mg.category]) acc[mg.category] = []
      acc[mg.category].push(mg)
      return acc
    },
    {} as Record<string, MuscleGroup[]>,
  )

  return (
    <div className="fixed inset-0 z-[65] bg-gray-900/95 flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-700">
        <h2 className="text-lg font-semibold">Create Exercise</h2>
        <button
          type="button"
          onClick={onClose}
          className="text-gray-400 hover:text-gray-200 p-1"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
          </svg>
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {error && (
          <div className="bg-red-900/30 border border-red-700 rounded-lg p-3 text-sm text-red-300">
            {error}
          </div>
        )}

        {/* Name */}
        <div>
          <label className="text-sm text-gray-400 mb-1 block">
            Exercise Name *
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Reverse Grip Pulldown"
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-sm
              placeholder-gray-500 focus:outline-none focus:border-flame-500"
          />
        </div>

        {/* Equipment */}
        <div>
          <label className="text-sm text-gray-400 mb-1 block">Equipment</label>
          <select
            value={equipment}
            onChange={(e) => setEquipment(e.target.value as Equipment | '')}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-300"
          >
            <option value="">Select equipment</option>
            {EQUIPMENT_OPTIONS.map((eq) => (
              <option key={eq} value={eq}>
                {eq.charAt(0).toUpperCase() + eq.slice(1)}
              </option>
            ))}
          </select>
        </div>

        {/* Body region */}
        <div>
          <label className="text-sm text-gray-400 mb-1 block">
            Body Region
          </label>
          <div className="flex gap-2">
            {(['upper', 'lower', 'full'] as const).map((region) => (
              <button
                key={region}
                type="button"
                onClick={() => setBodyRegion(bodyRegion === region ? '' : region)}
                className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors ${
                  bodyRegion === region
                    ? 'bg-flame-600 text-white'
                    : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                }`}
              >
                {region.charAt(0).toUpperCase() + region.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {/* Muscle groups */}
        <div>
          <label className="text-sm text-gray-400 mb-2 block">
            Target Muscles (optional)
          </label>
          <div className="space-y-3">
            {Object.entries(musclesByCategory).map(([category, muscles]) => (
              <div key={category}>
                <p className="text-xs text-gray-500 font-medium mb-1">
                  {category}
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {muscles.map((mg) => (
                    <button
                      key={mg.id}
                      type="button"
                      onClick={() => toggleMuscle(mg.id)}
                      className={`px-2.5 py-1 rounded-full text-xs transition-colors ${
                        selectedMuscles.has(mg.id)
                          ? 'bg-flame-600 text-white'
                          : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                      }`}
                    >
                      {mg.name}
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Submit */}
      <div className="p-4 border-t border-gray-700">
        <Button
          className="w-full"
          onClick={handleSubmit}
          disabled={!name.trim() || isSubmitting}
        >
          {isSubmitting ? 'Creating...' : 'Create Exercise'}
        </Button>
      </div>
    </div>
  )
}
