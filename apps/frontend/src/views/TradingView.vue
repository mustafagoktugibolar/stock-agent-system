<!-- apps/frontend/src/views/TradingView.vue -->
<template>
  <div class="trading-view">

    <!-- ── Page header ──────────────────────────────────────────────────────── -->
    <header class="page-header">
      <div class="header-inner">
        <div class="header-title-group">
          <h1 class="page-title">Trading Dashboard</h1>
          <p class="page-subtitle">Autonomous AI paper trading — Alpaca sandbox</p>
        </div>
        <div class="header-actions">
          <button
            class="btn btn-secondary btn-icon-left"
            :disabled="store.isTriggeringCycle"
            @click="store.runCycleNow()"
          >
            <svg v-if="store.isTriggeringCycle" class="spin-icon" viewBox="0 0 24 24" fill="none">
              <circle class="opacity-20" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" />
              <path class="opacity-80" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
            </svg>
            <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            Run Cycle Now
          </button>

          <button
            class="btn"
            :class="store.status?.running ? 'btn-danger' : 'btn-success'"
            :disabled="store.isToggling"
            @click="store.toggleTrader()"
          >
            <svg v-if="store.isToggling" class="spin-icon" viewBox="0 0 24 24" fill="none">
              <circle class="opacity-20" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" />
              <path class="opacity-80" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
            </svg>
            <svg v-else-if="store.status?.running" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="6" y="4" width="4" height="16" rx="1" />
              <rect x="14" y="4" width="4" height="16" rx="1" />
            </svg>
            <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polygon points="5 3 19 12 5 21 5 3" />
            </svg>
            {{ store.status?.running ? 'Stop Trader' : 'Start Trader' }}
          </button>
        </div>
      </div>
    </header>

    <!-- ── Analysis context banner ──────────────────────────────────────────── -->
    <div v-if="analysisStore.hasResult && analysisStore.currentAnalysis" class="analysis-context-banner">
      <div class="context-inner">
        <div class="context-left">
          <span class="context-label">Analysis context</span>
          <span class="context-symbol">{{ analysisStore.currentAnalysis.symbol }}</span>
          <span
            class="context-rec"
            :class="{
              'rec-buy': analysisStore.recommendation?.recommendation === 'BUY',
              'rec-sell': analysisStore.recommendation?.recommendation === 'SELL',
              'rec-hold': analysisStore.recommendation?.recommendation === 'HOLD',
            }"
          >
            {{ analysisStore.recommendation?.recommendation }}
          </span>
          <span class="context-conf">{{ Math.round((analysisStore.recommendation?.confidence ?? 0) * 100) }}% confidence</span>
          <span v-if="analysisStore.recommendation?.target_price" class="context-target">
            Target ${{ analysisStore.recommendation.target_price.toFixed(2) }}
          </span>
        </div>
        <button class="context-dismiss" @click="analysisStore.clear()" title="Dismiss context">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>

    <!-- ── Error banner ────────────────────────────────────────────────────── -->
    <div v-if="store.error" class="error-banner">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10" />
        <line x1="12" y1="8" x2="12" y2="12" />
        <line x1="12" y1="16" x2="12.01" y2="16" />
      </svg>
      {{ store.error }}
    </div>

    <!-- ── Loading skeleton ────────────────────────────────────────────────── -->
    <template v-if="store.isLoading">
      <div class="status-grid">
        <div v-for="i in 4" :key="i" class="card skeleton-card">
          <div class="skeleton skeleton-title" />
          <div class="skeleton skeleton-body" />
          <div class="skeleton skeleton-body short" />
        </div>
      </div>
      <div class="card skeleton-card mt-section">
        <div class="skeleton skeleton-title" />
        <div class="skeleton skeleton-table-row" v-for="j in 3" :key="j" />
      </div>
    </template>

    <!-- ── Main content ────────────────────────────────────────────────────── -->
    <template v-else>

      <!-- ── 1. Status cards ──────────────────────────────────────────────── -->
      <section class="status-grid" aria-label="System status">

        <!-- System status -->
        <div class="card status-card">
          <p class="card-label">System</p>
          <div class="status-row">
            <span class="status-dot" :class="store.status?.running ? 'dot-green' : 'dot-red'" />
            <span class="status-value">{{ store.status?.running ? 'Running' : 'Stopped' }}</span>
          </div>
          <span class="badge" :class="store.status?.trading_enabled ? 'badge-green' : 'badge-amber'">
            {{ store.status?.trading_enabled ? 'Trading enabled' : 'Dry-run mode' }}
          </span>
        </div>

        <!-- Watchlist -->
        <div class="card status-card">
          <p class="card-label">Watchlist</p>
          <div class="chip-list">
            <span
              v-for="sym in store.status?.watchlist"
              :key="sym"
              class="chip chip-removable"
            >
              {{ sym }}
              <button class="chip-remove" @click="store.removeSymbol(sym)" :title="`Remove ${sym}`">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </span>
          </div>
          <form class="watchlist-add-form" @submit.prevent="submitAddSymbol">
            <input
              v-model="newSymbol"
              class="watchlist-input"
              placeholder="Add symbol…"
              maxlength="10"
              autocomplete="off"
              autocapitalize="characters"
            />
            <button type="submit" class="watchlist-add-btn" :disabled="!newSymbol.trim()">+</button>
          </form>
        </div>

        <!-- Limits -->
        <div class="card status-card">
          <p class="card-label">Limits</p>
          <dl class="limits-list">
            <div class="limit-row">
              <dt class="limit-key">Max positions</dt>
              <dd class="limit-val">{{ store.status?.max_open_positions ?? '—' }}</dd>
            </div>
            <div class="limit-row">
              <dt class="limit-key">Min confidence</dt>
              <dd class="limit-val">{{ store.status ? pct(store.status.min_decision_confidence) : '—' }}</dd>
            </div>
            <div class="limit-row">
              <dt class="limit-key">Max size</dt>
              <dd class="limit-val">{{ store.status ? usd(store.status.max_position_size_usd) : '—' }}</dd>
            </div>
          </dl>
        </div>

        <!-- Next cycles -->
        <div class="card status-card">
          <p class="card-label">Next Cycles</p>
          <ul v-if="store.status?.jobs?.length" class="job-list">
            <li v-for="job in store.status.jobs" :key="job.id" class="job-row">
              <span class="job-id">{{ job.id }}</span>
              <span class="job-time">{{ job.next_run ? formatJobTime(job.next_run) : 'Not scheduled' }}</span>
            </li>
          </ul>
          <span v-else class="empty-inline">No scheduled jobs</span>
        </div>

      </section>

      <!-- ── Historical Backtest (time machine) ───────────────────────────── -->
      <section class="mt-section">
        <div class="card">
          <div class="section-header">
            <h2 class="section-title">Historical Backtest</h2>
            <span class="bt-subtitle">Replay the decision agent over past market data — same LLM, same prompt, no lookahead</span>
          </div>

          <form class="bt-form" @submit.prevent="submitBacktest">
            <div class="bt-field">
              <label class="bt-label" for="bt-symbols">Symbols</label>
              <input
                id="bt-symbols"
                v-model="btSymbols"
                class="bt-input"
                placeholder="NVDA, AAPL"
                :disabled="store.isBacktestRunning"
              />
            </div>
            <div class="bt-field">
              <label class="bt-label" for="bt-start">Start date</label>
              <input
                id="bt-start"
                v-model="btStart"
                class="bt-input"
                type="date"
                :max="todayIso"
                :disabled="store.isBacktestRunning"
              />
            </div>
            <div class="bt-field">
              <label class="bt-label" for="bt-end">End date</label>
              <input
                id="bt-end"
                v-model="btEnd"
                class="bt-input"
                type="date"
                :max="todayIso"
                :disabled="store.isBacktestRunning"
              />
            </div>
            <div class="bt-field">
              <label class="bt-label" for="bt-capital">Initial capital ($)</label>
              <input
                id="bt-capital"
                v-model.number="btCapital"
                class="bt-input"
                type="number"
                min="1000"
                step="1000"
                :disabled="store.isBacktestRunning"
              />
            </div>
            <div class="bt-field">
              <label class="bt-label" for="bt-conf">Min confidence</label>
              <input
                id="bt-conf"
                v-model.number="btMinConf"
                class="bt-input"
                type="number"
                min="0"
                max="1"
                step="0.05"
                :disabled="store.isBacktestRunning"
              />
            </div>
            <button class="btn btn-secondary bt-run-btn" type="submit" :disabled="store.isBacktestRunning">
              <svg v-if="store.isBacktestRunning" class="spin-icon" viewBox="0 0 24 24" fill="none">
                <circle class="opacity-20" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" />
                <path class="opacity-80" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
              </svg>
              <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="9" />
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 7v5l3 2" />
              </svg>
              {{ store.isBacktestRunning ? 'Simulating…' : 'Run Backtest' }}
            </button>
          </form>

          <div v-if="store.isBacktestRunning && btProgress" class="bt-progress">
            <div class="bt-progress-track">
              <div class="bt-progress-fill" :style="{ width: `${btProgressPct}%` }" />
            </div>
            <p class="bt-progress-text">
              Simulating {{ btProgress.current_date }} — day {{ btProgress.day }}/{{ btProgress.total_days }}
              · equity {{ usd(btProgress.equity) }}
              · {{ btProgress.trades_closed }} trades closed
              · {{ btProgress.open_positions }} open
            </p>
          </div>
          <div v-else-if="store.isBacktestRunning" class="bt-progress">
            <p class="bt-progress-text">Fetching historical data…</p>
          </div>

          <div v-if="store.backtest?.status === 'failed'" class="error-banner bt-error">
            {{ store.backtest.error }}
          </div>

          <div v-if="btResult" class="bt-result">
            <div class="bt-stats-grid">
              <div class="bt-stat">
                <span class="bt-stat-label">Initial capital</span>
                <span class="bt-stat-value">{{ usd(btResult.initial_capital) }}</span>
              </div>
              <div class="bt-stat">
                <span class="bt-stat-label">Final equity</span>
                <span class="bt-stat-value" :class="btResult.final_equity >= btResult.initial_capital ? 'positive' : 'negative'">
                  {{ usd(btResult.final_equity) }}
                </span>
              </div>
              <div class="bt-stat">
                <span class="bt-stat-label">Agent return</span>
                <span class="bt-stat-value" :class="btResult.total_return_pct >= 0 ? 'positive' : 'negative'">
                  {{ btResult.total_return_pct >= 0 ? '+' : '' }}{{ btResult.total_return_pct }}%
                </span>
                <span v-if="btResult.spy_return_pct != null" class="bt-stat-sub">
                  S&P 500: {{ btResult.spy_return_pct >= 0 ? '+' : '' }}{{ btResult.spy_return_pct }}%
                </span>
              </div>
              <div class="bt-stat">
                <span class="bt-stat-label">Trades</span>
                <span class="bt-stat-value">{{ btResult.total_trades }}</span>
                <span v-if="btResult.win_rate_pct != null" class="bt-stat-sub">{{ btResult.win_rate_pct }}% win rate</span>
              </div>
              <div class="bt-stat">
                <span class="bt-stat-label">Max drawdown</span>
                <span class="bt-stat-value negative">{{ btResult.max_drawdown_pct }}%</span>
              </div>
              <div class="bt-stat">
                <span class="bt-stat-label">Decisions</span>
                <span class="bt-stat-value">{{ btResult.trading_days }}d</span>
                <span class="bt-stat-sub">
                  {{ btResult.decision_counts.BUY ?? 0 }} buy · {{ btResult.decision_counts.SELL ?? 0 }} sell · {{ btResult.decision_counts.HOLD ?? 0 }} hold
                </span>
              </div>
            </div>
            <p v-if="btDataSourceLabel" class="bt-data-source">{{ btDataSourceLabel }}</p>

            <svg v-if="btSparkline" class="bt-sparkline" viewBox="0 0 600 140" preserveAspectRatio="none" aria-label="Equity curve">
              <line x1="0" :y1="btSparkline.baselineY" x2="600" :y2="btSparkline.baselineY" class="bt-spark-baseline" />
              <polyline :points="btSparkline.points" fill="none" :class="btResult.total_return_pct >= 0 ? 'bt-spark-pos' : 'bt-spark-neg'" />
            </svg>

            <div v-if="btResult.trades.length" class="table-wrapper bt-trades">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>Symbol</th>
                    <th>Entry</th>
                    <th>Exit</th>
                    <th class="num">Entry $</th>
                    <th class="num">Exit $</th>
                    <th class="num">P&L</th>
                    <th>Exit Reason</th>
                    <th class="num">Held</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(t, i) in btResult.trades" :key="i">
                    <td class="symbol-cell">{{ t.symbol }}</td>
                    <td class="muted">{{ t.entry_date }}</td>
                    <td class="muted">{{ t.exit_date }}</td>
                    <td class="num">${{ t.entry_price.toFixed(2) }}</td>
                    <td class="num">${{ t.exit_price.toFixed(2) }}</td>
                    <td class="num" :class="pnlClass(t.pnl)">
                      {{ t.pnl >= 0 ? '+' : '' }}${{ Math.abs(t.pnl).toFixed(2) }}
                      <span class="pnl-pct">({{ t.pnl_pct >= 0 ? '+' : '' }}{{ t.pnl_pct.toFixed(2) }}%)</span>
                    </td>
                    <td>
                      <span class="exit-reason-badge" :class="exitReasonClass(t.exit_reason)">
                        {{ formatExitReason(t.exit_reason) }}
                      </span>
                    </td>
                    <td class="num muted">{{ t.hold_days }}d</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div v-else class="empty-state">
              <p>No trades in this period</p>
              <span>The agent held through the whole range — try a different window or lower the confidence threshold.</span>
            </div>
          </div>
        </div>
      </section>

      <!-- ── 2. Open Positions ─────────────────────────────────────────────── -->
      <section class="mt-section">
        <div class="card">
          <div class="section-header">
            <h2 class="section-title">Open Positions</h2>
            <span class="count-badge">{{ store.positions.length }}</span>
          </div>

          <div v-if="store.positions.length" class="table-wrapper">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Symbol</th>
                  <th>Side</th>
                  <th class="num">Qty</th>
                  <th class="num">Entry</th>
                  <th class="num">Stop Loss</th>
                  <th class="num">Take Profit</th>
                  <th class="num">Unrealized P&L</th>
                  <th>Opened</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="pos in store.positions" :key="pos.id">
                  <td class="symbol-cell">{{ pos.symbol }}</td>
                  <td>
                    <span class="badge" :class="pos.side.toLowerCase() === 'long' ? 'badge-green' : 'badge-red'">
                      {{ pos.side.toUpperCase() }}
                    </span>
                  </td>
                  <td class="num">{{ pos.quantity }}</td>
                  <td class="num">{{ fmt(pos.entry_price) }}</td>
                  <td class="num muted">{{ pos.stop_loss != null ? fmt(pos.stop_loss) : '—' }}</td>
                  <td class="num muted">{{ pos.take_profit != null ? fmt(pos.take_profit) : '—' }}</td>
                  <td class="num" :class="pnlClass(pos.unrealized_pnl)">
                    {{ pos.unrealized_pnl != null ? fmtPnl(pos.unrealized_pnl) : '—' }}
                  </td>
                  <td class="muted">{{ relTime(pos.opened_at) }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div v-else class="empty-state">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M2.25 18.75a60.07 60.07 0 0115.797 2.101c.727.198 1.453-.342 1.453-1.096V18.75M3.75 4.5v.75A.75.75 0 013 6h-.75m0 0v-.375c0-.621.504-1.125 1.125-1.125H20.25M2.25 6v9m18-10.5v.75c0 .414.336.75.75.75h.75m-1.5-1.5h.375c.621 0 1.125.504 1.125 1.125v9.75c0 .621-.504 1.125-1.125 1.125h-.375m1.5-1.5H21a.75.75 0 01-.75.75h-.75m0 0H3.75" />
            </svg>
            <p>No open positions</p>
            <span>The trader has no active positions right now.</span>
          </div>
        </div>
      </section>

      <!-- ── 3. Recent Decisions ──────────────────────────────────────────── -->
      <section class="mt-section">
        <div class="card">
          <div class="section-header">
            <h2 class="section-title">Recent Decisions</h2>
            <span class="count-badge">{{ store.decisions.length }}</span>
          </div>

          <div v-if="store.decisions.length" class="table-wrapper">
            <table class="data-table decisions-table">
              <thead>
                <tr>
                  <th>Symbol</th>
                  <th>Action</th>
                  <th>Confidence</th>
                  <th>Regime</th>
                  <th>Time</th>
                </tr>
              </thead>
              <tbody>
                <template v-for="d in store.decisions" :key="d.id">
                  <tr
                    class="decision-row"
                    :class="{ 'row-expanded': expandedDecisions.has(d.id) }"
                    @click="toggleDecision(d.id)"
                  >
                    <td class="symbol-cell">{{ d.symbol }}</td>
                    <td>
                      <span class="badge" :class="actionBadgeClass(d.action)">{{ d.action }}</span>
                    </td>
                    <td class="confidence-cell">
                      <div class="confidence-bar-wrap">
                        <div
                          class="confidence-bar"
                          :class="confidenceBarClass(d.confidence)"
                          :style="{ width: pct(d.confidence) }"
                        />
                      </div>
                      <span class="confidence-pct">{{ pct(d.confidence) }}</span>
                    </td>
                    <td class="muted regime-cell">{{ d.market_regime ?? '—' }}</td>
                    <td class="muted">{{ relTime(d.decided_at) }}</td>
                  </tr>
                  <tr v-if="expandedDecisions.has(d.id)" class="reasoning-row">
                    <td colspan="5">
                      <p class="reasoning-text">{{ d.reasoning }}</p>
                    </td>
                  </tr>
                </template>
              </tbody>
            </table>
          </div>

          <div v-else class="empty-state">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25zM6.75 12h.008v.008H6.75V12zm0 3h.008v.008H6.75V15zm0 3h.008v.008H6.75V18z" />
            </svg>
            <p>No decisions yet</p>
            <span>Run a trading cycle to see the AI's decisions.</span>
          </div>
        </div>
      </section>

      <!-- ── 4. Trade History (closed positions) ────────────────────────── -->
      <section class="mt-section">
        <div class="card">
          <div class="section-header">
            <h2 class="section-title">Trade History</h2>
            <span class="count-badge">{{ store.closedPositions.length }}</span>
          </div>

          <div v-if="store.closedPositions.length" class="table-wrapper">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Symbol</th>
                  <th>Side</th>
                  <th class="num">Entry</th>
                  <th class="num">Exit</th>
                  <th class="num">Qty</th>
                  <th class="num">Realized P&L</th>
                  <th>Exit Reason</th>
                  <th>Held</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="pos in store.closedPositions" :key="pos.id">
                  <td class="symbol-cell">{{ pos.symbol }}</td>
                  <td>
                    <span class="badge" :class="pos.side === 'long' ? 'badge-green' : 'badge-red'">
                      {{ pos.side.toUpperCase() }}
                    </span>
                  </td>
                  <td class="num">${{ pos.entry_price.toFixed(2) }}</td>
                  <td class="num">{{ pos.exit_price != null ? `$${pos.exit_price.toFixed(2)}` : '—' }}</td>
                  <td class="num muted">{{ pos.quantity }}</td>
                  <td class="num" :class="pnlClass(pos.realized_pnl)">
                    <span v-if="pos.realized_pnl != null">
                      {{ pos.realized_pnl >= 0 ? '+' : '' }}${{ Math.abs(pos.realized_pnl).toFixed(2) }}
                      <span class="pnl-pct">({{ pos.realized_pnl_pct != null ? `${pos.realized_pnl_pct >= 0 ? '+' : ''}${pos.realized_pnl_pct.toFixed(2)}%` : '' }})</span>
                    </span>
                    <span v-else>—</span>
                  </td>
                  <td>
                    <span class="exit-reason-badge" :class="exitReasonClass(pos.exit_reason)">
                      {{ formatExitReason(pos.exit_reason) }}
                    </span>
                  </td>
                  <td class="muted">{{ holdDuration(pos.opened_at, pos.closed_at) }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div v-else class="empty-state">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" />
            </svg>
            <p>No closed trades yet</p>
            <span>Completed trades will appear here with P&L.</span>
          </div>
        </div>
      </section>

      <!-- ── 5. Reflections feed ──────────────────────────────────────────── -->
      <section class="mt-section pb-section">
        <div class="section-header-standalone">
          <h2 class="section-title">Reflections</h2>
          <span class="count-badge">{{ store.reflections.length }}</span>
        </div>

        <div v-if="store.reflections.length" class="reflections-grid">
          <article v-for="r in store.reflections" :key="r.id" class="card reflection-card">
            <div class="reflection-top">
              <div class="reflection-meta">
                <span class="symbol-cell">{{ r.symbol }}</span>
                <span class="badge" :class="outcomeBadgeClass(r.outcome)">
                  {{ r.outcome }}
                </span>
                <span v-if="r.memory_stored" class="memory-chip">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M9 3H5a2 2 0 00-2 2v4m6-6h10a2 2 0 012 2v4M9 3v18m0 0h10a2 2 0 002-2V9M9 21H5a2 2 0 01-2-2V9m0 0h18" />
                  </svg>
                  Memory stored
                </span>
              </div>
              <span v-if="r.pnl_pct != null" class="pnl-badge" :class="r.pnl_pct >= 0 ? 'pnl-pos' : 'pnl-neg'">
                {{ r.pnl_pct >= 0 ? '+' : '' }}{{ r.pnl_pct.toFixed(2) }}%
              </span>
            </div>
            <p v-if="r.lessons_learned" class="lessons-text">{{ r.lessons_learned }}</p>
            <p v-else class="lessons-text muted-italic">No lessons recorded.</p>
            <time class="reflection-time">{{ relTime(r.reflected_at) }}</time>
          </article>
        </div>

        <div v-else class="card empty-state">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 18v-5.25m0 0a6.01 6.01 0 001.5-.189m-1.5.189a6.01 6.01 0 01-1.5-.189m3.75 7.478a12.06 12.06 0 01-4.5 0m3.75 2.383a14.406 14.406 0 01-3 0M14.25 18v-.192c0-.983.658-1.823 1.508-2.316a7.5 7.5 0 10-7.517 0c.85.493 1.509 1.333 1.509 2.316V18" />
          </svg>
          <p>No reflections yet</p>
          <span>Reflections appear after trades are closed and evaluated.</span>
        </div>
      </section>

    </template>

    <!-- ── Toast notification ──────────────────────────────────────────────── -->
    <Transition name="toast">
      <div v-if="store.toastMessage" class="toast" role="alert">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        {{ store.toastMessage }}
      </div>
    </Transition>

  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { useTradingStore } from '@/stores/trading'
import { useAnalysisStore } from '@/stores/analysis'

const store = useTradingStore()
const analysisStore = useAnalysisStore()
const expandedDecisions = ref<Set<string>>(new Set())
const newSymbol = ref('')

const todayIso = new Date().toISOString().slice(0, 10)
const btSymbols = ref('NVDA')
const btStart = ref('2024-09-02')
const btEnd = ref('2024-10-31')
const btCapital = ref(100_000)
const btMinConf = ref(0.55)

const btResult = computed(() => store.backtest?.result ?? null)
const btProgress = computed(() => store.backtest?.progress ?? null)
const btProgressPct = computed(() => {
  const p = btProgress.value
  if (!p || p.total_days === 0) return 0
  return Math.round((p.day / p.total_days) * 100)
})

const btDataSourceLabel = computed(() => {
  const result = btResult.value
  const sources = result?.config.market_data_sources
  if (!result || !sources) return ''
  const entries = Object.entries(sources).filter(([symbol]) => symbol !== 'SPY')
  const uniqueSources = Array.from(new Set(entries.map(([, source]) => source)))
  const sourceText = uniqueSources.length === 1
    ? uniqueSources[0]
    : entries.map(([symbol, source]) => `${symbol}: ${source}`).join(', ')
  const warmup = result.config.market_data_fetch_start
  return warmup ? `Market data: ${sourceText} (warmup from ${warmup})` : `Market data: ${sourceText}`
})

const btSparkline = computed(() => {
  const result = btResult.value
  if (!result || result.equity_curve.length < 2) return null
  const values = result.equity_curve.map((p) => p.equity)
  const min = Math.min(...values, result.initial_capital)
  const max = Math.max(...values, result.initial_capital)
  const range = max - min || 1
  const toY = (v: number) => 130 - ((v - min) / range) * 120
  const points = values
    .map((v, i) => `${(i / (values.length - 1)) * 600},${toY(v).toFixed(1)}`)
    .join(' ')
  return { points, baselineY: toY(result.initial_capital).toFixed(1) }
})

function submitBacktest() {
  const symbols = btSymbols.value
    .split(',')
    .map((s) => s.trim().toUpperCase())
    .filter(Boolean)
  if (!symbols.length || !btStart.value || !btEnd.value) return
  store.runBacktest({
    symbols,
    start_date: btStart.value,
    end_date: btEnd.value,
    initial_capital: btCapital.value || 100_000,
    min_confidence: btMinConf.value ?? 0.55,
  })
}

function submitAddSymbol() {
  const sym = newSymbol.value.trim().toUpperCase()
  if (!sym) return
  store.addSymbol(sym)
  newSymbol.value = ''
}
let refreshInterval: ReturnType<typeof setInterval> | null = null

onMounted(() => {
  store.fetchAll()
  refreshInterval = setInterval(() => store.fetchAll(), 30_000)
})

onUnmounted(() => {
  if (refreshInterval !== null) clearInterval(refreshInterval)
  store.stopBacktestPolling()
})

function toggleDecision(id: string) {
  const next = new Set(expandedDecisions.value)
  next.has(id) ? next.delete(id) : next.add(id)
  expandedDecisions.value = next
}

function pct(v: number): string {
  return `${Math.round(v * 100)}%`
}

function usd(v: number): string {
  return `$${v.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`
}

function fmt(v: number): string {
  return `$${v.toFixed(2)}`
}

function fmtPnl(v: number): string {
  return (v >= 0 ? '+$' : '-$') + Math.abs(v).toFixed(2)
}

function pnlClass(v: number | null): string {
  if (v == null) return 'muted'
  return v > 0 ? 'positive' : v < 0 ? 'negative' : 'muted'
}

function actionBadgeClass(action: 'BUY' | 'SELL' | 'HOLD'): string {
  if (action === 'BUY') return 'badge-green'
  if (action === 'SELL') return 'badge-red'
  return 'badge-neutral-action'
}

function confidenceBarClass(v: number): string {
  if (v >= 0.7) return 'bar-green'
  if (v >= 0.45) return 'bar-amber'
  return 'bar-red'
}

function outcomeBadgeClass(outcome: string): string {
  switch (outcome) {
    case 'profitable': return 'badge-green'
    case 'loss': return 'badge-red'
    case 'breakeven': return 'badge-amber'
    default: return 'badge-neutral-action'
  }
}

function formatExitReason(reason: string | null): string {
  if (!reason) return '—'
  return { stop_loss: 'Stop Loss', take_profit: 'Take Profit', time_limit: 'Time Limit', agent_sell: 'Agent Sell' }[reason] ?? reason
}

function exitReasonClass(reason: string | null): string {
  if (reason === 'take_profit') return 'exit-green'
  if (reason === 'stop_loss') return 'exit-red'
  if (reason === 'time_limit') return 'exit-amber'
  return 'exit-neutral'
}

function holdDuration(openedAt: string, closedAt: string | null): string {
  const end = closedAt ? new Date(closedAt) : new Date()
  const ms = end.getTime() - new Date(openedAt).getTime()
  const hours = Math.floor(ms / 3_600_000)
  if (hours < 24) return `${hours}h`
  return `${Math.floor(hours / 24)}d ${hours % 24}h`
}

function relTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60_000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  const days = Math.floor(hrs / 24)
  return `${days}d ago`
}

function formatJobTime(iso: string): string {
  const d = new Date(iso)
  const now = new Date()
  const diffMs = d.getTime() - now.getTime()
  if (diffMs < 0) return 'Overdue'
  const mins = Math.floor(diffMs / 60_000)
  if (mins < 1) return 'in <1m'
  if (mins < 60) return `in ${mins}m`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `in ${hrs}h ${mins % 60}m`
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}
</script>

<style scoped>
/* ── Historical backtest ─────────────────────────────────────────────────── */
.bt-subtitle {
  font-size: 0.75rem;
  color: var(--color-text-muted);
}

.bt-form {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 0.75rem;
}

.bt-field {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  min-width: 8rem;
}

.bt-field:first-child {
  flex: 1;
  min-width: 10rem;
}

.bt-label {
  font-size: 0.6875rem;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--color-text-muted);
}

