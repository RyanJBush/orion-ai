interface PageHeaderProps {
  title: string
  subtitle: string
}

export function PageHeader({ title, subtitle }: PageHeaderProps) {
  return (
    <header className="page-header">
      <h2>{title}</h2>
      <p className="muted">{subtitle}</p>
    </header>
  )
}
