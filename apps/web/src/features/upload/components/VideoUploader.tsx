import { useRef } from 'react'

interface VideoUploaderProps {
  onFileSelect: (file: File) => void
  preview: string | null
  fileName?: string
  fileSize?: number
  error?: string | null
}

export function VideoUploader({
  onFileSelect,
  preview,
  fileName,
  fileSize,
  error,
}: VideoUploaderProps) {
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    if (!file.type.startsWith('video/')) {
      return
    }

    if (file.size > 100 * 1024 * 1024) {
      return
    }

    onFileSelect(file)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    const file = e.dataTransfer.files[0]
    if (file && file.type.startsWith('video/') && file.size <= 100 * 1024 * 1024) {
      onFileSelect(file)
    }
  }

  return (
    <div
      onDrop={handleDrop}
      onDragOver={(e) => e.preventDefault()}
      onClick={() => fileInputRef.current?.click()}
      className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
        preview
          ? 'border-flame-500 bg-flame-500/10'
          : 'border-gray-700 hover:border-gray-600 bg-gray-800/50'
      }`}
    >
      <input
        ref={fileInputRef}
        type="file"
        accept="video/mp4,video/quicktime,video/mov"
        onChange={handleFileSelect}
        className="hidden"
      />

      {preview ? (
        <div>
          <video
            src={preview}
            controls
            className="max-h-64 mx-auto rounded-lg mb-4"
          />
          <p className="text-gray-400 text-sm">{fileName}</p>
          {fileSize && (
            <p className="text-gray-500 text-xs mt-1">
              {(fileSize / (1024 * 1024)).toFixed(1)} MB
            </p>
          )}
        </div>
      ) : (
        <div>
          <div className="text-5xl mb-4">📹</div>
          <p className="text-gray-300 mb-2">
            Drag and drop your video here, or click to browse
          </p>
          <p className="text-gray-500 text-sm">
            MP4 or MOV, max 30 seconds, max 100MB
          </p>
        </div>
      )}

      {error && (
        <p className="text-red-400 text-sm mt-4">{error}</p>
      )}
    </div>
  )
}
