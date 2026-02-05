interface UploadProgressProps {
  uploading: boolean
  analyzing: boolean
  progress: number
}

export function UploadProgress({ uploading, analyzing, progress }: UploadProgressProps) {
  if (!uploading && !analyzing) return null

  return (
    <div className="mt-6">
      <div className="flex justify-between text-sm text-gray-400 mb-2">
        <span>{uploading ? 'Uploading...' : 'Analyzing...'}</span>
        <span>{progress}%</span>
      </div>
      <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
        <div
          className="h-full bg-flame-500 transition-all duration-300"
          style={{ width: `${progress}%` }}
        />
      </div>
      {analyzing && (
        <p className="text-gray-500 text-sm mt-2">
          Running pose estimation and form analysis...
        </p>
      )}
    </div>
  )
}
