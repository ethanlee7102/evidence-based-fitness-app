import type { Gender } from '@flame-fitness/shared'
import type { OnboardingFormData } from '../types'

interface StepBasicInfoProps {
  formData: OnboardingFormData
  updateFormData: (updates: Partial<OnboardingFormData>) => void
}

const GENDER_OPTIONS: { value: Gender; label: string }[] = [
  { value: 'male', label: 'Male' },
  { value: 'female', label: 'Female' },
  { value: 'other', label: 'Other' },
  { value: 'prefer_not_to_say', label: 'Prefer not to say' },
]

export function StepBasicInfo({ formData, updateFormData }: StepBasicInfoProps) {
  return (
    <div className="space-y-6">
      <div>
        <label htmlFor="displayName" className="block text-sm font-medium text-gray-300 mb-1">
          Display Name <span className="text-flame-400">*</span>
        </label>
        <input
          type="text"
          id="displayName"
          value={formData.displayName}
          onChange={(e) => updateFormData({ displayName: e.target.value })}
          placeholder="What should we call you?"
          className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg focus:outline-none focus:border-flame-500 transition-colors"
        />
      </div>

      <div>
        <label htmlFor="birthday" className="block text-sm font-medium text-gray-300 mb-1">
          Birthday <span className="text-flame-400">*</span>
        </label>
        <input
          type="date"
          id="birthday"
          value={formData.birthday}
          onChange={(e) => updateFormData({ birthday: e.target.value })}
          className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg focus:outline-none focus:border-flame-500 transition-colors"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          Gender <span className="text-flame-400">*</span>
        </label>
        <div className="grid grid-cols-2 gap-3">
          {GENDER_OPTIONS.map((option) => (
            <button
              key={option.value}
              type="button"
              onClick={() => updateFormData({ gender: option.value })}
              className={`px-4 py-3 rounded-lg border transition-colors ${
                formData.gender === option.value
                  ? 'bg-flame-600/20 border-flame-500 text-flame-400'
                  : 'bg-gray-800 border-gray-700 hover:border-gray-600'
              }`}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
