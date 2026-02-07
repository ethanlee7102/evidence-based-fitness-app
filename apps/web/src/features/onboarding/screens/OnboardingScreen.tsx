import { useNavigate } from 'react-router-dom'
import {
  OnboardingLayout,
  StepBasicInfo,
  StepFitnessProfile,
  StepPhysicalStats,
  StepSchedule,
} from '../components'
import { useOnboarding } from '../hooks'

export function OnboardingScreen() {
  const navigate = useNavigate()
  const {
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
  } = useOnboarding()

  const isLastStep = currentStep === totalSteps - 1

  const handleNext = async () => {
    if (isLastStep) {
      const success = await submitOnboarding()
      if (success) {
        navigate('/dashboard', { replace: true })
      }
    } else {
      goToNextStep()
    }
  }

  const renderStep = () => {
    switch (currentStep) {
      case 0:
        return <StepBasicInfo formData={formData} updateFormData={updateFormData} />
      case 1:
        return <StepPhysicalStats formData={formData} updateFormData={updateFormData} />
      case 2:
        return <StepFitnessProfile formData={formData} updateFormData={updateFormData} />
      case 3:
        return <StepSchedule formData={formData} updateFormData={updateFormData} />
      default:
        return null
    }
  }

  return (
    <OnboardingLayout currentStep={currentStep}>
      {error && (
        <div className="mb-6 p-3 bg-red-500/20 border border-red-500/50 rounded-lg text-red-400 text-sm">
          {error}
        </div>
      )}

      {renderStep()}

      {/* Navigation buttons */}
      <div className="flex gap-3 mt-8">
        {currentStep > 0 && (
          <button
            type="button"
            onClick={goToPreviousStep}
            disabled={submitting}
            className="flex-1 py-3 bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 disabled:cursor-not-allowed rounded-lg font-medium transition-colors"
          >
            Back
          </button>
        )}
        <button
          type="button"
          onClick={handleNext}
          disabled={!canGoNext() || submitting}
          className="flex-1 py-3 bg-flame-600 hover:bg-flame-500 disabled:bg-gray-700 disabled:cursor-not-allowed rounded-lg font-medium transition-colors"
        >
          {submitting ? 'Saving...' : isLastStep ? 'Complete Setup' : 'Continue'}
        </button>
      </div>
    </OnboardingLayout>
  )
}
