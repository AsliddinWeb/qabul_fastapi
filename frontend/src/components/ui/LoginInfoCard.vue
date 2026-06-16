<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import {
  KeyRound, Phone, Clock, ShieldCheck, ShieldAlert, RotateCcw, Copy, Check,
} from 'lucide-vue-next'
import { adminApi, type UserRead } from '@/api/admin.api'
import { usersApi } from '@/api/users.api'
import { useAuthStore } from '@/stores/auth'
import { useToast } from '@/composables/useToast'
import { useConfirm } from '@/composables/useConfirm'
import { formatPhone } from '@/utils/validators'

const props = defineProps<{
  userId: string
}>()

const auth = useAuthStore()
const toast = useToast()
const { ask } = useConfirm()

// Loose `any` so we can hold either a full UserRead (admin path) or
// a UserLookup (operator path) without making the template care.
const user = ref<UserRead | any>(null)
const loading = ref(true)
const copied = ref(false)
const resetting = ref(false)

const isAdmin = computed(() => ['admin', 'superadmin'].includes(auth.user?.role || ''))
const canReadUsers = computed(() => auth.hasPermission('users.read'))

async function load() {
  if (!props.userId) return
  loading.value = true
  try {
    if (canReadUsers.value) {
      // Admin path — full UserRead so we get is_active + last_login_at
      // for the status pill and "Oxirgi kirish" row, plus password reset.
      user.value = await adminApi.users.get(props.userId)
    } else {
      // Operator / accountant path — minimal lookup, no 403 anymore.
      user.value = await usersApi.one(props.userId)
    }
  } catch {
    user.value = null
  } finally {
    loading.value = false
  }
}
onMounted(load)
watch(() => props.userId, load)

const loginMethod = computed(() => {
  if (!user.value) return ''
  return user.value.role === 'applicant' ? 'SMS-OTP' : 'Telefon + parol'
})

function relTime(iso: string | null | undefined): string {
  if (!iso) return 'hech qachon'
  const d = new Date(iso); const diff = Date.now() - d.getTime()
  if (diff < 60_000) return 'hozirgina'
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)} daq oldin`
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)} soat oldin`
  if (diff < 7 * 86_400_000) return `${Math.floor(diff / 86_400_000)} kun oldin`
  return d.toLocaleDateString('uz-UZ', { day: '2-digit', month: 'short', year: 'numeric' })
}

async function copyPhone() {
  if (!user.value?.phone) return
  try {
    await navigator.clipboard.writeText(user.value.phone)
    copied.value = true
    setTimeout(() => { copied.value = false }, 1500)
  } catch { toast.error("Nusxalab bo'lmadi") }
}

function generatePassword(): string {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789'
  let p = ''
  for (let i = 0; i < 10; i++) p += chars[Math.floor(Math.random() * chars.length)]
  return p
}

async function resetPassword() {
  if (!user.value) return
  const newPwd = generatePassword()
  const ok = await ask({
    title: 'Parolni tiklash',
    message: `${user.value.phone} uchun yangi parol o'rnatilsinmi?\n\nYangi parol: ${newPwd}\n\nFoydalanuvchi keyingi safarda shu parol bilan kirishi mumkin.`,
    confirmLabel: "Tiklash",
    tone: 'danger',
  })
  if (!ok) return
  resetting.value = true
  try {
    await adminApi.users.resetPassword(user.value.id, newPwd)
    await navigator.clipboard.writeText(newPwd).catch(() => {})
    toast.success(`Parol tiklandi va clipboard'ga nusxalandi: ${newPwd}`)
  } catch (e: any) {
    toast.error(e?.response?.data?.error?.message || "Parolni tiklab bo'lmadi")
  } finally {
    resetting.value = false
  }
}
</script>

