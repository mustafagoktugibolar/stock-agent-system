<!-- apps/frontend/src/components/AppNav.vue -->
<template>
  <nav class="app-nav">
    <div class="nav-inner">
      <div class="nav-brand">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="22 7 13.5 15.5 8.5 10.5 2 17" />
          <polyline points="16 7 22 7 22 13" />
        </svg>
        <span>StockAgent</span>
      </div>

      <div class="nav-links">
        <RouterLink to="/" class="nav-link" :class="{ active: route.path === '/' }">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          Analysis
        </RouterLink>

        <RouterLink to="/trading" class="nav-link" :class="{ active: route.path === '/trading' }">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
          Trading
          <span v-if="tradingStore.status?.running" class="live-dot" />
        </RouterLink>
      </div>
    </div>
  </nav>
</template>

<script setup lang="ts">
import { useRoute, RouterLink } from 'vue-router'
import { useTradingStore } from '@/stores/trading'
import { onMounted } from 'vue'

const route = useRoute()
const tradingStore = useTradingStore()

onMounted(() => {
  tradingStore.fetchStatus()
})
</script>

<style scoped>
.app-nav {
  position: sticky;
  top: 0;
  z-index: 50;
  background: color-mix(in srgb, var(--color-bg) 88%, transparent);
  backdrop-filter: blur(16px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.nav-inner {
  max-width: 1280px;
  margin: 0 auto;
  padding: 0 1rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 52px;
}

@media (min-width: 640px) { .nav-inner { padding: 0 1.5rem; } }
@media (min-width: 1024px) { .nav-inner { padding: 0 2rem; } }

.nav-brand {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.9375rem;
  font-weight: 700;
  color: var(--color-text);
  letter-spacing: -0.02em;
}

.nav-brand svg {
  width: 1.125rem;
  height: 1.125rem;
  color: #60a5fa;
}

.nav-links {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.nav-link {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.375rem 0.75rem;
  border-radius: 0.5rem;
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--color-text-muted);
  text-decoration: none;
  transition: background 0.15s, color 0.15s;
  position: relative;
}

.nav-link svg {
  width: 0.875rem;
  height: 0.875rem;
  flex-shrink: 0;
}

.nav-link:hover {
  background: rgba(255, 255, 255, 0.06);
  color: var(--color-text);
}

.nav-link.active {
  background: rgba(96, 165, 250, 0.12);
  color: #60a5fa;
}

.live-dot {
  width: 0.4rem;
  height: 0.4rem;
  border-radius: 50%;
  background: #4ade80;
  animation: pulse-green 2s ease-in-out infinite;
  margin-left: 0.1rem;
}

@keyframes pulse-green {
  0%, 100% { box-shadow: 0 0 0 2px rgba(74, 222, 128, 0.2); }
  50% { box-shadow: 0 0 0 4px rgba(74, 222, 128, 0.06); }
}
</style>
