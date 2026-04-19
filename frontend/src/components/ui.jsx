export function Card({ title, children }) {
  return (
    <section className="rounded-xl border border-slate-800 bg-slate-900 p-4 shadow-lg shadow-slate-950/40">
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-400">{title}</h2>
      {children}
    </section>
  )
}
