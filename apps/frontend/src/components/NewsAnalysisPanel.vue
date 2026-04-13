<template>
  <div class="rounded-lg border border-zinc-200 bg-white p-5 shadow-sm">
    <h3 class="mb-3 flex items-center gap-2 font-semibold text-zinc-800">
      News & Sentiment
      <span class="ml-auto rounded-full px-2 py-0.5 text-xs font-medium capitalize" :class="sentimentClass">
        {{ analysis.overall_sentiment }}
      </span>
    </h3>

    <!-- Aggregate score bar -->
    <div class="mb-4">
      <div class="mb-1 flex justify-between text-xs text-zinc-500">
        <span>Very Negative</span>
        <span class="font-medium text-zinc-700">Score: {{ analysis.sentiment_score.toFixed(2) }}</span>
        <span>Very Positive</span>
      </div>
      <div class="relative h-2 w-full overflow-hidden rounded-full bg-zinc-100">
        <!-- Center line -->
        <div class="absolute left-1/2 top-0 h-full w-0.5 -translate-x-1/2 bg-zinc-300" />
        <!-- Score indicator -->
        <div
          class="absolute top-0 h-full w-1 rounded-full transition-all duration-700"
          :class="scoreBarClass"
          :style="{ left: `${((analysis.sentiment_score + 1) / 2) * 100}%` }"
        />
      </div>
    </div>

    <!-- News items -->
    <div class="mb-3 space-y-2">
      <div
        v-for="(item, i) in analysis.news_items.slice(0, 5)"
        :key="i"
        class="rounded-lg bg-zinc-50 px-3 py-2 text-sm"
      >
        <div class="flex items-start justify-between gap-2">
          <p class="flex-1 font-medium leading-snug text-zinc-700">{{ item.title }}</p>
          <span
            class="shrink-0 rounded text-xs font-semibold"
            :class="scoreColor(item.sentiment_score)"
          >
            {{ item.sentiment_score > 0 ? '+' : '' }}{{ item.sentiment_score.toFixed(2) }}
          </span>
        </div>
        <p class="mt-0.5 text-xs text-zinc-500">{{ item.source }}</p>
      </div>
    </div>

    <!-- Summary -->
    <p class="text-sm text-zinc-600">{{ analysis.summary }}</p>
    <p class="mt-1 text-right text-xs text-zinc-400">Confidence: {{ Math.round(analysis.confidence * 100) }}%</p>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { NewsOutput } from '@/services/api'

const props = defineProps<{ analysis: NewsOutput }>()

const sentimentClass = computed(() => ({
  'bg-green-100 text-green-800': props.analysis.overall_sentiment === 'positive',
  'bg-red-100 text-red-800': props.analysis.overall_sentiment === 'negative',
  'bg-zinc-100 text-zinc-700': props.analysis.overall_sentiment === 'neutral',
}))

const scoreBarClass = computed(() => ({
  'bg-green-500': props.analysis.sentiment_score > 0.15,
  'bg-red-500': props.analysis.sentiment_score < -0.15,
  'bg-zinc-400': Math.abs(props.analysis.sentiment_score) <= 0.15,
}))

function scoreColor(score: number) {
  if (score > 0.15) return 'text-green-600'
  if (score < -0.15) return 'text-red-600'
  return 'text-zinc-500'
}
</script>