.bt-input {
  padding: 0.45rem 0.6rem;
  border-radius: 0.375rem;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.04);
  color: var(--color-text);
  font-size: 0.8125rem;
  outline: none;
  transition: border-color 0.15s;
  color-scheme: dark;
}

.bt-input:focus {
  border-color: rgba(96, 165, 250, 0.4);
}

.bt-input:disabled {
  opacity: 0.5;
}

.bt-run-btn {
  white-space: nowrap;
}

.bt-progress {
  margin-top: 1rem;
}

.bt-progress-track {
  height: 0.375rem;
  border-radius: 9999px;
  background: rgba(255, 255, 255, 0.06);
  overflow: hidden;
}

.bt-progress-fill {
  height: 100%;
  border-radius: 9999px;
  background: linear-gradient(90deg, #3b82f6, #22c55e);
  transition: width 0.5s ease;
}

.bt-progress-text {
  margin-top: 0.5rem;
  font-size: 0.75rem;
  color: var(--color-text-muted);
}

.bt-error {
  margin-top: 1rem;
}

.bt-result {
  margin-top: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.bt-stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(9rem, 1fr));
  gap: 0.75rem;
}

.bt-stat {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
  padding: 0.625rem 0.75rem;
  border-radius: 0.5rem;
  border: 1px solid rgba(255, 255, 255, 0.06);
  background: rgba(255, 255, 255, 0.03);
}

