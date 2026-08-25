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
  const { profile, loading: profileLoading, needsOnboarding, error, refetch } = useProfile()
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

  // Profile failed to load (not merely missing), so surface it with a retry rather
  // than spinning forever.
  if (error) {
    return (
      <div className="min-h-[60vh] flex flex-col items-center justify-center gap-4 text-center px-4">
        <p className="text-gray-400">We couldn't load your profile.</p>
        <button
          onClick={() => refetch()}
          className="px-4 py-2 rounded-lg bg-flame-600 hover:bg-flame-500 font-medium transition-colors"
        >
          Retry
        </button>
      </div>
    )
  }

  // Default: show loading while we figure things out
  return (
    <div className="min-h-[60vh] flex items-center justify-center">
      <Loading />
    </div>
  )
}
