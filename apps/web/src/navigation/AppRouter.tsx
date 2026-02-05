import { Routes, Route } from 'react-router-dom'
import { Layout } from '../shared/components'
import { HomeScreen } from '../features/home'
import { LoginScreen, SignupScreen } from '../features/auth'
import { UploadScreen } from '../features/upload'
import { AnalysisResultScreen } from '../features/analysis'
import { ProtectedRoute } from './ProtectedRoute'

export function AppRouter() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<HomeScreen />} />
        <Route path="login" element={<LoginScreen />} />
        <Route path="signup" element={<SignupScreen />} />
        <Route
          path="upload"
          element={
            <ProtectedRoute>
              <UploadScreen />
            </ProtectedRoute>
          }
        />
        <Route
          path="analysis/:id"
          element={
            <ProtectedRoute>
              <AnalysisResultScreen />
            </ProtectedRoute>
          }
        />
      </Route>
    </Routes>
  )
}
