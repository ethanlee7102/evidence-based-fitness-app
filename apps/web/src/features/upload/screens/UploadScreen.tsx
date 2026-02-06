import { useNavigate } from 'react-router-dom'
import { VideoUploader, ExerciseSelector, CameraSideSelector, UploadProgress } from '../components'
import { useVideoUpload } from '../hooks'

export function UploadScreen() {
  const navigate = useNavigate()
  const {
    file,
    preview,
    exerciseType,
    cameraSide,
    uploading,
    analyzing,
    progress,
    error,
    setFile,
    setExerciseType,
    setCameraSide,
    upload,
    reset,
  } = useVideoUpload()

  const handleSubmit = async () => {
    const analysisId = await upload()
    if (analysisId) {
      navigate(`/analysis/${analysisId}`)
    }
  }

  return (
    <div className="max-w-2xl mx-auto px-4 py-12">
      <h1 className="text-3xl font-bold mb-2">Analyze Your Lift</h1>
      <p className="text-gray-400 mb-8">
        Upload a video of your lift from a side view (sagittal plane) for best results.
      </p>

      {error && (
        <div className="mb-6 p-3 bg-red-500/20 border border-red-500/50 rounded-lg text-red-400 text-sm">
          {error}
        </div>
      )}

      <div className="mb-6">
        <ExerciseSelector value={exerciseType} onChange={setExerciseType} />
      </div>

      <div className="mb-6">
        <CameraSideSelector value={cameraSide} onChange={setCameraSide} />
      </div>

      <VideoUploader
        onFileSelect={setFile}
        preview={preview}
        fileName={file?.name}
        fileSize={file?.size}
      />

      <UploadProgress
        uploading={uploading}
        analyzing={analyzing}
        progress={progress}
      />

      <div className="mt-8 flex gap-4">
        <button
          onClick={reset}
          disabled={!file || uploading || analyzing}
          className="px-6 py-3 bg-gray-800 hover:bg-gray-700 disabled:bg-gray-800 disabled:text-gray-600 disabled:cursor-not-allowed rounded-lg font-medium transition-colors"
        >
          Clear
        </button>
        <button
          onClick={handleSubmit}
          disabled={!file || uploading || analyzing}
          className="flex-1 px-6 py-3 bg-flame-600 hover:bg-flame-500 disabled:bg-gray-700 disabled:cursor-not-allowed rounded-lg font-medium transition-colors"
        >
          {uploading ? 'Uploading...' : analyzing ? 'Analyzing...' : 'Analyze Video'}
        </button>
      </div>

      <div className="mt-8 p-4 bg-gray-800/50 rounded-lg">
        <h3 className="font-medium mb-2">Tips for Best Results</h3>
        <ul className="text-sm text-gray-400 space-y-1">
          <li>• Record from the side (sagittal plane) for deadlifts and squats</li>
          <li>• Ensure good lighting and your full body is visible</li>
          <li>• Include 1-3 reps in the video</li>
          <li>• Keep the camera stable (tripod recommended)</li>
        </ul>
      </div>
    </div>
  )
}
