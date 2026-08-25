import { useState } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { LoginForm } from '../components'
import { useAuth } from '../hooks'

export function LoginScreen() {
  const navigate = useNavigate()
  const location = useLocation()
  const { signInAsGuest } = useAuth()
  const [guestLoading, setGuestLoading] = useState(false)
  const [guestError, setGuestError] = useState<string | null>(null)

  const from = (location.state as { from?: { pathname: string } })?.from?.pathname || '/dashboard'

  const handleSuccess = () => {
    navigate(from, { replace: true })
  }

  // Anonymous sign-in has no redirect-on-auth wired into /login, so navigate
  // explicitly once the guest session is established.
  const handleGuest = async () => {
    setGuestError(null)
    setGuestLoading(true)
    try {
      await signInAsGuest()
      navigate('/dashboard', { replace: true })
    } catch (err) {
      setGuestError(err instanceof Error ? err.message : 'Failed to start demo')
      setGuestLoading(false)
    }
  }

  return (
    <div className="max-w-md mx-auto px-4 py-16">
      <h1 className="text-3xl font-bold text-center mb-8">Welcome Back</h1>

      <LoginForm onSuccess={handleSuccess} />

      <div className="mt-6">
        <div className="relative flex items-center">
          <div className="flex-grow border-t border-gray-700"></div>
          <span className="mx-3 text-xs uppercase tracking-wide text-gray-500">or</span>
          <div className="flex-grow border-t border-gray-700"></div>
        </div>

        {guestError && (
          <div className="mt-4 p-3 bg-red-500/20 border border-red-500/50 rounded-lg text-red-400 text-sm">
            {guestError}
          </div>
        )}

        <button
          onClick={handleGuest}
          disabled={guestLoading}
          className="mt-4 w-full py-2.5 rounded-lg border border-flame-500/60 text-flame-300 font-medium hover:bg-flame-500/10 disabled:opacity-60 transition-colors"
        >
          {guestLoading ? 'Starting demo...' : 'Try the live demo (no sign-up)'}
        </button>
        <p className="mt-2 text-center text-xs text-gray-500">
          Explore the app with sample training data. No account needed.
        </p>
      </div>

      <p className="text-center text-gray-400 mt-6">
        Don't have an account?{' '}
        <Link to="/signup" className="text-flame-400 hover:text-flame-300">
          Sign up
        </Link>
      </p>
    </div>
  )
}
