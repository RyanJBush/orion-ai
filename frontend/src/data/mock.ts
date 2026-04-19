import type { AgentHealth, TaskSummary, WorkflowRun } from '../types/workflow'

export const mockTasks: TaskSummary[] = [
  { id: 101, title: 'Quarterly KPI report', status: 'running', createdAt: '2026-04-19T08:30:00Z' },
  { id: 102, title: 'Outbound lead scoring', status: 'completed', createdAt: '2026-04-19T07:15:00Z' },
  { id: 103, title: 'Support ticket triage', status: 'queued', createdAt: '2026-04-19T09:05:00Z' },
]

export const mockRun: WorkflowRun = {
  id: 501,
  taskTitle: 'Quarterly KPI report',
  workflowName: 'default',
  status: 'running',
  startedAt: '2026-04-19T08:32:00Z',
  steps: [
    {
      id: 1,
      name: 'Collect source metrics',
      agent: 'worker-general',
      status: 'completed',
      startedAt: '2026-04-19T08:32:10Z',
      completedAt: '2026-04-19T08:33:02Z',
      log: 'Fetched CRM and billing counters from connectors.',
    },
    {
      id: 2,
      name: 'Compute growth deltas',
      agent: 'worker-math',
      status: 'running',
      startedAt: '2026-04-19T08:33:10Z',
      log: 'Calculating month-over-month and quarter-over-quarter growth.',
    },
    {
      id: 3,
      name: 'Draft executive summary',
      agent: 'worker-general',
      status: 'queued',
      startedAt: '2026-04-19T08:34:00Z',
      log: 'Waiting for previous step completion.',
    },
  ],
}

export const mockAgents: AgentHealth[] = [
  { id: 1, name: 'planner', role: 'planner', status: 'healthy', queueDepth: 2, successRate: 99.1 },
  { id: 2, name: 'worker-general', role: 'worker', status: 'healthy', queueDepth: 4, successRate: 97.4 },
  { id: 3, name: 'worker-math', role: 'worker', status: 'degraded', queueDepth: 6, successRate: 93.2 },
]
