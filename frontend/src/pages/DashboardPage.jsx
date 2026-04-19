import { Card } from '../components/ui'

const kpis = [
  { label: 'Active Workflows', value: '4' },
  { label: 'Pending Tasks', value: '12' },
  { label: 'Healthy Agents', value: '8' },
]

export function DashboardPage() {
  return (
    <div className="grid gap-4 md:grid-cols-3">
      {kpis.map((kpi) => (
        <Card key={kpi.label} title={kpi.label}>
          <p className="text-3xl font-bold text-indigo-300">{kpi.value}</p>
        </Card>
      ))}
    </div>
  )
}
