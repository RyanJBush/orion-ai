import { useEffect, useState } from 'react'

import { KpiCard } from '../components/KpiCard'
import { PageHeader } from '../components/PageHeader'
import { fetchJSON } from '../services/api'

interface WorkflowMetricsSnapshot {
  total_runs: number
  completion_rate: number
  retry_rate: number
  avg_step_latency_ms: number
  run_status_counts: Record<string, number>
}

export function DashboardPage() {
  const [metrics, setMetrics] = useState<WorkflowMetricsSnapshot | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    fetchJSON<WorkflowMetricsSnapshot>('/workflows/metrics')
      .then((data) => {
        if (!active) return
        setMetrics(data)
      })
      .catch((loadError) => {
        if (!active) return
        setError(loadError instanceof Error ? loadError.message : 'Unable to load dashboard metrics')
      })
    return () => {
      active = false
    }
  }, [])

  const totalRuns = metrics?.total_runs ?? 0
  const running = metrics?.run_status_counts?.running ?? 0
  const completed = metrics?.run_status_counts?.completed ?? 0
  const completionRate = metrics ? `${Math.round(metrics.completion_rate * 100)}%` : '—'
  const avgLatency = metrics ? `${Math.round(metrics.avg_step_latency_ms)} ms` : '—'

  return (
    <section className="page">
      <PageHeader
        title="Dashboard"
        subtitle="Live visibility into task throughput, workflow health, and orchestration reliability."
      />

      <div className="kpi-grid">
        <KpiCard label="Total Runs" value={String(totalRuns)} />
        <KpiCard label="Running Workflows" value={String(running)} />
        <KpiCard label="Completed Runs" value={String(completed)} />
        <KpiCard label="Avg Step Latency" value={avgLatency} delta={`Completion ${completionRate}`} />
      </div>

      <div className="panel">
        <h3>Operational Summary</h3>
        {error ? <p className="error-text">{error}</p> : null}
        {!metrics ? <p className="muted">Collecting live orchestration telemetry…</p> : null}
        {metrics ? (
          <p>
            Orion has processed <strong>{metrics.total_runs}</strong> runs with a completion rate of{' '}
            <strong>{Math.round(metrics.completion_rate * 100)}%</strong> and retry rate of{' '}
            <strong>{Math.round(metrics.retry_rate * 100)}%</strong>.
          </p>
        ) : null}
      </div>
    </section>
  )
}
