import { useEffect, useState } from 'react'
import { api, ArticleListItem } from '../api'
import StatusBadge from '../components/StatusBadge'

export default function ArticlesPage() {
  const [articles, setArticles] = useState<ArticleListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [crawlBusy, setCrawlBusy] = useState(false)
  const [crawlMsg, setCrawlMsg] = useState<string | null>(null)

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await api.listArticles({ limit: 100 })
      setArticles(data)
    } catch (e: any) {
      setError(e.message || '加载失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const handleCrawl = async () => {
    setCrawlBusy(true)
    setCrawlMsg(null)
    try {
      const res = await api.crawl({ source: 'jiuyan_web', pages: 2, fetch_details: true })
      setCrawlMsg(`已触发: ${res.status || 'ok'}`)
      setTimeout(load, 1500)
    } catch (e: any) {
      setCrawlMsg(`失败: ${e.response?.data?.detail || e.message}`)
    } finally {
      setCrawlBusy(false)
    }
  }

  const handleExtract = async (id: string) => {
    try {
      await api.extractArticle(id)
      await load()
    } catch (e: any) {
      setError(`抽取失败: ${e.response?.data?.detail || e.message}`)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">文章</h1>
        <div className="flex items-center gap-2">
          {crawlMsg && <span className="text-sm text-slate-500">{crawlMsg}</span>}
          <button
            onClick={handleCrawl}
            disabled={crawlBusy}
            className="btn-secondary"
          >
            {crawlBusy ? '爬取中...' : '触发爬取'}
          </button>
          <button onClick={load} className="btn-primary">刷新</button>
        </div>
      </div>

      {error && <div className="bg-rose-50 text-rose-700 p-3 rounded text-sm">{error}</div>}

      <div className="card overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-50 text-slate-500">
            <tr>
              <th className="text-left py-2 px-3 font-medium">标题</th>
              <th className="text-left py-2 px-3 font-medium">来源</th>
              <th className="text-left py-2 px-3 font-medium">信任</th>
              <th className="text-left py-2 px-3 font-medium">抽取状态</th>
              <th className="text-left py-2 px-3 font-medium">发布时间</th>
              <th className="text-left py-2 px-3 font-medium">操作</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {articles.map(a => (
              <tr key={a.id} className="hover:bg-slate-50">
                <td className="py-2 px-3 max-w-md truncate">{a.title}</td>
                <td className="py-2 px-3 text-slate-500">{a.source}</td>
                <td className="py-2 px-3">
                  <span className="badge bg-slate-100 text-slate-700">{a.trust_level}</span>
                </td>
                <td className="py-2 px-3"><StatusBadge status={a.extraction_status} /></td>
                <td className="py-2 px-3 text-slate-500 text-xs">
                  {a.published_at ? new Date(a.published_at).toLocaleString('zh-CN') : '-'}
                </td>
                <td className="py-2 px-3">
                  {a.extraction_status !== 'extracted' && (
                    <button
                      onClick={() => handleExtract(a.id)}
                      className="text-brand-600 hover:underline text-xs"
                    >
                      抽取
                    </button>
                  )}
                </td>
              </tr>
            ))}
            {!loading && articles.length === 0 && (
              <tr>
                <td colSpan={6} className="text-center py-8 text-slate-400">暂无文章</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
