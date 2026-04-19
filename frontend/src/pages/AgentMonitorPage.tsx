import { PageHeader } from '../components/PageHeader'
import { mockAgents } from '../data/mock'

export function AgentMonitorPage() {
  return (
    <section className="page">
      <PageHeader title="Agent Monitor" subtitle="Track capacity, health, and execution quality across agents." />

      <div className="panel">
        <h3>Agent Health</h3>
        <table className="agent-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Role</th>
              <th>Status</th>
              <th>Queue Depth</th>
              <th>Success Rate</th>
            </tr>
          </thead>
          <tbody>
            {mockAgents.map((agent) => (
              <tr key={agent.id}>
                <td>{agent.name}</td>
                <td>{agent.role}</td>
                <td>
                  <span className={`health-pill health-${agent.status}`}>{agent.status}</span>
                </td>
                <td>{agent.queueDepth}</td>
                <td>{agent.successRate.toFixed(1)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
