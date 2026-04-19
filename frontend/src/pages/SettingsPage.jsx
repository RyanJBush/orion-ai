import { Card } from '../components/ui'

export function SettingsPage() {
  return (
    <Card title="Settings">
      <div className="space-y-2 text-sm text-slate-300">
        <p>Environment: local</p>
        <p>Auth mode: JWT + RBAC</p>
        <p>Memory store: FAISS vector index + SQL records</p>
      </div>
    </Card>
  )
}
