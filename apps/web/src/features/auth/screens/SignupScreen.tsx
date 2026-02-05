import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { SignupForm } from '../components'

export function SignupScreen() {
  const [successEmail, setSuccessEmail] = useState<string | null>(null)
  const navigate = useNavigate()

  if (successEmail) {
    return (
      <div className="max-w-md mx-auto px-4 py-16 text-center">
        <div className="text-6xl mb-4">✉️</div>
        <h1 className="text-2xl font-bold mb-4">Check Your Email</h1>
        <p className="text-gray-400 mb-6">
          We've sent a confirmation link to <strong className="text-gray-200">{successEmail}</strong>.
          Click the link to activate your account.
        </p>
        <button
          onClick={() => navigate('/login')}
          className="px-6 py-2 bg-flame-600 hover:bg-flame-500 rounded-lg font-medium transition-colors"
        >
          Go to Login
        </button>
      </div>
    )
  }

  return (
    <div className="max-w-md mx-auto px-4 py-16">
      <h1 className="text-3xl font-bold text-center mb-8">Create Account</h1>

      <SignupForm onSuccess={setSuccessEmail} />

      <p className="text-center text-gray-400 mt-6">
        Already have an account?{' '}
        <Link to="/login" className="text-flame-400 hover:text-flame-300">
          Log in
        </Link>
      </p>
    </div>
  )
}
