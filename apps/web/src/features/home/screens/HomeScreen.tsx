import { FlameVisualization, QuickActions } from '../components'

const features = [
  { title: 'Log Workouts', description: 'Quick and easy workout logging', icon: '📝' },
  { title: 'Track Progress', description: 'Monitor strength improvements over time', icon: '📈' },
  { title: 'AI Insights', description: 'Get personalized trend analysis', icon: '🤖' },
  { title: 'Consistency', description: 'Track workout frequency and streaks', icon: '🔥' },
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
          Track your workouts, monitor your progress, and get AI-powered insights
          to help you reach your fitness goals.
        </p>
      </div>

      <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 mb-16">
        {features.map((feature) => (
          <div
            key={feature.title}
            className="p-6 rounded-xl bg-gray-800/50 border border-gray-700 hover:border-flame-500/50 transition-colors"
          >
            <div className="text-3xl mb-3">{feature.icon}</div>
            <h3 className="text-lg font-semibold mb-1">{feature.title}</h3>
            <p className="text-gray-400 text-sm">{feature.description}</p>
          </div>
        ))}
      </div>

      <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-8 text-center">
        <h2 className="text-2xl font-bold mb-4">Start Your Fitness Journey</h2>
        <p className="text-gray-400 mb-8 max-w-xl mx-auto">
          Log your workouts, track your progress, and let AI help you identify trends
          and optimize your training.
        </p>
        <QuickActions />
      </div>
    </div>
  )
}
