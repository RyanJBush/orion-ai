import { useCallback, useMemo, useState } from 'react'

import { ExecutionLogPanel } from '../components/workflow/ExecutionLogPanel'
import { WorkflowSteps } from '../components/workflow/WorkflowSteps'
import { PageHeader } from '../components/PageHeader'
import { StatusBadge } from '../components/StatusBadge'
import {
  cancelRun,
  getWorkflowRun,
  getWorkflowRunInsights,
  getWorkflowRunMetrics,
  getWorkflowTimeline,
  pauseRun,
  replayRun,
  resumeRun,
  type ApiRunInsight,
  type ApiRunMetrics,
  type ApiTimelineEvent,
  type ApiWorkflowRun,
} from '../services/api'

export function WorkflowExecutionPage() {
  const [runIdInput, setRunIdInput] = useState('1')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [run, setRun] = useState<ApiWorkflowRun | null>(null)
  const [timeline, setTimeline] = useState<ApiTimelineEvent[]>([])
  const [metrics, setMetrics] = useState<ApiRunMetrics | null>(null)
  const [insight, setInsight] = useState<ApiRunInsight | null>(null)
  const [selectedStepId, setSelectedStepId] = useState<number | null>(null)

  const runId = useMemo(() => Number.parseInt(runIdInput, 10), [runIdInput])

  const refreshRun = useCallback(async () => {
    if (Number.isNaN(runId) || runId <= 0) {
      setError('Enter a valid run ID (positive integer).')
      return
    }

    setLoading(true)
    setError(null)
    try {
      const [runData, timelineData, metricsData, insightData] = await Promise.all([
        getWorkflowRun(runId),
        getWorkflowTimeline(runId),
        getWorkflowRunMetrics(runId),
        getWorkflowRunInsights(runId),
      ])
      setRun(runData)
      setTimeline(timelineData)
      setMetrics(metricsData)
      setInsight(insightData)
      setSelectedStepId(runData.steps[0]?.id ?? null)
      setSelectedStepId((prev) => prev ?? runData.steps[0]?.id ?? null)
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Unable to load workflow run.')
    } finally {
      setLoading(false)
    }
  }, [runId])

  const runAction = useCallback(
    async (action: 'pause' | 'resume' | 'cancel' | 'replay') => {
      if (!run) return
      setLoading(true)
      setError(null)
      try {
        if (action === 'pause') await pauseRun(run.id)
        if (action === 'resume') await resumeRun(run.id)
        if (action === 'cancel') await cancelRun(run.id)
        if (action === 'replay') {
          const replayed = await replayRun(run.id)
          setRunIdInput(String(replayed.id))
        }
      } catch (actionError) {
        setError(actionError instanceof Error ? actionError.message : `Unable to ${action} run.`)
      } finally {
        setLoading(false)
      }
      await refreshRun()
    },
    [refreshRun, run],
  )

  return (
    <section className="page">
      <PageHeader
        title="Workflow Execution View"
        subtitle="Inspect run graph, control execution, and review timeline-level telemetry."
      />

      <div className="panel form-grid">
        <h3>Run Inspector</h3>
        <label>
          Run ID
          <input value={runIdInput} onChange={(event) => setRunIdInput(event.target.value)} placeholder="e.g. 12" />
        </label>
        <div className="control-row">
          <button type="button" onClick={refreshRun} disabled={loading}>
            {loading ? 'Loading…' : 'Load Run'}
          </button>
          <button type="button" onClick={() => runAction('pause')} disabled={!run || loading}>
            Pause
          </button>
          <button type="button" onClick={() => runAction('resume')} disabled={!run || loading}>
            Resume
          </button>
          <button type="button" onClick={() => runAction('cancel')} disabled={!run || loading}>
            Cancel
          </button>
          <button type="button" onClick={() => runAction('replay')} disabled={!run || loading}>
            Replay
          </button>
        </div>
        {error ? <p className="error-text">{error}</p> : null}
      </div>

      {run ? (
        <>
          <div className="panel run-header">
            <div>
              <h3>Run #{run.id}</h3>
              <p className="muted">
                Task #{run.task_id} · Workflow: {run.workflow_name} · Trace: {run.trace_id}
              </p>
            </div>
            <StatusBadge status={run.status} />
          </div>

          <div className="kpi-grid">
            <div className="kpi-card">
              <p className="kpi-label">Total Steps</p>
              <h2>{metrics?.total_steps ?? run.steps.length}</h2>
            </div>
            <div className="kpi-card">
              <p className="kpi-label">Completed</p>
              <h2>{metrics?.completed_steps ?? 0}</h2>
            </div>
            <div className="kpi-card">
              <p className="kpi-label">Failed</p>
              <h2>{metrics?.failed_steps ?? 0}</h2>
            </div>
            <div className="kpi-card">
              <p className="kpi-label">Avg Step Latency</p>
              <h2>{metrics ? `${Math.round(metrics.avg_step_latency_ms)} ms` : '—'}</h2>
            </div>
          </div>

          {insight ? (
            <div className="panel insight-panel">
              <h3>Execution Insight</h3>
              <p>{insight.summary}</p>
              <p className="muted">{insight.plan_explanation}</p>
              <p>
                <strong>Reflection:</strong> {insight.reflection}
              </p>
              <ul className="muted">
                {insight.suggested_actions.map((tip) => (
                  <li key={tip}>{tip}</li>
                ))}
              </ul>
            </div>
          ) : null}

          <div className="two-column">
            <WorkflowSteps steps={run.steps} selectedStepId={selectedStepId} onSelectStep={setSelectedStepId} />
            <ExecutionLogPanel events={timeline} selectedStep={run.steps.find((step) => step.id === selectedStepId) ?? null} />
          </div>
        </>
      ) : (
        <div className="panel">
          <p className="muted">Load a run ID to inspect graph, metrics, and event timeline.</p>
        </div>
      )}
    </section>
  )
}
