<template>
  <form
    :class="compact ? 'flex items-center gap-2' : 'space-y-4'"
    @submit.prevent="handleSubmit"
  >
    <!-- Market selector (only in expanded mode) -->
    <div v-if="!compact" class="flex gap-2">
      <button
        v-for="option in marketOptions"
        :key="option.id"
        type="button"
        class="flex-1 rounded-lg border px-3 py-2.5 text-left text-xs transition disabled:opacity-40"
        :class="
          market === option.id
            ? 'border-green-500/30 bg-green-500/10 text-green-400'
            : 'border-white/[0.06] bg-white/[0.03] text-[var(--color-text-secondary)] hover:border-white/[0.12] hover:text-white'
        "
        :disabled="isLoading"
        @click="market = option.id"
      >
        <span class="block font-semibold">{{ option.label }}</span>
        <span class="block text-[10px] text-[var(--color-text-muted)]">{{ option.hint }}</span>
      </button>
    </div>

    <!-- Input -->
    <div :class="compact ? 'flex items-center gap-2' : 'flex items-end gap-2'">
      <div class="relative flex-1">
        <input
          id="symbol-input"
          v-model="symbol"
          type="text"
          :placeholder="compact ? 'Search ticker...' : activeMarket.placeholder"
          :class="[
            'w-full rounded-lg border border-white/[0.08] bg-white/[0.04] font-semibold uppercase text-white outline-none transition placeholder:font-normal placeholder:normal-case placeholder:text-[var(--color-text-muted)] focus:border-green-500/40 focus:ring-1 focus:ring-green-500/20 disabled:opacity-40',
            compact ? 'h-9 px-3 text-sm' : 'h-12 px-4 text-base',
          ]"
          :disabled="isLoading"
          maxlength="24"
          spellcheck="false"
          autocomplete="off"
        />
      </div>
      <button
        type="submit"
        :disabled="isLoading || !normalizedSymbol"
        :class="[
          'shrink-0 rounded-lg bg-green-600 font-semibold text-white transition hover:bg-green-500 disabled:cursor-not-allowed disabled:opacity-40',
          compact ? 'h-9 px-4 text-xs' : 'h-12 px-6 text-sm',
        ]"
      >
        <span v-if="isLoading" class="flex items-center gap-1.5">
          <svg class="h-3.5 w-3.5 animate-spin" viewBox="0 0 24 24" fill="none"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" /><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" /></svg>
          Analyzing
        </span>
        <span v-else>{{ compact ? 'Go' : `Analyze ${normalizedSymbol || 'symbol'}` }}</span>
      </button>
    </div>

    <!-- Quick picks (only in expanded mode) -->
    <div v-if="!compact" class="space-y-2">
      <p class="text-xs font-medium text-[var(--color-text-muted)]">Quick picks</p>
      <div class="flex flex-wrap gap-1.5">
        <button
          v-for="example in activeMarket.examples"
          :key="example"
          type="button"
          class="rounded-md border border-white/[0.06] bg-white/[0.03] px-2.5 py-1.5 text-xs font-semibold text-[var(--color-text-secondary)] transition hover:border-green-500/30 hover:bg-green-500/10 hover:text-green-400 disabled:opacity-40"
          :disabled="isLoading"
          @click="useExample(example)"
        >
          {{ example }}
        </button>
      </div>
    </div>
  </form>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'

type MarketId = 'nasdaq' | 'bist' | 'global'

interface MarketOption {
  id: MarketId
  label: string
  hint: string
  placeholder: string
  examples: string[]
}

defineProps<{
  isLoading: boolean
  compact?: boolean
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
    hint: 'US equities',
    placeholder: 'AAPL, NVDA, MSFT',
    examples: ['AAPL', 'NVDA', 'MSFT', 'TSLA', 'AMD'],
  },
  {
    id: 'bist',
    label: 'BIST',
    hint: '.IS symbols',
    placeholder: 'THYAO, GARAN, ASELS',
    examples: ['THYAO.IS', 'GARAN.IS', 'ASELS.IS', 'BIMAS.IS', 'TUPRS.IS'],
  },
  {
    id: 'global',
    label: 'Global',
    hint: 'Yahoo Finance',
    placeholder: 'BMW.DE, 7203.T',
    examples: ['BMW.DE', '7203.T', 'SHOP.TO', 'RELIANCE.NS', 'VOD.L'],
  },
]

const activeMarket = computed(
  () => marketOptions.find((o) => o.id === market.value) ?? marketOptions[0],
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