.bt-stat-label {
  font-size: 0.6875rem;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--color-text-muted);
}

.bt-stat-value {
  font-size: 1.125rem;
  font-weight: 700;
  color: var(--color-text);
}

.bt-stat-value.positive { color: #4ade80; }
.bt-stat-value.negative { color: #f87171; }

.bt-stat-sub {
  font-size: 0.6875rem;
  color: var(--color-text-muted);
}

.bt-data-source {
  margin: -0.25rem 0 0;
  font-size: 0.75rem;
  color: var(--color-text-muted);
}

.bt-sparkline {
  width: 100%;
  height: 8.75rem;
  border-radius: 0.5rem;
  border: 1px solid rgba(255, 255, 255, 0.06);
  background: rgba(255, 255, 255, 0.02);
}

.bt-spark-baseline {
  stroke: rgba(255, 255, 255, 0.15);
  stroke-width: 1;
  stroke-dasharray: 4 4;
}

.bt-spark-pos { stroke: #4ade80; stroke-width: 2; }
.bt-spark-neg { stroke: #f87171; stroke-width: 2; }

/* ── Analysis context banner ─────────────────────────────────────────────── */
.analysis-context-banner {
  max-width: 1280px;
  margin: 1rem auto 0;
  border-radius: 0.625rem;
  border: 1px solid rgba(96, 165, 250, 0.2);
  background: rgba(96, 165, 250, 0.07);
  padding: 0.625rem 1rem;
}

.context-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.context-left {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  flex-wrap: wrap;
}

.context-label {
  font-size: 0.6875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  color: var(--color-text-muted);
}

.context-symbol {
  font-size: 0.875rem;
  font-weight: 700;
  font-family: ui-monospace, 'Cascadia Code', monospace;
  letter-spacing: 0.04em;
  color: var(--color-text);
}

.context-rec {
  padding: 0.175rem 0.5rem;
  border-radius: 0.375rem;
  font-size: 0.6875rem;
  font-weight: 700;
  letter-spacing: 0.04em;
}

.rec-buy  { background: rgba(34, 197, 94, 0.15);  color: #4ade80; }
.rec-sell { background: rgba(239, 68, 68, 0.15);  color: #f87171; }
.rec-hold { background: rgba(245, 158, 11, 0.15); color: #fbbf24; }

.context-conf {
  font-size: 0.75rem;
  color: var(--color-text-secondary);
}

.context-target {
  font-size: 0.75rem;
  font-weight: 600;
  color: #60a5fa;
}

.context-dismiss {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0.25rem;
  border-radius: 0.375rem;
  background: transparent;
  border: none;
  color: var(--color-text-muted);
  cursor: pointer;
  transition: color 0.15s, background 0.15s;
  flex-shrink: 0;
}

.context-dismiss:hover {
  background: rgba(255, 255, 255, 0.06);
  color: var(--color-text);
}

.context-dismiss svg { width: 0.875rem; height: 0.875rem; }

/* ── Layout ──────────────────────────────────────────────────────────────── */
.trading-view {
  min-height: 100vh;
  background: var(--color-bg);
  padding: 0 1rem 0;
}

@media (min-width: 640px) { .trading-view { padding: 0 1.5rem; } }
@media (min-width: 1024px) { .trading-view { padding: 0 2rem; } }

.mt-section { margin-top: 1.25rem; }
.pb-section { padding-bottom: 4rem; }

/* ── Page header ─────────────────────────────────────────────────────────── */
.page-header {
  position: sticky;
  top: 0;
  z-index: 30;
  background: color-mix(in srgb, var(--color-bg) 85%, transparent);
  backdrop-filter: blur(16px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  margin: 0 -1rem;
  padding: 0 1rem;
}

@media (min-width: 640px) {
  .page-header { margin: 0 -1.5rem; padding: 0 1.5rem; }
}
@media (min-width: 1024px) {
  .page-header { margin: 0 -2rem; padding: 0 2rem; }
}

.header-inner {
  max-width: 1280px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 1rem 0;
  flex-wrap: wrap;
}

.header-title-group { min-width: 0; }

.page-title {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--color-text);
  letter-spacing: -0.01em;
  line-height: 1.25;
}

@media (min-width: 640px) { .page-title { font-size: 1.5rem; } }

.page-subtitle {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  margin-top: 0.125rem;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  flex-shrink: 0;
}

/* ── Buttons ─────────────────────────────────────────────────────────────── */
.btn {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  border-radius: 0.5rem;
  font-size: 0.8125rem;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid transparent;
  transition: background 0.15s, opacity 0.15s, transform 0.1s;
  white-space: nowrap;
  line-height: 1;
}

.btn svg { width: 1rem; height: 1rem; flex-shrink: 0; }
.btn:disabled { opacity: 0.45; cursor: not-allowed; transform: none; }
.btn:not(:disabled):active { transform: scale(0.97); }

.btn-success {
  background: rgba(34, 197, 94, 0.15);
  border-color: rgba(34, 197, 94, 0.3);
  color: #4ade80;
}
.btn-success:not(:disabled):hover {
  background: rgba(34, 197, 94, 0.25);
  border-color: rgba(34, 197, 94, 0.5);
}

.btn-danger {
  background: rgba(239, 68, 68, 0.15);
  border-color: rgba(239, 68, 68, 0.3);
  color: #f87171;
}
.btn-danger:not(:disabled):hover {
  background: rgba(239, 68, 68, 0.25);
  border-color: rgba(239, 68, 68, 0.5);
}

.btn-secondary {
  background: rgba(61, 142, 240, 0.1);
  border-color: rgba(61, 142, 240, 0.25);
  color: #60a5fa;
}
.btn-secondary:not(:disabled):hover {
  background: rgba(61, 142, 240, 0.2);
  border-color: rgba(61, 142, 240, 0.45);
}

/* ── Error banner ────────────────────────────────────────────────────────── */
.error-banner {
  max-width: 1280px;
  margin: 1rem auto 0;
  display: flex;
  align-items: center;
  gap: 0.625rem;
  padding: 0.75rem 1rem;
  border-radius: 0.5rem;
  border: 1px solid rgba(239, 68, 68, 0.2);
  background: rgba(239, 68, 68, 0.08);
  color: #f87171;
  font-size: 0.8125rem;
}
.error-banner svg { width: 1rem; height: 1rem; flex-shrink: 0; }

/* ── Card base ───────────────────────────────────────────────────────────── */
.card {
  background: var(--color-surface);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 0.75rem;
  padding: 1.25rem;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.25);
}

/* ── Status grid ─────────────────────────────────────────────────────────── */
.status-grid {
  max-width: 1280px;
  margin: 1.25rem auto 0;
  display: grid;
  grid-template-columns: 1fr;
  gap: 1rem;
}

@media (min-width: 640px) { .status-grid { grid-template-columns: repeat(2, 1fr); } }
@media (min-width: 1024px) { .status-grid { grid-template-columns: repeat(4, 1fr); } }

.status-card { display: flex; flex-direction: column; gap: 0.75rem; }

.card-label {
  font-size: 0.6875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--color-text-muted);
}

.status-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.status-dot {
  width: 0.5rem;
  height: 0.5rem;
  border-radius: 50%;
  flex-shrink: 0;
}

.dot-green {
  background: #4ade80;
  box-shadow: 0 0 0 3px rgba(74, 222, 128, 0.2);
  animation: pulse-green 2s ease-in-out infinite;
}

.dot-red {
  background: #f87171;
}

@keyframes pulse-green {
  0%, 100% { box-shadow: 0 0 0 3px rgba(74, 222, 128, 0.2); }
  50% { box-shadow: 0 0 0 5px rgba(74, 222, 128, 0.08); }
}

.status-value {
  font-size: 0.9375rem;
  font-weight: 600;
  color: var(--color-text);
}

/* ── Badges ──────────────────────────────────────────────────────────────── */
.badge {
  display: inline-flex;
  align-items: center;
  padding: 0.2rem 0.625rem;
  border-radius: 0.375rem;
  font-size: 0.6875rem;
  font-weight: 600;
  letter-spacing: 0.02em;
  align-self: flex-start;
}

.badge-green { background: rgba(34, 197, 94, 0.15); color: #4ade80; }
.badge-red { background: rgba(239, 68, 68, 0.15); color: #f87171; }
.badge-amber { background: rgba(245, 158, 11, 0.15); color: #fbbf24; }
.badge-neutral-action { background: rgba(255, 255, 255, 0.07); color: var(--color-text-secondary); }

/* ── Chip list (watchlist) ───────────────────────────────────────────────── */
.chip-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.375rem;
}

.chip {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.2rem 0.5rem;
  border-radius: 0.375rem;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.04);
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--color-text-secondary);
  letter-spacing: 0.04em;
}

.chip-removable {
  padding-right: 0.25rem;
}

.chip-remove {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 0.875rem;
  height: 0.875rem;
  border: none;
  background: transparent;
  color: var(--color-text-muted);
  cursor: pointer;
  border-radius: 0.2rem;
  padding: 0;
  transition: color 0.15s, background 0.15s;
  flex-shrink: 0;
}

.chip-remove:hover {
  color: #f87171;
  background: rgba(239, 68, 68, 0.12);
}

.chip-remove svg {
  width: 0.625rem;
  height: 0.625rem;
}

.watchlist-add-form {
  display: flex;
  gap: 0.375rem;
  margin-top: 0.5rem;
}

.watchlist-input {
  flex: 1;
  min-width: 0;
  padding: 0.3rem 0.5rem;
  border-radius: 0.375rem;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.04);
  color: var(--color-text);
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  outline: none;
  transition: border-color 0.15s;
}

.watchlist-input::placeholder {
  color: var(--color-text-muted);
  text-transform: none;
  font-weight: 400;
  letter-spacing: 0;
}

.watchlist-input:focus {
  border-color: rgba(96, 165, 250, 0.4);
}

.watchlist-add-btn {
  padding: 0.3rem 0.625rem;
  border-radius: 0.375rem;
  border: 1px solid rgba(96, 165, 250, 0.25);
  background: rgba(96, 165, 250, 0.1);
  color: #60a5fa;
  font-size: 1rem;
  font-weight: 600;
  line-height: 1;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
  flex-shrink: 0;
}

.watchlist-add-btn:hover:not(:disabled) {
  background: rgba(96, 165, 250, 0.2);
  border-color: rgba(96, 165, 250, 0.45);
}

.watchlist-add-btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

/* ── Limits list ─────────────────────────────────────────────────────────── */
.limits-list { display: flex; flex-direction: column; gap: 0.375rem; }

.limit-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.limit-key {
  font-size: 0.75rem;
  color: var(--color-text-muted);
}

.limit-val {
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--color-text);
}

/* ── Job list ────────────────────────────────────────────────────────────── */
.job-list { display: flex; flex-direction: column; gap: 0.5rem; }

.job-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.job-id {
  font-size: 0.75rem;
  color: var(--color-text-secondary);
  font-family: ui-monospace, 'Cascadia Code', monospace;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.job-time {
  font-size: 0.75rem;
  font-weight: 600;
  color: #60a5fa;
  flex-shrink: 0;
}

/* ── Section headers ─────────────────────────────────────────────────────── */
.section-header {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  margin-bottom: 1rem;
}

.section-header-standalone {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  margin-bottom: 0.75rem;
  max-width: 1280px;
  margin-left: auto;
  margin-right: auto;
  padding: 0;
}

.section-title {
  font-size: 0.875rem;
  font-weight: 700;
  color: var(--color-text);
  letter-spacing: -0.005em;
}

.count-badge {
  padding: 0.15rem 0.5rem;
  border-radius: 9999px;
  background: rgba(255, 255, 255, 0.07);
  color: var(--color-text-muted);
  font-size: 0.6875rem;
  font-weight: 600;
}

/* ── Tables ──────────────────────────────────────────────────────────────── */
.mt-section .card,
.mt-section > .card {
  max-width: 1280px;
  margin-left: auto;
  margin-right: auto;
}

.table-wrapper {
  overflow-x: auto;
  margin: 0 -0.25rem;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.8125rem;
}

.data-table th {
  padding: 0.5rem 0.75rem;
  font-size: 0.6875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--color-text-muted);
  text-align: left;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  white-space: nowrap;
}

.data-table th.num,
.data-table td.num {
  text-align: right;
}

.data-table tbody tr {
  border-bottom: 1px solid rgba(255, 255, 255, 0.03);
  transition: background 0.1s;
}

.data-table tbody tr:last-child { border-bottom: none; }

.data-table tbody tr:hover { background: rgba(255, 255, 255, 0.025); }

.data-table td {
  padding: 0.625rem 0.75rem;
  color: var(--color-text);
  vertical-align: middle;
}

.symbol-cell {
  font-weight: 700;
  font-family: ui-monospace, 'Cascadia Code', monospace;
  letter-spacing: 0.04em;
  color: var(--color-text);
}

.muted { color: var(--color-text-muted); }
.positive { color: #4ade80; font-weight: 600; }
.negative { color: #f87171; font-weight: 600; }

/* ── Decisions table specifics ───────────────────────────────────────────── */
.decision-row { cursor: pointer; }
.decision-row.row-expanded { background: rgba(255, 255, 255, 0.02); }

.confidence-cell {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  min-width: 140px;
}

.confidence-bar-wrap {
  flex: 1;
  height: 5px;
  background: rgba(255, 255, 255, 0.07);
  border-radius: 9999px;
  overflow: hidden;
}

.confidence-bar {
  height: 100%;
  border-radius: 9999px;
  transition: width 0.4s ease;
}

.bar-green { background: #4ade80; }
.bar-amber { background: #fbbf24; }
.bar-red { background: #f87171; }

.confidence-pct {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--color-text-secondary);
  min-width: 2.75rem;
  text-align: right;
}

.regime-cell {
  font-size: 0.75rem;
  text-transform: capitalize;
}

.reasoning-row td {
  padding: 0 0.75rem 0.875rem;
  background: rgba(0, 0, 0, 0.15);
}

.reasoning-text {
  font-size: 0.8rem;
  line-height: 1.6;
  color: var(--color-text-secondary);
  max-width: 72ch;
}

/* ── Empty states ────────────────────────────────────────────────────────── */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.375rem;
  padding: 3rem 1rem;
  text-align: center;
}

.empty-state svg {
  width: 2rem;
  height: 2rem;
  color: var(--color-text-muted);
  margin-bottom: 0.25rem;
}

.empty-state p {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-text-secondary);
}

.empty-state span {
  font-size: 0.75rem;
  color: var(--color-text-muted);
}

.empty-inline {
  font-size: 0.8125rem;
  color: var(--color-text-muted);
}

/* ── Trade history ───────────────────────────────────────────────────────── */
.pnl-pct {
  font-size: 0.7rem;
  opacity: 0.75;
  margin-left: 0.15rem;
}

.exit-reason-badge {
  display: inline-flex;
  padding: 0.175rem 0.5rem;
  border-radius: 0.375rem;
  font-size: 0.6875rem;
  font-weight: 600;
}

.exit-green  { background: rgba(34, 197, 94, 0.12);  color: #4ade80; }
.exit-red    { background: rgba(239, 68, 68, 0.12);  color: #f87171; }
.exit-amber  { background: rgba(245, 158, 11, 0.12); color: #fbbf24; }
.exit-neutral { background: rgba(255,255,255,0.06);  color: var(--color-text-muted); }

/* ── Reflections grid ────────────────────────────────────────────────────── */
.reflections-grid {
  max-width: 1280px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 1fr;
  gap: 1rem;
}

@media (min-width: 640px) { .reflections-grid { grid-template-columns: repeat(2, 1fr); } }
@media (min-width: 1024px) { .reflections-grid { grid-template-columns: repeat(3, 1fr); } }

.reflection-card {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.reflection-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.5rem;
}

.reflection-meta {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.memory-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.175rem 0.5rem;
  border-radius: 0.375rem;
  font-size: 0.6875rem;
  font-weight: 600;
  background: rgba(61, 142, 240, 0.12);
  color: #60a5fa;
  border: 1px solid rgba(61, 142, 240, 0.2);
}

.memory-chip svg {
  width: 0.75rem;
  height: 0.75rem;
}

.pnl-badge {
  padding: 0.2rem 0.625rem;
  border-radius: 0.375rem;
  font-size: 0.8125rem;
  font-weight: 700;
  flex-shrink: 0;
}

.pnl-pos { background: rgba(34, 197, 94, 0.12); color: #4ade80; }
.pnl-neg { background: rgba(239, 68, 68, 0.12); color: #f87171; }

.lessons-text {
  font-size: 0.8rem;
  line-height: 1.65;
  color: var(--color-text-secondary);
  flex: 1;
}

.muted-italic {
  color: var(--color-text-muted);
  font-style: italic;
}

.reflection-time {
  font-size: 0.6875rem;
  color: var(--color-text-muted);
}

/* ── Skeleton loading ────────────────────────────────────────────────────── */
.skeleton-card { display: flex; flex-direction: column; gap: 0.75rem; }

.skeleton {
  border-radius: 0.375rem;
  background: linear-gradient(90deg,
    rgba(255,255,255,0.04) 25%,
    rgba(255,255,255,0.07) 50%,
    rgba(255,255,255,0.04) 75%
  );
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}

.skeleton-title { height: 0.75rem; width: 40%; }
.skeleton-body { height: 0.875rem; width: 80%; }
.skeleton-body.short { width: 55%; }
.skeleton-table-row { height: 2.5rem; width: 100%; border-radius: 0.25rem; margin-top: 0.375rem; }

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* ── Spin icon ───────────────────────────────────────────────────────────── */
.spin-icon {
  width: 1rem;
  height: 1rem;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* ── Toast ───────────────────────────────────────────────────────────────── */
.toast {
  position: fixed;
  bottom: 1.5rem;
  right: 1.5rem;
  z-index: 9999;
  display: flex;
  align-items: center;
  gap: 0.625rem;
  padding: 0.75rem 1.125rem;
  border-radius: 0.625rem;
  background: var(--color-surface-2, #1a2030);
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4), 0 2px 8px rgba(0, 0, 0, 0.3);
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--color-text);
  max-width: 320px;
}

.toast svg {
  width: 1rem;
  height: 1rem;
  color: #4ade80;
  flex-shrink: 0;
}

/* ── Toast transition ────────────────────────────────────────────────────── */
.toast-enter-active {
  transition: opacity 0.2s ease, transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.toast-leave-active {
  transition: opacity 0.2s ease, transform 0.15s ease;
}

.toast-enter-from {
  opacity: 0;
  transform: translateY(0.75rem) scale(0.95);
}

.toast-leave-to {
  opacity: 0;
  transform: translateY(0.5rem) scale(0.97);
}
</style>
