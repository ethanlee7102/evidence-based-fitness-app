import { useState, useEffect } from 'react'
import type { UnitsPreference } from '@flame-fitness/shared'
import type { OnboardingFormData } from '../types'
import { cmToFeetInches, feetInchesToCm, kgToLbs, lbsToKg } from '../utils/unitConversion'

interface StepPhysicalStatsProps {
  formData: OnboardingFormData
  updateFormData: (updates: Partial<OnboardingFormData>) => void
}

export function StepPhysicalStats({ formData, updateFormData }: StepPhysicalStatsProps) {
  const isImperial = formData.unitsPreference === 'imperial'

  // Local state for imperial height (feet/inches)
  const [feet, setFeet] = useState<number | ''>('')
  const [inches, setInches] = useState<number | ''>('')
  const [weightDisplay, setWeightDisplay] = useState<number | ''>('')

  // Initialize local state from formData
  useEffect(() => {
    if (formData.heightCm) {
      if (isImperial) {
        const { feet: f, inches: i } = cmToFeetInches(Number(formData.heightCm))
        setFeet(f)
        setInches(i)
      }
    }
    if (formData.weightKg) {
      if (isImperial) {
        setWeightDisplay(kgToLbs(Number(formData.weightKg)))
      } else {
        setWeightDisplay(Number(formData.weightKg))
      }
    }
  }, [])

  const handleUnitsChange = (units: UnitsPreference) => {
    if (units === formData.unitsPreference) return

    updateFormData({ unitsPreference: units })

    // Convert existing values to new unit display
    if (formData.heightCm) {
      if (units === 'imperial') {
        const { feet: f, inches: i } = cmToFeetInches(Number(formData.heightCm))
        setFeet(f)
        setInches(i)
      }
    }

    if (formData.weightKg) {
      if (units === 'imperial') {
        setWeightDisplay(kgToLbs(Number(formData.weightKg)))
      } else {
        setWeightDisplay(Number(formData.weightKg))
      }
    }
  }

  const handleHeightChange = (value: number | '', field: 'cm' | 'feet' | 'inches') => {
    if (field === 'cm') {
      updateFormData({ heightCm: value })
    } else if (field === 'feet') {
      setFeet(value)
      if (value !== '' && inches !== '') {
        updateFormData({ heightCm: feetInchesToCm(Number(value), Number(inches)) })
      } else if (value !== '') {
        updateFormData({ heightCm: feetInchesToCm(Number(value), 0) })
      }
    } else if (field === 'inches') {
      setInches(value)
      if (feet !== '' && value !== '') {
        updateFormData({ heightCm: feetInchesToCm(Number(feet), Number(value)) })
      } else if (value !== '' && feet !== '') {
        updateFormData({ heightCm: feetInchesToCm(Number(feet), Number(value)) })
      }
    }
  }

  const handleWeightChange = (value: number | '') => {
    setWeightDisplay(value)
    if (value === '') {
      updateFormData({ weightKg: '' })
    } else if (isImperial) {
      updateFormData({ weightKg: lbsToKg(Number(value)) })
    } else {
      updateFormData({ weightKg: value })
    }
  }

  return (
    <div className="space-y-6">
      {/* Units toggle */}
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">Units</label>
        <div className="flex rounded-lg overflow-hidden border border-gray-700">
          <button
            type="button"
            onClick={() => handleUnitsChange('imperial')}
            className={`flex-1 py-3 text-center transition-colors ${
              isImperial
                ? 'bg-flame-600 text-white'
                : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
            }`}
          >
            Imperial (ft, lbs)
          </button>
          <button
            type="button"
            onClick={() => handleUnitsChange('metric')}
            className={`flex-1 py-3 text-center transition-colors ${
              !isImperial
                ? 'bg-flame-600 text-white'
                : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
            }`}
          >
            Metric (cm, kg)
          </button>
        </div>
      </div>

      {/* Height */}
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-1">
          Height <span className="text-flame-400">*</span>
        </label>
        {isImperial ? (
          <div className="flex gap-3">
            <div className="flex-1">
              <div className="relative">
                <input
                  type="number"
                  value={feet}
                  onChange={(e) =>
                    handleHeightChange(e.target.value ? Number(e.target.value) : '', 'feet')
                  }
                  placeholder="5"
                  min="0"
                  max="8"
                  className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg focus:outline-none focus:border-flame-500 transition-colors pr-12"
                />
                <span className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-500">ft</span>
              </div>
            </div>
            <div className="flex-1">
              <div className="relative">
                <input
                  type="number"
                  value={inches}
                  onChange={(e) =>
                    handleHeightChange(e.target.value ? Number(e.target.value) : '', 'inches')
                  }
                  placeholder="10"
                  min="0"
                  max="11"
                  className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg focus:outline-none focus:border-flame-500 transition-colors pr-12"
                />
                <span className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-500">in</span>
              </div>
            </div>
          </div>
        ) : (
          <div className="relative">
            <input
              type="number"
              value={formData.heightCm}
              onChange={(e) =>
                handleHeightChange(e.target.value ? Number(e.target.value) : '', 'cm')
              }
              placeholder="175"
              min="50"
              max="250"
              className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg focus:outline-none focus:border-flame-500 transition-colors pr-12"
            />
            <span className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-500">cm</span>
          </div>
        )}
      </div>

      {/* Weight */}
      <div>
        <label htmlFor="weight" className="block text-sm font-medium text-gray-300 mb-1">
          Weight <span className="text-flame-400">*</span>
        </label>
        <div className="relative">
          <input
            type="number"
            id="weight"
            value={weightDisplay}
            onChange={(e) =>
              handleWeightChange(e.target.value ? Number(e.target.value) : '')
            }
            placeholder={isImperial ? '150' : '70'}
            min="20"
            max={isImperial ? 700 : 300}
            step="0.1"
            className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg focus:outline-none focus:border-flame-500 transition-colors pr-12"
          />
          <span className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-500">
            {isImperial ? 'lbs' : 'kg'}
          </span>
        </div>
      </div>
    </div>
  )
}
