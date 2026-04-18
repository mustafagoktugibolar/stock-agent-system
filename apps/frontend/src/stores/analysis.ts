import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { analyzeSync, getCachedAnalysis, invalidateCache, client } from '@/services/api'
import { getLanguage, setLanguage, t } from '@/locales'
import type { Language } from '@/locales'
import type { AnalysisResponse } from '@/services/api'

export const useAnalysisStore = defineStore('analysis', () => {
  // ── State ───────────────────────────────────────────────────────────────────
  const currentAnalysis = ref<AnalysisResponse | null>(null)
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  const lastSymbol = ref<string>('')
  const language = ref<Language>(getLanguage())
  const loadingMessage = ref('')
  const loadingSteps = ref<{ label: string; done: boolean }[]>([])

  function resetSteps() {
    loadingMessage.value = t('nav.agent') + '...'
    loadingSteps.value = [
      { label: 'Fundamentals', done: false },
      { label: 'Technical', done: false },
      { label: 'News', done: false },
      { label: 'Risk', done: false },
      { label: 'Supervisor', done: false },
    ]
  }

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
    resetSteps()

    let ws: WebSocket | null = null
    try {
      const baseURL = (client.defaults.baseURL || window.location.origin).replace(/^http/, 'ws')
      ws = new WebSocket(`${baseURL}/api/v1/ws/analysis/${symbol}`)
      
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          if (data && data.agent) {
             const mapping: Record<string, string> = {
                'fundamentals_agent': 'Fundamentals',
                'technical_agent': 'Technical',
                'news_agent': 'News',
                'risk_agent': 'Risk',
                'supervisor_agent': 'Supervisor',
             }
             const stepName = mapping[data.agent]
             if (stepName) {
                const step = loadingSteps.value.find(s => s.label === stepName)
                if (step) step.done = true
                loadingMessage.value = `Completed ${stepName} analysis...`
             }
          }
        } catch (e) {}
      }

      currentAnalysis.value = await analyzeSync(symbol, language.value, forceRefresh)
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : 'Analysis failed. Please try again.'
      currentAnalysis.value = null
    } finally {
      if (ws) ws.close()
      isLoading.value = false
    }
  }

  async function loadCached(symbol: string): Promise<void> {
    isLoading.value = true
    error.value = null

    try {
      currentAnalysis.value = await getCachedAnalysis(symbol, language.value)
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
      await invalidateCache(lastSymbol.value, language.value)
    }
    await analyzeSymbol(lastSymbol.value, true)
  }

  function clear(): void {
    currentAnalysis.value = null
    error.value = null
    lastSymbol.value = ''
  }

  function changeLanguage(lang: Language): void {
    language.value = lang
    setLanguage(lang)
    if (lastSymbol.value) {
      analyzeSymbol(lastSymbol.value, true)
    } else {
      window.location.reload()
    }
  }

  return {
    // state
    currentAnalysis,
    isLoading,
    error,
    lastSymbol,
    language,
    loadingMessage,
    loadingSteps,
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
    changeLanguage,
  }
})
