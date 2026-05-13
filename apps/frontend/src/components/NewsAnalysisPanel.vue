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
        @dblclick.prevent="selectedArticle = item"
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
          <span class="ml-auto opacity-40 text-[9px]">double-click to expand</span>
        </p>
      </a>
    </div>

    <p class="text-sm text-[var(--color-text-secondary)]">{{ analysis.summary }}</p>
    <p class="mt-2 text-right text-[10px] text-[var(--color-text-muted)]">
      {{ t('rec.confidence') }}: {{ Math.round(analysis.confidence * 100) }}%
    </p>

    <!-- Article detail modal -->
    <Teleport to="body">
      <div
        v-if="selectedArticle"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4 backdrop-blur-sm"
        @click.self="selectedArticle = null"
      >
        <div class="w-full max-w-lg rounded-xl border border-white/[0.08] bg-[#0f1117] p-6 shadow-2xl">
          <!-- Header -->
          <div class="mb-4 flex items-start justify-between gap-3">
            <h2 class="flex-1 text-base font-semibold leading-snug text-white">{{ selectedArticle.title }}</h2>
            <button
              class="shrink-0 rounded-md p-1 text-[var(--color-text-muted)] hover:bg-white/[0.06] hover:text-white transition"
              @click="selectedArticle = null"
            >
              <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <!-- Meta -->
          <div class="mb-4 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-[var(--color-text-muted)]">
            <span class="font-medium text-[var(--color-text-secondary)]">{{ selectedArticle.source }}</span>
            <span v-if="selectedArticle.published_at">· {{ formatDate(selectedArticle.published_at) }}</span>
            <span
              class="ml-auto font-bold tabular-nums"
              :class="scoreColor(selectedArticle.sentiment_score)"
            >
              {{ selectedArticle.sentiment_score > 0 ? '+' : '' }}{{ selectedArticle.sentiment_score.toFixed(2) }} sentiment
            </span>
          </div>

          <!-- Summary -->
          <p class="mb-5 text-sm leading-relaxed text-[var(--color-text-secondary)]">{{ selectedArticle.summary }}</p>

          <!-- Actions -->
          <div class="flex justify-end gap-2">
            <button
              class="rounded-lg px-3 py-1.5 text-xs text-[var(--color-text-muted)] hover:bg-white/[0.06] hover:text-white transition"
              @click="selectedArticle = null"
            >
              Close
            </button>
            <a
              v-if="selectedArticle.url"
              :href="selectedArticle.url"
              target="_blank"
              rel="noopener noreferrer"
              class="flex items-center gap-1.5 rounded-lg bg-white/[0.08] px-3 py-1.5 text-xs font-medium text-white hover:bg-white/[0.12] transition"
            >
              Read Original
              <svg class="h-3 w-3 opacity-70" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
              </svg>
            </a>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { NewsOutput, NewsItem } from '@/services/api'
import { t, tVal } from '@/locales'

const props = defineProps<{ analysis: NewsOutput }>()

const selectedArticle = ref<NewsItem | null>(null)

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

function formatDate(dateStr: string | null): string {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  if (isNaN(d.getTime())) return dateStr
  return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })
}
</script>
