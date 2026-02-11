import { NavLink, useNavigate } from 'react-router-dom'
import { LogOut } from 'lucide-react'
import { NAV_ITEMS } from '../types'
import { useAuth } from '../../auth/hooks'

interface SidebarProps {
  className?: string
}

export function Sidebar({ className = '' }: SidebarProps) {
  const { signOut } = useAuth()
  const navigate = useNavigate()

  const handleSignOut = async () => {
    await signOut()
    navigate('/')
  }

  return (
    <aside className={`flex flex-col bg-gray-900 border-r border-gray-800 ${className}`}>
      <div className="p-6">
        <h1 className="text-xl font-bold bg-gradient-to-r from-flame-400 to-flame-600 bg-clip-text text-transparent">
          Flame Fitness
        </h1>
      </div>

      <nav className="flex-1 px-4">
        <ul className="space-y-1">
          {NAV_ITEMS.map((item) => (
            <li key={item.path}>
              <NavLink
                to={item.path}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                    isActive
                      ? 'bg-flame-600/20 text-flame-400'
                      : 'text-gray-400 hover:bg-gray-800 hover:text-white'
                  }`
                }
              >
                <item.icon className="w-5 h-5" />
                <span>{item.label}</span>
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      <div className="p-4 border-t border-gray-800">
        <button
          type="button"
          onClick={handleSignOut}
          className="flex items-center gap-3 w-full px-4 py-3 rounded-lg text-gray-400 hover:bg-gray-800 hover:text-white transition-colors"
        >
          <LogOut className="w-5 h-5" />
          <span>Sign Out</span>
        </button>
      </div>
    </aside>
  )
}
