<template>
  <div class="space-y-8">
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
defineProps<{ isLoading: boolean }>()
defineEmits<{ (e: 'select', symbol: string): void }>()

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
