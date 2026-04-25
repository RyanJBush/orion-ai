import type { ApiTimelineEvent } from '../../services/api'

interface ExecutionLogPanelProps {
  events: ApiTimelineEvent[]
}

function getMetadata(event: ApiTimelineEvent): Record<string, unknown> {
  return event.metadata ?? event.event_metadata ?? {}
}

export function ExecutionLogPanel({ events }: ExecutionLogPanelProps) {
  return (
    <div className="panel">
      <h3>Execution Timeline</h3>
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
