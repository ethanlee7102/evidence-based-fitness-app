import { Link } from 'react-router-dom'
import { useAuth } from '../../auth/hooks'

export function QuickActions() {
  const { user } = useAuth()

  return (
    <div className="text-center">
      <Link
        to={user ? '/upload' : '/signup'}
        className="inline-flex items-center gap-2 px-6 py-3 bg-flame-600 hover:bg-flame-500 rounded-lg font-medium transition-colors"
      >
        {user ? 'Analyze Your Lift' : 'Get Started'}
        <span>→</span>
      </Link>
    </div>
  )
}
