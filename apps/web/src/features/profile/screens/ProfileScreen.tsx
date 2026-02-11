import { useProfile } from '../../onboarding/hooks'

export function ProfileScreen() {
  const { profile } = useProfile()

  return (
    <div className="max-w-4xl mx-auto">
      <h1 className="text-3xl font-bold mb-2">Profile</h1>
      <p className="text-gray-400 mb-8">Manage your account and preferences.</p>

      <div className="space-y-6">
        <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-6">
          <h2 className="text-lg font-semibold mb-4">Personal Info</h2>
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="block text-sm text-gray-400 mb-1">Display Name</label>
              <p className="text-white">{profile?.displayName || 'Not set'}</p>
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Experience Level</label>
              <p className="text-white capitalize">{profile?.experienceLevel || 'Not set'}</p>
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Goal</label>
              <p className="text-white capitalize">{profile?.goal?.replace(/_/g, ' ') || 'Not set'}</p>
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Workouts per Week</label>
              <p className="text-white">{profile?.workoutDaysPerWeek || 'Not set'}</p>
            </div>
          </div>
        </div>

        <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-6">
          <h2 className="text-lg font-semibold mb-4">Settings</h2>
          <p className="text-gray-400">More settings coming soon.</p>
        </div>
      </div>
    </div>
  )
}
