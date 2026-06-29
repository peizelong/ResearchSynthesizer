import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, Theme } from '../api'

export default function ThemesPage() {
  const [themes, setThemes] = useState<Theme[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [batchId, setBatchId] = useState('')

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await api.listThemes({
        batch_id: batchId || undefined,
        limit: 100,
      })
      setThemes(data)
    } catch (e: any) {
      setError(e.response?.data?.detail || e.message || '加载失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [batchId])

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">融合主题</h1>
        <button onClick={load} className="btn-primary">刷新</button>
      </div>

      <div className="card flex items-center gap-3">
        <label className="text-sm text-slate-500">按批次筛选</label>
        <input
          type="text"
          value={batchId}
          onChange={e => setBatchId(e.target.value)}
          placeholder="批次 ID"
          className="border border-slate-200 rounded px-2 py-1.5 text-sm flex-1 max-w-xs"
        />
      </div>

      {error && <div className="bg-rose-50 text-rose-700 p-3 rounded text-sm">{error}</div>}

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {themes.map(theme => (
          <Link
            key={theme.id}
            to={`/themes/${theme.id}`}
            className="card hover:shadow-md transition-shadow block"
          >
            <div className="flex items-start justify-between gap-3">
              <h3 className="font-medium text-slate-800 leading-snug">{theme.theme_label}</h3>
              <span className="badge bg-brand-50 text-brand-700 shrink-0">{theme.member_count}</span>
            </div>

            <div className="text-xs text-slate-500 mt-2">
              {theme.article_ids.length} 篇文章 · {theme.companies.length} 个公司映射
            </div>

            {theme.consensus && (
              <p className="mt-3 text-sm text-slate-600 line-clamp-3">{theme.consensus}</p>
            )}

            {theme.sub_directions.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-1">
                {theme.sub_directions.slice(0, 5).map(direction => (
                  <span key={direction} className="badge bg-slate-100 text-slate-700">
                    {direction}
                  </span>
                ))}
              </div>
            )}

            {theme.catalysts.length > 0 && (
              <div className="mt-3 text-xs text-slate-500">
                催化：{theme.catalysts.slice(0, 3).join('、')}
              </div>
            )}
          </Link>
        ))}
        {!loading && themes.length === 0 && (
          <div className="col-span-full text-center py-12 text-slate-400">暂无融合主题</div>
        )}
      </div>
    </div>
  )
}
