import type { ExperienceLevel, FitnessGoal } from '@flame-fitness/shared'
import type { OnboardingFormData } from '../types'

interface StepFitnessProfileProps {
  formData: OnboardingFormData
  updateFormData: (updates: Partial<OnboardingFormData>) => void
}

const EXPERIENCE_OPTIONS: { value: ExperienceLevel; label: string; description: string }[] = [
  { value: 'beginner', label: 'Beginner', description: 'New to lifting or less than 1 year' },
  { value: 'intermediate', label: 'Intermediate', description: '1-3 years of consistent training' },
  { value: 'advanced', label: 'Advanced', description: '3+ years of serious training' },
]

const GOAL_OPTIONS: { value: FitnessGoal; label: string; icon: string }[] = [
  { value: 'strength', label: 'Build Strength', icon: '💪' },
  { value: 'build_muscle', label: 'Build Muscle', icon: '🏋️' },
  { value: 'lose_weight', label: 'Lose Weight', icon: '⚡' },
  { value: 'general_fitness', label: 'General Fitness', icon: '🎯' },
  { value: 'cardio_endurance', label: 'Cardio & Endurance', icon: '🏃' },
]

export function StepFitnessProfile({ formData, updateFormData }: StepFitnessProfileProps) {
  return (
    <div className="space-y-8">
      {/* Experience Level */}
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-3">
          Experience Level <span className="text-flame-400">*</span>
        </label>
        <div className="space-y-3">
          {EXPERIENCE_OPTIONS.map((option) => (
            <button
              key={option.value}
              type="button"
              onClick={() => updateFormData({ experienceLevel: option.value })}
              className={`w-full px-4 py-4 rounded-lg border text-left transition-colors ${
                formData.experienceLevel === option.value
                  ? 'bg-flame-600/20 border-flame-500'
                  : 'bg-gray-800 border-gray-700 hover:border-gray-600'
              }`}
            >
              <div
                className={`font-medium ${
                  formData.experienceLevel === option.value ? 'text-flame-400' : 'text-white'
                }`}
              >
                {option.label}
              </div>
              <div className="text-sm text-gray-400 mt-1">{option.description}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Fitness Goal */}
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-3">
          Primary Goal <span className="text-flame-400">*</span>
        </label>
        <div className="grid grid-cols-2 gap-3">
          {GOAL_OPTIONS.map((option) => (
            <button
              key={option.value}
              type="button"
              onClick={() => updateFormData({ goal: option.value })}
              className={`px-4 py-4 rounded-lg border text-center transition-colors ${
                formData.goal === option.value
                  ? 'bg-flame-600/20 border-flame-500'
                  : 'bg-gray-800 border-gray-700 hover:border-gray-600'
              }`}
            >
              <div className="text-2xl mb-1">{option.icon}</div>
              <div
                className={`text-sm font-medium ${
                  formData.goal === option.value ? 'text-flame-400' : 'text-white'
                }`}
              >
                {option.label}
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
