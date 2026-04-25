import { StatusBadge } from '../StatusBadge'
import type { ApiExecutionStep } from '../../services/api'

interface WorkflowStepsProps {
  steps: ApiExecutionStep[]
}

export function WorkflowSteps({ steps }: WorkflowStepsProps) {
  return (
    <div className="panel">
      <h3>Workflow Graph</h3>
      <p className="muted">Dependency-aware step view with execution status and retry signals.</p>
      <ul className="step-list">
        {[...steps]
          .sort((a, b) => a.step_order - b.step_order)
          .map((step) => (
            <li key={step.id} className="step-item step-item-graph">
              <div>
                <strong>
                  {step.step_id} · {step.action}
                </strong>
                <p className="muted">Agent: {step.worker_name}</p>
                <p className="muted">Depends on: {step.dependencies.length ? step.dependencies.join(', ') : 'none'}</p>
                <p className="muted">
                  Attempts: {step.attempt_count} · Latency: {step.latency_ms ?? '—'}ms
                </p>
              </div>
              <StatusBadge status={step.status} />
            </li>
          ))}
      </ul>
    </div>
  )
}
