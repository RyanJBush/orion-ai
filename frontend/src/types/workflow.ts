export type Status =
  | 'pending'
  | 'queued'
  | 'planning'
  | 'running'
  | 'paused'
  | 'blocked'
  | 'retrying'
  | 'completed'
  | 'canceled'
  | 'failed'

export interface ExecutionStep {
  id: number
  name: string
  agent: string
  status: Status
  startedAt: string
  completedAt?: string
  log: string
}

export interface WorkflowRun {
  id: number
  taskTitle: string
  workflowName: string
  status: Status
  startedAt: string
  steps: ExecutionStep[]
}

export interface TaskSummary {
  id: number
  title: string
  status: Status
  createdAt: string
}

export interface AgentHealth {
  id: number
  name: string
  role: string
  status: 'healthy' | 'degraded' | 'offline'
  queueDepth: number
  successRate: number
}
