import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api, Narrative, Theme } from '../api'

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="card">
      <h2 className="font-medium mb-3">{title}</h2>
      {children}
    </section>
  )
}

function EmptyText() {
  return <div className="text-sm text-slate-400">暂无数据</div>
}

export default function ThemeDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [theme, setTheme] = useState<Theme | null>(null)
  const [narratives, setNarratives] = useState<Narrative[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    setLoading(true)
    setError(null)
    api.getTheme(id)
      .then(async data => {
        setTheme(data)
        return api.listNarrativesByBatch(data.batch_id)
      })
      .then(setNarratives)
      .catch(e => setError(e.response?.data?.detail || e.message))
      .finally(() => setLoading(false))
  }, [id])

  if (loading) return <div className="text-slate-400">加载中...</div>
  if (error) return <div className="bg-rose-50 text-rose-700 p-3 rounded text-sm">{error}</div>
  if (!theme) return <div className="text-slate-400">未找到</div>

  const themeNarratives = narratives.filter(item => theme.article_ids.includes(item.article_id))

  return (
    <div className="space-y-4">
      <Link to="/themes" className="text-sm text-brand-600 hover:underline">返回融合主题</Link>

      <div className="card">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="text-xl font-semibold">{theme.theme_label}</h1>
            <div className="text-sm text-slate-500 mt-1">
              {theme.article_ids.length} 篇文章 · {theme.member_count} 个叙事来源 · {theme.companies.length} 个公司映射
            </div>
          </div>
          <div className="flex flex-wrap gap-1">
            {theme.sub_directions.map(direction => (
              <span key={direction} className="badge bg-brand-50 text-brand-700">{direction}</span>
            ))}
          </div>
        </div>
      </div>

      <Section title="多文共识">
        {theme.consensus ? <p className="text-sm text-slate-700 leading-6">{theme.consensus}</p> : <EmptyText />}
      </Section>

      <Section title="不同文章的切入角度">
        {Object.keys(theme.article_angles).length > 0 ? (
          <div className="space-y-2">
            {Object.entries(theme.article_angles).map(([articleId, angle]) => (
              <div key={articleId} className="border border-slate-100 rounded p-3">
                <div className="text-xs text-slate-400 mb-1">{articleId}</div>
                <div className="text-sm text-slate-700">{angle}</div>
              </div>
            ))}
          </div>
        ) : <EmptyText />}
      </Section>

      <Section title="综合逻辑链">
        {theme.combined_logic_chain ? (
          <p className="text-sm text-slate-700 leading-6 whitespace-pre-line">{theme.combined_logic_chain}</p>
        ) : <EmptyText />}
      </Section>

      <Section title="产业链映射">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
          <div>
            <div className="text-xs text-slate-500 mb-2">上游</div>
            {theme.upstream.length ? theme.upstream.map(item => (
              <span key={item} className="badge bg-slate-100 text-slate-700 mr-1 mb-1">{item}</span>
            )) : <EmptyText />}
          </div>
          <div>
            <div className="text-xs text-slate-500 mb-2">中游</div>
            {theme.midstream.length ? theme.midstream.map(item => (
              <span key={item} className="badge bg-slate-100 text-slate-700 mr-1 mb-1">{item}</span>
            )) : <EmptyText />}
          </div>
          <div>
            <div className="text-xs text-slate-500 mb-2">下游</div>
            {theme.downstream.length ? theme.downstream.map(item => (
              <span key={item} className="badge bg-slate-100 text-slate-700 mr-1 mb-1">{item}</span>
            )) : <EmptyText />}
          </div>
        </div>
      </Section>

      <Section title="公司映射">
        {theme.companies.length > 0 ? (
          <div className="divide-y divide-slate-100">
            {theme.companies.map((company, index) => (
              <div key={`${company.name}-${index}`} className="py-2 flex flex-wrap items-center justify-between gap-2 text-sm">
                <span className="font-medium text-slate-800">{company.name}</span>
                <span className="text-slate-500">{company.direction || '未标注方向'}</span>
                <span className="text-xs text-slate-400">{company.article_ids?.length || 0} 篇提及</span>
              </div>
            ))}
          </div>
        ) : <EmptyText />}
      </Section>

      <Section title="催化因素与差异视角">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div>
            <div className="text-xs text-slate-500 mb-2">催化因素</div>
            {theme.catalysts.length ? (
              <ul className="list-disc pl-5 space-y-1 text-slate-700">
                {theme.catalysts.map(item => <li key={item}>{item}</li>)}
              </ul>
            ) : <EmptyText />}
          </div>
          <div>
            <div className="text-xs text-slate-500 mb-2">需要保留的差异</div>
            {theme.divergence_points.length ? (
              <ul className="list-disc pl-5 space-y-1 text-slate-700">
                {theme.divergence_points.map(item => <li key={item}>{item}</li>)}
              </ul>
            ) : <EmptyText />}
          </div>
        </div>
      </Section>

      <Section title="相关单文叙事">
        {themeNarratives.length > 0 ? (
          <div className="space-y-3">
            {themeNarratives.map(item => (
              <div key={item.id} className="border border-slate-100 rounded p-3">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-medium text-sm text-slate-800">{item.angle || '未标注角度'}</span>
                  <span className="badge bg-slate-100 text-slate-700">{item.sentiment || '中性'}</span>
                  {item.time_window && <span className="text-xs text-slate-400">{item.time_window}</span>}
                </div>
                {item.logic_chains.length > 0 && (
                  <p className="mt-2 text-sm text-slate-600">{item.logic_chains[0]}</p>
                )}
              </div>
            ))}
          </div>
        ) : <EmptyText />}
      </Section>
    </div>
  )
}
