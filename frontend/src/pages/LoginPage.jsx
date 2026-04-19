import { useState } from 'react'
import { Card } from '../components/ui'

export function LoginPage() {
  const [email, setEmail] = useState('operator@orion.ai')
  const [role, setRole] = useState('operator')
  const [status, setStatus] = useState('')

  const onSubmit = async (event) => {
    event.preventDefault()
    try {
      const response = await fetch('http://localhost:8000/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, role }),
      })
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || 'Login failed')
      localStorage.setItem('orion_token', data.access_token)
      setStatus('Authenticated. Token stored locally.')
    } catch (error) {
      setStatus(`Login unavailable (${error.message}) - backend likely not running.`)
    }
  }

  return (
    <Card title="Login">
      <form className="grid max-w-md gap-3" onSubmit={onSubmit}>
        <input
          className="rounded-md border border-slate-700 bg-slate-950 px-3 py-2"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          aria-label="Email"
        />
        <select
          className="rounded-md border border-slate-700 bg-slate-950 px-3 py-2"
          value={role}
          onChange={(event) => setRole(event.target.value)}
        >
          <option value="admin">admin</option>
          <option value="operator">operator</option>
          <option value="viewer">viewer</option>
        </select>
        <button className="rounded-md bg-indigo-600 px-3 py-2 font-medium hover:bg-indigo-500" type="submit">
          Sign in
        </button>
        <p className="text-sm text-slate-400">{status}</p>
      </form>
    </Card>
  )
}
