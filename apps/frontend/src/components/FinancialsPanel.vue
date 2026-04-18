<template>
  <div class="card">
    <div class="card-header">
      <span class="card-title">{{ t('fin.title') }}</span>
      <div class="flex gap-1">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          class="rounded-md px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider transition"
          :class="
            activeTab === tab.id
              ? 'bg-white/[0.08] text-white'
              : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]'
          "
          @click="activeTab = tab.id"
        >
          {{ t(tab.labelKey) }}
        </button>
      </div>
    </div>

    <!-- Periods header -->
    <div
      v-if="statements.periods.length"
      class="mb-1 grid items-end gap-2 text-[10px] font-semibold uppercase tracking-wider text-[var(--color-text-muted)]"
      :style="gridStyle"
    >
      <span></span>
      <span v-for="period in displayPeriods" :key="period" class="text-right">
        {{ formatPeriod(period) }}
      </span>
    </div>

    <!-- Rows -->
    <div class="space-y-px">
      <div
        v-for="item in activeItems"
        :key="item.label"
        class="grid items-center gap-2 rounded bg-white/[0.02] px-2 py-1.5 text-xs"
        :style="gridStyle"
      >
        <span class="truncate text-[var(--color-text-secondary)]">{{ cleanLabel(item.label) }}</span>
        <span
          v-for="period in displayPeriods"
          :key="period"
          class="text-right font-semibold tabular-nums"
          :class="valueColor(item.values[period])"
        >
          {{ formatValue(item.values[period]) }}
        </span>
      </div>
    </div>

    <p v-if="activeItems.length === 0" class="py-4 text-center text-xs text-[var(--color-text-muted)]">
      {{ t('fin.no.data') }}
    </p>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { FinancialStatements, FinancialLineItem } from '@/services/api'
import { t } from '@/locales'

const props = defineProps<{
  statements: FinancialStatements
  symbol: string
}>()

type TabId = 'balance' | 'income' | 'cashflow'

const activeTab = ref<TabId>('balance')

const tabs = [
  { id: 'balance' as const, labelKey: 'fin.balance' },
  { id: 'income' as const, labelKey: 'fin.income' },
  { id: 'cashflow' as const, labelKey: 'fin.cashflow' },
]

const activeItems = computed((): FinancialLineItem[] => {
  switch (activeTab.value) {
    case 'balance': return props.statements.balance_sheet
    case 'income': return props.statements.income_statement
    case 'cashflow': return props.statements.cash_flow
    default: return []
  }
})

const displayPeriods = computed(() => props.statements.periods.slice(0, 4))

const gridStyle = computed(() => ({
  gridTemplateColumns: `minmax(140px, 1fr) ${displayPeriods.value.map(() => 'minmax(70px, 1fr)').join(' ')}`,
}))

function formatPeriod(period: string): string {
  const d = new Date(period)
  if (isNaN(d.getTime())) return period
  return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short' })
}

function cleanLabel(label: string): string {
  return label
    .replace(/Net Minority Interest/g, '')
    .replace(/And Cash Equivalents/g, '& Equiv.')
    .trim()
}

function formatValue(value: number | null | undefined): string {
  if (value === null || value === undefined) return '—'
  const abs = Math.abs(value)
  const sign = value < 0 ? '-' : ''
  if (abs >= 1e12) return `${sign}${(abs / 1e12).toFixed(1)}T`
  if (abs >= 1e9) return `${sign}${(abs / 1e9).toFixed(1)}B`
  if (abs >= 1e6) return `${sign}${(abs / 1e6).toFixed(0)}M`
  if (abs >= 1e3) return `${sign}${(abs / 1e3).toFixed(0)}K`
  return `${sign}${abs.toFixed(0)}`
}

function valueColor(value: number | null | undefined) {
  if (value === null || value === undefined) return 'text-[var(--color-text-muted)]'
  if (value < 0) return 'text-red-400'
  return 'text-white'
}
</script>
