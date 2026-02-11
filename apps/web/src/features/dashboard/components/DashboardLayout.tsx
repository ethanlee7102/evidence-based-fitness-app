import { Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'

export function DashboardLayout() {
  return (
    <div className="flex min-h-screen bg-gray-950">
      <Sidebar className="hidden md:flex md:fixed md:inset-y-0 w-64" />
      <main className="flex-1 md:ml-64 p-6">
        <Outlet />
      </main>
    </div>
  )
}
