<template>
  <div class="card">
    <div class="mb-3 flex flex-wrap items-start gap-4">
      <!-- Company name + meta -->
      <div class="min-w-0 flex-1">
        <div class="flex items-center gap-3">
          <h1 class="truncate text-2xl font-bold text-white">{{ displayName }}</h1>
          <span
            v-if="profile?.sector"
            class="badge badge-neutral shrink-0"
          >{{ profile.sector }}</span>
        </div>
        <div class="mt-1 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-[var(--color-text-muted)]">
          <span v-if="profile?.exchange">{{ profile.exchange }}</span>
          <span v-if="profile?.industry">{{ profile.industry }}</span>
          <span v-if="profile?.employees">{{ formatNumber(profile.employees) }} {{ t('header.employees') }}</span>
          <a
            v-if="profile?.website"
            :href="profile.website"
            target="_blank"
            rel="noopener"
            class="text-green-500/70 transition hover:text-green-400"
          >{{ cleanUrl(profile.website) }} ↗</a>
        </div>
      </div>

      <!-- Price + 52w range -->
      <div v-if="profile?.current_price" class="shrink-0 text-right">
        <p class="text-2xl font-bold tabular-nums text-white">
          {{ formatCurrency(profile.current_price, profile.currency) }}
        </p>
        <p v-if="profile.fifty_two_week_low && profile.fifty_two_week_high" class="mt-0.5 text-[10px] text-[var(--color-text-muted)]">
          52W: {{ formatCurrency(profile.fifty_two_week_low, profile.currency) }} – {{ formatCurrency(profile.fifty_two_week_high, profile.currency) }}
        </p>
      </div>
    </div>

    <!-- Key metrics strip -->
    <div v-if="profile" class="mb-4 flex flex-wrap gap-2">
      <div v-if="profile.market_cap" class="metric-box">
        <p class="stat-label">{{ t('header.market.cap') }}</p>
        <p class="text-sm font-semibold text-white">{{ formatMarketCap(profile.market_cap) }}</p>
      </div>
      <div v-if="profile.pe_ratio" class="metric-box">
        <p class="stat-label">{{ t('header.pe') }}</p>
        <p class="text-sm font-semibold text-white">{{ profile.pe_ratio.toFixed(1) }}</p>
      </div>
      <div v-if="profile.forward_pe" class="metric-box">
        <p class="stat-label">{{ t('header.fwd.pe') }}</p>
        <p class="text-sm font-semibold text-white">{{ profile.forward_pe.toFixed(1) }}</p>
      </div>
      <div v-if="profile.dividend_yield" class="metric-box">
        <p class="stat-label">{{ t('header.div.yield') }}</p>
        <p class="text-sm font-semibold text-white">{{ (profile.dividend_yield * 100).toFixed(2) }}%</p>
      </div>
    </div>

    <!-- Company description -->
    <p
      v-if="profile?.description"
      class="text-sm leading-relaxed text-[var(--color-text-secondary)]"
      :class="{ 'line-clamp-3': !expanded }"
    >
      {{ profile.description }}
    </p>
    <button
      v-if="profile?.description && profile.description.length > 200"
      class="mt-1 text-xs text-green-500/70 transition hover:text-green-400"
      @click="expanded = !expanded"
    >
      {{ expanded ? t('header.show.less') : t('header.read.more') }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { CompanyProfile, FinalRecommendation } from '@/services/api'
import { t } from '@/locales'

const props = defineProps<{
  profile: CompanyProfile | null
  recommendation: FinalRecommendation | null
}>()

const expanded = ref(false)

const displayName = computed(() => {
  if (props.profile?.name) return props.profile.name
  return props.recommendation?.symbol ?? '—'
})

function formatCurrency(value: number, currency = 'USD'): string {
  if (currency === 'TRY') return `₺${value.toFixed(2)}`
  if (currency === 'EUR') return `€${value.toFixed(2)}`
  if (currency === 'GBP') return `£${value.toFixed(2)}`
  if (currency === 'JPY') return `¥${Math.round(value)}`
  return `$${value.toFixed(2)}`
}

function formatMarketCap(value: number): string {
  if (value >= 1e12) return `${(value / 1e12).toFixed(1)}T`
  if (value >= 1e9) return `${(value / 1e9).toFixed(1)}B`
  if (value >= 1e6) return `${(value / 1e6).toFixed(0)}M`
  return value.toLocaleString()
}

function formatNumber(value: number): string {
  return value.toLocaleString()
}

function cleanUrl(url: string): string {
  return url.replace(/^https?:\/\/(www\.)?/, '').replace(/\/$/, '')
}
</script>
