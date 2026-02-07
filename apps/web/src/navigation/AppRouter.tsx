import { Routes, Route } from 'react-router-dom'
import { Layout } from '../shared/components'
import { HomeScreen } from '../features/home'
import { LoginScreen, SignupScreen } from '../features/auth'
import { OnboardingScreen } from '../features/onboarding'
import { DashboardScreen } from '../features/dashboard'
import { ProtectedRoute } from './ProtectedRoute'
import { OnboardingRoute } from './OnboardingRoute'

export function AppRouter() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<HomeScreen />} />
        <Route path="login" element={<LoginScreen />} />
        <Route path="signup" element={<SignupScreen />} />
        <Route
          path="onboarding"
          element={
            <ProtectedRoute>
              <OnboardingScreen />
            </ProtectedRoute>
          }
        />
        <Route
          path="dashboard"
          element={
            <OnboardingRoute>
              <DashboardScreen />
            </OnboardingRoute>
          }
        />
      </Route>
    </Routes>
  )
}
