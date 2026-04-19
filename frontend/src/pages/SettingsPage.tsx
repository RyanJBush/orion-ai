import { PageHeader } from '../components/PageHeader'

export function SettingsPage() {
  return (
    <section className="page">
      <PageHeader title="Settings" subtitle="Configure runtime defaults, alerting, and environment targets." />

      <div className="panel form-grid">
        <h3>Execution Defaults</h3>
        <label>
          API Base URL
          <input defaultValue="http://localhost:8000/api/v1" />
        </label>
        <label>
          Default Workflow
          <select defaultValue="default">
            <option value="default">default</option>
            <option value="research">research</option>
            <option value="ops">ops</option>
          </select>
        </label>
        <label>
          Enable Verbose Logs
          <select defaultValue="true">
            <option value="true">true</option>
            <option value="false">false</option>
          </select>
        </label>
        <button type="button">Save Settings</button>
      </div>
    </section>
  )
}
