import { Navigate, Route, Routes } from 'react-router-dom'

import { AppLayout } from './layout/AppLayout'
import { AgentMonitorPage } from './pages/AgentMonitorPage'
import { DashboardPage } from './pages/DashboardPage'
import { SettingsPage } from './pages/SettingsPage'
import { TasksPage } from './pages/TasksPage'
import { WorkflowExecutionPage } from './pages/WorkflowExecutionPage'

export function App() {
  return (
    <AppLayout>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/tasks" element={<TasksPage />} />
        <Route path="/execution" element={<WorkflowExecutionPage />} />
        <Route path="/agents" element={<AgentMonitorPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AppLayout>
  )
}
