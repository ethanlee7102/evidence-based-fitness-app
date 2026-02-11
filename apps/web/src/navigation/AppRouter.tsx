import { Routes, Route, Navigate } from 'react-router-dom'
import { Layout } from '../shared/components'
import { HomeScreen, HomeDashboardScreen } from '../features/home'
import { LoginScreen, SignupScreen } from '../features/auth'
import { OnboardingScreen } from '../features/onboarding'
import { DashboardLayout } from '../features/dashboard'
import { WorkoutsScreen } from '../features/workouts'
import { AnalysisScreen } from '../features/analysis'
import { ChatScreen } from '../features/chat'
import { ProfileScreen } from '../features/profile'
import { ProtectedRoute } from './ProtectedRoute'
import { OnboardingRoute } from './OnboardingRoute'

export function AppRouter() {
  return (
    <Routes>
      {/* Public routes with Layout */}
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
      </Route>

      {/* Dashboard with sidebar layout */}
      <Route
        path="dashboard"
        element={
          <OnboardingRoute>
            <DashboardLayout />
          </OnboardingRoute>
        }
      >
        <Route index element={<Navigate to="home" replace />} />
        <Route path="home" element={<HomeDashboardScreen />} />
        <Route path="workouts" element={<WorkoutsScreen />} />
        <Route path="analysis" element={<AnalysisScreen />} />
        <Route path="chat" element={<ChatScreen />} />
        <Route path="profile" element={<ProfileScreen />} />
      </Route>
    </Routes>
  )
}
