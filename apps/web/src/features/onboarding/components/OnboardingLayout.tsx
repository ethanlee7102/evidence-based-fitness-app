import { ONBOARDING_STEPS, type OnboardingStep } from '../types'

interface OnboardingLayoutProps {
  currentStep: OnboardingStep
  children: React.ReactNode
}

export function OnboardingLayout({ currentStep, children }: OnboardingLayoutProps) {
  const stepInfo = ONBOARDING_STEPS[currentStep]

  return (
    <div className="max-w-lg mx-auto px-4 py-8">
      {/* Progress bar */}
      <div className="mb-8">
        <div className="flex justify-between mb-2">
          {ONBOARDING_STEPS.map((step, index) => (
            <div
              key={step.title}
              className={`flex-1 text-center text-xs ${
                index <= currentStep ? 'text-flame-400' : 'text-gray-500'
              }`}
            >
              {step.title}
            </div>
          ))}
        </div>
        <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-flame-600 to-flame-400 transition-all duration-300"
            style={{ width: `${((currentStep + 1) / ONBOARDING_STEPS.length) * 100}%` }}
          />
        </div>
      </div>

      {/* Step header */}
      <div className="text-center mb-8">
        <h1 className="text-2xl font-bold mb-2">{stepInfo.title}</h1>
        <p className="text-gray-400">{stepInfo.description}</p>
      </div>

      {/* Step content */}
      {children}
    </div>
  )
}
