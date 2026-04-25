import type { Status } from '../types/workflow'

const labelMap: Record<Status, string> = {
  pending: 'Pending',
  queued: 'Queued',
  planning: 'Planning',
  running: 'Running',
  paused: 'Paused',
  blocked: 'Blocked',
  retrying: 'Retrying',
  completed: 'Completed',
  canceled: 'Canceled',
  failed: 'Failed',
}

export function StatusBadge({ status }: { status: Status }) {
  return <span className={`status-badge status-${status}`}>{labelMap[status]}</span>
}
