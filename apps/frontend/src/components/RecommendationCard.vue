<template>
  <div
    class="card flex flex-col gap-4"
    :class="glowClass"
  >
    <!-- BUY / HOLD / SELL badge -->
    <div class="flex items-center justify-between">
      <span class="card-title">{{ t('rec.recommendation') }}</span>
      <span
        class="rounded-lg px-4 py-1.5 text-lg font-extrabold tracking-wider"
        :class="recBadgeClass"
      >
        {{ tVal(recommendation.recommendation) }}
      </span>
    </div>

    <!-- Confidence ring -->
    <div class="flex items-center gap-4">
      <div class="relative h-16 w-16 shrink-0">
        <svg class="h-16 w-16 -rotate-90" viewBox="0 0 36 36">
          <circle
            cx="18" cy="18" r="15.5"
            fill="none" stroke="currentColor"
            stroke-width="2.5"
            class="text-white/[0.06]"
          />
          <circle
            cx="18" cy="18" r="15.5"
            fill="none"
            :stroke="ringColor"
            stroke-width="2.5"
            stroke-linecap="round"
            :stroke-dasharray="`${confidencePct * 0.9735} 97.35`"
            class="transition-all duration-1000"
          />
        </svg>
        <span class="absolute inset-0 flex items-center justify-center text-sm font-bold text-white">
          {{ confidencePct }}%
        </span>
      </div>
      <div class="min-w-0 flex-1">
        <p class="text-xs text-[var(--color-text-muted)]">{{ t('rec.confidence') }}</p>
        <p class="mt-0.5 text-sm font-medium text-[var(--color-text-secondary)]">
          {{ t(confidenceLabelKey) }}
        </p>
      </div>
    </div>

    <!-- Target / Stop / Horizon -->
    <div class="grid grid-cols-3 gap-2">
      <div class="metric-box text-center">
        <p class="stat-label">{{ t('rec.target') }}</p>
        <p class="text-sm font-semibold text-green-400">
          {{ recommendation.target_price ? formatPrice(recommendation.target_price) : '—' }}
        </p>
      </div>
      <div class="metric-box text-center">
        <p class="stat-label">{{ t('rec.stop') }}</p>
        <p class="text-sm font-semibold text-red-400">
          {{ recommendation.stop_loss ? formatPrice(recommendation.stop_loss) : '—' }}
        </p>
      </div>
      <div class="metric-box text-center">
        <p class="stat-label">{{ t('rec.horizon') }}</p>
        <p class="text-sm font-semibold capitalize text-white">
          {{ recommendation.time_horizon.replace('_', ' ') }}
        </p>
      </div>
    </div>

    <!-- Reasoning -->
    <p class="text-sm leading-relaxed text-[var(--color-text-secondary)]">
      {{ recommendation.reasoning }}
    </p>

    <span v-if="cached" class="badge badge-neutral self-end text-[10px]">{{ t('rec.cached') }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { FinalRecommendation } from '@/services/api'
import { t, tVal } from '@/locales'

const props = defineProps<{
  recommendation: FinalRecommendation
  cached?: boolean
}>()

const confidencePct = computed(() => Math.round(props.recommendation.confidence * 100))

const confidenceLabelKey = computed(() => {
  const c = props.recommendation.confidence
  if (c >= 0.8) return 'rec.very.high'
  if (c >= 0.65) return 'rec.high'
  if (c >= 0.5) return 'rec.moderate'
  return 'rec.low'
})

const ringColor = computed(() => {
  const r = props.recommendation.recommendation
  if (r === 'BUY') return '#22c55e'
  if (r === 'SELL') return '#ef4444'
  return '#f59e0b'
})

const recBadgeClass = computed(() => ({
  'bg-green-500/15 text-green-400': props.recommendation.recommendation === 'BUY',
  'bg-red-500/15 text-red-400': props.recommendation.recommendation === 'SELL',
  'bg-amber-500/15 text-amber-400': props.recommendation.recommendation === 'HOLD',
}))

const glowClass = computed(() => ({
  'glow-green': props.recommendation.recommendation === 'BUY',
  'glow-red': props.recommendation.recommendation === 'SELL',
  'glow-amber': props.recommendation.recommendation === 'HOLD',
}))

function formatPrice(value: number): string {
  if (props.recommendation.symbol.endsWith('.IS')) return `₺${value.toFixed(2)}`
  if (props.recommendation.symbol.includes('.')) return value.toFixed(2)
  return `$${value.toFixed(2)}`
}
</script>
