<template>
  <div class="min-h-screen bg-[var(--color-bg)]">
    <AppNav />
    <RouterView />
  </div>
</template>

<script setup lang="ts">
import { RouterView } from 'vue-router'
import AppNav from '@/components/AppNav.vue'
</script>
