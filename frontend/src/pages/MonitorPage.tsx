import { useEffect, useState } from 'react'
import { api, Overview } from '../api'

export default function MonitorPage() {
  const [overview, setOverview] = useState<Overview | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const load = () => {
      api.overview()
        .then(setOverview)
        .catch(e => setError(e.response?.data?.detail || e.message))
    }
    load()
    const timer = setInterval(load, 10000)
    return () => clearInterval(timer)
  }, [])

  if (error) return <div className="bg-rose-50 text-rose-700 p-3 rounded text-sm">{error}</div>
  if (!overview) return <div className="text-slate-400">加载中...</div>

  const cards = [
    { label: '文章', value: overview.articles, color: 'text-brand-700' },
    { label: '单文叙事', value: overview.narratives, color: 'text-emerald-700' },
    { label: '研究批次', value: overview.batches, color: 'text-amber-700' },
    { label: '融合主题', value: overview.merged_themes, color: 'text-violet-700' },
  ]

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">监控总览</h1>
        <span className="text-xs text-slate-400">每 10 秒自动刷新</span>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {cards.map(c => (
          <div key={c.label} className="card text-center">
            <div className={`text-3xl font-bold ${c.color}`}>{c.value}</div>
            <div className="text-sm text-slate-500 mt-1">{c.label}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
