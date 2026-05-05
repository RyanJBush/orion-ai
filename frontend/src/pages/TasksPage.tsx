import { type FormEvent, useCallback, useEffect, useMemo, useState } from 'react'

import { PageHeader } from '../components/PageHeader'
import { StatusBadge } from '../components/StatusBadge'
import { listTasks, submitTask, type ApiTask, type ApiWorkflowRun } from '../services/api'

export function TasksPage() {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [workflowName, setWorkflowName] = useState('default')
  const [submitting, setSubmitting] = useState(false)
  const [submitResult, setSubmitResult] = useState<ApiWorkflowRun | null>(null)
  const [submitError, setSubmitError] = useState<string | null>(null)

  const [tasks, setTasks] = useState<ApiTask[]>([])
  const [tasksLoading, setTasksLoading] = useState(false)
  const [tasksError, setTasksError] = useState<string | null>(null)

  const canSubmit = useMemo(() => title.trim().length >= 3, [title])

  const loadTasks = useCallback(async () => {
    setTasksLoading(true)
    setTasksError(null)
    try {
      const data = await listTasks()
      setTasks(data)
    } catch (err) {
      setTasksError(err instanceof Error ? err.message : 'Unable to load tasks.')
    } finally {
      setTasksLoading(false)
    }
  }, [])

  useEffect(() => {
    loadTasks()
  }, [loadTasks])

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!canSubmit) return

    setSubmitting(true)
    setSubmitError(null)
    setSubmitResult(null)
    try {
      const run = await submitTask({ title: title.trim(), description: description.trim() || undefined, workflow_name: workflowName })
      setSubmitResult(run)
      setTitle('')
      setDescription('')
      await loadTasks()
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : 'Submission failed.')
    } finally {
      setSubmitting(false)
    }
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
        <button type="submit" disabled={!canSubmit || submitting}>
          {submitting ? 'Submitting…' : 'Submit Task'}
        </button>
        {submitError ? <p className="error-text">{submitError}</p> : null}
        {submitResult ? (
          <p className="success-text">
            Task submitted — Run #{submitResult.id} created with status{' '}
            <strong>{submitResult.status}</strong> ({submitResult.steps.length} steps).
          </p>
        ) : null}
      </form>

      <div className="panel">
        <div className="panel-title-row">
          <h3>Recent Tasks</h3>
          <button type="button" className="btn-small" onClick={loadTasks} disabled={tasksLoading}>
            {tasksLoading ? 'Refreshing…' : 'Refresh'}
          </button>
        </div>
        {tasksError ? <p className="error-text">{tasksError}</p> : null}
        {tasks.length === 0 && !tasksLoading ? (
          <p className="muted">No tasks yet. Submit one above.</p>
        ) : (
          <ul className="task-list">
            {tasks.map((task) => (
              <li key={task.id}>
                <div>
                  <strong>{task.title}</strong>
                  <p className="muted">Task #{task.id}{task.description ? ` · ${task.description.slice(0, 60)}` : ''}</p>
                </div>
                <StatusBadge status={task.status} />
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  )
}
