import type { ApiExecutionStep, ApiTimelineEvent } from '../../services/api'

interface ExecutionLogPanelProps {
  events: ApiTimelineEvent[]
  selectedStep: ApiExecutionStep | null
}

function getMetadata(event: ApiTimelineEvent): Record<string, unknown> {
  return event.metadata ?? event.event_metadata ?? {}
}

export function ExecutionLogPanel({ events, selectedStep }: ExecutionLogPanelProps) {
  return (
    <div className="panel">
      <h3>Execution Timeline</h3>
      {selectedStep ? (
        <div className="panel nested-panel">
          <h4>Step Detail · {selectedStep.step_id}</h4>
          <p><strong>Input:</strong> {selectedStep.input_text}</p>
          <p><strong>Output:</strong> {selectedStep.output_text || '—'}</p>
          <p className="muted">Agent: {selectedStep.worker_name} · Attempts: {selectedStep.attempt_count}</p>
        </div>
      ) : null}
      <div className="logs">
        {events.map((event) => {
          const metadata = getMetadata(event)
          const metaPreview = Object.keys(metadata).length ? JSON.stringify(metadata) : null
          return (
            <article key={event.id} className="log-item">
              <p>
                <strong>{event.event_type}</strong> · {event.message}
              </p>
              {metaPreview ? <p className="muted">{metaPreview}</p> : null}
              <small>{new Date(event.created_at).toLocaleString()}</small>
            </article>
          )
        })}
      </div>
    </div>
  )
}
