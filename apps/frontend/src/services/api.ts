import axios from 'axios'

export const client = axios.create({
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
  url: string | null
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

export interface CompanyProfile {
  symbol: string
  name: string
  sector: string | null
  industry: string | null
  description: string | null
  market_cap: number | null
  pe_ratio: number | null
  forward_pe: number | null
  dividend_yield: number | null
  fifty_two_week_high: number | null
  fifty_two_week_low: number | null
  current_price: number | null
  currency: string
  exchange: string | null
  website: string | null
  employees: number | null
}

export interface FinancialLineItem {
  label: string
  values: Record<string, number | null>
}

export interface FinancialStatements {
  symbol: string
  timestamp: string
  balance_sheet: FinancialLineItem[]
  income_statement: FinancialLineItem[]
  cash_flow: FinancialLineItem[]
  periods: string[]
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
  company_profile: CompanyProfile | null
  financial_statements: FinancialStatements | null
  technical_analysis: TechnicalOutput | null
  news_analysis: NewsOutput | null
  risk_analysis: RiskOutput | null
  errors: string[]
  cached: boolean
}

// ── API functions ─────────────────────────────────────────────────────────────

export async function analyzeSync(
  symbol: string,
  language: string = 'en',
  forceRefresh = false,
): Promise<AnalysisResponse> {
  const { data } = await client.post<AnalysisResponse>('/api/v1/analyze/sync', {
    symbol,
    timeframe: '1d',
    language,
    force_refresh: forceRefresh,
  })
  return data
}

export async function getCachedAnalysis(symbol: string, language: string = 'en'): Promise<AnalysisResponse> {
  const { data } = await client.get<AnalysisResponse>(`/api/v1/analysis/${symbol}?language=${language}`)
  return data
}

export async function invalidateCache(symbol: string, language: string = 'en'): Promise<void> {
  await client.delete(`/api/v1/analysis/${symbol}?language=${language}`)
}

export async function checkHealth(): Promise<{ status: string; redis: string }> {
  const { data } = await client.get('/health')
  return data
}

export type ChatMessageRole = 'user' | 'assistant'

export interface ChatMessage {
  role: ChatMessageRole
  content: string
}

export async function* streamChat(
  symbol: string,
  message: string,
  history: ChatMessage[],
  language: string = 'en',
): AsyncGenerator<string, void, unknown> {
  const response = await fetch(`${client.defaults.baseURL}/api/v1/chat/${symbol}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, history, timeframe: '1d', language }),
  })

  if (!response.ok) {
    throw new Error('Failed to connect to chat stream')
  }

  const reader = response.body?.pipeThrough(new TextDecoderStream()).getReader()
  if (!reader) throw new Error('No readable stream')

  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    if (value) yield value
  }
}
