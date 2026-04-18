<template>
  <div class="card">
    <div class="card-header">
      <span class="card-title">{{ t('risk.title') }}</span>
      <span class="badge capitalize" :class="riskBadge">{{ tVal(analysis.risk_level.replace('_', ' ')) }}</span>
    </div>

    <!-- Metrics grid -->
    <div class="mb-4 grid grid-cols-2 gap-2 sm:grid-cols-3">
      <div
        v-for="metric in analysis.metrics"
        :key="metric.metric_name"
        class="metric-box"
      >
        <p class="stat-label">{{ metric.metric_name }}</p>
        <p class="text-sm font-semibold text-white">{{ formatValue(metric) }}</p>
      </div>
    </div>

    <!-- Max Drawdown bar -->
    <div class="mb-3">
      <div class="mb-1 flex justify-between text-[10px] text-[var(--color-text-muted)]">
        <span>{{ t('risk.drawdown') }}</span>
        <span class="font-semibold text-red-400">{{ (analysis.max_drawdown * 100).toFixed(1) }}%</span>
      </div>
      <div class="h-1.5 w-full overflow-hidden rounded-full bg-white/[0.06]">
        <div
          class="h-1.5 rounded-full bg-red-500/60 transition-all duration-700"
          :style="{ width: `${Math.min(Math.abs(analysis.max_drawdown) * 100, 100)}%` }"
        />
      </div>
    </div>

    <!-- Beta -->
    <div v-if="analysis.beta !== null" class="mb-3 text-xs text-[var(--color-text-secondary)]">
      <span class="text-[var(--color-text-muted)]">Beta vs SPY:</span>
      <span class="ml-1 font-semibold text-white">{{ analysis.beta?.toFixed(2) }}</span>
      <span class="ml-1 text-[var(--color-text-muted)]">({{ betaLabel }})</span>
    </div>

    <p class="text-sm text-[var(--color-text-secondary)]">{{ analysis.summary }}</p>
    <p class="mt-2 text-right text-[10px] text-[var(--color-text-muted)]">
      {{ t('rec.confidence') }}: {{ Math.round(analysis.confidence * 100) }}%
    </p>>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { RiskOutput, RiskMetric } from '@/services/api'
import { t, tVal } from '@/locales'

const props = defineProps<{ analysis: RiskOutput }>()

const riskBadge = computed(() => ({
  'badge-bullish': props.analysis.risk_level === 'low',
  'badge-hold': props.analysis.risk_level === 'medium',
  'bg-orange-500/15 text-orange-400': props.analysis.risk_level === 'high',
  'badge-bearish': props.analysis.risk_level === 'very_high',
}))

const betaLabel = computed(() => {
  const b = props.analysis.beta
  if (b === null) return ''
  if (b > 1.5) return 'high sensitivity'
  if (b > 1.0) return 'above market'
  if (b > 0.5) return 'moderate'
  return 'defensive'
})

function formatValue(metric: RiskMetric): string {
  const name = metric.metric_name.toLowerCase()
  if (name.includes('drawdown') || name.includes('return') || name.includes('volatility')) {
    return `${(metric.value * 100).toFixed(1)}%`
  }
  return metric.value.toFixed(2)
}
</script>
