import { type FormEvent, useMemo, useState } from 'react'

import { PageHeader } from '../components/PageHeader'
import { StatusBadge } from '../components/StatusBadge'
import { mockTasks } from '../data/mock'

export function TasksPage() {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [workflowName, setWorkflowName] = useState('default')
  const [submitted, setSubmitted] = useState<string | null>(null)

  const canSubmit = useMemo(() => title.trim().length >= 3, [title])

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!canSubmit) return

    setSubmitted(`Submitted "${title}" to workflow "${workflowName}".`)
    setTitle('')
    setDescription('')
  }

  return (
    <section className="page">
      <PageHeader title="Tasks" subtitle="Submit new work and monitor task states." />

      <form className="panel form-grid" onSubmit={onSubmit}>
        <h3>Submit Task</h3>
        <label>
          Task Title
          <input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Quarterly KPI report" />
        </label>
        <label>
          Description
          <textarea
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            placeholder="Collect metrics. Compute growth deltas. Draft summary."
            rows={3}
          />
        </label>
        <label>
          Workflow
          <select value={workflowName} onChange={(event) => setWorkflowName(event.target.value)}>
            <option value="default">default</option>
            <option value="research">research</option>
            <option value="ops">ops</option>
          </select>
        </label>
        <button type="submit" disabled={!canSubmit}>
          Submit Task
        </button>
        {submitted ? <p className="success-text">{submitted}</p> : null}
      </form>

      <div className="panel">
        <h3>Recent Tasks</h3>
        <ul className="task-list">
          {mockTasks.map((task) => (
            <li key={task.id}>
              <div>
                <strong>{task.title}</strong>
                <p className="muted">Task #{task.id}</p>
              </div>
              <StatusBadge status={task.status} />
            </li>
          ))}
        </ul>
      </div>
    </section>
  )
}
