import { Card } from '../components/ui'

const agents = [
  { name: 'planner-1', role: 'planner', status: 'active' },
  { name: 'worker-1', role: 'worker', status: 'active' },
  { name: 'worker-2', role: 'worker', status: 'idle' },
]

export function AgentMonitorPage() {
  return (
    <Card title="Agent Monitor">
      <table className="w-full text-left text-sm">
        <thead className="text-slate-400">
          <tr>
            <th className="pb-2">Agent</th>
            <th className="pb-2">Role</th>
            <th className="pb-2">Status</th>
          </tr>
        </thead>
        <tbody>
          {agents.map((agent) => (
            <tr key={agent.name} className="border-t border-slate-800">
              <td className="py-2">{agent.name}</td>
              <td className="py-2">{agent.role}</td>
              <td className="py-2 capitalize">{agent.status}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  )
}
