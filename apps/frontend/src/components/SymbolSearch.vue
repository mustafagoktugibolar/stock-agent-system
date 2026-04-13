<template>
  <div class="space-y-5">
    <div class="grid gap-2 sm:grid-cols-3" aria-label="Market" role="group">
      <button
        v-for="option in marketOptions"
        :key="option.id"
        type="button"
        class="rounded-lg border px-4 py-3 text-left transition disabled:cursor-not-allowed disabled:opacity-60"
        :class="
          market === option.id
            ? 'border-emerald-500 bg-emerald-50 text-zinc-950 shadow-sm'
            : 'border-zinc-200 bg-white text-zinc-700 hover:border-zinc-300 hover:bg-zinc-50'
        "
        :disabled="isLoading"
        @click="market = option.id"
      >
        <span class="block text-sm font-semibold">{{ option.label }}</span>
        <span class="mt-1 block text-xs leading-5 text-zinc-500">{{ option.hint }}</span>
      </button>
    </div>

    <form class="grid gap-3 sm:grid-cols-[minmax(0,1fr)_auto]" @submit.prevent="handleSubmit">
      <div class="space-y-2">
        <label for="symbol-input" class="text-sm font-medium text-zinc-700">Ticker symbol</label>
        <input
          id="symbol-input"
          v-model="symbol"
          type="text"
          :placeholder="activeMarket.placeholder"
          class="h-14 w-full rounded-lg border border-zinc-300 bg-white px-4 text-base font-semibold uppercase text-zinc-950 shadow-sm outline-none transition placeholder:font-normal placeholder:normal-case placeholder:text-zinc-400 focus:border-emerald-500 focus:ring-4 focus:ring-emerald-100 disabled:bg-zinc-100"
          :disabled="isLoading"
          maxlength="24"
          spellcheck="false"
          autocomplete="off"
        />
        <p class="text-xs leading-5 text-zinc-500">{{ activeMarket.helper }}</p>
      </div>

      <button
        type="submit"
        :disabled="isLoading || !normalizedSymbol"
        class="h-14 w-full self-end rounded-lg bg-zinc-950 px-6 text-sm font-semibold text-white shadow-sm transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto"
      >
        <span v-if="isLoading" class="flex items-center gap-2">
          <svg class="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
          </svg>
          Analyzing
        </span>
        <span v-else>Analyze {{ normalizedSymbol || 'symbol' }}</span>
      </button>
    </form>

    <div class="space-y-2">
      <p class="text-sm font-medium text-zinc-700">Quick picks</p>
      <div class="flex flex-wrap gap-2">
        <button
          v-for="example in activeMarket.examples"
          :key="example"
          type="button"
          class="rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm font-semibold text-zinc-700 transition hover:border-emerald-500 hover:bg-emerald-50 hover:text-zinc-950 disabled:cursor-not-allowed disabled:opacity-60"
          :disabled="isLoading"
          @click="useExample(example)"
        >
          {{ example }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'

type MarketId = 'nasdaq' | 'bist' | 'global'

interface MarketOption {
  id: MarketId
  label: string
  hint: string
  placeholder: string
  helper: string
  examples: string[]
}

defineProps<{
  isLoading: boolean
}>()

const emit = defineEmits<{
  (e: 'analyze', symbol: string): void
}>()

const symbol = ref('')
const market = ref<MarketId>('nasdaq')

const marketOptions: MarketOption[] = [
  {
    id: 'nasdaq',
    label: 'NASDAQ',
    hint: 'US growth and mega-cap tickers',
    placeholder: 'AAPL, NVDA, MSFT',
    helper: 'Enter the ticker without an exchange prefix, for example NVDA.',
    examples: ['AAPL', 'NVDA', 'MSFT', 'TSLA', 'AMD'],
  },
  {
    id: 'bist',
    label: 'Borsa Istanbul',
    hint: 'Turkish equities with .IS symbols',
    placeholder: 'THYAO, GARAN, ASELS',
    helper: 'BIST entries are sent with .IS, for example THYAO.IS.',
    examples: ['THYAO.IS', 'GARAN.IS', 'ASELS.IS', 'BIMAS.IS', 'TUPRS.IS'],
  },
  {
    id: 'global',
    label: 'Other markets',
    hint: 'Yahoo Finance symbol format',
    placeholder: 'BMW.DE, 7203.T, RELIANCE.NS',
    helper: 'Use the Yahoo Finance exchange suffix for other markets.',
    examples: ['BMW.DE', '7203.T', 'SHOP.TO', 'RELIANCE.NS', 'VOD.L'],
  },
]

const activeMarket = computed(
  () => marketOptions.find((option) => option.id === market.value) ?? marketOptions[0],
)

const normalizedSymbol = computed(() => normalizeSymbol(symbol.value))

function normalizeSymbol(value: string): string {
  let next = value.trim().toUpperCase().replace(/\s+/g, '')
  next = next.replace(/^NASDAQ:/, '').replace(/^(BIST|IST):/, '')

  if (market.value === 'bist' && next && !next.includes('.')) {
    if (next.endsWith('IS') && next.length > 2) {
      return `${next.slice(0, -2)}.IS`
    }

    return `${next}.IS`
  }

  return next
}

function useExample(example: string) {
  symbol.value = example
  handleSubmit()
}

function handleSubmit() {
  const next = normalizedSymbol.value
  if (next) emit('analyze', next)
}
</script>
