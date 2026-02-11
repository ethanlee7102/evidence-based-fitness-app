import { useProfile } from '../../onboarding/hooks'

export function HomeDashboardScreen() {
  const { profile } = useProfile()

  return (
    <div className="max-w-4xl mx-auto">
      <h1 className="text-3xl font-bold mb-2">
        Welcome{profile?.displayName ? `, ${profile.displayName}` : ''}!
      </h1>
      <p className="text-gray-400 mb-8">Your fitness journey starts here.</p>

      <div className="grid gap-6 md:grid-cols-2">
        <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-6">
          <h2 className="text-lg font-semibold mb-4">Quick Stats</h2>
          <p className="text-gray-400">No workouts logged yet. Start your first workout!</p>
        </div>

        <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-6">
          <h2 className="text-lg font-semibold mb-4">Recent Activity</h2>
          <p className="text-gray-400">Your recent workouts will appear here.</p>
        </div>
      </div>

      <div className="mt-8 text-center">
        <button
          type="button"
          className="px-8 py-4 bg-flame-600 hover:bg-flame-500 rounded-xl font-medium text-lg transition-colors"
        >
          Log Workout
        </button>
      </div>
    </div>
  )
}
