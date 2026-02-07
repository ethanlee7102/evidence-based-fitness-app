import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../features/auth/hooks'
import { useProfile } from '../features/onboarding/hooks'
import { Loading } from '../shared/components'

interface OnboardingRouteProps {
  children: React.ReactNode
}

/**
 * Route guard that ensures user has completed onboarding.
 * Must be used inside ProtectedRoute (requires authenticated user).
 */
export function OnboardingRoute({ children }: OnboardingRouteProps) {
  const { user, loading: authLoading } = useAuth()
  const { profile, loading: profileLoading, needsOnboarding } = useProfile()
  const location = useLocation()

  // Still checking auth or profile
  if (authLoading || profileLoading) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <Loading />
      </div>
    )
  }

  // Not authenticated - let ProtectedRoute handle this
  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  // Profile not loaded yet or needs onboarding
  if (needsOnboarding) {
    return <Navigate to="/onboarding" replace />
  }

  // Profile loaded and onboarding completed
  if (profile?.onboardingCompleted) {
    return <>{children}</>
  }

  // Default: show loading while we figure things out
  return (
    <div className="min-h-[60vh] flex items-center justify-center">
      <Loading />
    </div>
  )
}
