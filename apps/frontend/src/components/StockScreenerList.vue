<template>
  <div class="space-y-6">
    <!-- Search input -->
    <div class="relative">
      <input
        v-model="searchQuery"
        type="text"
        placeholder="Search stocks by name or ticker..."
        class="w-full rounded-xl border border-white/[0.06] bg-white/[0.03] px-4 py-3 pr-10 text-sm text-white placeholder-[var(--color-text-muted)] outline-none ring-0 transition focus:border-green-500/40 focus:bg-white/[0.05]"
      />
      <div class="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2">
        <svg v-if="!isSearching" class="h-4 w-4 text-[var(--color-text-muted)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0z" />
        </svg>
        <svg v-else class="h-4 w-4 animate-spin text-green-400" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
        </svg>
      </div>
    </div>

    <!-- Search results -->
    <div v-if="searchResults.length > 0">
      <h3 class="mb-3 text-sm font-semibold uppercase tracking-wider text-green-400">
        Search Results
      </h3>
      <div class="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-5">
        <button
          v-for="stock in searchResults"
          :key="stock.symbol"
          class="group flex flex-col items-start rounded-xl border border-green-500/20 bg-green-500/5 p-4 text-left transition hover:border-green-500/40 hover:bg-green-500/10 disabled:opacity-40"
          :disabled="isLoading"
          @click="$emit('select', stock.symbol)"
        >
          <div class="flex w-full items-center justify-between">
            <span class="font-bold text-white group-hover:text-green-400">{{ stock.symbol }}</span>
            <span class="rounded bg-white/[0.06] px-1.5 py-0.5 text-[10px] font-semibold text-[var(--color-text-muted)] group-hover:bg-green-500/20 group-hover:text-green-300">
              {{ stock.exchange }}
            </span>
          </div>
          <span class="mt-1 truncate w-full text-xs text-[var(--color-text-muted)] group-hover:text-[var(--color-text-secondary)]">
            {{ stock.name || '—' }}
          </span>
        </button>
      </div>
    </div>

    <p v-else-if="searchQuery.length >= 2 && !isSearching" class="text-center text-xs text-[var(--color-text-muted)] py-2">
      No results for "{{ searchQuery }}"
    </p>

    <!-- Featured categories -->
    <div v-for="category in categories" :key="category.title">
      <h3 class="mb-3 text-sm font-semibold uppercase tracking-wider text-[var(--color-text-secondary)]">
        {{ category.title }}
      </h3>
      <div class="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-5">
        <button
          v-for="stock in category.stocks"
          :key="stock.symbol"
          class="group flex flex-col items-start rounded-xl border border-white/[0.04] bg-white/[0.02] p-4 text-left transition hover:border-green-500/30 hover:bg-green-500/10 disabled:opacity-40"
          :disabled="isLoading"
          @click="$emit('select', stock.symbol)"
        >
          <div class="flex w-full items-center justify-between">
            <span class="font-bold text-white group-hover:text-green-400">{{ stock.symbol }}</span>
            <span class="rounded bg-white/[0.06] px-1.5 py-0.5 text-[10px] font-semibold text-[var(--color-text-muted)] group-hover:bg-green-500/20 group-hover:text-green-300">
              {{ stock.exchange }}
            </span>
          </div>
          <span class="mt-1 truncate w-full text-xs text-[var(--color-text-muted)] group-hover:text-[var(--color-text-secondary)]">
            {{ stock.name }}
          </span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { searchStocks, type StockSearchResult } from '@/services/api'

defineProps<{ isLoading: boolean }>()
defineEmits<{ (e: 'select', symbol: string): void }>()

const searchQuery = ref('')
const searchResults = ref<StockSearchResult[]>([])
const isSearching = ref(false)

let debounceTimer: ReturnType<typeof setTimeout> | null = null

watch(searchQuery, (q) => {
  if (debounceTimer) clearTimeout(debounceTimer)
  if (q.length < 2) {
    searchResults.value = []
    return
  }
  debounceTimer = setTimeout(async () => {
    isSearching.value = true
    try {
      searchResults.value = await searchStocks(q)
    } catch {
      searchResults.value = []
    } finally {
      isSearching.value = false
    }
  }, 300)
})

const categories = [
  {
    title: 'US Mega Cap Tech',
    stocks: [
      { symbol: 'AAPL', name: 'Apple Inc.', exchange: 'NASDAQ' },
      { symbol: 'MSFT', name: 'Microsoft Corp.', exchange: 'NASDAQ' },
      { symbol: 'NVDA', name: 'NVIDIA Corp.', exchange: 'NASDAQ' },
      { symbol: 'GOOGL', name: 'Alphabet Inc.', exchange: 'NASDAQ' },
      { symbol: 'AMZN', name: 'Amazon.com Inc.', exchange: 'NASDAQ' },
      { symbol: 'META', name: 'Meta Platforms', exchange: 'NASDAQ' },
      { symbol: 'TSLA', name: 'Tesla Inc.', exchange: 'NASDAQ' },
      { symbol: 'AVGO', name: 'Broadcom Inc.', exchange: 'NASDAQ' },
      { symbol: 'AMD', name: 'Advanced Micro Devices', exchange: 'NASDAQ' },
      { symbol: 'TSM', name: 'Taiwan Semiconductor', exchange: 'NYSE' },
    ],
  },
  {
    title: 'BIST 30 Leaders',
    stocks: [
      { symbol: 'THYAO.IS', name: 'Turk Hava Yollari', exchange: 'BIST' },
      { symbol: 'KCHOL.IS', name: 'Koc Holding', exchange: 'BIST' },
      { symbol: 'TUPRS.IS', name: 'Tupras', exchange: 'BIST' },
      { symbol: 'AKBNK.IS', name: 'Akbank', exchange: 'BIST' },
      { symbol: 'GARAN.IS', name: 'Garanti Bankasi', exchange: 'BIST' },
      { symbol: 'YKBNK.IS', name: 'Yapi Kredi Bankasi', exchange: 'BIST' },
      { symbol: 'ISCTR.IS', name: 'Is Bankasi (C)', exchange: 'BIST' },
      { symbol: 'ASELS.IS', name: 'Aselsan', exchange: 'BIST' },
      { symbol: 'BIMAS.IS', name: 'BIM Birlesik Magazalar', exchange: 'BIST' },
      { symbol: 'SAHOL.IS', name: 'Sabanci Holding', exchange: 'BIST' },
    ],
  },
  {
    title: 'Global ETF & Indices',
    stocks: [
      { symbol: 'SPY', name: 'SPDR S&P 500 ETF', exchange: 'NYSEARCA' },
      { symbol: 'QQQ', name: 'Invesco QQQ Trust', exchange: 'NASDAQ' },
      { symbol: 'DIA', name: 'SPDR Dow Jones', exchange: 'NYSEARCA' },
      { symbol: 'IWM', name: 'iShares Russell 2000', exchange: 'NYSEARCA' },
      { symbol: 'XLF', name: 'Financial Select Sector', exchange: 'NYSEARCA' },
    ],
  },
]
</script>
