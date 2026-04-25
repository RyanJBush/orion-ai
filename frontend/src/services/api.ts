import type { Status } from '../types/workflow'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1'

export async function fetchJSON<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })

  if (!response.ok) {
    throw new Error(`API error ${response.status}`)
  }

  return (await response.json()) as T
}

export interface ApiExecutionStep {
  id: number
  step_id: string
  step_order: number
  worker_name: string
  action: string
  input_text: string
  dependencies: string[]
  output_text: string
  status: Status
  attempt_count: number
  latency_ms: number | null
  fallback_action: string | null
}

export interface ApiWorkflowRun {
  id: number
  workflow_name: string
  task_id: number
  trace_id: string
  status: Status
  pause_requested: boolean
  cancel_requested: boolean
  created_at?: string
  steps: ApiExecutionStep[]
}

export interface ApiTimelineEvent {
  id: number
  run_id: number
  step_id: number | null
  event_type: string
  message: string
  metadata?: Record<string, unknown>
  event_metadata?: Record<string, unknown>
  created_at: string
}

export interface ApiRunMetrics {
  run_id: number
  trace_id: string
  total_steps: number
  completed_steps: number
  failed_steps: number
  retried_steps: number
  fallback_steps: number
  avg_step_latency_ms: number
}

export interface ApiRunInsight {
  run_id: number
  trace_id: string
  summary: string
  plan_explanation: string
  quality_score: number
  reflection: string
  suggested_actions: string[]
}

export function getWorkflowRun(runId: number) {
  return fetchJSON<ApiWorkflowRun>(`/workflows/runs/${runId}`)
}

export function getWorkflowTimeline(runId: number) {
  return fetchJSON<ApiTimelineEvent[]>(`/workflows/runs/${runId}/timeline`)
}

export function getWorkflowRunMetrics(runId: number) {
  return fetchJSON<ApiRunMetrics>(`/workflows/runs/${runId}/metrics`)
}

export function getWorkflowRunInsights(runId: number) {
  return fetchJSON<ApiRunInsight>(`/workflows/runs/${runId}/insights`)
}

export function pauseRun(runId: number) {
  return fetchJSON(`/workflows/runs/${runId}/pause`, { method: 'POST' })
}

export function resumeRun(runId: number) {
  return fetchJSON(`/workflows/runs/${runId}/resume`, { method: 'POST' })
}

export function cancelRun(runId: number) {
  return fetchJSON(`/workflows/runs/${runId}/cancel`, { method: 'POST' })
}

export function replayRun(runId: number, fromStepId?: string) {
  return fetchJSON<ApiWorkflowRun>(`/workflows/runs/${runId}/replay`, {
    method: 'POST',
    body: JSON.stringify({ from_step_id: fromStepId || null }),
  })
}
