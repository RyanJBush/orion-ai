import { useMemo } from 'react'
import { Card } from '../components/ui'

const tasks = [
  { id: 101, title: 'Analyze support backlog', status: 'running' },
  { id: 102, title: 'Generate onboarding sequence', status: 'completed' },
  { id: 103, title: 'Inspect model drift', status: 'pending' },
]

export function TasksPage() {
  const statuses = useMemo(() => {
    return tasks.reduce((acc, task) => ({ ...acc, [task.status]: (acc[task.status] || 0) + 1 }), {})
  }, [])

  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <Card title="Task Status Tracking">
        <ul className="space-y-2 text-sm text-slate-300">
          {Object.entries(statuses).map(([key, value]) => (
            <li key={key} className="flex justify-between rounded bg-slate-800 px-3 py-2">
              <span>{key}</span>
              <span>{value}</span>
            </li>
          ))}
        </ul>
      </Card>
      <Card title="Tasks">
        <ul className="space-y-3 text-sm">
          {tasks.map((task) => (
            <li key={task.id} className="rounded-md border border-slate-700 p-3">
              <p className="font-semibold">{task.title}</p>
              <p className="text-slate-400">
                #{task.id} · <span className="capitalize">{task.status}</span>
              </p>
            </li>
          ))}
        </ul>
      </Card>
      <Card title="Execution Logs">
        <pre className="overflow-x-auto rounded-md bg-slate-950 p-3 text-xs text-slate-300">
{`[planner-1] decomposed task #103
[worker-2] called summarize tool
[worker-1] stored vector memory snapshot`}
        </pre>
      </Card>
    </div>
  )
}
