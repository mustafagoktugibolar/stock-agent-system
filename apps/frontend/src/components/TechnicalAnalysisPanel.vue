<template>
  <div class="rounded-lg border border-zinc-200 bg-white p-5 shadow-sm">
    <h3 class="mb-3 flex items-center gap-2 font-semibold text-zinc-800">
      Technical Analysis
      <span class="ml-auto rounded-full px-2 py-0.5 text-xs font-medium capitalize" :class="biasClass">
        {{ analysis.overall_technical_bias }}
      </span>
    </h3>

    <!-- Signals -->
    <div class="mb-4 space-y-2">
      <div
        v-for="signal in analysis.signals"
        :key="signal.indicator"
        class="flex items-start justify-between rounded-lg bg-zinc-50 px-3 py-2 text-sm"
      >
        <div>
          <span class="font-medium text-zinc-700">{{ signal.indicator }}</span>
          <p class="text-xs text-zinc-500">{{ signal.description }}</p>
        </div>
        <div class="text-right">
          <span class="text-zinc-800">{{ signal.value.toFixed(2) }}</span>
          <span class="ml-2 text-xs font-medium capitalize" :class="signalColor(signal.signal)">
            {{ signal.signal }}
          </span>
        </div>
      </div>
    </div>

    <!-- Support / Resistance -->
    <div class="mb-3 flex gap-3 text-xs">
      <div v-if="analysis.support_levels.length" class="flex-1">
        <span class="font-medium text-green-700">Support:</span>
        {{ analysis.support_levels.map(formatPrice).join(', ') }}
      </div>
      <div v-if="analysis.resistance_levels.length" class="flex-1 text-right">
        <span class="font-medium text-red-700">Resistance:</span>
        {{ analysis.resistance_levels.map(formatPrice).join(', ') }}
      </div>
    </div>

    <!-- Summary -->
    <p class="text-sm text-zinc-600">{{ analysis.summary }}</p>
    <p class="mt-1 text-right text-xs text-zinc-400">Confidence: {{ Math.round(analysis.confidence * 100) }}%</p>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { TechnicalOutput } from '@/services/api'

const props = defineProps<{ analysis: TechnicalOutput }>()

const biasClass = computed(() => ({
  'bg-green-100 text-green-800': props.analysis.overall_technical_bias === 'bullish',
  'bg-red-100 text-red-800': props.analysis.overall_technical_bias === 'bearish',
  'bg-zinc-100 text-zinc-700': props.analysis.overall_technical_bias === 'neutral',
}))

function signalColor(signal: string) {
  return {
    'text-green-600': signal === 'bullish',
    'text-red-600': signal === 'bearish',
    'text-zinc-500': signal === 'neutral',
  }
}

function formatPrice(value: number): string {
  if (props.analysis.symbol.endsWith('.IS')) {
    return `TRY ${value.toFixed(2)}`
  }

  if (props.analysis.symbol.includes('.')) {
    return value.toFixed(2)
  }

  return `$${value.toFixed(2)}`
}
</script>
