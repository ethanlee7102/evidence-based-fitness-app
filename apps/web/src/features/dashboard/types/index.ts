import { Home, Dumbbell, BarChart3, MessageCircle, User } from 'lucide-react'

export interface NavItem {
  path: string
  label: string
  icon: typeof Home
}

export const NAV_ITEMS: NavItem[] = [
  { path: '/dashboard/home', label: 'Home', icon: Home },
  { path: '/dashboard/workouts', label: 'Workouts', icon: Dumbbell },
  { path: '/dashboard/analysis', label: 'Analysis', icon: BarChart3 },
  { path: '/dashboard/chat', label: 'Chat', icon: MessageCircle },
  { path: '/dashboard/profile', label: 'Profile', icon: User },
]
