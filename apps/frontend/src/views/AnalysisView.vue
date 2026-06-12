<template>
  <div class="flex min-h-screen flex-col items-center gap-3 px-4 pb-16 pt-10 sm:px-6 lg:px-8">
    <!-- Spinner (centered overlay) -->
    <LoadingSpinner v-if="store.isLoading" :symbol="store.lastSymbol" :message="store.loadingMessage" :steps="store.loadingSteps" />

    <!-- Quick picks on initial state -->
    <section v-if="!store.isLoading && !store.currentAnalysis" class="mx-auto w-full max-w-6xl pt-10">
      <!-- Top absolute controls for homepage -->
      <div class="absolute right-4 top-4 z-10 flex gap-2 sm:right-8 sm:top-8">
        <div class="flex items-center rounded-lg border border-white/[0.08] bg-white/[0.04] p-0.5 text-xs font-semibold">
          <button
            class="rounded-md px-2 py-1.5 transition"
            :class="store.language === 'en' ? 'bg-white/[0.1] text-white' : 'text-[var(--color-text-muted)] hover:text-white'"
            @click="store.changeLanguage('en')"
          >EN</button>
          <button
            class="rounded-md px-2 py-1.5 transition"
            :class="store.language === 'tr' ? 'bg-white/[0.1] text-white' : 'text-[var(--color-text-muted)] hover:text-white'"
            @click="store.changeLanguage('tr')"
          >TR</button>
        </div>
      </div>

      <div class="mb-10 text-center">
        <span class="badge badge-neutral mb-4 inline-flex text-[10px] tracking-widest">{{ t('nav.agent') }}</span>
        <h1 class="text-3xl font-bold tracking-tight text-[var(--color-text)] sm:text-4xl">
          {{ t('nav.market.overview') }}
        </h1>
        <p class="mt-3 text-sm leading-relaxed text-[var(--color-text-muted)]">
          {{ t('nav.select.ticker') }}
        </p>
        <div class="mx-auto mt-6 flex max-w-md flex-col items-center gap-3">
          <SymbolSearch class="w-full" :is-loading="store.isLoading" compact @analyze="handleAnalyze" />
          <button
            class="flex items-center gap-2 rounded-lg border border-white/[0.08] bg-white/[0.03] px-4 py-2 text-sm font-medium text-[var(--color-text-secondary)] transition hover:border-green-500/30 hover:bg-green-500/10 hover:text-green-400"
            @click="isAdvisorOpen = !isAdvisorOpen"
          >
            <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
            {{ t('advisor.open') }}
          </button>
        </div>
      </div>

      <!-- Portfolio Advisor panel -->
      <div v-if="isAdvisorOpen" class="mx-auto mb-8 w-full max-w-2xl">
        <PortfolioAdvisor @analyze="handleAnalyze" />
      </div>

      <StockScreenerList :is-loading="store.isLoading" @select="handleAnalyze" />
    </section>

    <!-- Results -->
    <template v-if="!store.isLoading && store.hasResult && store.currentAnalysis">
      <!-- Sticky top bar with search + symbol aligned with 7xl container -->
      <header class="sticky top-0 z-30 -mx-4 w-[calc(100%+2rem)] border-b border-white/[0.06] bg-[var(--color-bg)]/80 py-3 backdrop-blur-xl sm:-mx-6 sm:w-[calc(100%+3rem)] px-4 sm:px-6 lg:-mx-8 lg:w-[calc(100%+4rem)] lg:px-8">
        <div class="mx-auto flex w-full max-w-7xl items-center gap-3">
          <!-- Return to Homepage Button -->
          <button 
            @click="store.currentAnalysis = null" 
            class="hidden shrink-0 items-center justify-center rounded-lg border border-white/[0.08] bg-white/[0.04] p-2 text-white hover:bg-white/[0.08] transition sm:flex mr-1"
            title="Return to Homepage"
          >
            <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
            </svg>
          </button>

          <SymbolSearch :is-loading="store.isLoading" compact @analyze="handleAnalyze" />
          
          <div class="ml-auto flex items-center gap-2">
            <!-- Mobile Return to Homepage Button -->
            <button 
              @click="store.currentAnalysis = null" 
              class="flex sm:hidden shrink-0 items-center justify-center rounded-lg border border-white/[0.08] bg-white/[0.04] p-2 text-[var(--color-text-secondary)] hover:text-white transition"
              title="Return to Homepage"
            >
              <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
              </svg>
            </button>
            
            <!-- Language Toggle -->
            <div class="flex items-center rounded-lg border border-white/[0.08] bg-white/[0.04] p-0.5 text-xs font-semibold">
              <button
                class="rounded-md px-2 py-1.5 transition"
                :class="store.language === 'en' ? 'bg-white/[0.1] text-white' : 'text-[var(--color-text-muted)] hover:text-white'"
                @click="store.changeLanguage('en')"
              >EN</button>
              <button
                class="rounded-md px-2 py-1.5 transition"
                :class="store.language === 'tr' ? 'bg-white/[0.1] text-white' : 'text-[var(--color-text-muted)] hover:text-white'"
                @click="store.changeLanguage('tr')"
              >TR</button>
            </div>

            <button
              class="shrink-0 rounded-lg border border-white/[0.08] bg-white/[0.04] px-3 py-2 text-xs font-medium text-[var(--color-text-secondary)] transition hover:bg-white/[0.08] hover:text-white disabled:opacity-40"
              :disabled="store.isLoading"
              @click="store.refresh()"
            >
              {{ t('nav.refresh') }}
            </button>

            <button
              class="shrink-0 inline-flex items-center gap-1.5 rounded-lg border border-blue-500/30 bg-blue-500/10 px-3 py-2 text-xs font-semibold text-blue-400 transition hover:border-blue-500/50 hover:bg-blue-500/20"
              @click="goToTrading()"
              title="Go to Trading Dashboard with this analysis"
            >
              <svg class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              <span class="hidden sm:inline">Trade</span>
            </button>
          </div>
        </div>
      </header>

      <!-- Error banner -->
      <div
        v-if="store.error"
        class="w-full max-w-7xl rounded-lg border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-400"
      >
        {{ store.error }}
      </div>

      <div class="mx-auto w-full max-w-7xl">
        <!-- Company Header + Recommendation -->
        <div class="mb-4 grid gap-4 lg:grid-cols-[1fr_auto]">
          <CompanyHeader
            :profile="store.currentAnalysis.company_profile"
            :recommendation="store.currentAnalysis.recommendation"
          />
          <RecommendationCard
            v-if="store.currentAnalysis.recommendation"
            :recommendation="store.currentAnalysis.recommendation"
            :cached="store.isCached"
          />
        </div>

        <!-- Analysis Grid -->
        <div class="grid gap-4 lg:grid-cols-2">
          <TechnicalAnalysisPanel
            v-if="store.currentAnalysis.technical_analysis"
            :analysis="store.currentAnalysis.technical_analysis"
          />
          <RiskAnalysisPanel
            v-if="store.currentAnalysis.risk_analysis"
            :analysis="store.currentAnalysis.risk_analysis"
          />
          <NewsAnalysisPanel
            v-if="store.currentAnalysis.news_analysis"
            :analysis="store.currentAnalysis.news_analysis"
          />
          <FinancialsPanel
            v-if="store.currentAnalysis.financial_statements"
            :statements="store.currentAnalysis.financial_statements"
            :symbol="store.currentAnalysis.symbol"
          />
        </div>

        <JudgeVerdictCard
          v-if="store.currentAnalysis.judge_verdict"
          class="mt-4"
          :verdict="store.currentAnalysis.judge_verdict"
        />
      </div>

      <!-- Chatbot FAB & Panel -->
      <div v-if="store.hasResult" class="fixed z-40 transition-all duration-300" :class="isChatFullscreen ? 'inset-4 sm:inset-6 md:inset-10' : 'bottom-6 right-6'">
        <!-- Always render button to keep layout simple, hide when chat is open -->
        <button
          v-if="!isChatOpen"
          @click="isChatOpen = true"
          class="flex items-center justify-center gap-2 rounded-full border border-green-500/30 bg-green-600 px-5 py-3.5 font-semibold text-white shadow-lg shadow-green-900/20 transition hover:bg-green-500 hover:scale-105"
        >
          <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" class="w-5 h-5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
          {{ t('nav.ask.agent') }}
        </button>
        
        <div v-if="isChatOpen" class="origin-bottom-right animate-in zoom-in-95 fade-in duration-200" :class="isChatFullscreen ? 'w-full h-full' : 'w-[380px] h-[600px] max-h-[calc(100vh-8rem)] max-w-[calc(100vw-2rem)]'">
          <AnalysisChatbot
            v-if="store.lastSymbol"
            class="h-full w-full"
            :symbol="store.lastSymbol"
            :language="store.language"
            @toggle-fullscreen="isChatFullscreen = !isChatFullscreen"
            @close="isChatOpen = false"
          />
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAnalysisStore } from '@/stores/analysis'
import { useTradingStore } from '@/stores/trading'
import { t } from '@/locales'
import SymbolSearch from '@/components/SymbolSearch.vue'
import StockScreenerList from '@/components/StockScreenerList.vue'
import CompanyHeader from '@/components/CompanyHeader.vue'
import RecommendationCard from '@/components/RecommendationCard.vue'
import TechnicalAnalysisPanel from '@/components/TechnicalAnalysisPanel.vue'
import NewsAnalysisPanel from '@/components/NewsAnalysisPanel.vue'
import RiskAnalysisPanel from '@/components/RiskAnalysisPanel.vue'
import FinancialsPanel from '@/components/FinancialsPanel.vue'
import JudgeVerdictCard from '@/components/JudgeVerdictCard.vue'
import AnalysisChatbot from '@/components/AnalysisChatbot.vue'
import LoadingSpinner from '@/components/LoadingSpinner.vue'
import PortfolioAdvisor from '@/components/PortfolioAdvisor.vue'

const store = useAnalysisStore()
const router = useRouter()
const tradingStore = useTradingStore()

async function goToTrading() {
  const symbol = store.lastSymbol
  if (symbol) {
    await tradingStore.addSymbol(symbol)
    if (tradingStore.status?.running) {
      tradingStore.runCycleNow()
    }
  }
  router.push('/trading')
}
const isChatOpen = ref(false)
const isChatFullscreen = ref(false)
const isAdvisorOpen = ref(false)

// Close chat automatically if user searches a different symbol
watch(() => store.lastSymbol, () => {
  isChatOpen.value = false
})

async function handleAnalyze(symbol: string) {
  await store.analyzeSymbol(symbol)
}
</script>
