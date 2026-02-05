import { Outlet, Link } from 'react-router-dom'
import { useAuth } from '../../features/auth/hooks'

export function Layout() {
  const { user, signOut, loading } = useAuth()

  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-gray-800 bg-gray-900/80 backdrop-blur-sm sticky top-0 z-50">
        <nav className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2 text-xl font-bold">
            <img src="/flame.svg" alt="Flame" className="w-8 h-8" />
            <span className="bg-gradient-to-r from-flame-400 to-flame-600 bg-clip-text text-transparent">
              Flame Fitness
            </span>
          </Link>

          <div className="flex items-center gap-4">
            {loading ? null : user ? (
              <>
                <Link
                  to="/upload"
                  className="px-4 py-2 bg-flame-600 hover:bg-flame-500 rounded-lg font-medium transition-colors"
                >
                  Analyze Lift
                </Link>
                <button
                  onClick={() => signOut()}
                  className="px-4 py-2 text-gray-400 hover:text-gray-200 transition-colors"
                >
                  Sign Out
                </button>
              </>
            ) : (
              <>
                <Link to="/login" className="px-4 py-2 text-gray-400 hover:text-gray-200 transition-colors">
                  Log In
                </Link>
                <Link
                  to="/signup"
                  className="px-4 py-2 bg-flame-600 hover:bg-flame-500 rounded-lg font-medium transition-colors"
                >
                  Sign Up
                </Link>
              </>
            )}
          </div>
        </nav>
      </header>

      <main className="flex-1">
        <Outlet />
      </main>

      <footer className="border-t border-gray-800 py-6">
        <div className="max-w-6xl mx-auto px-4 text-center text-gray-500 text-sm">
          Flame Fitness - Track your improvement across Technique, Consistency, Progress, and Knowledge
        </div>
      </footer>
    </div>
  )
}
