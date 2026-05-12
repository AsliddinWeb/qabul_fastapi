<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import { Phone, ArrowRight, AlertCircle, CheckCircle2, ShieldCheck } from 'lucide-vue-next'
import { authApi } from '@/api/auth.api'
import { AxiosError } from 'axios'
import { formatPhoneLocal, localToCompact, PLACEHOLDERS } from '@/utils/validators'

const router = useRouter()
const route = useRoute()
const phone = ref('')
const loading = ref(false)
const error = ref<string | null>(null)
const errorCode = ref<string | null>(null)
const refCode = ref<string | null>(null)

onMounted(() => {
  // Capture ?ref=CODE so the new applicant gets attached to the inviter once
  // they complete the OTP + onboarding wizard. We stash it on sessionStorage
  // so the value survives the OTP redirect; the ProfilePage onboarding step
  // reads it back when calling POST /applicants/me.
  const q = (route.query.ref || route.query.referral_code) as string | undefined
  if (q && typeof q === 'string') {
    const cleaned = q.toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 8)
    if (cleaned.length >= 4) {
      sessionStorage.setItem('referrer_code', cleaned)
      refCode.value = cleaned
    }
  } else {
    refCode.value = sessionStorage.getItem('referrer_code')
  }
})

function onPhoneInput(e: Event) {
  phone.value = formatPhoneLocal((e.target as HTMLInputElement).value)
  if (error.value) { error.value = null; errorCode.value = null }
}

const isValid = computed(() => /^\+998\d{9}$/.test(localToCompact(phone.value)))

