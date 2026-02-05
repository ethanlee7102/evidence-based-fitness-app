import { FlameVisualization, QuickActions } from '../components'

const pillars = [
  { title: 'Technique', description: 'AI analyzes your form from video uploads', status: 'Active', icon: '🎯' },
  { title: 'Consistency', description: 'Track workout frequency and streaks', status: 'Coming Soon', icon: '📅' },
  { title: 'Progress', description: 'Monitor strength improvements over time', status: 'Coming Soon', icon: '📈' },
  { title: 'Knowledge', description: 'AI-powered fitness education', status: 'Coming Soon', icon: '📚' },
]

const lifts = [
  { name: 'Deadlift', checks: ['Bar path tracking', 'Back angle', 'Hip hinge pattern', 'Lockout position'] },
  { name: 'Squat', checks: ['Depth detection', 'Knee tracking', 'Bar path', 'Symmetry'] },
  { name: 'Bench Press', checks: ['Bar path (J-curve)', 'Elbow angle', 'Wrist alignment', 'Arch maintenance'] },
]

export function HomeScreen() {
  return (
    <div className="max-w-6xl mx-auto px-4 py-16">
      <div className="text-center mb-16">
        <div className="w-24 h-24 mx-auto mb-8">
          <FlameVisualization size="lg" />
        </div>
        <h1 className="text-5xl font-bold mb-4">
          <span className="bg-gradient-to-r from-flame-400 via-flame-500 to-flame-600 bg-clip-text text-transparent">
            Ignite Your Progress
          </span>
        </h1>
        <p className="text-xl text-gray-400 max-w-2xl mx-auto">
          AI-powered form analysis for the Big 3 lifts. Upload your videos, get instant feedback,
          and watch your technique improve.
        </p>
      </div>

      <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 mb-16">
        {pillars.map((pillar) => (
          <div
            key={pillar.title}
            className="p-6 rounded-xl bg-gray-800/50 border border-gray-700 hover:border-flame-500/50 transition-colors"
          >
            <div className="text-3xl mb-3">{pillar.icon}</div>
            <h3 className="text-lg font-semibold mb-1">{pillar.title}</h3>
            <p className="text-gray-400 text-sm mb-3">{pillar.description}</p>
            <span
              className={`text-xs px-2 py-1 rounded-full ${
                pillar.status === 'Active'
                  ? 'bg-green-500/20 text-green-400'
                  : 'bg-gray-700 text-gray-400'
              }`}
            >
              {pillar.status}
            </span>
          </div>
        ))}
      </div>

      <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-8">
        <h2 className="text-2xl font-bold mb-4">Form Analysis for the Big 3</h2>
        <div className="grid md:grid-cols-3 gap-6 mb-8">
          {lifts.map((lift) => (
            <div key={lift.name} className="p-4 rounded-lg bg-gray-900/50">
              <h3 className="font-semibold text-flame-400 mb-3">{lift.name}</h3>
              <ul className="space-y-2">
                {lift.checks.map((check) => (
                  <li key={check} className="text-sm text-gray-400 flex items-center gap-2">
                    <span className="w-1.5 h-1.5 bg-flame-500 rounded-full" />
                    {check}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <QuickActions />
      </div>
    </div>
  )
}
