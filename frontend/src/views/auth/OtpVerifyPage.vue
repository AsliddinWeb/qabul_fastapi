<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { AxiosError } from 'axios'
import {
  ArrowLeft, MessageSquare, AlertCircle, RefreshCw, ShieldCheck, AlertTriangle,
} from 'lucide-vue-next'
import { authApi, sessionToUser } from '@/api/auth.api'
import { useAuthStore } from '@/stores/auth'
import { formatPhone } from '@/utils/validators'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const phone = (route.query.phone as string) || ''
const initialTtl = Number(route.query.ttl) || 120
const initialCooldown = Number(route.query.cooldown) || 60
const wasDelivered = route.query.delivered !== '0'  // default true (real SMS)

// Server-configured code length (4 or 6, set via OTP_LENGTH env). Falls back to 4.
const OTP_LEN = Math.max(4, Math.min(8, Number(route.query.len) || 4))
const codePattern = new RegExp(`^\\d{${OTP_LEN}}$`)
const digits = ref<string[]>(Array(OTP_LEN).fill(''))
const inputs = ref<HTMLInputElement[]>([])
const loading = ref(false)
const resending = ref(false)
const error = ref<string | null>(null)
const errorCode = ref<string | null>(null)
const success = ref<string | null>(null)
const remaining = ref(initialTtl)
const cooldown = ref(initialCooldown)

let timer: ReturnType<typeof setInterval> | null = null

onMounted(() => {
  if (!phone) {
    router.replace({ name: 'phone-login' })
    return
  }
  // Focus first digit
  nextTick(() => inputs.value[0]?.focus())
  timer = setInterval(() => {
    remaining.value = Math.max(0, remaining.value - 1)
    cooldown.value = Math.max(0, cooldown.value - 1)
  }, 1000)
})
onUnmounted(() => { if (timer) clearInterval(timer) })

const code = computed(() => digits.value.join(''))
const isComplete = computed(() => code.value.length === OTP_LEN && codePattern.test(code.value))
const minutes = computed(() => String(Math.floor(remaining.value / 60)).padStart(2, '0'))
const seconds = computed(() => String(remaining.value % 60).padStart(2, '0'))

function setRef(el: any, idx: number) {
  if (el) inputs.value[idx] = el
}

function onDigitInput(idx: number, e: Event) {
  const v = (e.target as HTMLInputElement).value.replace(/\D/g, '').slice(-1)
  digits.value[idx] = v
  error.value = null
  errorCode.value = null
  if (v && idx < OTP_LEN - 1) {
    nextTick(() => inputs.value[idx + 1]?.focus())
  }
  // Auto-submit when last digit entered
  if (idx === OTP_LEN - 1 && v && isComplete.value) {
    submit()
  }
}

function onKeyDown(idx: number, e: KeyboardEvent) {
  if (e.key === 'Backspace' && !digits.value[idx] && idx > 0) {
    nextTick(() => inputs.value[idx - 1]?.focus())
  } else if (e.key === 'ArrowLeft' && idx > 0) {
    inputs.value[idx - 1]?.focus()
  } else if (e.key === 'ArrowRight' && idx < OTP_LEN - 1) {
    inputs.value[idx + 1]?.focus()
  }
}

function onPaste(e: ClipboardEvent) {
  const t = (e.clipboardData?.getData('text') || '').replace(/\D/g, '').slice(0, OTP_LEN)
  if (!t) return
  e.preventDefault()
  for (let i = 0; i < OTP_LEN; i++) digits.value[i] = t[i] || ''
  nextTick(() => {
    const lastFilled = Math.min(t.length, OTP_LEN) - 1
    inputs.value[Math.min(lastFilled + 1, OTP_LEN - 1)]?.focus()
    if (isComplete.value) submit()
  })
}

