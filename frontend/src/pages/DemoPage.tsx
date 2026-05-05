import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { PageHeader } from '../components/PageHeader'
import { StatusBadge } from '../components/StatusBadge'
import {
  listWorkflowTemplates,
  runWorkflowTemplate,
  seedDemoTemplates,
  seedDemoAgents,
  type ApiWorkflowTemplate,
  type ApiWorkflowRun,
} from '../services/api'

/** Tag pill colours mapped by tag name */
const TAG_COLORS: Record<string, string> = {
  demo: 'tag-demo',
  research: 'tag-research',
  analysis: 'tag-analysis',
  reporting: 'tag-reporting',
  reasoning: 'tag-reasoning',
  approval: 'tag-approval',
  resilience: 'tag-resilience',
  code: 'tag-code',
}

export function DemoPage() {
  const navigate = useNavigate()

  const [templates, setTemplates] = useState<ApiWorkflowTemplate[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [seeding, setSeeding] = useState(false)
  const [seedMsg, setSeedMsg] = useState<string | null>(null)
  const [runningId, setRunningId] = useState<number | null>(null)
  const [lastRun, setLastRun] = useState<ApiWorkflowRun | null>(null)

  const loadTemplates = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await listWorkflowTemplates()
      setTemplates(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load workflow templates.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadTemplates()
  }, [loadTemplates])

  const handleSeedAll = async () => {
    setSeeding(true)
    setSeedMsg(null)
    setError(null)
    try {
      await seedDemoAgents()
      const created = await seedDemoTemplates()
      setSeedMsg(
        created.length > 0
          ? `✓ Seeded ${created.length} demo template(s) and demo agents.`
          : '✓ Demo templates and agents already up-to-date.',
      )
      await loadTemplates()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Seed failed.')
    } finally {
      setSeeding(false)
    }
  }

  const handleRun = async (templateId: number) => {
    setRunningId(templateId)
    setError(null)
    setLastRun(null)
    try {
      const run = await runWorkflowTemplate(templateId)
      setLastRun(run)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start workflow.')
    } finally {
      setRunningId(null)
    }
  }

  const demoTemplates = templates.filter((t) => t.is_demo)
  const customTemplates = templates.filter((t) => !t.is_demo)

  return (
    <section className="page">
      <PageHeader
        title="Demo Scenarios"
        subtitle="Pre-built workflow templates you can run instantly to explore agent orchestration."
      />

      <div className="panel demo-seed-panel">
        <div className="demo-seed-row">
          <div>
            <h3>Quick Start</h3>
            <p className="muted">Seed all demo templates and agents with one click, then run any scenario below.</p>
          </div>
          <button type="button" onClick={handleSeedAll} disabled={seeding}>
            {seeding ? 'Seeding…' : '⚡ Seed Demo Data'}
          </button>
        </div>
        {seedMsg ? <p className="success-text">{seedMsg}</p> : null}
        {error ? <p className="error-text">{error}</p> : null}
      </div>

      {lastRun ? (
        <div className="panel demo-run-result">
          <div className="demo-run-result-header">
            <div>
              <h3>Workflow Started</h3>
              <p className="muted">
                Run #{lastRun.id} · {lastRun.workflow_name} · Trace: {lastRun.trace_id}
              </p>
            </div>
            <StatusBadge status={lastRun.status} />
          </div>
          <div className="demo-run-steps">
            {lastRun.steps.map((step) => (
              <div key={step.id} className="demo-step-chip">
                <span className="demo-step-id">{step.step_id}</span>
                <span className="demo-step-action">{step.action}</span>
                <StatusBadge status={step.status} />
              </div>
            ))}
          </div>
          <button
            type="button"
            className="btn-small"
            onClick={() => navigate(`/execution?run=${lastRun.id}`)}
          >
            View in Execution Inspector →
          </button>
        </div>
      ) : null}

      <TemplateSection
        title="Demo Workflows"
        subtitle="Pre-built scenarios covering research, analysis, resilience, and approval patterns."
        templates={demoTemplates}
        loading={loading}
        runningId={runningId}
        onRun={handleRun}
        emptyMessage={'No demo templates yet \u2014 click \u201cSeed Demo Data\u201d above.'}
      />

      {customTemplates.length > 0 ? (
        <TemplateSection
          title="Custom Workflows"
          subtitle="User-created workflow templates."
          templates={customTemplates}
          loading={false}
          runningId={runningId}
          onRun={handleRun}
          emptyMessage="No custom templates."
        />
      ) : null}
    </section>
  )
}

interface TemplateSectionProps {
  title: string
  subtitle: string
  templates: ApiWorkflowTemplate[]
  loading: boolean
  runningId: number | null
  onRun: (id: number) => void
  emptyMessage: string
}

function TemplateSection({ title, subtitle, templates, loading, runningId, onRun, emptyMessage }: TemplateSectionProps) {
  return (
    <div className="panel">
      <h3>{title}</h3>
      <p className="muted" style={{ marginBottom: '1rem' }}>{subtitle}</p>
      {loading ? (
        <p className="muted">Loading templates…</p>
      ) : templates.length === 0 ? (
        <p className="muted">{emptyMessage}</p>
      ) : (
        <div className="template-grid">
          {templates.map((template) => (
            <TemplateCard
              key={template.id}
              template={template}
              isRunning={runningId === template.id}
              onRun={() => onRun(template.id)}
            />
          ))}
        </div>
      )}
    </div>
  )
}

interface TemplateCardProps {
  template: ApiWorkflowTemplate
  isRunning: boolean
  onRun: () => void
}

function TemplateCard({ template, isRunning, onRun }: TemplateCardProps) {
  return (
    <article className="template-card">
      <div className="template-card-body">
        <h4>{template.task_title}</h4>
        <p className="muted">{template.description}</p>
        <p className="template-task-desc">{template.task_description}</p>
        <div className="template-tags">
          {template.tags.map((tag) => (
            <span key={tag} className={`tag-pill ${TAG_COLORS[tag] ?? 'tag-demo'}`}>
              {tag}
            </span>
          ))}
        </div>
      </div>
      <div className="template-card-footer">
        <span className="muted template-workflow-name">{template.workflow_name}</span>
        <button type="button" onClick={onRun} disabled={isRunning}>
          {isRunning ? 'Running…' : '▶ Run'}
        </button>
      </div>
    </article>
  )
}
