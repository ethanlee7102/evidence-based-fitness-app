export function WorkoutsScreen() {
  return (
    <div className="max-w-4xl mx-auto">
      <h1 className="text-3xl font-bold mb-2">Workouts</h1>
      <p className="text-gray-400 mb-8">Log and view your workout history.</p>

      <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-8 text-center">
        <div className="text-5xl mb-4">🏋️</div>
        <h2 className="text-xl font-semibold mb-2">No Workouts Yet</h2>
        <p className="text-gray-400 mb-6">
          Start logging your workouts to track your progress.
        </p>
        <button
          type="button"
          className="px-6 py-3 bg-flame-600 hover:bg-flame-500 rounded-lg font-medium transition-colors"
        >
          Log Your First Workout
        </button>
      </div>
    </div>
  )
}
