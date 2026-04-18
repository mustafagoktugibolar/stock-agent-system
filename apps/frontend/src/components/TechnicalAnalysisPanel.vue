<template>
  <div class="card">
    <div class="card-header">
      <span class="card-title">{{ t('tech.title') }}</span>
      <span class="badge capitalize" :class="biasClass">{{ tVal(analysis.overall_technical_bias) }}</span>
    </div>

    <!-- Signals table -->
    <div class="mb-4 space-y-1.5">
      <div
        v-for="signal in analysis.signals"
        :key="signal.indicator"
        class="flex items-center justify-between rounded-lg bg-white/[0.02] px-3 py-2 text-sm"
      >
        <div class="min-w-0 flex-1">
          <span class="font-medium text-white">{{ signal.indicator }}</span>
          <p class="truncate text-xs text-[var(--color-text-muted)]">{{ signal.description }}</p>
        </div>
        <div class="flex shrink-0 items-center gap-3 pl-3 text-right">
          <span class="tabular-nums text-[var(--color-text-secondary)]">{{ signal.value.toFixed(2) }}</span>
          <span class="w-16 text-right text-xs font-semibold capitalize" :class="signalColor(signal.signal)">
            {{ tVal(signal.signal) }}
          </span>
        </div>
      </div>
    </div>

    <!-- Support & Resistance -->
    <div class="mb-3 flex gap-4 text-xs">
      <div v-if="analysis.support_levels.length">
        <span class="text-[var(--color-text-muted)]">{{ t('tech.support') }}</span>
        <span class="ml-1.5 font-semibold text-green-400">
          {{ analysis.support_levels.map(formatPrice).join(' · ') }}
        </span>
      </div>
      <div v-if="analysis.resistance_levels.length">
        <span class="text-[var(--color-text-muted)]">{{ t('tech.resistance') }}</span>
        <span class="ml-1.5 font-semibold text-red-400">
          {{ analysis.resistance_levels.map(formatPrice).join(' · ') }}
        </span>
      </div>
    </div>

    <!-- Summary -->
    <p class="text-sm text-[var(--color-text-secondary)]">{{ analysis.summary }}</p>
    <p class="mt-2 text-right text-[10px] text-[var(--color-text-muted)]">
      {{ t('rec.confidence') }}: {{ Math.round(analysis.confidence * 100) }}%
    </p>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { TechnicalOutput } from '@/services/api'
import { t, tVal } from '@/locales'

const props = defineProps<{ analysis: TechnicalOutput }>()

const biasClass = computed(() => ({
  'badge-bullish': props.analysis.overall_technical_bias === 'bullish',
  'badge-bearish': props.analysis.overall_technical_bias === 'bearish',
  'badge-neutral': props.analysis.overall_technical_bias === 'neutral',
}))

function signalColor(signal: string) {
  return {
    'text-green-400': signal === 'bullish',
    'text-red-400': signal === 'bearish',
    'text-[var(--color-text-muted)]': signal === 'neutral',
  }
}

function formatPrice(value: number): string {
  if (props.analysis.symbol.endsWith('.IS')) return `₺${value.toFixed(2)}`
  if (props.analysis.symbol.includes('.')) return value.toFixed(2)
  return `$${value.toFixed(2)}`
}
</script>
