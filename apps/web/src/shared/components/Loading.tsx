interface LoadingProps {
  text?: string
  size?: 'sm' | 'md' | 'lg'
}

export function Loading({ text, size = 'md' }: LoadingProps) {
  const sizes = {
    sm: 'w-6 h-6 border-2',
    md: 'w-8 h-8 border-4',
    lg: 'w-12 h-12 border-4',
  }

  return (
    <div className="text-center">
      <div
        className={`${sizes[size]} border-flame-500 border-t-transparent rounded-full animate-spin mx-auto mb-4`}
      />
      {text && <p className="text-gray-400">{text}</p>}
    </div>
  )
}
