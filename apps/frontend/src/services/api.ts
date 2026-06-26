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
  atr: number | null
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
  period_type?: 'quarterly' | 'annual'
  annual_balance_sheet?: FinancialLineItem[]
  annual_income_statement?: FinancialLineItem[]
  annual_cash_flow?: FinancialLineItem[]
  annual_periods?: string[]
  quarterly_balance_sheet?: FinancialLineItem[]
  quarterly_income_statement?: FinancialLineItem[]
  quarterly_cash_flow?: FinancialLineItem[]
  quarterly_periods?: string[]
  computed_ratios: Record<string, number | null>
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

export interface JudgeVerdict {
  symbol: string
  timestamp: string
  verdict: 'pass' | 'fail'
  overall_score: number
  coherence_score: number
  evidence_score: number
  risk_alignment_score: number
  critique: string
  suggestions: string[]
}

export interface AnalysisResponse {
  analysis_id: string
  symbol: string
  status: 'pending' | 'running' | 'completed' | 'partial' | 'failed'
  created_at: string
  completed_at: string | null
  recommendation: FinalRecommendation | null
  company_profile: CompanyProfile | null
  financial_statements: FinancialStatements | null
  technical_analysis: TechnicalOutput | null
  news_analysis: NewsOutput | null
  risk_analysis: RiskOutput | null
  judge_verdict: JudgeVerdict | null
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

export interface StockSearchResult {
  symbol: string
  name: string
  exchange: string
}

export interface UserPreferences {
  riskTolerance: 'low' | 'medium' | 'high'
  sectors: string[]
  horizon: 'short' | 'medium' | 'long'
}

export async function searchStocks(q: string): Promise<StockSearchResult[]> {
  const { data } = await client.get<StockSearchResult[]>('/api/v1/stocks/search', { params: { q, limit: 10 } })
  return data
}

export async function* streamAdvisor(
  message: string,
  history: ChatMessage[],
  preferences: UserPreferences,
  language: string = 'en',
): AsyncGenerator<string, void, unknown> {
  const response = await fetch(`${client.defaults.baseURL}/api/v1/advisor`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      history,
      preferences: {
        risk_tolerance: preferences.riskTolerance,
        sectors: preferences.sectors,
        horizon: preferences.horizon,
      },
      language,
    }),
  })

  if (!response.ok) {
    throw new Error('Failed to connect to advisor stream')
  }

  const reader = response.body?.pipeThrough(new TextDecoderStream()).getReader()
  if (!reader) throw new Error('No readable stream')

  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    if (value) yield value
  }
}

// ── Trader types ──────────────────────────────────────────────────────────────

export interface TraderJob {
  id: string
  next_run: string | null
}

export interface TraderStatus {
  running: boolean
  trading_enabled: boolean
  watchlist: string[]
  max_open_positions: number
  min_decision_confidence: number
  max_position_size_usd: number
  jobs: TraderJob[]
}

export interface TradeDecisionItem {
  id: string
  symbol: string
  action: 'BUY' | 'SELL' | 'HOLD'
  confidence: number
  market_regime: string | null
  reasoning: string
  decided_at: string
}

export interface TradePositionItem {
  id: string
  symbol: string
  side: string
  quantity: number
  entry_price: number
  stop_loss: number | null
  take_profit: number | null
  unrealized_pnl: number | null
  opened_at: string
}

export interface ClosedPositionItem {
  id: string
  symbol: string
  side: string
  quantity: number
  entry_price: number
  exit_price: number | null
  realized_pnl: number | null
  realized_pnl_pct: number | null
  exit_reason: string | null
  opened_at: string
  closed_at: string | null
}

export interface TradeReflectionItem {
  id: string
  symbol: string
  outcome: 'profitable' | 'loss' | 'breakeven' | 'inconclusive'
  pnl_pct: number | null
  lessons_learned: string | null
  memory_stored: boolean
  reflected_at: string
}

