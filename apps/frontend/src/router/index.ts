import { createRouter, createWebHistory } from 'vue-router'
import AnalysisView from '@/views/AnalysisView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'analysis',
      component: AnalysisView,
    },
    {
      path: '/trading',
      name: 'trading',
      component: () => import('@/views/TradingView.vue'),
    },
  ],
})

export default router
