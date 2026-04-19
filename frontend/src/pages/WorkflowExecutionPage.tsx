import { ExecutionLogPanel } from '../components/workflow/ExecutionLogPanel'
import { WorkflowSteps } from '../components/workflow/WorkflowSteps'
import { PageHeader } from '../components/PageHeader'
import { StatusBadge } from '../components/StatusBadge'
import { mockRun } from '../data/mock'

export function WorkflowExecutionPage() {
  return (
    <section className="page">
      <PageHeader
        title="Workflow Execution View"
        subtitle="Visualize step-by-step orchestration, assigned agents, and execution logs."
      />

      <div className="panel run-header">
        <div>
          <h3>Run #{mockRun.id}</h3>
          <p className="muted">
            Task: {mockRun.taskTitle} · Workflow: {mockRun.workflowName}
          </p>
        </div>
        <StatusBadge status={mockRun.status} />
      </div>

      <div className="two-column">
        <WorkflowSteps steps={mockRun.steps} />
        <ExecutionLogPanel steps={mockRun.steps} />
      </div>
    </section>
  )
}
