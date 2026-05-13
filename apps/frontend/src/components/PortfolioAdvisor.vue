<template>
  <div class="flex flex-col rounded-xl border border-white/[0.08] bg-[#0f1117] shadow-2xl" style="height: 520px;">
    <!-- Header -->
    <div class="flex shrink-0 items-center justify-between border-b border-white/[0.06] px-4 py-3">
      <div class="flex items-center gap-2.5">
        <div class="flex h-7 w-7 items-center justify-center rounded-full bg-green-500/20">
          <svg class="h-4 w-4 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
        </div>
        <div>
          <p class="text-sm font-semibold text-white">{{ t('advisor.title') }}</p>
          <div class="flex items-center gap-1">
            <div class="h-1.5 w-1.5 rounded-full" :class="isGenerating ? 'bg-amber-400 animate-pulse' : 'bg-green-400'" />
            <span class="text-[10px] text-[var(--color-text-muted)]">{{ isGenerating ? 'Thinking...' : 'Ready' }}</span>
          </div>
        </div>
      </div>
      <button
        class="rounded-lg border border-white/[0.06] p-1.5 text-[var(--color-text-muted)] hover:bg-white/[0.06] hover:text-white transition"
        title="Preferences"
        @click="showPrefs = true"
      >
        <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
          <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
      </button>
    </div>

    <!-- Messages -->
    <div ref="scrollEl" class="flex-1 overflow-y-auto space-y-4 p-4">
      <div v-for="(msg, i) in messages" :key="i">
        <!-- User message -->
        <div v-if="msg.role === 'user'" class="flex justify-end">
          <div class="max-w-[80%] rounded-2xl rounded-tr-sm bg-green-600 px-3.5 py-2.5 text-sm text-white">
            {{ msg.content }}
          </div>
        </div>

        <!-- Assistant message -->
        <div v-else class="flex flex-col gap-1.5">
          <div
            class="max-w-[90%] rounded-2xl rounded-tl-sm border border-white/[0.06] bg-white/[0.04] px-3.5 py-2.5 text-sm text-[var(--color-text-secondary)] prose prose-sm prose-invert max-w-none"
            v-html="renderMarkdown(msg.content)"
          />
          <!-- Ticker pills extracted from response -->
          <div v-if="msg.tickers && msg.tickers.length" class="flex flex-wrap gap-1.5 pl-1">
            <button
              v-for="ticker in msg.tickers"
              :key="ticker"
              class="flex items-center gap-1 rounded-full border border-green-500/40 bg-green-500/10 px-2.5 py-0.5 text-xs font-bold text-green-400 transition hover:bg-green-500/20 hover:text-green-300"
              @click="$emit('analyze', ticker)"
            >
              {{ ticker }}
              <svg class="h-3 w-3 opacity-70" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
              </svg>
              <span class="font-normal opacity-60">{{ t('advisor.analyze') }}</span>
            </button>
          </div>
        </div>
      </div>

      <!-- Typing indicator -->
      <div v-if="isGenerating && messages[messages.length - 1]?.role !== 'assistant'" class="flex gap-1 pl-1">
        <span v-for="n in 3" :key="n" class="h-1.5 w-1.5 rounded-full bg-green-400 animate-bounce" :style="{ animationDelay: `${(n - 1) * 0.15}s` }" />
      </div>
    </div>

    <!-- Input -->
    <form class="shrink-0 border-t border-white/[0.06] p-3" @submit.prevent="send">
      <div class="flex gap-2">
        <input
          v-model="inputText"
          :placeholder="t('advisor.placeholder')"
          :disabled="isGenerating"
          class="flex-1 rounded-lg border border-white/[0.06] bg-white/[0.04] px-3 py-2 text-sm text-white placeholder-[var(--color-text-muted)] outline-none focus:border-green-500/40 disabled:opacity-50 transition"
        />
        <button
          type="submit"
          :disabled="!inputText.trim() || isGenerating"
          class="flex items-center justify-center rounded-lg bg-green-600 px-3 py-2 text-white transition hover:bg-green-500 disabled:opacity-40"
        >
          <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
          </svg>
        </button>
      </div>
    </form>
  </div>

  <UserPreferencesModal
    v-if="showPrefs"
    :preferences="preferences"
    @close="showPrefs = false"
    @save="savePreferences"
  />
</template>

<script setup lang="ts">
import { ref, nextTick, onMounted } from 'vue'
import { marked } from 'marked'
import { streamAdvisor, type ChatMessage, type UserPreferences } from '@/services/api'
import { t } from '@/locales'
import UserPreferencesModal from './UserPreferencesModal.vue'

const emit = defineEmits<{ (e: 'analyze', symbol: string): void }>()

interface AdvisorMessage {
  role: 'user' | 'assistant'
  content: string
  tickers?: string[]
}

const PREFS_KEY = 'userPreferences'
const DEFAULT_PREFS: UserPreferences = { riskTolerance: 'medium', sectors: [], horizon: 'medium' }

function loadPreferences(): UserPreferences {
  try {
    const raw = localStorage.getItem(PREFS_KEY)
    return raw ? { ...DEFAULT_PREFS, ...JSON.parse(raw) } : { ...DEFAULT_PREFS }
  } catch {
    return { ...DEFAULT_PREFS }
  }
}

const preferences = ref<UserPreferences>(loadPreferences())
const messages = ref<AdvisorMessage[]>([])
const inputText = ref('')
const isGenerating = ref(false)
const showPrefs = ref(false)
const scrollEl = ref<HTMLElement | null>(null)

const lang = localStorage.getItem('lang') || 'en'

onMounted(() => {
  messages.value.push({ role: 'assistant', content: t('advisor.welcome'), tickers: [] })
})

function extractTickers(text: string): string[] {
  const matches = [...text.matchAll(/\$([A-Z]{1,5}(?:\.[A-Z]{1,3})?)\b/g)]
  return [...new Set(matches.map(m => m[1]))]
}

function renderMarkdown(text: string): string {
  return marked.parse(text) as string
}

async function scrollToBottom() {
  await nextTick()
  if (scrollEl.value) scrollEl.value.scrollTop = scrollEl.value.scrollHeight
}

async function send() {
  const text = inputText.value.trim()
  if (!text || isGenerating.value) return

  inputText.value = ''
  messages.value.push({ role: 'user', content: text })
  await scrollToBottom()

  const botMsg: AdvisorMessage = { role: 'assistant', content: '', tickers: [] }
  messages.value.push(botMsg)
  isGenerating.value = true

  const history: ChatMessage[] = messages.value
    .slice(1, -1)
    .filter(m => m.content)
    .map(m => ({ role: m.role, content: m.content }))

  try {
    const generator = streamAdvisor(text, history, preferences.value, lang)
    for await (const chunk of generator) {
      botMsg.content += chunk
      await scrollToBottom()
    }
    botMsg.tickers = extractTickers(botMsg.content)
  } catch (e) {
    botMsg.content += `\n\n*Error: ${e}*`
  } finally {
    isGenerating.value = false
    await scrollToBottom()
  }
}

function savePreferences(prefs: UserPreferences) {
  preferences.value = prefs
  localStorage.setItem(PREFS_KEY, JSON.stringify(prefs))
  showPrefs.value = false
}
</script>
