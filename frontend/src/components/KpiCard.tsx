interface KpiCardProps {
  label: string
  value: string
  delta?: string
}

export function KpiCard({ label, value, delta }: KpiCardProps) {
  return (
    <article className="kpi-card">
      <p className="kpi-label">{label}</p>
      <h3>{value}</h3>
      {delta ? <p className="kpi-delta">{delta}</p> : null}
    </article>
  )
}
