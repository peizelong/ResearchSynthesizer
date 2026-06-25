import { useEffect, useState } from 'react'
import { api, Batch } from '../api'
import StatusBadge from '../components/StatusBadge'

export default function BatchesPage() {
  const [batches, setBatches] = useState<Batch[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [name, setName] = useState('')
  const [creating, setCreating] = useState(false)
  const [runningId, setRunningId] = useState<string | null>(null)

  const load = async () => {
    setLoading(true)
    try {
      const data = await api.listBatches({ limit: 100 })
      setBatches(data)
    } catch (e: any) {
      setError(e.message || '加载失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const handleCreate = async () => {
    setCreating(true)
    setError(null)
    try {
      await api.createBatch({ name: name || undefined })
      setName('')
      await load()
    } catch (e: any) {
      setError(e.response?.data?.detail || e.message)
    } finally {
      setCreating(false)
    }
  }

  const handleRun = async (id: string) => {
    setRunningId(id)
    setError(null)
    try {
      await api.runBatch(id, { extract: true, cluster: true })
      await load()
    } catch (e: any) {
      setError(e.response?.data?.detail || e.message)
    } finally {
      setRunningId(null)
    }
  }

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">研究批次</h1>

      <div className="card flex flex-wrap items-end gap-3">
        <div className="flex-1 min-w-[200px]">
          <label className="block text-xs text-slate-500 mb-1">批次名称（可选）</label>
          <input
            type="text"
            value={name}
            onChange={e => setName(e.target.value)}
            placeholder="例如：本周半导体研究"
            className="w-full border border-slate-200 rounded px-2 py-1.5 text-sm"
          />
        </div>
        <button
          onClick={handleCreate}
          disabled={creating}
          className="btn-primary"
        >
          {creating ? '创建中...' : '创建批次（匹配全部文章）'}
        </button>
      </div>

      {error && <div className="bg-rose-50 text-rose-700 p-3 rounded text-sm">{error}</div>}

      <div className="card overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-50 text-slate-500">
            <tr>
              <th className="text-left py-2 px-3 font-medium">名称</th>
              <th className="text-left py-2 px-3 font-medium">文章数</th>
              <th className="text-left py-2 px-3 font-medium">状态</th>
              <th className="text-left py-2 px-3 font-medium">阶段</th>
              <th className="text-left py-2 px-3 font-medium">创建时间</th>
              <th className="text-left py-2 px-3 font-medium">操作</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {batches.map(b => (
              <tr key={b.id} className="hover:bg-slate-50">
                <td className="py-2 px-3">{b.name || <span className="text-slate-400">未命名</span>}</td>
                <td className="py-2 px-3 text-slate-600">{b.article_ids.length}</td>
                <td className="py-2 px-3"><StatusBadge status={b.status} /></td>
                <td className="py-2 px-3 text-slate-500 text-xs">{b.current_stage || '-'}</td>
                <td className="py-2 px-3 text-slate-500 text-xs">
                  {new Date(b.created_at).toLocaleString('zh-CN')}
                </td>
                <td className="py-2 px-3">
                  <button
                    onClick={() => handleRun(b.id)}
                    disabled={runningId === b.id || b.status === 'running'}
                    className="text-brand-600 hover:underline text-xs disabled:text-slate-400"
                  >
                    {runningId === b.id ? '运行中...' : '运行'}
                  </button>
                </td>
              </tr>
            ))}
            {!loading && batches.length === 0 && (
              <tr>
                <td colSpan={6} className="text-center py-8 text-slate-400">暂无批次</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
