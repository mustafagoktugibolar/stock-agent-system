<template>
  <main class="min-h-screen bg-[#f5f7f8] text-zinc-950">
    <section class="border-b border-zinc-200 bg-white">
      <div class="mx-auto grid max-w-7xl gap-8 px-4 py-8 sm:px-6 lg:grid-cols-[1.1fr_0.9fr] lg:px-8 lg:py-10">
        <div class="flex flex-col justify-center">
          <div class="mb-7 max-w-3xl">
            <p class="mb-3 inline-flex rounded-lg bg-emerald-50 px-3 py-1 text-sm font-semibold text-emerald-700">
              Multi-market AI research
            </p>
            <h1 class="max-w-2xl text-4xl font-bold leading-tight text-zinc-950 sm:text-5xl">
              Stock Analysis Agent
            </h1>
            <p class="mt-4 max-w-2xl text-base leading-7 text-zinc-600">
              Select NASDAQ, Borsa Istanbul, or another Yahoo Finance symbol and run one clean multi-agent analysis.
            </p>
          </div>

          <SymbolSearch :is-loading="store.isLoading" @analyze="handleAnalyze" />
        </div>

        <aside class="relative min-h-[360px] overflow-hidden rounded-lg bg-zinc-950 text-white shadow-sm">
          <img
            src="https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?auto=format&fit=crop&w=1400&q=80"
            alt="Market terminal with price charts"
            class="absolute inset-0 h-full w-full object-cover opacity-60"
          />
          <div class="absolute inset-0 bg-gradient-to-t from-zinc-950 via-zinc-950/75 to-zinc-950/10" />
          <div class="relative flex h-full min-h-[360px] flex-col justify-between p-6 sm:p-8">
            <div>
              <p class="text-sm font-semibold text-emerald-200">Coverage</p>
              <h2 class="mt-3 max-w-md text-3xl font-bold leading-tight">
                US tech, BIST 100, and global exchange suffixes.
              </h2>
            </div>

            <div class="border-y border-white/25 py-2">
              <div
                v-for="item in coverageItems"
                :key="item.label"
                class="flex items-center justify-between gap-4 py-3 text-sm"
              >
                <span class="font-semibold text-white">{{ item.label }}</span>
                <span class="text-right text-white/75">{{ item.symbols }}</span>
              </div>
            </div>
          </div>
        </aside>
      </div>
    </section>

    <section class="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
      <div
        v-if="store.error"
        class="mb-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
      >
        {{ store.error }}
      </div>

      <LoadingSpinner v-if="store.isLoading" :symbol="store.lastSymbol" />

      <template v-else-if="store.hasResult && store.currentAnalysis">
        <div
          class="grid gap-6"
          :class="store.recommendation ? 'lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]' : ''"
        >
          <div v-if="store.recommendation">
            <RecommendationCard
              :recommendation="store.recommendation"
              :cached="store.isCached"
            />
          </div>

          <div>
            <div class="mb-4 flex flex-wrap gap-2 border-b border-zinc-200">
              <button
                v-for="tab in tabs"
                :key="tab.id"
                class="-mb-px border-b-2 px-4 py-3 text-sm font-semibold transition"
                :class="
                  activeTab === tab.id
                    ? 'border-emerald-600 text-emerald-700'
                    : 'border-transparent text-zinc-500 hover:text-zinc-800'
                "
                @click="activeTab = tab.id"
              >
                {{ tab.label }}
              </button>
            </div>

            <Transition name="fade" mode="out-in">
              <TechnicalAnalysisPanel
                v-if="activeTab === 'technical' && store.currentAnalysis.technical_analysis"
                :analysis="store.currentAnalysis.technical_analysis"
                :key="'technical'"
              />
              <NewsAnalysisPanel
                v-else-if="activeTab === 'news' && store.currentAnalysis.news_analysis"
                :analysis="store.currentAnalysis.news_analysis"
                :key="'news'"
              />
              <RiskAnalysisPanel
                v-else-if="activeTab === 'risk' && store.currentAnalysis.risk_analysis"
                :analysis="store.currentAnalysis.risk_analysis"
                :key="'risk'"
              />
            </Transition>

            <div class="mt-6 flex justify-end">
              <button
                class="rounded-lg border border-zinc-300 bg-white px-4 py-2 text-sm font-semibold text-zinc-700 transition hover:border-emerald-500 hover:bg-emerald-50 hover:text-zinc-950 disabled:cursor-not-allowed disabled:opacity-60"
                @click="store.refresh()"
                :disabled="store.isLoading"
              >
                Refresh analysis
              </button>
            </div>
          </div>
        </div>
      </template>

      <div
        v-else-if="!store.isLoading && !store.currentAnalysis"
        class="grid gap-5 lg:grid-cols-[0.85fr_1.15fr]"
      >
        <div>
          <p class="text-lg font-semibold text-zinc-900">Ready for a symbol</p>
          <p class="mt-2 max-w-xl text-sm leading-6 text-zinc-600">
            Start with a NASDAQ ticker like NVDA, a Borsa Istanbul ticker like THYAO.IS, or any supported Yahoo Finance symbol.
          </p>
        </div>
        <div class="grid gap-3 sm:grid-cols-3">
          <div
            v-for="item in emptyStateItems"
            :key="item.label"
            class="rounded-lg border border-zinc-200 bg-white p-4 shadow-sm"
          >
            <p class="text-sm font-semibold text-zinc-900">{{ item.label }}</p>
            <p class="mt-2 text-sm leading-6 text-zinc-500">{{ item.copy }}</p>
          </div>
        </div>
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useAnalysisStore } from '@/stores/analysis'
import SymbolSearch from '@/components/SymbolSearch.vue'
import RecommendationCard from '@/components/RecommendationCard.vue'
import TechnicalAnalysisPanel from '@/components/TechnicalAnalysisPanel.vue'
import NewsAnalysisPanel from '@/components/NewsAnalysisPanel.vue'
import RiskAnalysisPanel from '@/components/RiskAnalysisPanel.vue'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const store = useAnalysisStore()
const activeTab = ref<'technical' | 'news' | 'risk'>('technical')

const tabs = [
  { id: 'technical' as const, label: 'Technical' },
  { id: 'news' as const, label: 'News & Sentiment' },
  { id: 'risk' as const, label: 'Risk' },
]

const coverageItems = [
  { label: 'NASDAQ', symbols: 'AAPL, NVDA, MSFT' },
  { label: 'Borsa Istanbul', symbols: 'THYAO.IS, GARAN.IS' },
  { label: 'Other markets', symbols: 'BMW.DE, 7203.T' },
]

const emptyStateItems = [
  { label: 'Choose market', copy: 'Pick NASDAQ, BIST, or the global symbol format.' },
  { label: 'Enter ticker', copy: 'Use exchange suffixes when the market needs them.' },
  { label: 'Run agents', copy: 'Technical, news, and risk analysis return together.' },
]

async function handleAnalyze(symbol: string) {
  activeTab.value = 'technical'
  await store.analyzeSymbol(symbol)
}
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