async function submit() {
  if (loading.value || !isComplete.value) return
  error.value = null
  errorCode.value = null
  loading.value = true
  try {
    const res = await authApi.verifyOtp(phone, code.value)
    auth.setSession(
      res.tokens.access_token,
      res.tokens.refresh_token,
      sessionToUser(res.session),
    )
    const target =
      res.session.role === 'applicant' ? '/applicant' :
      res.session.role === 'operator'  ? '/operator'  :
      res.session.role === 'admin' || res.session.role === 'superadmin' ? '/admin' :
      res.session.role === 'director'  ? '/director'  :
      res.session.role === 'accountant' ? '/accountant' : '/'
    router.push(target)
  } catch (e) {
    const ax = e as AxiosError<{ error?: { message?: string; code?: string } }>
    errorCode.value = ax.response?.data?.error?.code || null
    error.value = ax.response?.data?.error?.message ||
      "Kod noto'g'ri yoki muddati o'tdi"
    // Clear digits on wrong code
    digits.value = Array(OTP_LEN).fill('')
    nextTick(() => inputs.value[0]?.focus())
  } finally { loading.value = false }
}

async function resend() {
  if (cooldown.value > 0 || resending.value) return
  error.value = null
  errorCode.value = null
  success.value = null
  resending.value = true
  try {
    const res = await authApi.requestOtp(phone)
    remaining.value = res.expires_in
    cooldown.value = res.resend_after
    digits.value = Array(OTP_LEN).fill('')
    nextTick(() => inputs.value[0]?.focus())
    success.value = res.delivered
      ? "Yangi kod yuborildi"
      : "Yangi kod tayyor (test rejimi)"
    setTimeout(() => { success.value = null }, 4000)
  } catch (e) {
    const ax = e as AxiosError<{ error?: { message?: string; code?: string } }>
    errorCode.value = ax.response?.data?.error?.code || null
    error.value = ax.response?.data?.error?.message || "Qayta yuborib bo'lmadi"
  } finally { resending.value = false }
}
</script>

