import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import type { UserProfile } from '@flame-fitness/shared'
import { useAuth } from '../../auth/hooks'
import { getProfile } from '../services/profileService'

interface ProfileContextType {
  profile: UserProfile | null
  loading: boolean
  error: string | null
  needsOnboarding: boolean
  setProfile: (profile: UserProfile | null) => void
  refetch: () => Promise<void>
}

export const ProfileContext = createContext<ProfileContextType | undefined>(undefined)

export function useProfile() {
  const context = useContext(ProfileContext)
  if (context === undefined) {
    throw new Error('useProfile must be used within a ProfileProvider')
  }
  return context
}

export function useProfileProvider() {
  const { session } = useAuth()
  const [profile, setProfile] = useState<UserProfile | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchProfile = useCallback(async () => {
    if (!session?.access_token) {
      setProfile(null)
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
    setProfile,
    refetch: fetchProfile,
  }
}
