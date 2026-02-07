import type { DayOfWeek } from '@flame-fitness/shared'
import type { OnboardingFormData } from '../types'

interface StepScheduleProps {
  formData: OnboardingFormData
  updateFormData: (updates: Partial<OnboardingFormData>) => void
}

const DAYS: { value: DayOfWeek; label: string; short: string }[] = [
  { value: 'monday', label: 'Monday', short: 'M' },
  { value: 'tuesday', label: 'Tuesday', short: 'T' },
  { value: 'wednesday', label: 'Wednesday', short: 'W' },
  { value: 'thursday', label: 'Thursday', short: 'T' },
  { value: 'friday', label: 'Friday', short: 'F' },
  { value: 'saturday', label: 'Saturday', short: 'S' },
  { value: 'sunday', label: 'Sunday', short: 'S' },
]

export function StepSchedule({ formData, updateFormData }: StepScheduleProps) {
  const toggleDay = (day: DayOfWeek) => {
    const currentDays = formData.preferredDays
    if (currentDays.includes(day)) {
      updateFormData({ preferredDays: currentDays.filter((d) => d !== day) })
    } else {
      updateFormData({ preferredDays: [...currentDays, day] })
    }
  }

  return (
    <div className="space-y-8">
      {/* Workout days per week */}
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-3">
          How many days per week do you want to work out?
        </label>
        <div className="px-2">
          <input
            type="range"
            min="1"
            max="7"
            value={formData.workoutDaysPerWeek}
            onChange={(e) => updateFormData({ workoutDaysPerWeek: Number(e.target.value) })}
            className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-flame-500"
          />
          <div className="flex justify-between text-sm text-gray-500 mt-2">
            {[1, 2, 3, 4, 5, 6, 7].map((num) => (
              <span
                key={num}
                className={num === formData.workoutDaysPerWeek ? 'text-flame-400 font-medium' : ''}
              >
                {num}
              </span>
            ))}
          </div>
        </div>
        <div className="text-center mt-4">
          <span className="text-3xl font-bold text-flame-400">{formData.workoutDaysPerWeek}</span>
          <span className="text-gray-400 ml-2">days per week</span>
        </div>
      </div>

      {/* Preferred days */}
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-3">
          Preferred workout days <span className="text-gray-500">(optional)</span>
        </label>
        <div className="flex gap-2 justify-center">
          {DAYS.map((day) => (
            <button
              key={day.value}
              type="button"
              onClick={() => toggleDay(day.value)}
              title={day.label}
              className={`w-10 h-10 rounded-full flex items-center justify-center font-medium transition-colors ${
                formData.preferredDays.includes(day.value)
                  ? 'bg-flame-600 text-white'
                  : 'bg-gray-800 border border-gray-700 text-gray-400 hover:border-gray-600'
              }`}
            >
              {day.short}
            </button>
          ))}
        </div>
        {formData.preferredDays.length > 0 && (
          <p className="text-center text-sm text-gray-500 mt-2">
            {formData.preferredDays.length} day{formData.preferredDays.length !== 1 ? 's' : ''}{' '}
            selected
          </p>
        )}
      </div>

      {/* Injuries/limitations */}
      <div>
        <label htmlFor="injuries" className="block text-sm font-medium text-gray-300 mb-1">
          Any injuries or limitations? <span className="text-gray-500">(optional)</span>
        </label>
        <textarea
          id="injuries"
          value={formData.injuriesLimitations}
          onChange={(e) => updateFormData({ injuriesLimitations: e.target.value })}
          placeholder="e.g., Lower back pain, recovering from shoulder surgery..."
          rows={3}
          className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg focus:outline-none focus:border-flame-500 transition-colors resize-none"
        />
      </div>
    </div>
  )
}
