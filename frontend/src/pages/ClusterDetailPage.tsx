import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api, ClusterDetail } from '../api'

export default function ClusterDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [cluster, setCluster] = useState<ClusterDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    setLoading(true)
    api.getCluster(id)
      .then(setCluster)
      .catch(e => setError(e.response?.data?.detail || e.message))
      .finally(() => setLoading(false))
  }, [id])

  if (loading) return <div className="text-slate-400">加载中...</div>
  if (error) return <div className="bg-rose-50 text-rose-700 p-3 rounded text-sm">{error}</div>
  if (!cluster) return <div className="text-slate-400">未找到</div>

  const angleColors: Record<string, string> = {
    policy: 'bg-violet-100 text-violet-700',
    industry: 'bg-blue-100 text-blue-700',
    company: 'bg-amber-100 text-amber-700',
    tech: 'bg-emerald-100 text-emerald-700',
    macro: 'bg-rose-100 text-rose-700',
  }

  return (
    <div className="space-y-4">
      <Link to="/clusters" className="text-sm text-brand-600 hover:underline">← 返回聚类列表</Link>

      <div className="card">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-xl font-semibold">{cluster.cluster_label}</h1>
            <div className="text-sm text-slate-500 mt-1">
              {cluster.member_count} 条论断 · {cluster.article_count} 篇文章 · 方法: {cluster.cluster_method}
            </div>
          </div>
          <div className="text-right">
            {cluster.coherence_score !== null && (
              <div className="text-sm">
                <span className="text-slate-500">一致性：</span>
                <span className="font-medium">{(cluster.coherence_score * 100).toFixed(0)}%</span>
              </div>
            )}
          </div>
        </div>

        {cluster.cluster_summary && (
          <p className="mt-3 text-sm text-slate-600">{cluster.cluster_summary}</p>
        )}

        <div className="mt-4 grid grid-cols-2 gap-4 text-sm">
          <div>
            <div className="text-xs text-slate-500 mb-1">角度分布</div>
            <div className="flex flex-wrap gap-1">
              {cluster.angle_distribution &&
                Object.entries(cluster.angle_distribution).map(([angle, count]) => (
                  <span key={angle} className={`badge ${angleColors[angle] || 'bg-slate-100 text-slate-700'}`}>
                    {angle} · {count}
                  </span>
                ))}
            </div>
          </div>
          <div>
            <div className="text-xs text-slate-500 mb-1">来源分布</div>
            <div className="flex flex-wrap gap-1">
              {cluster.source_distribution &&
                Object.entries(cluster.source_distribution).map(([src, count]) => (
                  <span key={src} className="badge bg-slate-100 text-slate-700">
                    {src} · {count}
                  </span>
                ))}
            </div>
          </div>
        </div>
      </div>

      <div className="card">
        <h2 className="font-medium mb-3">论断列表</h2>
        <div className="space-y-3">
          {cluster.claims.map(c => (
            <div key={c.id} className="border border-slate-100 rounded p-3">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="text-sm">
                    <span className="font-medium">{c.subject}</span>
                    <span className="text-slate-400 mx-1">→</span>
                    <span>{c.predicate}</span>
                    {c.object_value && <span className="text-slate-500">: {c.object_value}</span>}
                  </div>
                  <div className="mt-1 flex items-center gap-2">
                    <span className={`badge ${angleColors[c.direction_angle || ''] || 'bg-slate-100 text-slate-700'}`}>
                      {c.direction_angle || 'unknown'}
                    </span>
                    <span className="badge bg-slate-100 text-slate-700">{c.claim_type}</span>
                    <span className="text-xs text-slate-500">
                      置信度: {(c.confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                  <p className="mt-2 text-xs text-slate-600 italic border-l-2 border-slate-200 pl-2">
                    "{c.evidence_text}"
                  </p>
                </div>
                {cluster.representative_claim_id === c.id && (
                  <span className="badge bg-amber-100 text-amber-700">代表</span>
                )}
              </div>
            </div>
          ))}
          {cluster.claims.length === 0 && (
            <div className="text-center py-6 text-slate-400 text-sm">暂无论断</div>
          )}
        </div>
      </div>
    </div>
  )
}
