import type { ExecutionStep } from '../../types/workflow'

export function ExecutionLogPanel({ steps }: { steps: ExecutionStep[] }) {
  return (
    <div className="panel">
      <h3>Execution Logs</h3>
      <div className="logs">
        {steps.map((step) => (
          <article key={step.id} className="log-item">
            <p>
              <strong>Step {step.id}:</strong> {step.log}
            </p>
            <small>
              {step.startedAt}
              {step.completedAt ? ` → ${step.completedAt}` : ''}
            </small>
          </article>
        ))}
      </div>
    </div>
  )
}
