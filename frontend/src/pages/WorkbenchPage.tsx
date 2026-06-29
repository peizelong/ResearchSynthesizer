import { useEffect, useMemo, useState } from 'react'
import { api, RadarConfig, RadarLatest } from '../api'

const statusLabel: Record<string, string> = {
  stopped: '已停止',
  running: '自动运行中',
  refreshing: '刷新中',
  stopping: '停止中',
  failed: '异常',
}

const stageLabel: Record<string, string> = {
  idle: '空闲',
  starting: '启动中',
  waiting: '等待下次刷新',
  queued: '等待执行',
  crawl: '采集文章',
  build_window: '构建观察窗口',
  fusion: '叙事融合',
  failed: '异常',
  stopping: '停止中',
}

function formatTime(value: string | null | undefined) {
  if (!value) return '-'
  return new Date(value).toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function numberValue(value: unknown) {
  return typeof value === 'number' ? value : 0
}

function StatusPill({ status }: { status: string }) {
  const cls = status === 'running'
    ? 'bg-emerald-50 text-emerald-700'
    : status === 'failed'
      ? 'bg-rose-50 text-rose-700'
      : 'bg-slate-100 text-slate-600'
  return <span className={`rounded px-2 py-1 text-xs font-medium ${cls}`}>{statusLabel[status] || status}</span>
}

function Metric({
  label,
  value,
  hint,
}: {
  label: string
  value: string | number
  hint: string
}) {
  return (
    <div className="border-r border-slate-100 px-5 py-4 last:border-r-0">
      <div className="text-xs text-slate-500">{label}</div>
      <div className="mt-2 text-2xl font-semibold text-slate-950">{value}</div>
      <div className="mt-1 text-xs text-slate-400">{hint}</div>
    </div>
  )
}

function EmptyState({ title, description }: { title: string; description: string }) {
  return (
    <div className="rounded-lg border border-dashed border-slate-200 bg-slate-50 px-4 py-10 text-center">
      <div className="font-medium text-slate-800">{title}</div>
      <div className="mx-auto mt-2 max-w-sm text-sm leading-6 text-slate-500">{description}</div>
    </div>
  )
}

export default function WorkbenchPage() {
  const [latest, setLatest] = useState<RadarLatest | null>(null)
  const [selectedThemeId, setSelectedThemeId] = useState('')
  const [config, setConfig] = useState<RadarConfig>({
    interval_seconds: 900,
    window_hours: 24,
    article_limit: 120,
    crawl_enabled: true,
    crawl_pages: 1,
    fetch_details: true,
  })
  const [busy, setBusy] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const load = async () => {
    try {
      const data = await api.radarLatest()
      setLatest(data)
      setConfig(current => ({ ...current, ...data.config }))
    } catch (e: any) {
      setError(e.response?.data?.detail || e.message || '加载雷达状态失败')
    }
  }

  useEffect(() => {
    load()
    const timer = window.setInterval(load, 5000)
    return () => window.clearInterval(timer)
  }, [])

  const themes = latest?.themes || []
  useEffect(() => {
    setSelectedThemeId(current => {
      if (themes.some(theme => theme.id === current)) return current
      return themes[0]?.id || ''
    })
  }, [themes])

  const activeTheme = useMemo(() => {
    return themes.find(theme => theme.id === selectedThemeId) || themes[0] || null
  }, [themes, selectedThemeId])

  const runAction = async (kind: 'start' | 'stop' | 'refresh') => {
    setBusy(kind)
    setError(null)
    try {
      if (kind === 'start') await api.radarStart(config)
      if (kind === 'stop') await api.radarStop()
      if (kind === 'refresh') await api.radarRefresh(config)
      await load()
    } catch (e: any) {
      setError(e.response?.data?.detail || e.message || '操作失败')
    } finally {
      setBusy(null)
    }
  }

  const exportReport = () => {
    if (!latest?.report) return
    const blob = new Blob([latest.report], { type: 'text/markdown;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${latest.batch?.name || 'radar-report'}.md`
    link.click()
    URL.revokeObjectURL(url)
  }

  const result = latest?.last_result || {}
  const status = latest?.status || 'stopped'
  const isRunning = Boolean(latest?.auto_running || latest?.refresh_running)

  return (
    <div className="mx-auto max-w-[1680px] space-y-4">
      <section className="rounded-lg border border-slate-200 bg-white px-4 py-4 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex flex-wrap items-center gap-3">
              <h1 className="text-xl font-semibold text-slate-950">自动投研叙事雷达</h1>
              <StatusPill status={status} />
            </div>
            <p className="mt-2 text-sm text-slate-500">
              系统持续采集文章、自动抽取单文叙事、滚动融合主题，并刷新研究报告。
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button onClick={() => runAction('refresh')} disabled={busy === 'refresh' || isRunning} className="btn-secondary">
              {busy === 'refresh' ? '刷新中...' : '立即刷新一次'}
            </button>
            {latest?.auto_running ? (
              <button onClick={() => runAction('stop')} disabled={busy === 'stop'} className="btn-secondary">
                {busy === 'stop' ? '停止中...' : '停止自动流'}
              </button>
            ) : (
              <button onClick={() => runAction('start')} disabled={busy === 'start'} className="btn-primary">
                {busy === 'start' ? '启动中...' : '启动自动流'}
              </button>
            )}
          </div>
        </div>

        {error && <div className="mt-4 rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</div>}
        {latest?.last_error && <div className="mt-4 rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">{latest.last_error}</div>}
      </section>

      <section className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
        <div className="grid grid-cols-1 divide-y divide-slate-100 md:grid-cols-4 md:divide-x md:divide-y-0">
          <Metric
            label="持续采集"
            value={numberValue(result.crawled)}
            hint={`新增 ${numberValue(result.saved)} 篇 · ${config.crawl_enabled ? '采集开启' : '仅用存量'}`}
          />
          <Metric
            label="滚动窗口"
            value={numberValue(result.articles_in_window)}
            hint={`近 ${config.window_hours} 小时 · 最多 ${config.article_limit} 篇`}
          />
          <Metric
            label="融合方向"
            value={themes.length}
            hint={`批次 ${latest?.last_batch_id ? latest.last_batch_id.slice(0, 8) : '-'}`}
          />
          <Metric
            label="报告刷新"
            value={latest?.report ? `${latest.report.length} 字` : '-'}
            hint={`上次完成 ${formatTime(latest?.last_run_finished_at)}`}
          />
        </div>
      </section>

      <section className="rounded-lg border border-slate-200 bg-white shadow-sm">
        <div className="grid grid-cols-1 gap-3 border-b border-slate-100 px-4 py-4 lg:grid-cols-[180px_180px_180px_1fr]">
          <div>
            <label className="text-xs text-slate-500">观察窗口</label>
            <select
              value={config.window_hours}
              onChange={event => setConfig({ ...config, window_hours: Number(event.target.value) })}
              className="mt-1 w-full rounded-md border border-slate-200 px-2 py-2 text-sm"
            >
              <option value={24}>近 24 小时</option>
              <option value={72}>近 3 日</option>
              <option value={168}>近 7 日</option>
            </select>
          </div>
          <div>
            <label className="text-xs text-slate-500">文章上限</label>
            <input
              type="number"
              min={1}
              max={500}
              value={config.article_limit}
              onChange={event => setConfig({ ...config, article_limit: Number(event.target.value) })}
              className="mt-1 w-full rounded-md border border-slate-200 px-2 py-2 text-sm"
            />
          </div>
          <div>
            <label className="text-xs text-slate-500">刷新间隔</label>
            <select
              value={config.interval_seconds}
              onChange={event => setConfig({ ...config, interval_seconds: Number(event.target.value) })}
              className="mt-1 w-full rounded-md border border-slate-200 px-2 py-2 text-sm"
            >
              <option value={300}>5 分钟</option>
              <option value={900}>15 分钟</option>
              <option value={1800}>30 分钟</option>
              <option value={3600}>1 小时</option>
            </select>
          </div>
          <div className="flex items-end gap-4 text-sm text-slate-600">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={Boolean(config.crawl_enabled)}
                onChange={event => setConfig({ ...config, crawl_enabled: event.target.checked })}
                className="h-4 w-4 rounded border-slate-300 text-brand-600"
              />
              自动采集新文章
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={Boolean(config.fetch_details)}
                onChange={event => setConfig({ ...config, fetch_details: event.target.checked })}
                className="h-4 w-4 rounded border-slate-300 text-brand-600"
              />
              抓取详情正文
            </label>
          </div>
        </div>
      </section>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[360px_minmax(0,1fr)_420px]">
        <section className="rounded-lg border border-slate-200 bg-white shadow-sm">
          <div className="border-b border-slate-100 px-4 py-3">
            <h2 className="font-semibold text-slate-950">当前融合方向</h2>
            <p className="mt-1 text-xs text-slate-500">由滚动窗口内多篇文章自动聚合得出。</p>
          </div>
          <div className="max-h-[680px] overflow-auto p-2">
            {themes.length ? themes.map(theme => (
              <button
                key={theme.id}
                onClick={() => setSelectedThemeId(theme.id)}
                className={`w-full rounded-md px-3 py-3 text-left transition-colors ${
                  activeTheme?.id === theme.id ? 'bg-brand-50 text-brand-800' : 'hover:bg-slate-50'
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="font-medium leading-5">{theme.theme_label}</div>
                  <span className="badge bg-slate-100 text-slate-600">{theme.member_count}</span>
                </div>
                <div className="mt-2 flex flex-wrap gap-1">
                  {theme.sub_directions.slice(0, 3).map(direction => (
                    <span key={direction} className="badge bg-white text-slate-600 ring-1 ring-slate-200">{direction}</span>
                  ))}
                </div>
              </button>
            )) : (
              <EmptyState
                title="还没有融合方向"
                description="启动自动流或立即刷新一次后，系统会把滚动窗口内文章自动融合成主题方向。"
              />
            )}
          </div>
        </section>

        <section className="rounded-lg border border-slate-200 bg-white shadow-sm">
          <div className="border-b border-slate-100 px-4 py-3">
            <h2 className="font-semibold text-slate-950">方向详情</h2>
            <p className="mt-1 text-xs text-slate-500">看共同叙事、新增视角、逻辑链和产业链位置。</p>
          </div>
          <div className="space-y-5 p-4">
            {activeTheme ? (
              <>
                <div>
                  <h3 className="text-lg font-semibold text-slate-950">{activeTheme.theme_label}</h3>
                  <div className="mt-2 flex flex-wrap gap-1">
                    {activeTheme.sub_directions.map(direction => (
                      <span key={direction} className="badge bg-brand-50 text-brand-700">{direction}</span>
                    ))}
                  </div>
                </div>

                <div>
                  <div className="mb-2 text-sm font-medium text-slate-900">多文共识</div>
                  <p className="text-sm leading-6 text-slate-700">{activeTheme.consensus || '暂无共识摘要'}</p>
                </div>

                <div>
                  <div className="mb-2 text-sm font-medium text-slate-900">综合逻辑链</div>
                  <p className="whitespace-pre-line rounded-md bg-slate-50 p-3 text-sm leading-6 text-slate-700">
                    {activeTheme.combined_logic_chain || '暂无逻辑链'}
                  </p>
                </div>

                <div>
                  <div className="mb-2 text-sm font-medium text-slate-900">产业链映射</div>
                  <div className="grid grid-cols-1 gap-2 md:grid-cols-3">
                    <div className="rounded-md border border-slate-200 p-3">
                      <div className="text-xs font-medium text-brand-700">上游</div>
                      <div className="mt-2 text-sm leading-6 text-slate-600">{activeTheme.upstream.join('、') || '暂无'}</div>
                    </div>
                    <div className="rounded-md border border-slate-200 p-3">
                      <div className="text-xs font-medium text-brand-700">中游</div>
                      <div className="mt-2 text-sm leading-6 text-slate-600">{activeTheme.midstream.join('、') || '暂无'}</div>
                    </div>
                    <div className="rounded-md border border-slate-200 p-3">
                      <div className="text-xs font-medium text-brand-700">下游</div>
                      <div className="mt-2 text-sm leading-6 text-slate-600">{activeTheme.downstream.join('、') || '暂无'}</div>
                    </div>
                  </div>
                </div>

                <div>
                  <div className="mb-2 text-sm font-medium text-slate-900">反复出现公司</div>
                  <div className="flex flex-wrap gap-1">
                    {activeTheme.companies.length ? activeTheme.companies.map((company, index) => (
                      <span key={`${company.name}-${index}`} className="badge bg-slate-100 text-slate-700">
                        {company.name}{company.direction ? ` · ${company.direction}` : ''}
                      </span>
                    )) : <span className="text-sm text-slate-400">暂无公司映射</span>}
                  </div>
                </div>

                <div>
                  <div className="mb-2 text-sm font-medium text-slate-900">差异视角</div>
                  {activeTheme.divergence_points.length ? (
                    <ul className="list-disc space-y-1 pl-5 text-sm leading-6 text-slate-700">
                      {activeTheme.divergence_points.map(point => <li key={point}>{point}</li>)}
                    </ul>
                  ) : <div className="text-sm text-slate-400">暂无明显差异视角</div>}
                </div>
              </>
            ) : (
              <EmptyState
                title="等待自动融合"
                description="这里不会展示文章正文，只展示系统从多篇文章里融合出的方向、逻辑链和映射。"
              />
            )}
          </div>
        </section>

        <aside className="space-y-4">
          <section className="rounded-lg border border-slate-200 bg-white shadow-sm">
            <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
              <div>
                <h2 className="font-semibold text-slate-950">最新报告</h2>
                <p className="mt-1 text-xs text-slate-500">{latest?.batch?.name || '等待生成'}</p>
              </div>
              <button onClick={exportReport} disabled={!latest?.report} className="btn-secondary">导出</button>
            </div>
            <div className="p-4">
              {latest?.report ? (
                <pre className="max-h-[420px] overflow-auto whitespace-pre-wrap rounded-md bg-slate-50 p-3 text-xs leading-6 text-slate-700">
                  {latest.report}
                </pre>
              ) : (
                <EmptyState
                  title="报告未生成"
                  description="自动流完成一次融合后，这里会展示最新 Markdown 报告。"
                />
              )}
            </div>
          </section>

          <section className="rounded-lg border border-slate-200 bg-white shadow-sm">
            <div className="border-b border-slate-100 px-4 py-3">
              <h2 className="font-semibold text-slate-950">流水线状态</h2>
              <p className="mt-1 text-xs text-slate-500">
                当前阶段：{stageLabel[latest?.current_stage || 'idle'] || latest?.current_stage || '-'}
              </p>
            </div>
            <div className="max-h-[300px] overflow-auto p-3">
              {latest?.logs.length ? latest.logs.slice(-12).reverse().map(log => (
                <div key={log} className="border-b border-slate-100 py-2 text-xs leading-5 text-slate-600 last:border-b-0">
                  {log}
                </div>
              )) : <div className="py-6 text-center text-sm text-slate-400">暂无运行日志</div>}
            </div>
          </section>
        </aside>
      </div>
    </div>
  )
}
