<template>
  <div class="fixed inset-0 z-50 flex flex-col items-center justify-center gap-5 bg-[var(--color-bg)]">
    <!-- Pulsing ring -->
    <div class="relative flex h-20 w-20 items-center justify-center">
      <div class="absolute inset-0 animate-ping rounded-full bg-green-500/10" />
      <div class="absolute inset-2 animate-pulse rounded-full bg-green-500/5" />
      <svg class="relative h-8 w-8 animate-spin text-green-500" viewBox="0 0 24 24" fill="none">
        <circle class="opacity-20" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" />
        <path class="opacity-80" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
      </svg>
    </div>

    <div class="text-center">
      <p class="text-lg font-semibold text-white">Analyzing {{ symbol }}</p>
      <p class="mt-1 text-sm text-[var(--color-text-muted)]">{{ message }}</p>
    </div>

    <!-- Agent status pills -->
    <div class="flex flex-wrap justify-center gap-2">
      <span
        v-for="step in steps"
        :key="step.label"
        class="badge"
        :class="step.done ? 'badge-bullish' : 'badge-neutral'"
      >
        <svg v-if="step.done" class="mr-1 h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3">
          <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
        </svg>
        {{ step.label }}
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    symbol?: string
    message?: string
    steps?: Array<{ label: string; done: boolean }>
  }>(),
  {
    symbol: '...',
    message: 'Running multi-agent analysis — this usually takes 30–60 seconds.',
    steps: () => [
      { label: 'Fundamentals', done: false },
      { label: 'Technical', done: false },
      { label: 'News', done: false },
      { label: 'Risk', done: false },
      { label: 'Supervisor', done: false },
    ],
  },
)
</script>
