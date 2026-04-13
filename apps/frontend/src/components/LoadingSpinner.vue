<template>
  <div class="flex flex-col items-center justify-center gap-4 py-12 text-zinc-500">
    <svg class="h-10 w-10 animate-spin text-emerald-600" viewBox="0 0 24 24" fill="none">
      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
    </svg>
    <div class="text-center">
      <p class="font-medium text-zinc-700">Analyzing {{ symbol }}...</p>
      <p class="text-sm text-zinc-500">{{ message }}</p>
    </div>
    <div class="flex flex-wrap justify-center gap-2 text-xs text-zinc-400">
      <span
        v-for="step in steps"
        :key="step.label"
        class="flex items-center gap-1 rounded-lg px-2 py-0.5"
        :class="step.done ? 'bg-green-100 text-green-700' : 'bg-zinc-100'"
      >
        <span v-if="step.done">Done</span>
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
    message: 'Running multi-agent analysis. This usually takes 30-60 seconds.',
    steps: () => [
      { label: 'Technical', done: false },
      { label: 'News', done: false },
      { label: 'Risk', done: false },
      { label: 'Supervisor', done: false },
    ],
  },
)
</script>
