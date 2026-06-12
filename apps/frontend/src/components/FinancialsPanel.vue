<template>
  <div class="card">
    <div class="card-header">
      <span class="card-title">{{ t('fin.title') }}</span>
      <div class="flex flex-wrap justify-end gap-2">
        <div v-if="availableStatementModes.length > 1" class="flex gap-1">
          <button
            v-for="mode in availableStatementModes"
            :key="mode.id"
            class="rounded-md px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider transition"
            :class="
              statementMode === mode.id
                ? 'bg-emerald-500/15 text-emerald-300'
                : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]'
            "
            @click="statementMode = mode.id"
          >
            {{ mode.label }}
          </button>
        </div>
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
    </div>

    <!-- Key Ratios grid -->
    <template v-if="activeTab === 'ratios'">
      <div v-if="hasRatios" class="grid grid-cols-3 gap-2">
        <div
          v-for="ratio in ratioCards"
          :key="ratio.key"
          class="rounded-lg bg-white/[0.03] px-3 py-2.5"
        >
          <p class="mb-1 text-[10px] uppercase tracking-wider text-[var(--color-text-muted)]">
            {{ ratio.label }}
          </p>
          <p
            class="text-base font-semibold tabular-nums leading-none"
            :class="ratio.colorClass"
          >
            {{ ratio.display }}
          </p>
        </div>
      </div>
      <p v-else class="py-4 text-center text-xs text-[var(--color-text-muted)]">
        {{ t('fin.no.data') }}
      </p>
    </template>

    <!-- Statement tables -->
    <template v-else>
      <!-- Periods header -->
      <div
        v-if="displayPeriods.length"
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
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { FinancialStatements, FinancialLineItem } from '@/services/api'
import { t } from '@/locales'

const props = defineProps<{
  statements: FinancialStatements
  symbol: string
}>()

type TabId = 'ratios' | 'balance' | 'income' | 'cashflow'

const activeTab = ref<TabId>('ratios')
type StatementMode = 'quarterly' | 'annual'

const tabs = [
  { id: 'ratios' as const, labelKey: 'fin.ratios' },
  { id: 'balance' as const, labelKey: 'fin.balance' },
  { id: 'income' as const, labelKey: 'fin.income' },
  { id: 'cashflow' as const, labelKey: 'fin.cashflow' },
]

const hasQuarterly = computed(() => Boolean(props.statements.quarterly_periods?.length))
const hasAnnual = computed(() => Boolean(props.statements.annual_periods?.length))

function defaultStatementMode(): StatementMode {
  if (props.statements.period_type === 'quarterly' || hasQuarterly.value) return 'quarterly'
  return 'annual'
}

const statementMode = ref<StatementMode>(defaultStatementMode())

watch(
  () => props.statements.symbol,
  () => {
    statementMode.value = defaultStatementMode()
  }
)

const availableStatementModes = computed(() => {
  const modes: { id: StatementMode; label: string }[] = []
  if (hasQuarterly.value) modes.push({ id: 'quarterly', label: t('fin.quarterly') })
  if (hasAnnual.value) modes.push({ id: 'annual', label: t('fin.annual') })
  return modes
})

const activeStatementSet = computed(() => {
  if (statementMode.value === 'annual' && hasAnnual.value) {
    return {
      balance_sheet: props.statements.annual_balance_sheet ?? [],
      income_statement: props.statements.annual_income_statement ?? [],
      cash_flow: props.statements.annual_cash_flow ?? [],
      periods: props.statements.annual_periods ?? [],
    }
  }
  if (hasQuarterly.value) {
    return {
      balance_sheet: props.statements.quarterly_balance_sheet ?? [],
      income_statement: props.statements.quarterly_income_statement ?? [],
      cash_flow: props.statements.quarterly_cash_flow ?? [],
      periods: props.statements.quarterly_periods ?? [],
    }
  }
  return {
    balance_sheet: props.statements.balance_sheet,
    income_statement: props.statements.income_statement,
    cash_flow: props.statements.cash_flow,
    periods: props.statements.periods,
  }
})

// ── Ratio display config ───────────────────────────────────────────────────────

interface RatioConfig {
  key: string
  label: string
  format: 'pct' | 'ratio' | 'pct_raw'
  higherIsBetter: boolean | null  // null = neutral (just show sign)
}

const RATIO_CONFIGS: RatioConfig[] = [
  { key: 'gross_margin',         label: 'Gross Margin',     format: 'pct',     higherIsBetter: true },
  { key: 'net_margin',           label: 'Net Margin',       format: 'pct',     higherIsBetter: true },
  { key: 'roe',                  label: 'ROE',              format: 'pct',     higherIsBetter: true },
  { key: 'roa',                  label: 'ROA',              format: 'pct',     higherIsBetter: true },
  { key: 'fcf_margin',           label: 'FCF Margin',       format: 'pct',     higherIsBetter: true },
  { key: 'current_ratio',        label: 'Current Ratio',    format: 'ratio',   higherIsBetter: true },
  { key: 'debt_to_equity',       label: 'Debt / Equity',    format: 'ratio',   higherIsBetter: false },
  { key: 'revenue_growth_yoy',   label: 'Rev. Growth YoY',  format: 'pct',     higherIsBetter: true },
  { key: 'net_income_growth_yoy',label: 'NI Growth YoY',    format: 'pct',     higherIsBetter: true },
]

const hasRatios = computed(() =>
  RATIO_CONFIGS.some(c => props.statements.computed_ratios?.[c.key] != null)
)

const ratioCards = computed(() =>
  RATIO_CONFIGS
    .filter(c => props.statements.computed_ratios?.[c.key] != null)
    .map(c => {
      const raw = props.statements.computed_ratios[c.key] as number
      return {
        key: c.key,
        label: c.label,
        display: formatRatio(raw, c.format),
        colorClass: ratioColor(raw, c.higherIsBetter),
      }
    })
)

function formatRatio(value: number, format: RatioConfig['format']): string {
  if (format === 'pct') return `${(value * 100).toFixed(1)}%`
  if (format === 'ratio') return `${value.toFixed(2)}x`
  return `${(value * 100).toFixed(1)}%`
}

function ratioColor(value: number, higherIsBetter: boolean | null): string {
  if (higherIsBetter === null) return value >= 0 ? 'text-green-400' : 'text-red-400'
  if (higherIsBetter) return value >= 0 ? 'text-green-400' : 'text-red-400'
  // lower is better: positive value (e.g. high D/E) → warn
  return value > 2 ? 'text-red-400' : value > 1 ? 'text-amber-400' : 'text-green-400'
}

// ── Statement table helpers ────────────────────────────────────────────────────

const activeItems = computed((): FinancialLineItem[] => {
  switch (activeTab.value) {
    case 'balance': return activeStatementSet.value.balance_sheet
    case 'income': return activeStatementSet.value.income_statement
    case 'cashflow': return activeStatementSet.value.cash_flow
    default: return []
  }
})

const displayPeriods = computed(() => activeStatementSet.value.periods.slice(0, 4))

const gridStyle = computed(() => ({
  gridTemplateColumns: `minmax(140px, 1fr) ${displayPeriods.value.map(() => 'minmax(70px, 1fr)').join(' ')}`,
}))

function formatPeriod(period: string): string {
  const d = new Date(period)
  if (isNaN(d.getTime())) return period
  if (statementMode.value === 'quarterly') {
    const quarter = Math.floor(d.getUTCMonth() / 3) + 1
    return `Q${quarter} ${d.getUTCFullYear()}`
  }
  return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', timeZone: 'UTC' })
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
