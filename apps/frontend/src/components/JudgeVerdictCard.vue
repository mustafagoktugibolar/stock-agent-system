<template>
  <div class="card flex flex-col gap-4">
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-2">
        <svg class="h-4 w-4 text-[var(--color-text-muted)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
        </svg>
        <span class="card-title">{{ t('judge.title') }}</span>
      </div>
      <span
        class="rounded-lg px-3 py-1 text-sm font-extrabold tracking-wider"
        :class="verdictBadgeClass"
      >
        {{ t(verdict.verdict === 'pass' ? 'judge.pass' : 'judge.fail') }}
      </span>
    </div>

    <p class="text-xs text-[var(--color-text-muted)]">{{ t('judge.subtitle') }}</p>

    <div class="grid grid-cols-4 gap-2">
      <div
        v-for="score in scores"
        :key="score.key"
        class="metric-box text-center"
      >
        <p class="stat-label">{{ t(score.key) }}</p>
        <p class="text-sm font-semibold" :class="scoreColorClass(score.value)">
          {{ Math.round(score.value * 100) }}%
        </p>
        <div class="mt-1.5 h-1 w-full overflow-hidden rounded-full bg-white/[0.06]">
          <div
            class="h-full rounded-full transition-all duration-700"
            :class="scoreBarClass(score.value)"
            :style="{ width: `${score.value * 100}%` }"
          />
        </div>
      </div>
    </div>

    <div>
      <p class="stat-label mb-1">{{ t('judge.critique') }}</p>
      <p class="text-sm leading-relaxed text-[var(--color-text-secondary)]">
        {{ verdict.critique }}
      </p>
    </div>

    <div v-if="verdict.suggestions.length > 0">
      <p class="stat-label mb-1">{{ t('judge.suggestions') }}</p>
      <ul class="flex flex-col gap-1">
        <li
          v-for="(suggestion, i) in verdict.suggestions"
          :key="i"
          class="flex items-start gap-2 text-sm leading-relaxed text-[var(--color-text-secondary)]"
        >
          <span class="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-amber-400" />
          {{ suggestion }}
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { JudgeVerdict } from '@/services/api'
import { t } from '@/locales'

const props = defineProps<{
  verdict: JudgeVerdict
}>()

const scores = computed(() => [
  { key: 'judge.overall', value: props.verdict.overall_score },
  { key: 'judge.coherence', value: props.verdict.coherence_score },
  { key: 'judge.evidence', value: props.verdict.evidence_score },
  { key: 'judge.risk.alignment', value: props.verdict.risk_alignment_score },
])

const verdictBadgeClass = computed(() => ({
  'bg-green-500/15 text-green-400': props.verdict.verdict === 'pass',
  'bg-red-500/15 text-red-400': props.verdict.verdict === 'fail',
}))

function scoreColorClass(value: number): string {
  if (value >= 0.7) return 'text-green-400'
  if (value >= 0.5) return 'text-amber-400'
  return 'text-red-400'
}

function scoreBarClass(value: number): string {
  if (value >= 0.7) return 'bg-green-400'
  if (value >= 0.5) return 'bg-amber-400'
  return 'bg-red-400'
}
</script>
