import { useState } from 'react'
import type { OnboardingData } from '@flame-fitness/shared'
import { useAuth } from '../../auth/hooks'
import { completeOnboarding } from '../services/profileService'
import type { OnboardingFormData, OnboardingStep } from '../types'
import { INITIAL_FORM_DATA, ONBOARDING_STEPS } from '../types'

export function useOnboarding() {
  const { session } = useAuth()
  const [currentStep, setCurrentStep] = useState<OnboardingStep>(0)
  const [formData, setFormData] = useState<OnboardingFormData>(INITIAL_FORM_DATA)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const totalSteps = ONBOARDING_STEPS.length

  const updateFormData = (updates: Partial<OnboardingFormData>) => {
    setFormData((prev) => ({ ...prev, ...updates }))
  }

  const goToNextStep = () => {
    if (currentStep < totalSteps - 1) {
      setCurrentStep((prev) => (prev + 1) as OnboardingStep)
    }
  }

  const goToPreviousStep = () => {
    if (currentStep > 0) {
      setCurrentStep((prev) => (prev - 1) as OnboardingStep)
    }
  }

  const canGoNext = (): boolean => {
    switch (currentStep) {
      case 0:
        return Boolean(formData.displayName && formData.birthday && formData.gender)
      case 1:
        return Boolean(formData.heightCm && formData.weightKg)
      case 2:
        return Boolean(formData.experienceLevel && formData.goal)
      case 3:
        return true // Schedule step has no required fields beyond workoutDaysPerWeek which has a default
      default:
        return false
    }
  }

  const submitOnboarding = async (): Promise<boolean> => {
    if (!session?.access_token) {
      setError('Not authenticated')
      return false
    }

    // Validate all required fields
    if (
      !formData.displayName ||
      !formData.birthday ||
      !formData.gender ||
      !formData.heightCm ||
      !formData.weightKg ||
      !formData.experienceLevel ||
      !formData.goal
    ) {
      setError('Please complete all required fields')
      return false
    }

    setSubmitting(true)
    setError(null)

    try {
      const data: OnboardingData = {
        displayName: formData.displayName,
        birthday: formData.birthday,
        gender: formData.gender,
        heightCm: Number(formData.heightCm),
        weightKg: Number(formData.weightKg),
        unitsPreference: formData.unitsPreference,
        experienceLevel: formData.experienceLevel,
        goal: formData.goal,
        workoutDaysPerWeek: formData.workoutDaysPerWeek,
        preferredDays: formData.preferredDays.length > 0 ? formData.preferredDays : undefined,
        injuriesLimitations: formData.injuriesLimitations || undefined,
      }

      await completeOnboarding(session.access_token, data)
      return true
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to complete onboarding')
      return false
    } finally {
      setSubmitting(false)
    }
  }

  return {
    currentStep,
    totalSteps,
    formData,
    updateFormData,
    goToNextStep,
    goToPreviousStep,
    canGoNext,
    submitOnboarding,
    submitting,
    error,
  }
}
