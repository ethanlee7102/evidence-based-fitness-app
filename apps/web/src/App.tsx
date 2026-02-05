import { AuthContext, useAuthProvider } from './features/auth/hooks'
import { AppRouter } from './navigation'

function App() {
  const auth = useAuthProvider()

  return (
    <AuthContext.Provider value={auth}>
      <AppRouter />
    </AuthContext.Provider>
  )
}

export default App
