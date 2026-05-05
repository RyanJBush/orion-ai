import { useCallback, useEffect, useState } from 'react'

import { PageHeader } from '../components/PageHeader'
import { listAgentStats, seedDemoAgents, getToolHealth, type ApiAgentStat, type ApiToolHealth } from '../services/api'

export function AgentMonitorPage() {
  const [agents, setAgents] = useState<ApiAgentStat[]>([])
  const [toolHealth, setToolHealth] = useState<ApiToolHealth[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [seeding, setSeeding] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [agentData, toolData] = await Promise.all([listAgentStats(), getToolHealth()])
      setAgents(agentData)
      setToolHealth(toolData)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load agent data.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const handleSeed = async () => {
    setSeeding(true)
    try {
      await seedDemoAgents()
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Seed failed.')
    } finally {
      setSeeding(false)
    }
  }

  return (
    <section className="page">
      <PageHeader title="Agent Monitor" subtitle="Track capacity, health, and execution quality across agents." />

      <div className="panel">
        <div className="panel-title-row">
          <h3>Agent Health</h3>
          <div className="control-row">
            <button type="button" className="btn-small" onClick={load} disabled={loading}>
              {loading ? 'Loading…' : 'Refresh'}
            </button>
            <button type="button" className="btn-small btn-outline" onClick={handleSeed} disabled={seeding}>
              {seeding ? 'Seeding…' : 'Seed Demo Agents'}
            </button>
          </div>
        </div>
        {error ? <p className="error-text">{error}</p> : null}
        {agents.length === 0 && !loading ? (
          <p className="muted">No agents registered. Click "Seed Demo Agents" to initialise the canonical agent set.</p>
        ) : (
          <table className="agent-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Role</th>
                <th>Model</th>
                <th>Status</th>
                <th>Allowed Tools</th>
              </tr>
            </thead>
            <tbody>
              {agents.map((agent) => (
                <tr key={agent.id}>
                  <td><strong>{agent.name}</strong></td>
                  <td>{agent.role}</td>
                  <td className="muted">{agent.model}</td>
                  <td>
                    <span className={`health-pill health-${agent.status}`}>{agent.status}</span>
                  </td>
                  <td className="muted">{agent.allowed_tools.join(', ') || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="panel">
        <h3>Tool Health</h3>
        {toolHealth.length === 0 && !loading ? (
          <p className="muted">No tool health data.</p>
        ) : (
          <table className="agent-table">
            <thead>
              <tr>
                <th>Tool</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {toolHealth.map((tool) => (
                <tr key={tool.tool}>
                  <td><strong>{tool.tool}</strong></td>
                  <td>
                    <span className={`health-pill health-${tool.healthy ? 'healthy' : 'degraded'}`}>
                      {tool.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </section>
  )
}
