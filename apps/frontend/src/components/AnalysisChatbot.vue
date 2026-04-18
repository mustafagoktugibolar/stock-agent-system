<template>
  <div class="flex h-full flex-col rounded-xl border border-white/[0.08] bg-[var(--color-bg)] shadow-[0_0_40px_rgba(0,0,0,0.5)] overflow-hidden">
    <!-- Header -->
    <div class="flex items-center justify-between border-b border-white/[0.06] bg-[var(--color-bg)] px-4 py-3">
      <div class="flex items-center gap-3">
        <div class="relative flex h-8 w-8 items-center justify-center rounded-full bg-green-500/10">
          <svg class="h-4 w-4 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
          </svg>
          <span class="absolute bottom-0 right-0 block h-2.5 w-2.5 rounded-full border-2 border-[var(--color-bg)]" :class="isGenerating ? 'bg-amber-500' : 'bg-green-500'" />
        </div>
        <div>
          <h3 class="text-sm font-semibold text-white">{{ t('nav.ask.agent') }}</h3>
          <p class="text-[10px] text-[var(--color-text-muted)]">{{ t('chat.context', { symbol }) }}</p>
        </div>
      </div>
      <div class="flex items-center gap-1">
        <button @click="$emit('toggle-fullscreen')" class="p-1 text-[var(--color-text-muted)] hover:text-white transition" title="Toggle Fullscreen">
          <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" class="w-5 h-5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
          </svg>
        </button>
        <button @click="$emit('close')" class="p-1 text-[var(--color-text-muted)] hover:text-white transition" title="Close Chat">
          <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" class="w-5 h-5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>

    <!-- Message Area -->
    <div class="flex-1 overflow-y-auto p-4 space-y-4" ref="messagesContainer">
      <div
        v-for="(msg, i) in messages"
        :key="i"
        class="flex flex-col max-w-[85%]"
        :class="msg.role === 'user' ? 'self-end items-end' : 'self-start items-start'"
      >
        <span class="mb-1 text-[10px] text-[var(--color-text-muted)] uppercase tracking-wider font-semibold">
          {{ msg.role === 'user' ? 'You' : 'Agent' }}
        </span>
        <div v-if="msg.role === 'assistant' && msg.content"
          class="prose prose-invert prose-sm max-w-none px-4 py-2.5 rounded-2xl bg-white/[0.06] text-[var(--color-text)] rounded-tl-sm border border-white/[0.04] prose-p:leading-relaxed prose-pre:bg-black/50 prose-pre:border prose-pre:border-white/[0.08]"
          v-html="parseMarkdown(msg.content)"
        ></div>
        <div v-else
          class="px-4 py-2.5 rounded-2xl text-sm bg-green-600 text-white rounded-br-sm"
        >
          <p class="whitespace-pre-wrap leading-relaxed">{{ msg.content }}</p>
        </div>
      </div>

      <!-- Loading / Typing Indicator -->
      <div v-if="isGenerating" class="self-start flex flex-col max-w-[80%]">
         <span class="mb-1 text-[10px] text-[var(--color-text-muted)] uppercase tracking-wider font-semibold">Agent</span>
         <div class="px-4 py-3 rounded-2xl bg-white/[0.06] text-[var(--color-text)] rounded-tl-sm border border-white/[0.04]">
           <div class="flex space-x-1.5 h-4 items-center">
             <div class="w-1.5 h-1.5 bg-[var(--color-text-muted)] rounded-full animate-bounce"></div>
             <div class="w-1.5 h-1.5 bg-[var(--color-text-muted)] rounded-full animate-bounce" style="animation-delay: 0.2s"></div>
             <div class="w-1.5 h-1.5 bg-[var(--color-text-muted)] rounded-full animate-bounce" style="animation-delay: 0.4s"></div>
           </div>
         </div>
      </div>
    </div>

    <!-- Input Box -->
    <div class="p-3 border-t border-white/[0.06] bg-[var(--color-bg)]">
      <form @submit.prevent="sendMessage" class="relative flex items-center">
        <input
          v-model="inputText"
          type="text"
          :placeholder="t('chat.placeholder')"
          class="w-full bg-white/[0.04] border border-white/[0.08] rounded-full pl-4 pr-12 py-3 text-sm text-white placeholder-[var(--color-text-muted)] focus:outline-none focus:border-green-500/50 transition-colors"
          :disabled="isGenerating"
        />
        <button
          type="submit"
          :disabled="!inputText.trim() || isGenerating"
          class="absolute right-1.5 p-2 rounded-full bg-green-600 text-white hover:bg-green-500 disabled:opacity-30 disabled:hover:bg-green-600 transition"
        >
          <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" class="w-4 h-4 -rotate-45 ml-0.5 mb-0.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
          </svg>
        </button>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import { streamChat } from '@/services/api'
import type { ChatMessage } from '@/services/api'
import { t } from '@/locales'
import { marked } from 'marked'

const props = defineProps<{ symbol: string; language: string }>()
defineEmits<{ (e: 'close'): void; (e: 'toggle-fullscreen'): void }>()

const inputText = ref('')
const messages = ref<ChatMessage[]>([
  { role: 'assistant', content: `Hello! I've just analyzed ${props.symbol}. What would you like to know?` }
])
const isGenerating = ref(false)
const messagesContainer = ref<HTMLElement | null>(null)

const parseMarkdown = (content: string) => {
  return marked.parse(content, { async: false })
}

const scrollToBottom = async () => {
  await nextTick()
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

const sendMessage = async () => {
  const text = inputText.value.trim()
  if (!text || isGenerating.value) return

  // User message
  messages.value.push({ role: 'user', content: text })
  inputText.value = ''
  isGenerating.value = true
  scrollToBottom()

  // Assistant message placeholder
  const botMessage: ChatMessage = { role: 'assistant', content: '' }
  messages.value.push(botMessage)
  
  // Exclude the placeholder and the brand new user message to form the history correctly
  // Wait, the API takes history EXCLUDING the immediate new prompt
  const historyRaw = messages.value.slice(1, -2) // slice(1) to remove greeting

  try {
    const generator = streamChat(props.symbol, text, historyRaw, props.language)
    
    for await (const chunk of generator) {
      botMessage.content += chunk
      scrollToBottom() // Keep scrolling as it types
    }
  } catch (err) {
    botMessage.content += '\n\n*Error: Could not complete response.*'
  } finally {
    isGenerating.value = false
    scrollToBottom()
  }
}

onMounted(() => {
  scrollToBottom()
})
</script>
