<template>
  <div class="rounded-lg border border-zinc-200 bg-white p-6 shadow-sm">
    <!-- Header -->
    <div class="mb-4 flex items-center justify-between">
      <div>
        <h2 class="text-2xl font-bold text-zinc-950">{{ recommendation.symbol }}</h2>
        <p class="text-sm text-zinc-500">{{ formattedDate }}</p>
      </div>
      <span
        class="rounded-full px-5 py-2 text-lg font-bold"
        :class="badgeClass"
      >
        {{ recommendation.recommendation }}
      </span>
    </div>

    <!-- Confidence bar -->
    <div class="mb-4">
      <div class="mb-1 flex justify-between text-sm text-zinc-600">
        <span>Confidence</span>
        <span>{{ Math.round(recommendation.confidence * 100) }}%</span>
      </div>
      <div class="h-2 w-full overflow-hidden rounded-full bg-zinc-100">
        <div
          class="h-2 rounded-full transition-all duration-700"
          :class="confidenceBarClass"
          :style="{ width: `${recommendation.confidence * 100}%` }"
        />
      </div>
    </div>

    <!-- Target & Stop Loss -->
    <div class="mb-4 grid gap-3 sm:grid-cols-3">
      <div v-if="recommendation.target_price" class="rounded-lg bg-zinc-50 px-3 py-2 text-center">
        <p class="text-xs text-zinc-500">Target Price</p>
        <p class="font-semibold text-zinc-800">{{ formatPrice(recommendation.target_price) }}</p>
      </div>
      <div v-if="recommendation.stop_loss" class="rounded-lg bg-zinc-50 px-3 py-2 text-center">
        <p class="text-xs text-zinc-500">Stop Loss</p>
        <p class="font-semibold text-zinc-800">{{ formatPrice(recommendation.stop_loss) }}</p>
      </div>
      <div class="rounded-lg bg-zinc-50 px-3 py-2 text-center">
        <p class="text-xs text-zinc-500">Time Horizon</p>
        <p class="font-semibold capitalize text-zinc-800">{{ horizonLabel }}</p>
      </div>
    </div>

    <!-- Reasoning -->
    <p class="text-sm leading-relaxed text-zinc-700">{{ recommendation.reasoning }}</p>

    <!-- Cached badge -->
    <div v-if="cached" class="mt-3 text-right">
      <span class="rounded bg-yellow-100 px-2 py-0.5 text-xs text-yellow-700">Cached result</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { FinalRecommendation } from '@/services/api'

const props = defineProps<{
  recommendation: FinalRecommendation
  cached?: boolean
}>()

const badgeClass = computed(() => ({
  'bg-green-100 text-green-800': props.recommendation.recommendation === 'BUY',
  'bg-yellow-100 text-yellow-800': props.recommendation.recommendation === 'HOLD',
  'bg-red-100 text-red-800': props.recommendation.recommendation === 'SELL',
}))

const confidenceBarClass = computed(() => ({
  'bg-green-500': props.recommendation.confidence >= 0.7,
  'bg-yellow-400': props.recommendation.confidence >= 0.4 && props.recommendation.confidence < 0.7,
  'bg-red-400': props.recommendation.confidence < 0.4,
}))

const horizonLabel = computed(() =>
  props.recommendation.time_horizon.replace('_', ' ')
)

const formattedDate = computed(() => {
  const d = new Date(props.recommendation.timestamp)
  return d.toLocaleString()
})

function formatPrice(value: number): string {
  if (props.recommendation.symbol.endsWith('.IS')) {
    return `TRY ${value.toFixed(2)}`
  }

  if (props.recommendation.symbol.includes('.')) {
    return value.toFixed(2)
  }

  return `$${value.toFixed(2)}`
}
</script>