async function submit() {
  error.value = null
  errorCode.value = null
  const compact = localToCompact(phone.value)
  if (!compact.match(/^\+998\d{9}$/)) {
    error.value = "Telefon raqamini to'liq kiriting: 9 ta raqam"
    return
  }
  loading.value = true
  try {
    const res = await authApi.requestOtp(compact)
    // Only proceed if SMS was attempted (success). Backend already throws on failure.
    router.push({
      name: 'otp-verify',
      query: {
        phone: res.phone,
        ttl: String(res.expires_in),
        cooldown: String(res.resend_after),
        delivered: res.delivered ? '1' : '0',
        len: String(res.code_length),
      },
    })
  } catch (e) {
    const ax = e as AxiosError<{ error?: { message?: string; code?: string } }>
    errorCode.value = ax.response?.data?.error?.code || null
    error.value = ax.response?.data?.error?.message ||
      (ax.response?.status === 429 ? "Juda ko'p so'rov. Birozdan keyin urinib ko'ring." :
       ax.response?.status === 502 ? "SMS yuborib bo'lmadi. Internetni tekshiring yoki keyinroq urinib ko'ring." :
       "Xatolik. Qaytadan urinib ko'ring.")
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div>
      <div class="inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-brand-50 dark:bg-brand-500/15 text-brand-700 dark:text-brand-300 text-[11px] font-bold uppercase tracking-wider mb-3">
        <ShieldCheck class="w-3 h-3" />
        Xavfsiz kirish
      </div>
      <h1 class="text-2xl font-bold text-slate-900 dark:text-slate-100 tracking-tight">
        Tizimga kirish
      </h1>
      <p class="mt-2 text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
        Telefon raqamingizni kiriting — SMS-kod yuboramiz.
      </p>

      <div v-if="refCode" class="mt-3 inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-emerald-50 dark:bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 text-xs">
        <CheckCircle2 class="w-3.5 h-3.5 shrink-0" />
        <span>Sizni tavsiya qilgan kod: <strong class="font-mono">{{ refCode }}</strong></span>
      </div>
    </div>

    <form class="space-y-4" @submit.prevent="submit" novalidate>
      <div>
        <label for="phone" class="block text-[11px] font-bold uppercase tracking-wider text-slate-600 dark:text-slate-400 mb-2 inline-flex items-center gap-1.5">
          <Phone class="w-3 h-3" /> Telefon raqam
        </label>
        <div class="relative">
          <span class="absolute inset-y-0 left-0 flex items-center px-3 rounded-l-xl bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 text-sm font-mono font-semibold border border-r-0 border-slate-200 dark:border-slate-700 pointer-events-none select-none">
            +998
          </span>
          <input
            id="phone"
            :value="phone"
            type="tel"
            inputmode="tel"
            autocomplete="tel-national"
            autofocus
            :placeholder="PLACEHOLDERS.phoneUzLocal"
            class="input font-mono text-base !py-3.5 !pl-[4.5rem]"
            :class="error ? 'error' : ''"
            :disabled="loading"
            @input="onPhoneInput"
          />
        </div>
        <p v-if="!error && isValid" class="mt-2 text-xs inline-flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400">
          <CheckCircle2 class="w-3.5 h-3.5" />
          Telefon raqami to'g'ri kiritildi
        </p>
      </div>

      <!-- Error banner -->
      <Transition
        enter-active-class="transition-all duration-200"
        leave-active-class="transition-all duration-150"
        enter-from-class="opacity-0 -translate-y-1"
        leave-to-class="opacity-0"
      >
        <div v-if="error"
             class="rounded-xl px-4 py-3 flex items-start gap-3"
             :class="errorCode === 'sms_failed'
               ? 'bg-amber-50 dark:bg-amber-500/10 border border-amber-200/60 dark:border-amber-700/30'
               : 'bg-rose-50 dark:bg-rose-500/10 border border-rose-200/60 dark:border-rose-700/30'">
          <AlertCircle
            class="w-5 h-5 shrink-0 mt-0.5"
            :class="errorCode === 'sms_failed' ? 'text-amber-600 dark:text-amber-400' : 'text-rose-600 dark:text-rose-400'"
          />
          <div class="flex-1 min-w-0">
            <div class="text-sm font-semibold"
                 :class="errorCode === 'sms_failed' ? 'text-amber-900 dark:text-amber-200' : 'text-rose-900 dark:text-rose-200'">
              {{ errorCode === 'sms_failed' ? "SMS yuborib bo'lmadi" : "Xatolik" }}
            </div>
            <p class="text-xs mt-0.5 leading-relaxed"
               :class="errorCode === 'sms_failed' ? 'text-amber-800 dark:text-amber-300' : 'text-rose-800 dark:text-rose-300'">
              {{ error }}
            </p>
          </div>
        </div>
      </Transition>

      <button
        type="submit"
        class="w-full inline-flex items-center justify-center gap-2 px-5 py-3.5 rounded-xl text-[15px] font-semibold bg-brand-600 hover:bg-brand-700 text-white shadow-lg shadow-brand-500/25 hover:shadow-xl hover:shadow-brand-500/30 hover:-translate-y-0.5 transition-all disabled:opacity-50 disabled:pointer-events-none"
        :disabled="loading || !phone"
      >
        <span v-if="loading" class="inline-flex items-center gap-2">
          <svg class="animate-spin" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 12a9 9 0 1 1-6.219-8.56" />
          </svg>
          SMS yuborilmoqda...
        </span>
        <span v-else class="inline-flex items-center gap-2">
          SMS-kod olish
          <ArrowRight class="w-4 h-4" />
        </span>
      </button>
    </form>

    <!-- Privacy hint -->
    <div class="flex items-start gap-2 text-[11px] text-slate-500 dark:text-slate-400 leading-relaxed">
      <ShieldCheck class="w-3.5 h-3.5 shrink-0 mt-px" />
      <span>SMS-kod yuborish bepul. Davom ettirish bilan siz foydalanish shartlariga rozilik bildirasiz.</span>
    </div>

    <!-- Staff link -->
    <div class="pt-5 border-t border-slate-100 dark:border-slate-800 text-center">
      <RouterLink to="/auth/staff"
                  class="inline-flex items-center gap-1.5 text-sm font-medium text-slate-600 dark:text-slate-400 hover:text-brand-600 dark:hover:text-brand-300 transition-colors">
        Xodimmisiz?
        <span class="text-brand-600 dark:text-brand-300">Parol bilan kirish →</span>
      </RouterLink>
    </div>
  </div>
</template>
