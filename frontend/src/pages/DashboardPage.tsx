import { KpiCard } from '../components/KpiCard'
import { PageHeader } from '../components/PageHeader'
import { StatusBadge } from '../components/StatusBadge'
import { mockRun, mockTasks } from '../data/mock'

export function DashboardPage() {
  const running = mockTasks.filter((task) => task.status === 'running').length
  const completed = mockTasks.filter((task) => task.status === 'completed').length

  return (
    <section className="page">
      <PageHeader
        title="Dashboard"
        subtitle="Live visibility into task throughput, workflow health, and agent operations."
      />

      <div className="kpi-grid">
        <KpiCard label="Tasks Today" value="37" delta="+14% vs yesterday" />
        <KpiCard label="Running Workflows" value={String(running)} />
        <KpiCard label="Completed Tasks" value={String(completed)} />
        <KpiCard label="Avg Completion" value="3m 28s" delta="-22s this week" />
      </div>

      <div className="panel">
        <h3>Current Focus</h3>
        <p>
          Workflow <strong>#{mockRun.id}</strong> for <strong>{mockRun.taskTitle}</strong> is currently{' '}
          <StatusBadge status={mockRun.status} />.
        </p>
      </div>
    </section>
  )
}
