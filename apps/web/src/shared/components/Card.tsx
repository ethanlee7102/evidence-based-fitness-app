import { ReactNode } from 'react'

interface CardProps {
  children: ReactNode
  className?: string
}

export function Card({ children, className = '' }: CardProps) {
  return (
    <div className={`bg-gray-800/50 border border-gray-700 rounded-xl p-6 ${className}`}>
      {children}
    </div>
  )
}
