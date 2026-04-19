import type { Status } from '../types/workflow'

const labelMap: Record<Status, string> = {
  queued: 'Queued',
  running: 'Running',
  completed: 'Completed',
  failed: 'Failed',
}

export function StatusBadge({ status }: { status: Status }) {
  return <span className={`status-badge status-${status}`}>{labelMap[status]}</span>
}
