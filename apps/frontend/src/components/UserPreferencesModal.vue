<template>
  <Teleport to="body">
    <div
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4 backdrop-blur-sm"
      @click.self="$emit('close')"
    >
      <div class="w-full max-w-md rounded-xl border border-white/[0.08] bg-[#0f1117] p-6 shadow-2xl">
        <div class="mb-5 flex items-center justify-between">
          <h2 class="text-base font-semibold text-white">{{ t('advisor.prefs.title') }}</h2>
          <button
            class="rounded-md p-1 text-[var(--color-text-muted)] hover:bg-white/[0.06] hover:text-white transition"
            @click="$emit('close')"
          >
            <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <!-- Risk Tolerance -->
        <div class="mb-5">
          <p class="mb-2 text-xs font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">
            {{ t('advisor.prefs.risk') }}
          </p>
          <div class="flex gap-2">
            <button
              v-for="opt in riskOptions"
              :key="opt.value"
              class="flex-1 rounded-lg border py-2 text-xs font-medium transition"
              :class="form.riskTolerance === opt.value
                ? 'border-green-500/50 bg-green-500/15 text-green-400'
                : 'border-white/[0.06] bg-white/[0.02] text-[var(--color-text-muted)] hover:border-white/[0.1] hover:text-white'"
              @click="form.riskTolerance = opt.value"
            >
              {{ opt.label }}
            </button>
          </div>
        </div>

        <!-- Investment Horizon -->
        <div class="mb-5">
          <p class="mb-2 text-xs font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">
            {{ t('advisor.prefs.horizon') }}
          </p>
          <div class="flex gap-2">
            <button
              v-for="opt in horizonOptions"
              :key="opt.value"
              class="flex-1 rounded-lg border py-2 text-xs font-medium transition"
              :class="form.horizon === opt.value
                ? 'border-green-500/50 bg-green-500/15 text-green-400'
                : 'border-white/[0.06] bg-white/[0.02] text-[var(--color-text-muted)] hover:border-white/[0.1] hover:text-white'"
              @click="form.horizon = opt.value"
            >
              {{ opt.label }}
            </button>
          </div>
        </div>

        <!-- Sectors -->
        <div class="mb-6">
          <p class="mb-2 text-xs font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">
            {{ t('advisor.prefs.sectors') }}
          </p>
          <div class="flex flex-wrap gap-2">
            <button
              v-for="sector in SECTORS"
              :key="sector"
              class="rounded-full border px-3 py-1 text-xs font-medium transition"
              :class="form.sectors.includes(sector)
                ? 'border-green-500/50 bg-green-500/15 text-green-400'
                : 'border-white/[0.06] bg-white/[0.02] text-[var(--color-text-muted)] hover:border-white/[0.1] hover:text-white'"
              @click="toggleSector(sector)"
            >
              {{ sector }}
            </button>
          </div>
        </div>

        <button
          class="w-full rounded-lg bg-green-600 py-2.5 text-sm font-semibold text-white transition hover:bg-green-500"
          @click="save"
        >
          {{ t('advisor.prefs.save') }}
        </button>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { reactive } from 'vue'
import type { UserPreferences } from '@/services/api'
import { t } from '@/locales'

const props = defineProps<{ preferences: UserPreferences }>()
const emit = defineEmits<{
  (e: 'close'): void
  (e: 'save', prefs: UserPreferences): void
}>()

const SECTORS = [
  'Technology', 'Energy', 'Healthcare', 'Financials',
  'Consumer', 'Industrials', 'Materials', 'Utilities', 'Real Estate',
]

const riskOptions = [
  { value: 'low' as const, label: 'Low' },
  { value: 'medium' as const, label: 'Medium' },
  { value: 'high' as const, label: 'High' },
]

const horizonOptions = [
  { value: 'short' as const, label: 'Short-term' },
  { value: 'medium' as const, label: 'Medium-term' },
  { value: 'long' as const, label: 'Long-term' },
]

const form = reactive<UserPreferences>({
  riskTolerance: props.preferences.riskTolerance,
  sectors: [...props.preferences.sectors],
  horizon: props.preferences.horizon,
})

function toggleSector(sector: string) {
  const idx = form.sectors.indexOf(sector)
  if (idx === -1) form.sectors.push(sector)
  else form.sectors.splice(idx, 1)
}

function save() {
  emit('save', { riskTolerance: form.riskTolerance, sectors: [...form.sectors], horizon: form.horizon })
}
</script>
