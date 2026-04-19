import { Card } from '../components/ui'

const graph = [
  { from: 'Planner', to: 'Worker A' },
  { from: 'Planner', to: 'Worker B' },
  { from: 'Worker A', to: 'Memory' },
  { from: 'Worker B', to: 'Memory' },
]

export function WorkflowViewPage() {
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card title="Workflow Visualization">
        <div className="space-y-3 text-sm">
          {graph.map((edge, idx) => (
            <div key={`${edge.from}-${edge.to}-${idx}`} className="rounded-md bg-slate-800 px-3 py-2">
              <span className="font-semibold text-indigo-300">{edge.from}</span> → {edge.to}
            </div>
          ))}
        </div>
      </Card>
      <Card title="Execution Timeline">
        <ol className="list-decimal space-y-2 pl-4 text-sm text-slate-300">
          <li>Planner generated 3-step plan</li>
          <li>Worker agents executed tool abstraction layer</li>
          <li>FAISS memory updated and workflow marked completed</li>
        </ol>
      </Card>
    </div>
  )
}
