import { useCallback, useEffect, useState } from 'react'
import type { UserProfile } from '@flame-fitness/shared'
import { useAuth } from '../../auth/hooks'
import { getProfile } from '../services/profileService'

export function useProfile() {
  const { session } = useAuth()
  const [profile, setProfile] = useState<UserProfile | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchProfile = useCallback(async () => {
    if (!session?.access_token) {
      setLoading(false)
      return
    }

    try {
      setLoading(true)
      setError(null)
      const data = await getProfile(session.access_token)
      setProfile(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load profile')
    } finally {
      setLoading(false)
    }
  }, [session?.access_token])

  useEffect(() => {
    fetchProfile()
  }, [fetchProfile])

  const needsOnboarding = profile !== null && !profile.onboardingCompleted

  return {
    profile,
    loading,
    error,
    needsOnboarding,
    refetch: fetchProfile,
  }
}
