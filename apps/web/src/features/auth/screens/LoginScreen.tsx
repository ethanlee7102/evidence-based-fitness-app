import { Link, useNavigate, useLocation } from 'react-router-dom'
import { LoginForm } from '../components'

export function LoginScreen() {
  const navigate = useNavigate()
  const location = useLocation()

  const from = (location.state as { from?: { pathname: string } })?.from?.pathname || '/'

  const handleSuccess = () => {
    navigate(from, { replace: true })
  }

  return (
    <div className="max-w-md mx-auto px-4 py-16">
      <h1 className="text-3xl font-bold text-center mb-8">Welcome Back</h1>

      <LoginForm onSuccess={handleSuccess} />

      <p className="text-center text-gray-400 mt-6">
        Don't have an account?{' '}
        <Link to="/signup" className="text-flame-400 hover:text-flame-300">
          Sign up
        </Link>
      </p>
    </div>
  )
}
