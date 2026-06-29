import axios from 'axios'

const client = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

export interface ArticleListItem {
  id: string
  source: string
  title: string
  author: string | null
  published_at: string | null
  trust_level: string
  extraction_status: string
  created_at: string
}

export interface ArticleDetail extends ArticleListItem {
  source_article_id: string | null
  url: string
  content: string
  summary: string | null
  crawled_at: string
}

export interface Batch {
  id: string
  name: string | null
  description: string | null
  article_ids: string[]
  source_filter: string[] | null
  date_from: string | null
  date_to: string | null
  status: string
  current_stage: string | null
  error_message: string | null
  config: Record<string, unknown> | null
  created_at: string
  started_at: string | null
  finished_at: string | null
}

export interface CrawlStatus {
  source: string
  status: string
  is_running: boolean
  started_at: string | null
  finished_at: string | null
  last_error: string | null
  last_result: Record<string, unknown> | null
  mode: string | null
  pages: number | null
  sections: string[] | null
  sorts: string[] | null
  fetch_details: boolean | null
  logs: string[]
}

export interface RunBatchResult {
  status: string
  batch_id: string
  narratives_count: number
  merged_themes_count: number
  report: string
  errors: string[]
}

export interface RadarConfig {
  interval_seconds?: number
  window_hours?: number
  article_limit?: number
  crawl_enabled?: boolean
  crawl_pages?: number
  crawl_sections?: string[]
  crawl_sorts?: string[]
  fetch_details?: boolean
}

export interface RadarStatus {
  status: string
  auto_running: boolean
  refresh_running: boolean
  current_stage: string
  started_at: string | null
  stopped_at: string | null
  last_run_started_at: string | null
  last_run_finished_at: string | null
  last_error: string | null
  last_batch_id: string | null
  last_result: Record<string, unknown> | null
  config: Required<RadarConfig>
  logs: string[]
}

export interface RadarLatest extends RadarStatus {
  batch: Batch | null
  themes: Theme[]
  report: string
}

export interface CompanyMapping {
  name: string
  direction?: string
  article_ids?: string[]
}

export interface Theme {
  id: string
  batch_id: string
  theme_label: string
  sub_directions: string[]
  article_ids: string[]
  article_angles: Record<string, string>
  consensus: string | null
  combined_logic_chain: string | null
  upstream: string[]
  midstream: string[]
  downstream: string[]
  companies: CompanyMapping[]
  divergence_points: string[]
  catalysts: string[]
  member_count: number
  created_at: string
  updated_at: string | null
}

export interface Narrative {
  id: string
  article_id: string
  main_themes: string[]
  background: string | null
  catalysts: string[]
  industry_segments: string[]
  companies: string[]
  logic_chains: string[]
  angle: string | null
  sentiment: string | null
  time_window: string | null
  extractor_model: string | null
  extracted_at: string
}

export interface Overview {
  articles: number
  narratives: number
  batches: number
  merged_themes: number
}

export const api = {
  listArticles: (params?: { source?: string; limit?: number; offset?: number }) =>
    client.get<ArticleListItem[]>('/articles', { params }).then(r => r.data),
  getArticle: (id: string) =>
    client.get<ArticleDetail>(`/articles/${id}`).then(r => r.data),
  crawl: (body: { source?: string; pages?: number; fetch_details?: boolean }) =>
    client.post('/articles/crawl', body).then(r => r.data),
  crawlStatus: (source = 'jiuyan_web') =>
    client.get<CrawlStatus>('/articles/crawl/status', { params: { source } }).then(r => r.data),
  extractArticle: (id: string) =>
    client.post(`/articles/${id}/extract`).then(r => r.data),

  createBatch: (body: {
    name?: string
    description?: string
    article_ids?: string[]
    source_filter?: string[]
    date_from?: string
    date_to?: string
  }) => client.post<Batch>('/research/batches', body).then(r => r.data),
  listBatches: (params?: { limit?: number; offset?: number }) =>
    client.get<Batch[]>('/research/batches', { params }).then(r => r.data),
  getBatch: (id: string) =>
    client.get<Batch>(`/research/batches/${id}`).then(r => r.data),
  runBatch: (id: string) =>
    client.post<RunBatchResult>(`/research/batches/${id}/run`).then(r => r.data),

  listThemes: (params?: { batch_id?: string; limit?: number; offset?: number }) =>
    client.get<Theme[]>('/themes', { params }).then(r => r.data),
  getTheme: (id: string) =>
    client.get<Theme>(`/themes/${id}`).then(r => r.data),
  listNarrativesByBatch: (batchId: string) =>
    client.get<Narrative[]>(`/themes/batch/${batchId}/narratives`).then(r => r.data),

  overview: () => client.get<Overview>('/monitor/overview').then(r => r.data),

  radarStatus: () => client.get<RadarStatus>('/radar/status').then(r => r.data),
  radarLatest: () => client.get<RadarLatest>('/radar/latest').then(r => r.data),
  radarStart: (body?: RadarConfig) =>
    client.post<RadarStatus>('/radar/start', body || {}).then(r => r.data),
  radarStop: () =>
    client.post<RadarStatus>('/radar/stop').then(r => r.data),
  radarRefresh: (body?: RadarConfig) =>
    client.post<RadarStatus>('/radar/refresh', body || {}).then(r => r.data),
}

export default api
