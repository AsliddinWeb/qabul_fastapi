<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter, RouterLink } from 'vue-router'
import { AxiosError } from 'axios'
import {
  Phone, Eye, EyeOff, KeyRound, AlertCircle, ShieldCheck, ArrowRight,
} from 'lucide-vue-next'
import { authApi, sessionToUser } from '@/api/auth.api'
import { useAuthStore } from '@/stores/auth'
import { formatPhone, compactPhone, PLACEHOLDERS } from '@/utils/validators'

const router = useRouter()
const auth = useAuthStore()

const phone = ref('')
const password = ref('')
const showPassword = ref(false)
const loading = ref(false)
const error = ref<string | null>(null)

function onPhoneInput(e: Event) {
  phone.value = formatPhone((e.target as HTMLInputElement).value)
  if (error.value) error.value = null
}

const phoneValid = computed(() => /^\+998\d{9}$/.test(compactPhone(phone.value)))
const passwordValid = computed(() => password.value.length >= 8)
const canSubmit = computed(() => phoneValid.value && passwordValid.value && !loading.value)

async function submit() {
  error.value = null
  const compact = compactPhone(phone.value)
  if (!compact.match(/^\+998\d{9}$/)) {
    error.value = "Telefon: +998 XX XXX XX XX (12 raqam)"
    return
  }
  if (password.value.length < 8) {
    error.value = "Parol kamida 8 belgi bo'lishi kerak"
    return
  }
  loading.value = true
  try {
    const res = await authApi.staffLogin(compact, password.value)
    auth.setSession(
      res.tokens.access_token,
      res.tokens.refresh_token,
      sessionToUser(res.session),
    )
    const target =
      res.session.role === 'admin' || res.session.role === 'superadmin' ? '/admin' :
      res.session.role === 'operator'   ? '/operator'   :
      res.session.role === 'director'   ? '/director'   :
      res.session.role === 'accountant' ? '/accountant' : '/'
    router.push(target)
  } catch (e) {
    const ax = e as AxiosError<{ error?: { message?: string } }>
    error.value = ax.response?.data?.error?.message ||
      (ax.response?.status === 401 ? "Telefon yoki parol noto'g'ri" : "Xatolik yuz berdi")
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div>
      <div class="inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-violet-50 dark:bg-violet-500/15 text-violet-700 dark:text-violet-300 text-[11px] font-bold uppercase tracking-wider mb-3">
        <KeyRound class="w-3 h-3" />
        Xodim
      </div>
      <h1 class="text-2xl font-bold text-slate-900 dark:text-slate-100 tracking-tight">
        Xodim sifatida kirish
      </h1>
      <p class="mt-2 text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
        Telefon raqam va parolingiz bilan tizimga kiring.
      </p>
    </div>

    <form class="space-y-4" @submit.prevent="submit" novalidate>
      <!-- Phone -->
      <div>
        <label for="staff-phone" class="block text-[11px] font-bold uppercase tracking-wider text-slate-600 dark:text-slate-400 mb-2 inline-flex items-center gap-1.5">
          <Phone class="w-3 h-3" /> Telefon raqam
        </label>
        <input
          id="staff-phone"
          :value="phone"
          type="tel"
          inputmode="tel"
          autocomplete="username"
          autofocus
          :placeholder="PLACEHOLDERS.phoneUz"
          class="input font-mono text-base !py-3.5"
          :class="error ? 'error' : ''"
          :disabled="loading"
          @input="onPhoneInput"
        />
      </div>

      <!-- Password -->
      <div>
        <label for="staff-password" class="block text-[11px] font-bold uppercase tracking-wider text-slate-600 dark:text-slate-400 mb-2 inline-flex items-center gap-1.5">
          <KeyRound class="w-3 h-3" /> Parol
        </label>
        <div class="relative">
          <input
            id="staff-password"
            v-model="password"
            :type="showPassword ? 'text' : 'password'"
            autocomplete="current-password"
            placeholder="••••••••"
            class="input text-base !py-3.5 !pr-12"
            :class="error ? 'error' : ''"
            :disabled="loading"
          />
          <button
            type="button"
            class="absolute right-3 top-1/2 -translate-y-1/2 grid place-items-center w-8 h-8 rounded-lg text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
            tabindex="-1"
            :title="showPassword ? 'Yashirish' : 'Korsatish'"
            @click="showPassword = !showPassword"
          >
            <EyeOff v-if="showPassword" class="w-4 h-4" />
            <Eye v-else class="w-4 h-4" />
          </button>
        </div>
        <p v-if="password && !passwordValid" class="mt-2 text-xs text-amber-600 dark:text-amber-400">
          Kamida 8 belgi
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
             class="rounded-xl px-4 py-3 bg-rose-50 dark:bg-rose-500/10 border border-rose-200/60 dark:border-rose-700/30 flex items-start gap-3">
          <AlertCircle class="w-5 h-5 text-rose-600 dark:text-rose-400 shrink-0 mt-0.5" />
          <div class="flex-1 min-w-0">
            <div class="text-sm font-semibold text-rose-900 dark:text-rose-200">
              Kirish amalga oshmadi
            </div>
            <p class="text-xs mt-0.5 text-rose-800 dark:text-rose-300 leading-relaxed">
              {{ error }}
            </p>
          </div>
        </div>
      </Transition>

      <!-- Submit -->
      <button
        type="submit"
        class="w-full inline-flex items-center justify-center gap-2 px-5 py-3.5 rounded-xl text-[15px] font-semibold bg-brand-600 hover:bg-brand-700 text-white shadow-lg shadow-brand-500/25 hover:shadow-xl hover:shadow-brand-500/30 hover:-translate-y-0.5 transition-all disabled:opacity-50 disabled:pointer-events-none"
        :disabled="!canSubmit"
      >
        <span v-if="loading" class="inline-flex items-center gap-2">
          <svg class="animate-spin" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 12a9 9 0 1 1-6.219-8.56" />
          </svg>
          Kirilmoqda...
        </span>
        <span v-else class="inline-flex items-center gap-2">
          Kirish
          <ArrowRight class="w-4 h-4" />
        </span>
      </button>
    </form>

    <!-- Privacy hint -->
    <div class="flex items-start gap-2 text-[11px] text-slate-500 dark:text-slate-400 leading-relaxed">
      <ShieldCheck class="w-3.5 h-3.5 shrink-0 mt-px" />
      <span>Sizning ma'lumotlaringiz xavfsiz shifrlangan kanal orqali jo'natiladi.</span>
    </div>

    <!-- Applicant link -->
    <div class="pt-5 border-t border-slate-100 dark:border-slate-800 text-center">
      <RouterLink to="/auth/login"
                  class="inline-flex items-center gap-1.5 text-sm font-medium text-slate-600 dark:text-slate-400 hover:text-brand-600 dark:hover:text-brand-300 transition-colors">
        Abituriyentmi?
        <span class="text-brand-600 dark:text-brand-300">SMS-kod orqali kirish →</span>
      </RouterLink>
    </div>
  </div>
</template>