<template>
  <div class="space-y-6">
    <!-- Back button -->
    <button
      type="button"
      class="inline-flex items-center gap-1.5 text-sm font-medium text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 transition-colors"
      @click="router.push({ name: 'phone-login' })"
    >
      <ArrowLeft class="w-4 h-4" /> Boshqa raqam
    </button>

    <!-- Header -->
    <div>
      <div class="grid place-items-center w-12 h-12 rounded-2xl bg-brand-100 text-brand-600 dark:bg-brand-500/20 dark:text-brand-300 mb-4">
        <MessageSquare class="w-5 h-5" />
      </div>
      <h1 class="text-2xl font-bold text-slate-900 dark:text-slate-100 tracking-tight">
        SMS-kodni kiriting
      </h1>
      <p class="mt-2 text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
        <span class="font-mono font-bold text-slate-900 dark:text-slate-100">{{ formatPhone(phone) }}</span>
        raqamiga {{ OTP_LEN }} xonali kod yuborildi.
      </p>
    </div>

    <!-- Dev-mode warning (no real SMS sent) -->
    <div v-if="!wasDelivered"
         class="rounded-xl px-4 py-3 bg-amber-50 dark:bg-amber-500/10 border border-amber-200/60 dark:border-amber-700/30 flex items-start gap-3">
      <AlertTriangle class="w-5 h-5 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
      <div class="flex-1 min-w-0">
        <div class="text-sm font-semibold text-amber-900 dark:text-amber-200">
          Test rejimi — SMS yuborilmadi
        </div>
        <p class="text-xs mt-0.5 text-amber-800 dark:text-amber-300 leading-relaxed">
          SMS xizmati sozlanmagan. Backend logiga qarab kodni qo'lda kiriting yoki administrator bilan bog'laning.
        </p>
      </div>
    </div>

    <form @submit.prevent="submit">
      <!-- Digit boxes -->
      <div class="flex items-center justify-between gap-2 mb-1" @paste="onPaste">
        <input
          v-for="i in OTP_LEN"
          :key="i"
          :ref="(el) => setRef(el, i - 1)"
          v-model="digits[i - 1]"
          type="text"
          inputmode="numeric"
          autocomplete="one-time-code"
          maxlength="1"
          class="w-full h-14 sm:h-16 text-center text-2xl sm:text-3xl font-bold tabular-nums rounded-xl bg-slate-50 dark:bg-slate-800/40 border-2 transition-all
                 focus:outline-none focus:ring-4 focus:ring-brand-500/20"
          :class="[
            error ? 'border-rose-400' : digits[i - 1] ? 'border-brand-500' : 'border-transparent focus:border-brand-500',
            'text-slate-900 dark:text-slate-100',
          ]"
          :disabled="loading"
          @input="onDigitInput(i - 1, $event)"
          @keydown="onKeyDown(i - 1, $event)"
        />
      </div>

      <!-- Timer + resend -->
      <div class="flex items-center justify-between text-sm mt-4">
        <div class="inline-flex items-center gap-1.5 text-slate-500 dark:text-slate-400">
          <span v-if="remaining > 0" class="tabular-nums">
            Amal qilish: <strong class="text-slate-900 dark:text-slate-100">{{ minutes }}:{{ seconds }}</strong>
          </span>
          <span v-else class="text-rose-600 dark:text-rose-400 font-semibold">Kod muddati tugadi</span>
        </div>
        <button
          type="button"
          class="inline-flex items-center gap-1.5 font-semibold transition-colors disabled:text-slate-400 dark:disabled:text-slate-600 disabled:cursor-not-allowed"
          :class="cooldown > 0 ? '' : 'text-brand-600 dark:text-brand-300 hover:text-brand-700 dark:hover:text-brand-200'"
          :disabled="cooldown > 0 || resending"
          @click="resend"
        >
          <RefreshCw class="w-3.5 h-3.5" :class="resending ? 'animate-spin' : ''" />
          <span v-if="cooldown > 0" class="tabular-nums text-slate-400 dark:text-slate-600">Qayta yuborish ({{ cooldown }}s)</span>
          <span v-else>Qayta yuborish</span>
        </button>
      </div>

      <!-- Success banner -->
      <Transition
        enter-active-class="transition-all duration-200"
        leave-active-class="transition-all duration-200"
        enter-from-class="opacity-0 -translate-y-1"
        leave-to-class="opacity-0"
      >
        <div v-if="success"
             class="mt-4 rounded-xl px-4 py-3 bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-200/60 dark:border-emerald-700/30 inline-flex items-center gap-2.5 text-sm">
          <ShieldCheck class="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
          <span class="text-emerald-900 dark:text-emerald-200 font-medium">{{ success }}</span>
        </div>
      </Transition>

      <!-- Error banner -->
      <Transition
        enter-active-class="transition-all duration-200"
        leave-active-class="transition-all duration-150"
        enter-from-class="opacity-0 -translate-y-1"
        leave-to-class="opacity-0"
      >
        <div v-if="error"
             class="mt-4 rounded-xl px-4 py-3 flex items-start gap-3"
             :class="errorCode === 'sms_failed'
               ? 'bg-amber-50 dark:bg-amber-500/10 border border-amber-200/60 dark:border-amber-700/30'
               : 'bg-rose-50 dark:bg-rose-500/10 border border-rose-200/60 dark:border-rose-700/30'">
          <AlertCircle class="w-5 h-5 shrink-0 mt-0.5"
            :class="errorCode === 'sms_failed' ? 'text-amber-600 dark:text-amber-400' : 'text-rose-600 dark:text-rose-400'" />
          <div class="flex-1 min-w-0">
            <div class="text-sm font-semibold"
                 :class="errorCode === 'sms_failed' ? 'text-amber-900 dark:text-amber-200' : 'text-rose-900 dark:text-rose-200'">
              {{ errorCode === 'sms_failed' ? "SMS yuborib bo'lmadi" : "Tasdiqlanmadi" }}
            </div>
            <p class="text-xs mt-0.5 leading-relaxed"
               :class="errorCode === 'sms_failed' ? 'text-amber-800 dark:text-amber-300' : 'text-rose-800 dark:text-rose-300'">
              {{ error }}
            </p>
          </div>
        </div>
      </Transition>

      <!-- Submit -->
      <button
        type="submit"
        class="mt-5 w-full inline-flex items-center justify-center gap-2 px-5 py-3.5 rounded-xl text-[15px] font-semibold bg-brand-600 hover:bg-brand-700 text-white shadow-lg shadow-brand-500/25 hover:shadow-xl hover:shadow-brand-500/30 hover:-translate-y-0.5 transition-all disabled:opacity-50 disabled:pointer-events-none"
        :disabled="loading || !isComplete"
      >
        <span v-if="loading" class="inline-flex items-center gap-2">
          <svg class="animate-spin" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 12a9 9 0 1 1-6.219-8.56" />
          </svg>
          Tekshirilmoqda...
        </span>
        <span v-else>Tasdiqlash</span>
      </button>
    </form>
  </div>
</template>
