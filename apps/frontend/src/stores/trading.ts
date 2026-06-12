import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  getTraderStatus,
  startTrader,
  stopTrader,
  triggerTradingCycle,
  getTradeDecisions,
  getTradePositions,
  getClosedPositions,
  getTradeReflections,
  addToWatchlist,
  removeFromWatchlist,
  startBacktest,
  getBacktest,
} from '@/services/api'
import type {
  TraderStatus,
  TradeDecisionItem,
  TradePositionItem,
  ClosedPositionItem,
  TradeReflectionItem,
  BacktestState,
} from '@/services/api'

export const useTradingStore = defineStore('trading', () => {
  const status = ref<TraderStatus | null>(null)
  const decisions = ref<TradeDecisionItem[]>([])
  const positions = ref<TradePositionItem[]>([])
  const closedPositions = ref<ClosedPositionItem[]>([])
  const reflections = ref<TradeReflectionItem[]>([])
  const isLoading = ref(false)
  const isToggling = ref(false)
  const isTriggeringCycle = ref(false)
  const error = ref<string | null>(null)
  const toastMessage = ref<string | null>(null)

  function showToast(msg: string) {
    toastMessage.value = msg
    setTimeout(() => { toastMessage.value = null }, 3000)
  }

  async function fetchStatus() {
    try {
      status.value = await getTraderStatus()
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch trader status'
    }
  }

  async function fetchAll() {
    isLoading.value = true
    error.value = null
    try {
      const [s, d, p, cp, r] = await Promise.all([
        getTraderStatus(),
        getTradeDecisions(20),
        getTradePositions(),
        getClosedPositions(30),
        getTradeReflections(10),
      ])
      status.value = s
      decisions.value = d
      positions.value = p
      closedPositions.value = cp
      reflections.value = r
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to load trader data'
    } finally {
      isLoading.value = false
    }
  }

  async function toggleTrader() {
    if (!status.value) return
    isToggling.value = true
    try {
      const result = status.value.running ? await stopTrader() : await startTrader()
      showToast(result.message)
      await fetchStatus()
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Toggle failed'
    } finally {
      isToggling.value = false
    }
  }

  async function runCycleNow() {
    isTriggeringCycle.value = true
    try {
      const result = await triggerTradingCycle()
      showToast(result.message)
      setTimeout(fetchAll, 5000)
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Cycle trigger failed'
    } finally {
      isTriggeringCycle.value = false
    }
  }

  async function addSymbol(symbol: string) {
    try {
      const updated = await addToWatchlist(symbol)
      if (status.value) status.value = { ...status.value, watchlist: updated }
      showToast(`${symbol.toUpperCase()} added to watchlist`)
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to add symbol'
    }
  }

  async function removeSymbol(symbol: string) {
    try {
      const updated = await removeFromWatchlist(symbol)
      if (status.value) status.value = { ...status.value, watchlist: updated }
      showToast(`${symbol.toUpperCase()} removed from watchlist`)
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to remove symbol'
    }
  }

  const backtest = ref<BacktestState | null>(null)
  const isBacktestRunning = ref(false)
  let backtestTimer: ReturnType<typeof setInterval> | null = null

  function stopBacktestPolling() {
    if (backtestTimer !== null) {
      clearInterval(backtestTimer)
      backtestTimer = null
    }
    isBacktestRunning.value = false
  }

  async function runBacktest(params: {
    symbols: string[]
    start_date: string
    end_date: string
    initial_capital: number
    min_confidence: number
  }) {
    stopBacktestPolling()
    backtest.value = null
    isBacktestRunning.value = true
    try {
      const { backtest_id } = await startBacktest(params)
      backtestTimer = setInterval(async () => {
        try {
          const state = await getBacktest(backtest_id)
          backtest.value = state
          if (state.status === 'completed' || state.status === 'failed') {
            stopBacktestPolling()
            if (state.status === 'failed') {
              showToast(`Backtest failed: ${state.error ?? 'unknown error'}`)
            }
          }
        } catch {
          stopBacktestPolling()
        }
      }, 2000)
    } catch (e) {
      isBacktestRunning.value = false
      error.value = e instanceof Error ? e.message : 'Failed to start backtest'
    }
  }

  return {
    status,
    decisions,
    positions,
    closedPositions,
    reflections,
    isLoading,
    isToggling,
    isTriggeringCycle,
    error,
    toastMessage,
    backtest,
    isBacktestRunning,
    fetchAll,
    fetchStatus,
    toggleTrader,
    runCycleNow,
    addSymbol,
    removeSymbol,
    runBacktest,
    stopBacktestPolling,
  }
})
