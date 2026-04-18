<template>
  <div class="card">
    <div class="card-header">
      <span class="card-title">{{ t('news.title') }}</span>
      <span class="badge capitalize" :class="sentimentClass">{{ tVal(analysis.overall_sentiment) }}</span>
    </div>

    <!-- Sentiment bar -->
    <div class="mb-4">
      <div class="mb-1 flex justify-between text-[10px] text-[var(--color-text-muted)]">
        <span>{{ t('news.negative') }}</span>
        <span class="font-semibold text-[var(--color-text-secondary)]">
          {{ analysis.sentiment_score > 0 ? '+' : '' }}{{ analysis.sentiment_score.toFixed(2) }}
        </span>
        <span>{{ t('news.positive') }}</span>
      </div>
      <div class="relative h-1.5 w-full overflow-hidden rounded-full bg-white/[0.06]">
        <div class="absolute left-1/2 top-0 h-full w-px bg-white/10" />
        <div
          class="absolute top-0 h-full w-3 -translate-x-1/2 rounded-full transition-all duration-700"
          :class="dotClass"
          :style="{ left: `${((analysis.sentiment_score + 1) / 2) * 100}%` }"
        />
      </div>
    </div>

    <!-- News items -->
    <div class="mb-3 space-y-1.5">
      <a
        v-for="(item, i) in analysis.news_items.slice(0, 5)"
        :key="i"
        :href="item.url || '#'"
        :target="item.url ? '_blank' : '_self'"
        :class="[
          'block rounded-lg bg-white/[0.02] px-3 py-2 text-sm',
          item.url ? 'transition-colors hover:bg-white/[0.05]' : 'cursor-default'
        ]"
      >
        <div class="flex items-start justify-between gap-2">
          <p class="flex-1 leading-snug text-[var(--color-text-secondary)]" :class="{'group-hover:text-white transition': item.url}">{{ item.title }}</p>
          <span class="shrink-0 text-xs font-bold tabular-nums" :class="scoreColor(item.sentiment_score)">
            {{ item.sentiment_score > 0 ? '+' : '' }}{{ item.sentiment_score.toFixed(2) }}
          </span>
        </div>
        <p class="mt-0.5 text-[10px] text-[var(--color-text-muted)] flex items-center gap-1">
          {{ item.source }}
          <svg v-if="item.url" class="h-3 w-3 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
          </svg>
        </p>
      </a>
    </div>

    <p class="text-sm text-[var(--color-text-secondary)]">{{ analysis.summary }}</p>
    <p class="mt-2 text-right text-[10px] text-[var(--color-text-muted)]">
      {{ t('rec.confidence') }}: {{ Math.round(analysis.confidence * 100) }}%
    </p>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { NewsOutput } from '@/services/api'
import { t, tVal } from '@/locales'

const props = defineProps<{ analysis: NewsOutput }>()

const sentimentClass = computed(() => ({
  'badge-bullish': props.analysis.overall_sentiment === 'positive',
  'badge-bearish': props.analysis.overall_sentiment === 'negative',
  'badge-neutral': props.analysis.overall_sentiment === 'neutral',
}))

const dotClass = computed(() => ({
  'bg-green-400': props.analysis.sentiment_score > 0.15,
  'bg-red-400': props.analysis.sentiment_score < -0.15,
  'bg-[var(--color-text-muted)]': Math.abs(props.analysis.sentiment_score) <= 0.15,
}))

function scoreColor(score: number) {
  if (score > 0.15) return 'text-green-400'
  if (score < -0.15) return 'text-red-400'
  return 'text-[var(--color-text-muted)]'
}
</script>
