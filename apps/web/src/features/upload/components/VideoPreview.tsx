interface VideoPreviewProps {
  src: string
  className?: string
}

export function VideoPreview({ src, className = '' }: VideoPreviewProps) {
  return (
    <video
      src={src}
      controls
      className={`rounded-lg ${className}`}
    />
  )
}