<template>
  <section class="card overflow-hidden">
    <!-- Header -->
    <div class="flex items-center gap-3 px-5 sm:px-6 py-4 border-b border-slate-100 dark:border-slate-800">
      <span class="grid place-items-center w-9 h-9 rounded-xl bg-violet-100 text-violet-600 dark:bg-violet-500/20 dark:text-violet-300 shrink-0">
        <KeyRound class="w-4 h-4" />
      </span>
      <div class="flex-1 min-w-0">
        <h3 class="font-bold text-sm text-slate-900 dark:text-slate-100">
          Tizimga kirish ma'lumotlari
        </h3>
        <p class="text-[11px] text-slate-500 dark:text-slate-400">
          Foydalanuvchi tizimga shu ma'lumotlar bilan kiradi
        </p>
      </div>
      <!-- is_active comes from the full admin endpoint — hidden in
           operator/accountant view where we only have the lookup
           payload (id + name + phone + role). -->
      <span v-if="user && 'is_active' in user" class="pill"
            :class="user.is_active
              ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300'
              : 'bg-rose-50 text-rose-700 dark:bg-rose-500/15 dark:text-rose-300'">
        <component :is="user.is_active ? ShieldCheck : ShieldAlert" class="w-3 h-3" />
        {{ user.is_active ? 'Faol' : 'Bloklangan' }}
      </span>
    </div>

    <!-- Body -->
    <div class="p-5 sm:p-6 space-y-4">
      <!-- Loading skeleton -->
      <template v-if="loading">
        <div class="space-y-3">
          <div class="h-4 w-24 skel"></div>
          <div class="h-10 w-full skel"></div>
          <div class="h-3 w-32 skel"></div>
        </div>
      </template>

      <template v-else-if="!user">
        <p class="text-sm text-slate-500 dark:text-slate-400">
          Foydalanuvchi ma'lumotlari topilmadi
        </p>
      </template>

      <template v-else>
        <!-- Phone (login) -->
        <div>
          <div class="text-[10px] uppercase tracking-wider font-bold text-slate-500 dark:text-slate-400 mb-1.5 inline-flex items-center gap-1.5">
            <Phone class="w-3 h-3" />
            Telefon raqam (login)
          </div>
          <div class="flex items-center gap-2">
            <div class="flex-1 px-4 py-3 rounded-xl bg-slate-50 dark:bg-slate-800/40 ring-1 ring-slate-200/60 dark:ring-slate-700/40">
              <span class="font-mono text-base font-bold text-slate-900 dark:text-slate-100 tabular-nums">
                {{ formatPhone(user.phone) }}
              </span>
            </div>
            <button
              class="grid place-items-center w-11 h-11 rounded-xl text-slate-600 dark:text-slate-300 bg-slate-50 dark:bg-slate-800/40 hover:bg-slate-100 dark:hover:bg-slate-800 ring-1 ring-slate-200/60 dark:ring-slate-700/40 transition-colors"
              :title="copied ? 'Nusxalandi' : 'Nusxalash'"
              @click="copyPhone"
            >
              <Check v-if="copied" class="w-4 h-4 text-emerald-500" />
              <Copy v-else class="w-4 h-4" />
            </button>
          </div>
        </div>

        <!-- Login method -->
        <div>
          <div class="text-[10px] uppercase tracking-wider font-bold text-slate-500 dark:text-slate-400 mb-1.5">
            Tizimga kirish usuli
          </div>
          <div class="flex items-center gap-2 text-sm font-medium text-slate-900 dark:text-slate-100">
            <span class="grid place-items-center w-6 h-6 rounded-md bg-brand-50 text-brand-600 dark:bg-brand-500/20 dark:text-brand-300">
              <KeyRound class="w-3.5 h-3.5" />
            </span>
            {{ loginMethod }}
          </div>
        </div>

        <!-- Last login — same caveat: only present in the admin payload. -->
        <div v-if="'last_login_at' in user">
          <div class="text-[10px] uppercase tracking-wider font-bold text-slate-500 dark:text-slate-400 mb-1.5">
            Oxirgi kirish
          </div>
          <div class="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
            <Clock class="w-4 h-4 text-slate-400" />
            {{ relTime(user.last_login_at) }}
          </div>
        </div>

        <!-- Reset password (admin + only for users with passwords) -->
        <div v-if="isAdmin && user.role !== 'applicant'"
             class="pt-3 border-t border-slate-100 dark:border-slate-800">
          <button
            class="inline-flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-semibold text-slate-700 dark:text-slate-300 bg-slate-50 dark:bg-slate-800/40 hover:bg-slate-100 dark:hover:bg-slate-800 ring-1 ring-slate-200/60 dark:ring-slate-700/40 transition-colors disabled:opacity-50"
            :disabled="resetting"
            @click="resetPassword"
          >
            <RotateCcw class="w-3.5 h-3.5" />
            {{ resetting ? "Tiklanmoqda..." : "Parolni tiklash" }}
          </button>
          <p class="mt-2 text-[11px] text-slate-500 dark:text-slate-400">
            Yangi parol generatsiya qilinadi va clipboard'ga nusxalanadi
          </p>
        </div>

        <div v-else-if="user.role === 'applicant'"
             class="pt-3 border-t border-slate-100 dark:border-slate-800 text-[11px] text-slate-500 dark:text-slate-400 leading-relaxed">
          Abituriyent har safar tizimga SMS-OTP orqali kiradi. Parol talab qilinmaydi.
        </div>
      </template>
    </div>
  </section>
</template>
