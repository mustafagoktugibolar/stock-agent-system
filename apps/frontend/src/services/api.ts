import axios from 'axios'

const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  timeout: 120_000, // 2 min - analysis can take a while
  headers: { 'Content-Type': 'application/json' },
})

// ── Types ─────────────────────────────────────────────────────────────────────

export interface TechnicalSignal {
  indicator: string
  value: number
  signal: 'bullish' | 'bearish' | 'neutral'
  description: string
}

export interface TechnicalOutput {
  symbol: string
  timestamp: string
  signals: TechnicalSignal[]
  overall_technical_bias: 'bullish' | 'bearish' | 'neutral'
  support_levels: number[]
  resistance_levels: number[]
  summary: string
  confidence: number
}

export interface NewsItem {
  title: string
  source: string
  published_at: string | null
  sentiment_score: number
  summary: string
}

export interface NewsOutput {
  symbol: string
  timestamp: string
  news_items: NewsItem[]
  overall_sentiment: 'positive' | 'negative' | 'neutral'
  sentiment_score: number
  summary: string
  confidence: number
}

export interface RiskMetric {
  metric_name: string
  value: number
  interpretation: string
}

export interface RiskOutput {
  symbol: string
  timestamp: string
  metrics: RiskMetric[]
  risk_level: 'low' | 'medium' | 'high' | 'very_high'
  volatility_percentile: number
  max_drawdown: number
  beta: number | null
  summary: string
  confidence: number
}

export interface FinalRecommendation {
  symbol: string
  timestamp: string
  recommendation: 'BUY' | 'HOLD' | 'SELL'
  confidence: number
  target_price: number | null
  stop_loss: number | null
  time_horizon: 'short_term' | 'medium_term' | 'long_term'
  reasoning: string
  technical_weight: number
  news_weight: number
  risk_weight: number
  technical_summary: string
  news_summary: string
  risk_summary: string
}

export interface AnalysisResponse {
  analysis_id: string
  symbol: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  created_at: string
  completed_at: string | null
  recommendation: FinalRecommendation | null
  technical_analysis: TechnicalOutput | null
  news_analysis: NewsOutput | null
  risk_analysis: RiskOutput | null
  errors: string[]
  cached: boolean
}

// ── API functions ─────────────────────────────────────────────────────────────

export async function analyzeSync(
  symbol: string,
  forceRefresh = false,
): Promise<AnalysisResponse> {
  const { data } = await client.post<AnalysisResponse>('/api/v1/analyze/sync', {
    symbol,
    timeframe: '1d',
    force_refresh: forceRefresh,
  })
  return data
}

export async function getCachedAnalysis(symbol: string): Promise<AnalysisResponse> {
  const { data } = await client.get<AnalysisResponse>(`/api/v1/analysis/${symbol}`)
  return data
}

export async function invalidateCache(symbol: string): Promise<void> {
  await client.delete(`/api/v1/analysis/${symbol}`)
}

export async function checkHealth(): Promise<{ status: string; redis: string }> {
  const { data } = await client.get('/health')
  return data
}
