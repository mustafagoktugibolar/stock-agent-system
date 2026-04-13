<template>
  <div class="rounded-lg border border-zinc-200 bg-white p-5 shadow-sm">
    <h3 class="mb-3 flex items-center gap-2 font-semibold text-zinc-800">
      Risk Assessment
      <span class="ml-auto rounded-full px-2 py-0.5 text-xs font-medium capitalize" :class="riskClass">
        {{ analysis.risk_level.replace('_', ' ') }}
      </span>
    </h3>

    <!-- Metrics grid -->
    <div class="mb-4 grid grid-cols-2 gap-2 sm:grid-cols-3">
      <div
        v-for="metric in analysis.metrics"
        :key="metric.metric_name"
        class="rounded-lg bg-zinc-50 px-3 py-2 text-center"
      >
        <p class="text-xs text-zinc-500">{{ metric.metric_name }}</p>
        <p class="font-semibold text-zinc-800">{{ formatValue(metric) }}</p>
        <p class="mt-0.5 text-xs leading-tight text-zinc-400">{{ metric.interpretation }}</p>
      </div>
    </div>

    <!-- Max Drawdown bar -->
    <div class="mb-3">
      <div class="mb-1 flex justify-between text-xs text-zinc-500">
        <span>Max Drawdown</span>
        <span class="font-medium text-red-600">{{ (analysis.max_drawdown * 100).toFixed(1) }}%</span>
      </div>
      <div class="h-2 w-full overflow-hidden rounded-full bg-zinc-100">
        <div
          class="h-2 rounded-full bg-red-400 transition-all duration-700"
          :style="{ width: `${Math.min(Math.abs(analysis.max_drawdown) * 100, 100)}%` }"
        />
      </div>
    </div>

    <!-- Beta -->
    <div v-if="analysis.beta !== null" class="mb-3 text-sm text-zinc-600">
      <span class="font-medium">Beta vs SPY:</span> {{ analysis.beta?.toFixed(2) }}
      <span class="ml-1 text-xs text-zinc-400">({{ betaLabel }})</span>
    </div>

    <!-- Summary -->
    <p class="text-sm text-zinc-600">{{ analysis.summary }}</p>
    <p class="mt-1 text-right text-xs text-zinc-400">Confidence: {{ Math.round(analysis.confidence * 100) }}%</p>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { RiskOutput, RiskMetric } from '@/services/api'

const props = defineProps<{ analysis: RiskOutput }>()

const riskClass = computed(() => ({
  'bg-green-100 text-green-800': props.analysis.risk_level === 'low',
  'bg-yellow-100 text-yellow-800': props.analysis.risk_level === 'medium',
  'bg-orange-100 text-orange-800': props.analysis.risk_level === 'high',
  'bg-red-100 text-red-800': props.analysis.risk_level === 'very_high',
}))

const betaLabel = computed(() => {
  const b = props.analysis.beta
  if (b === null) return ''
  if (b > 1.5) return 'high market sensitivity'
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
