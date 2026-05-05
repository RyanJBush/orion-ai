import { NavLink } from 'react-router-dom'
import type { PropsWithChildren } from 'react'

const navItems = [
  { href: '/', label: 'Dashboard' },
  { href: '/tasks', label: 'Tasks' },
  { href: '/execution', label: 'Workflow Execution' },
  { href: '/agents', label: 'Agent Monitor' },
  { href: '/demo', label: '⚡ Demo Scenarios' },
  { href: '/settings', label: 'Settings' },
]

export function AppLayout({ children }: PropsWithChildren) {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div>
          <p className="sidebar-eyebrow">Orion AI</p>
          <h1>Workflow Control</h1>
        </div>
        <nav>
          {navItems.map((item) => (
            <NavLink key={item.href} to={item.href} className="nav-link">
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="content">{children}</main>
    </div>
  )
}