export interface BacktestTrade {
  symbol: string
  quantity: number
  entry_date: string
  entry_price: number
  exit_date: string
  exit_price: number
  exit_reason: string
  pnl: number
  pnl_pct: number
  hold_days: number
  entry_confidence: number
  entry_reasoning: string
}

export interface BacktestProgress {
  day: number
  total_days: number
  current_date: string
  equity: number
  trades_closed: number
  open_positions: number
}

export interface BacktestResult {
  config: {
    symbols: string[]
    start_date: string
    end_date: string
    initial_capital: number
    min_confidence: number
    market_data_sources?: Record<string, string>
    market_data_fetch_start?: string
    market_data_fetch_end?: string
    warmup_days?: number
  }
  initial_capital: number
  final_equity: number
  total_return_pct: number
  spy_return_pct: number | null
  total_trades: number
  winning_trades: number
  win_rate_pct: number | null
  max_drawdown_pct: number
  trading_days: number
  decision_counts: Record<string, number>
  trades: BacktestTrade[]
  equity_curve: { date: string; equity: number }[]
  decisions: { date: string; symbol: string; action: string; confidence: number; regime: string }[]
}

export interface BacktestState {
  backtest_id: string
  status: 'starting' | 'running' | 'completed' | 'failed'
  progress?: BacktestProgress
  result?: BacktestResult
  error?: string
}

// ── Trader API functions ───────────────────────────────────────────────────────

export async function getTraderStatus(): Promise<TraderStatus> {
  const { data } = await client.get<TraderStatus>('/api/v1/trader/status')
  return data
}

export async function startTrader(): Promise<{ status: string; message: string }> {
  const { data } = await client.post('/api/v1/trader/start')
  return data
}

export async function stopTrader(): Promise<{ status: string; message: string }> {
  const { data } = await client.post('/api/v1/trader/stop')
  return data
}

export async function triggerTradingCycle(): Promise<{ status: string; message: string }> {
  const { data } = await client.post('/api/v1/trader/cycle/run')
  return data
}

export async function getTradeDecisions(limit = 20): Promise<TradeDecisionItem[]> {
  const { data } = await client.get<TradeDecisionItem[]>('/api/v1/trader/decisions', { params: { limit } })
  return data
}

export async function getTradePositions(): Promise<TradePositionItem[]> {
  const { data } = await client.get<TradePositionItem[]>('/api/v1/trader/positions')
  return data
}

export async function getClosedPositions(limit = 50): Promise<ClosedPositionItem[]> {
  const { data } = await client.get<ClosedPositionItem[]>('/api/v1/trader/positions/closed', { params: { limit } })
  return data
}

export async function getTradeReflections(limit = 10): Promise<TradeReflectionItem[]> {
  const { data } = await client.get<TradeReflectionItem[]>('/api/v1/trader/reflections', { params: { limit } })
  return data
}

export async function getWatchlist(): Promise<string[]> {
  const { data } = await client.get<string[]>('/api/v1/trader/watchlist')
  return data
}

export async function addToWatchlist(symbol: string): Promise<string[]> {
  const { data } = await client.post<string[]>('/api/v1/trader/watchlist', { symbol })
  return data
}

export async function removeFromWatchlist(symbol: string): Promise<string[]> {
  const { data } = await client.delete<string[]>(`/api/v1/trader/watchlist/${symbol}`)
  return data
}

export async function startBacktest(params: {
  symbols: string[]
  start_date: string
  end_date: string
  initial_capital: number
  min_confidence: number
}): Promise<{ backtest_id: string; status: string }> {
  const { data } = await client.post('/api/v1/trader/backtest', params)
  return data
}

export async function getBacktest(backtestId: string): Promise<BacktestState> {
  const { data } = await client.get<BacktestState>(`/api/v1/trader/backtest/${backtestId}`)
  return data
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
