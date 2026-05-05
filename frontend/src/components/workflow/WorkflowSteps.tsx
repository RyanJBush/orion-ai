import { useMemo, useState } from 'react'
import { StatusBadge } from '../StatusBadge'
import { WorkflowGraph } from './WorkflowGraph'
import type { ApiExecutionStep } from '../../services/api'

interface WorkflowStepsProps {
  steps: ApiExecutionStep[]
  selectedStepId: number | null
  onSelectStep: (stepId: number) => void
}

export function WorkflowSteps({ steps, selectedStepId, onSelectStep }: WorkflowStepsProps) {
  const [view, setView] = useState<'graph' | 'list'>('graph')
  const sorted = useMemo(() => [...steps].sort((a, b) => a.step_order - b.step_order), [steps])

  return (
    <div className="panel">
      <div className="panel-title-row">
        <h3>Workflow Graph</h3>
        <div className="view-toggle">
          <button
            type="button"
            className={`view-toggle-btn ${view === 'graph' ? 'active' : ''}`}
            onClick={() => setView('graph')}
          >
            Graph
          </button>
          <button
            type="button"
            className={`view-toggle-btn ${view === 'list' ? 'active' : ''}`}
            onClick={() => setView('list')}
          >
            List
          </button>
        </div>
      </div>

      {view === 'graph' ? (
        <>
          <p className="muted" style={{ marginBottom: '0.75rem' }}>
            Nodes = steps · Edges = dependencies · Click a node to inspect.
          </p>
          <div className="graph-scroll-wrapper">
            <WorkflowGraph steps={steps} selectedStepId={selectedStepId} onSelectStep={onSelectStep} />
          </div>
        </>
      ) : (
        <>
          <p className="muted" style={{ marginBottom: '0.75rem' }}>
            Sorted by execution order. Click a step to inspect its input/output.
          </p>
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
        </>
      )}
    </div>
  )
}
