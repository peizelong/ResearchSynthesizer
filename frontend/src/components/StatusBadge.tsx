interface StatusBadgeProps {
  status: string
}

const statusColor: Record<string, string> = {
  pending: 'bg-slate-100 text-slate-600',
  running: 'bg-amber-100 text-amber-700',
  extracting: 'bg-amber-100 text-amber-700',
  clustering: 'bg-amber-100 text-amber-700',
  extracted: 'bg-emerald-100 text-emerald-700',
  completed: 'bg-emerald-100 text-emerald-700',
  failed: 'bg-rose-100 text-rose-700',
}

export default function StatusBadge({ status }: StatusBadgeProps) {
  const cls = statusColor[status] || 'bg-slate-100 text-slate-600'
  return <span className={`badge ${cls}`}>{status}</span>
}
