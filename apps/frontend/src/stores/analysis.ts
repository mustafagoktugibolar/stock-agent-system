import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { analyzeSync, getCachedAnalysis, invalidateCache } from '@/services/api'
import type { AnalysisResponse } from '@/services/api'

export const useAnalysisStore = defineStore('analysis', () => {
  // ── State ───────────────────────────────────────────────────────────────────
  const currentAnalysis = ref<AnalysisResponse | null>(null)
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  const lastSymbol = ref<string>('')

  // ── Computed ─────────────────────────────────────────────────────────────────
  const recommendation = computed(() => currentAnalysis.value?.recommendation ?? null)
  const confidence = computed(() => currentAnalysis.value?.recommendation?.confidence ?? 0)
  const isCached = computed(() => currentAnalysis.value?.cached ?? false)
  const hasResult = computed(() => currentAnalysis.value?.status === 'completed')

  // ── Actions ──────────────────────────────────────────────────────────────────
  async function analyzeSymbol(symbol: string, forceRefresh = false): Promise<void> {
    isLoading.value = true
    error.value = null
    lastSymbol.value = symbol.toUpperCase()

    try {
      currentAnalysis.value = await analyzeSync(symbol, forceRefresh)
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : 'Analysis failed. Please try again.'
      currentAnalysis.value = null
    } finally {
      isLoading.value = false
    }
  }

  async function loadCached(symbol: string): Promise<void> {
    isLoading.value = true
    error.value = null

    try {
      currentAnalysis.value = await getCachedAnalysis(symbol)
      lastSymbol.value = symbol.toUpperCase()
    } catch {
      // Cache miss is expected; not an error for the user
      currentAnalysis.value = null
    } finally {
      isLoading.value = false
    }
  }

  async function refresh(): Promise<void> {
    if (!lastSymbol.value) return
    if (lastSymbol.value) {
      await invalidateCache(lastSymbol.value)
    }
    await analyzeSymbol(lastSymbol.value, true)
  }

  function clear(): void {
    currentAnalysis.value = null
    error.value = null
    lastSymbol.value = ''
  }

  return {
    // state
    currentAnalysis,
    isLoading,
    error,
    lastSymbol,
    // computed
    recommendation,
    confidence,
    isCached,
    hasResult,
    // actions
    analyzeSymbol,
    loadCached,
    refresh,
    clear,
  }
})
