import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, Cluster } from '../api'

export default function ClustersPage() {
  const [clusters, setClusters] = useState<Cluster[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [batchId, setBatchId] = useState('')

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await api.listClusters({
        batch_id: batchId || undefined,
        limit: 100,
      })
      setClusters(data)
    } catch (e: any) {
      setError(e.message || '加载失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [batchId])

  const angleColors: Record<string, string> = {
    policy: 'bg-violet-100 text-violet-700',
    industry: 'bg-blue-100 text-blue-700',
    company: 'bg-amber-100 text-amber-700',
    tech: 'bg-emerald-100 text-emerald-700',
    macro: 'bg-rose-100 text-rose-700',
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">聚类</h1>
        <button onClick={load} className="btn-primary">刷新</button>
      </div>

      <div className="card flex items-center gap-3">
        <label className="text-sm text-slate-500">按批次筛选：</label>
        <input
          type="text"
          value={batchId}
          onChange={e => setBatchId(e.target.value)}
          placeholder="批次 ID"
          className="border border-slate-200 rounded px-2 py-1.5 text-sm flex-1 max-w-xs"
        />
      </div>

      {error && <div className="bg-rose-50 text-rose-700 p-3 rounded text-sm">{error}</div>}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {clusters.map(c => (
          <Link
            key={c.id}
            to={`/clusters/${c.id}`}
            className="card hover:shadow-md transition-shadow block"
          >
            <div className="flex items-start justify-between mb-2">
              <h3 className="font-medium text-slate-800">{c.cluster_label}</h3>
              <span className="badge bg-brand-50 text-brand-700">{c.member_count}</span>
            </div>
            <div className="text-xs text-slate-500 mb-3">
              {c.article_count} 篇文章 · {c.cluster_method}
            </div>
            {c.angle_distribution && (
              <div className="flex flex-wrap gap-1">
                {Object.entries(c.angle_distribution).map(([angle, count]) => (
                  <span
                    key={angle}
                    className={`badge ${angleColors[angle] || 'bg-slate-100 text-slate-700'}`}
                  >
                    {angle} · {count}
                  </span>
                ))}
              </div>
            )}
          </Link>
        ))}
        {!loading && clusters.length === 0 && (
          <div className="col-span-full text-center py-12 text-slate-400">暂无聚类</div>
        )}
      </div>
    </div>
  )
}
