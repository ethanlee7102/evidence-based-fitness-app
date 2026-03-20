import type { WorkoutSummary } from '../types'
import { WorkoutHistoryCard } from './WorkoutHistoryCard'
import { Button } from '../../../shared/components/Button'

interface WorkoutHistoryListProps {
  workouts: WorkoutSummary[]
  isLoadingMore: boolean
  hasMore: boolean
  onLoadMore: () => void
  onView: (id: string) => void
  onResume: (id: string) => void
  onDelete: (id: string) => void
}

export function WorkoutHistoryList({
  workouts,
  isLoadingMore,
  hasMore,
  onLoadMore,
  onView,
  onResume,
  onDelete,
}: WorkoutHistoryListProps) {
  if (workouts.length === 0) {
    return null
  }

  return (
    <div className="space-y-3">
      <h2 className="text-lg font-semibold text-gray-300">Workout History</h2>
      {workouts.map((workout) => (
        <WorkoutHistoryCard
          key={workout.id}
          workout={workout}
          onView={onView}
          onResume={onResume}
          onDelete={onDelete}
        />
      ))}
      {hasMore && (
        <div className="text-center pt-2">
          <Button
            variant="secondary"
            size="sm"
            onClick={onLoadMore}
            disabled={isLoadingMore}
          >
            {isLoadingMore ? 'Loading...' : 'Load More'}
          </Button>
        </div>
      )}
    </div>
  )
}
