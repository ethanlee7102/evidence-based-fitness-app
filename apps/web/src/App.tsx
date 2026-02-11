import { AuthContext, useAuthProvider } from './features/auth/hooks'
import { ProfileContext, useProfileProvider } from './features/onboarding/hooks'
import { AppRouter } from './navigation'

function ProfileProvider({ children }: { children: React.ReactNode }) {
  const profileContext = useProfileProvider()
  return (
    <ProfileContext.Provider value={profileContext}>
      {children}
    </ProfileContext.Provider>
  )
}

function App() {
  const auth = useAuthProvider()

  return (
    <AuthContext.Provider value={auth}>
      <ProfileProvider>
        <AppRouter />
      </ProfileProvider>
    </AuthContext.Provider>
  )
}

export default App
