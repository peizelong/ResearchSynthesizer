interface StatusBadgeProps {
  status: string
}

const statusColor: Record<string, string> = {
  pending: 'bg-slate-100 text-slate-600',
  running: 'bg-amber-100 text-amber-700',
  extracting: 'bg-amber-100 text-amber-700',
  extracted: 'bg-emerald-100 text-emerald-700',
  completed: 'bg-emerald-100 text-emerald-700',
  failed: 'bg-rose-100 text-rose-700',
}

const statusLabel: Record<string, string> = {
  pending: '待抽取',
  running: '运行中',
  extracting: '抽取中',
  extracted: '已抽取',
  completed: '已完成',
  failed: '失败',
}

export default function StatusBadge({ status }: StatusBadgeProps) {
  const cls = statusColor[status] || 'bg-slate-100 text-slate-600'
  return <span className={`badge ${cls}`}>{statusLabel[status] || status}</span>
}
