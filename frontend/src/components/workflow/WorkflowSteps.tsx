import { StatusBadge } from '../StatusBadge'
import type { ExecutionStep } from '../../types/workflow'

export function WorkflowSteps({ steps }: { steps: ExecutionStep[] }) {
  return (
    <div className="panel">
      <h3>Workflow Steps</h3>
      <ul className="step-list">
        {steps.map((step) => (
          <li key={step.id} className="step-item">
            <div>
              <strong>{step.name}</strong>
              <p className="muted">Agent: {step.agent}</p>
            </div>
            <StatusBadge status={step.status} />
          </li>
        ))}
      </ul>
    </div>
  )
}
