import type { FormIssue, IssueSeverity } from '../types'

interface IssuesListProps {
  issues: FormIssue[]
}

function getSeverityColor(severity: IssueSeverity) {
  switch (severity) {
    case 'major':
      return 'bg-red-500/20 text-red-400 border-red-500/50'
    case 'moderate':
      return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/50'
    default:
      return 'bg-blue-500/20 text-blue-400 border-blue-500/50'
  }
}

export function IssuesList({ issues }: IssuesListProps) {
  if (issues.length === 0) {
    return (
      <div className="bg-green-500/10 border border-green-500/50 rounded-xl p-6 text-center">
        <div className="text-4xl mb-2">✅</div>
        <p className="text-green-400 font-medium">
          Great form! No significant issues detected.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {issues.map((issue, index) => (
        <div
          key={index}
          className={`border rounded-xl p-4 ${getSeverityColor(issue.severity)}`}
        >
          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="font-medium">
                  {issue.issue.replace(/_/g, ' ')}
                </span>
                <span
                  className={`text-xs px-2 py-0.5 rounded-full capitalize ${getSeverityColor(
                    issue.severity
                  )}`}
                >
                  {issue.severity}
                </span>
              </div>
              <p className="text-sm opacity-80">{issue.description}</p>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
