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

export interface Cluster {
  id: string
  batch_id: string
  cluster_label: string
  cluster_summary: string | null
  representative_claim_id: string | null
  member_count: number
  article_count: number
  angle_distribution: Record<string, number> | null
  source_distribution: Record<string, number> | null
  cluster_method: string
  coherence_score: number | null
  created_at: string
}

export interface Claim {
  id: string
  article_id: string
  claim_type: string
  subject: string
  predicate: string
  object_value: string | null
  direction_tag: string | null
  direction_angle: string | null
  evidence_text: string
  confidence: number
  extractor_model: string | null
  extracted_at: string
  topic_cluster_id: string | null
  created_at: string
}

export interface ClusterDetail extends Cluster {
  claims: Claim[]
}

export interface Overview {
  articles: number
  claims: number
  batches: number
  clusters: number
}

export const api = {
  listArticles: (params?: { source?: string; limit?: number; offset?: number }) =>
    client.get<ArticleListItem[]>('/articles', { params }).then(r => r.data),
  getArticle: (id: string) =>
    client.get<ArticleDetail>(`/articles/${id}`).then(r => r.data),
  crawl: (body: { source?: string; pages?: number; fetch_details?: boolean }) =>
    client.post('/articles/crawl', body).then(r => r.data),
  crawlStatus: (source = 'jiuyan_web') =>
    client.get('/articles/crawl/status', { params: { source } }).then(r => r.data),
  extractArticle: (id: string) =>
    client.post(`/articles/${id}/extract`).then(r => r.data),

  createBatch: (body: {
    name?: string
    description?: string
    source_filter?: string[]
    date_from?: string
    date_to?: string
  }) => client.post<Batch>('/research/batches', body).then(r => r.data),
  listBatches: (params?: { limit?: number; offset?: number }) =>
    client.get<Batch[]>('/research/batches', { params }).then(r => r.data),
  getBatch: (id: string) =>
    client.get<Batch>(`/research/batches/${id}`).then(r => r.data),
  runBatch: (id: string, body: { extract?: boolean; cluster?: boolean }) =>
    client.post(`/research/batches/${id}/run`, body).then(r => r.data),

  listClusters: (params?: { batch_id?: string; limit?: number; offset?: number }) =>
    client.get<Cluster[]>('/clusters', { params }).then(r => r.data),
  getCluster: (id: string) =>
    client.get<ClusterDetail>(`/clusters/${id}`).then(r => r.data),
  getClusterClaims: (id: string) =>
    client.get<Claim[]>(`/clusters/${id}/claims`).then(r => r.data),

  overview: () => client.get<Overview>('/monitor/overview').then(r => r.data),
}

export default api
