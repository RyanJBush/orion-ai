import { useMemo } from 'react'
import { StatusBadge } from '../StatusBadge'
import type { ApiExecutionStep } from '../../services/api'

interface WorkflowStepsProps {
  steps: ApiExecutionStep[]
  selectedStepId: number | null
  onSelectStep: (stepId: number) => void
}

export function WorkflowSteps({ steps, selectedStepId, onSelectStep }: WorkflowStepsProps) {
  const sorted = useMemo(() => [...steps].sort((a, b) => a.step_order - b.step_order), [steps])

  return (
    <div className="panel">
      <h3>Workflow Graph</h3>
      <p className="muted">Nodes are execution steps, arrows represent dependencies.</p>
      <ul className="step-list">
        {sorted.map((step) => (
          <li key={step.id} className={`step-item step-item-graph ${selectedStepId === step.id ? 'selected' : ''}`}>
            <button type="button" className="step-select" onClick={() => onSelectStep(step.id)}>
              <div>
                <strong>{step.step_id} · {step.action}</strong>
                <p className="muted">Agent: {step.worker_name}</p>
                <p className="muted">Depends on: {step.dependencies.length ? step.dependencies.join(' → ') : 'start'}</p>
              </div>
              <StatusBadge status={step.status} />
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}
