<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { Download, X, Smartphone } from 'lucide-vue-next'

const deferredPrompt = ref<any>(null)
const showBanner = ref(false)
const installed = ref(false)

const STORAGE_KEY = 'xiu-install-dismissed-at'
const SUPPRESS_DAYS = 14

function isSuppressed(): boolean {
  const at = localStorage.getItem(STORAGE_KEY)
  if (!at) return false
  const ts = parseInt(at, 10)
  if (Number.isNaN(ts)) return false
  return Date.now() - ts < SUPPRESS_DAYS * 24 * 3600 * 1000
}

function isStandalone(): boolean {
  return window.matchMedia('(display-mode: standalone)').matches
      || (window.navigator as any).standalone === true
}

onMounted(() => {
  if (isStandalone()) { installed.value = true; return }
  if (isSuppressed()) return

  window.addEventListener('beforeinstallprompt', (e: Event) => {
    e.preventDefault()
    deferredPrompt.value = e
    // Delay banner so it doesn't pop up instantly
    setTimeout(() => { if (!isSuppressed()) showBanner.value = true }, 4000)
  })

  window.addEventListener('appinstalled', () => {
    installed.value = true
    showBanner.value = false
    deferredPrompt.value = null
  })
})

async function install() {
  const p = deferredPrompt.value
  if (!p) return
  p.prompt()
  try { await p.userChoice } catch { /* ignore */ }
  deferredPrompt.value = null
  showBanner.value = false
}

function dismiss() {
  showBanner.value = false
  localStorage.setItem(STORAGE_KEY, String(Date.now()))
}
</script>

<template>
  <Transition
    enter-active-class="transition-all duration-300 ease-out"
    leave-active-class="transition-all duration-200 ease-in"
    enter-from-class="opacity-0 translate-y-4"
    leave-to-class="opacity-0 translate-y-2"
  >
    <div
      v-if="showBanner && !installed"
      class="fixed bottom-20 md:bottom-4 inset-x-3 md:inset-x-auto md:right-6 md:max-w-sm z-40
             rounded-2xl bg-white dark:bg-slate-900 ring-1 ring-slate-200/70 dark:ring-slate-700/40
             shadow-xl shadow-brand-500/10 p-4 flex items-start gap-3"
    >
      <span class="grid place-items-center w-10 h-10 rounded-xl bg-gradient-to-br from-brand-500 to-violet-500 text-white shrink-0">
        <Smartphone class="w-5 h-5" />
      </span>
      <div class="flex-1 min-w-0">
        <div class="text-sm font-semibold text-slate-900 dark:text-slate-100">XIU'ni telefonga o'rnating</div>
        <p class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
          Tezroq ochish va offline rejim. Brauzerni ochib o'tirmasdan ishlang.
        </p>
        <div class="mt-2.5 flex items-center gap-2">
          <button
            class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-brand-600 hover:bg-brand-700 text-white shadow-sm"
            @click="install"
          >
            <Download class="w-3.5 h-3.5" /> O'rnatish
          </button>
          <button
            class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
            @click="dismiss"
          >
            Keyinroq
          </button>
        </div>
      </div>
      <button
        class="grid place-items-center w-7 h-7 rounded-lg text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors shrink-0"
        @click="dismiss"
        aria-label="Yopish"
      >
        <X class="w-4 h-4" />
      </button>
    </div>
  </Transition>
</template>
