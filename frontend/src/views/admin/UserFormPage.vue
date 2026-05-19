<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ArrowLeft, Save, Eye, EyeOff, KeyRound, ShieldCheck,
  User as UserIcon, Phone, Mail, Lock, Crown, Briefcase, Headphones,
  BarChart3, Wallet, ToggleRight, Check, X,
} from 'lucide-vue-next'
import { AxiosError } from 'axios'
import { adminApi, type UserCreatePayload } from '@/api/admin.api'
import type { Role } from '@/types'
import { useAuthStore } from '@/stores/auth'
import { useToast } from '@/composables/useToast'
import { useConfirm } from '@/composables/useConfirm'
import { PLACEHOLDERS, formatPhoneLocal, localToCompact, formatPhone, email as vEmail, password as vPassword } from '@/utils/validators'
import { TOGGLABLE_PERMISSIONS } from '@/utils/permissions'
import Skeleton from '@/components/ui/Skeleton.vue'
import PageHeader from '@/components/ui/PageHeader.vue'

const route = useRoute()
const router = useRouter()
const toast = useToast()
const auth = useAuthStore()
const { ask } = useConfirm()

const id = computed(() => route.params.id as string | undefined)
const isEdit = computed(() => !!id.value)

// Form holds the LOCAL phone portion (9 digits, "94 202 55 11"); the
// fixed "+998" sticker is rendered next to the input and prepended on
// submit. Keeps create/edit behaviour symmetric with the login screen.
const form = reactive<Omit<UserCreatePayload, 'phone'> & { phone: string }>({
  phone: '',
  full_name: '',
  email: '',
  role: 'operator',
  password: '',
  is_active: true,
  is_consulting: false,
})

const showPassword = ref(false)
const newPassword = ref('')
const showResetSection = ref(false)
const saving = ref(false)
const loading = ref(false)
const errors = ref<Record<string, string>>({})
const permissionsRevoked = ref<string[]>([])

// Role meta — shown as cards instead of a plain <select> so the choice is
// unmissable in both create and edit. Each card carries its own tone.
const ROLES: Array<{
  value: Role; label: string; desc: string;
  icon: any; tone: string; ring: string; iconBg: string;
}> = [
  { value: 'superadmin', label: 'Bosh administrator', desc: "Tizimga to'liq egalik. Faqat ishonchli shaxslar.",
    icon: Crown,       tone: 'from-violet-500/10 to-violet-500/0',
    ring: 'ring-violet-300 bg-violet-50/40 dark:ring-violet-500/40 dark:bg-violet-500/10',
    iconBg: 'bg-violet-100 text-violet-700 dark:bg-violet-500/20 dark:text-violet-300' },
  { value: 'admin',      label: 'Administrator', desc: 'Foydalanuvchilar, arizalar va auditni boshqaradi.',
    icon: ShieldCheck, tone: 'from-indigo-500/10 to-indigo-500/0',
    ring: 'ring-indigo-300 bg-indigo-50/40 dark:ring-indigo-500/40 dark:bg-indigo-500/10',
    iconBg: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-500/20 dark:text-indigo-300' },
  { value: 'operator',   label: 'Operator', desc: 'Lead, abituriyent, ariza va shartnomalar bilan ishlaydi.',
    icon: Headphones,  tone: 'from-amber-500/10 to-amber-500/0',
    ring: 'ring-amber-300 bg-amber-50/40 dark:ring-amber-500/40 dark:bg-amber-500/10',
    iconBg: 'bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-300' },
  { value: 'director',   label: 'Direktor', desc: "Hisobotlar va analitikani ko'radi (read-only).",
    icon: BarChart3,   tone: 'from-sky-500/10 to-sky-500/0',
    ring: 'ring-sky-300 bg-sky-50/40 dark:ring-sky-500/40 dark:bg-sky-500/10',
    iconBg: 'bg-sky-100 text-sky-700 dark:bg-sky-500/20 dark:text-sky-300' },
  { value: 'accountant', label: 'Buxgalter', desc: "To'lovlarni tasdiqlaydi, moliyaviy hisobot.",
    icon: Wallet,      tone: 'from-emerald-500/10 to-emerald-500/0',
    ring: 'ring-emerald-300 bg-emerald-50/40 dark:ring-emerald-500/40 dark:bg-emerald-500/10',
    iconBg: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-300' },
]

const visiblePermissions = computed(() =>
  TOGGLABLE_PERMISSIONS.filter(p => p.roles.includes(form.role)),
)
function isPermissionGranted(code: string): boolean {
  return !permissionsRevoked.value.includes(code)
}
function togglePermissionDirect(code: string) {
  if (permissionsRevoked.value.includes(code)) {
    permissionsRevoked.value = permissionsRevoked.value.filter(c => c !== code)
  } else {
    permissionsRevoked.value = [...permissionsRevoked.value, code]
  }
}

onMounted(async () => {
  if (!isEdit.value) return
  loading.value = true
  try {
    const u = await adminApi.users.get(id.value as string)
    // Strip "+998" from the loaded phone so the input matches the sticker
    // pattern — the user only edits the 9-digit local body.
    const localPhone = u.phone ? formatPhoneLocal(u.phone.replace(/^\+?998/, '')) : ''
    Object.assign(form, {
      phone: localPhone,
      full_name: u.full_name || '',
      email: u.email || '',
      role: u.role,
      is_active: u.is_active,
      is_consulting: !!u.is_consulting,
      password: '',
    })
    permissionsRevoked.value = Array.isArray(u.permissions_revoked) ? [...u.permissions_revoked] : []
  } catch (e) {
    const ax = e as AxiosError<{ error?: { message?: string } }>
    toast.error(ax.response?.data?.error?.message || "Foydalanuvchi topilmadi")
    router.push('/admin/users')
  } finally {
    loading.value = false
  }
})

watch(form, () => { errors.value = {} }, { deep: true })

function validateField(field: string) {
  const ne = { ...errors.value }
  delete ne[field]
  let err: string | null = null
  switch (field) {
    case 'phone':
      err = /^\+998\d{9}$/.test(localToCompact(form.phone)) ? null : "Telefon raqamini to'liq kiriting"
      break
    case 'role':     err = form.role ? null : "Rolni tanlang"; break
    case 'password': err = !isEdit.value ? vPassword(form.password || '') : null; break
    case 'email':    err = vEmail(form.email || ''); break
  }
  if (err) ne[field] = err
  errors.value = ne
}

function onPhoneInput(e: Event) {
  form.phone = formatPhoneLocal((e.target as HTMLInputElement).value)
  validateField('phone')
}

function validate(): boolean {
  ;['phone', 'role', 'password', 'email'].forEach(validateField)
  return Object.keys(errors.value).length === 0
}

async function submit() {
  if (!validate()) {
    toast.error("Maydonlarni to'g'ri to'ldiring")
    return
  }
  saving.value = true
  try {
    const compactPhone = localToCompact(form.phone)
    const sendable: any = {
      ...form,
      phone: compactPhone,
      email: form.email?.trim() ? form.email.trim() : null,
      permissions_revoked: permissionsRevoked.value,
    }
    if (isEdit.value && id.value) {
      // Don't send password on update — use reset password flow instead.
      const { password, ...payload } = sendable
      await adminApi.users.update(id.value, payload)
      toast.success("Foydalanuvchi yangilandi")
    } else {
      await adminApi.users.create(sendable)
      toast.success("Foydalanuvchi yaratildi")
    }
    router.push('/admin/users')
  } catch (e) {
    const ax = e as AxiosError<{ error?: { message?: string } }>
    toast.error(ax.response?.data?.error?.message || "Saqlab bo'lmadi")
  } finally {
    saving.value = false
  }
}

async function resetPassword() {
  if (newPassword.value.length < 8) {
    toast.error("Parol kamida 8 belgi bo'lishi kerak")
    return
  }
  const ok = await ask({
    title: "Parolni qayta tiklash",
    message: "Foydalanuvchining hozirgi paroli bekor qilinadi va yangisi o'rnatiladi.",
    confirmLabel: "Tasdiqlash",
    tone: 'primary',
  })
  if (!ok) return
  try {
    await adminApi.users.resetPassword(id.value as string, newPassword.value)
    toast.success("Parol yangilandi")
    newPassword.value = ''
    showResetSection.value = false
  } catch (e) {
    const ax = e as AxiosError<{ error?: { message?: string } }>
    toast.error(ax.response?.data?.error?.message || "Xatolik")
  }
}
</script>

<template>
  <div class="max-w-4xl mx-auto space-y-6">
    <PageHeader
      :title="isEdit ? 'Foydalanuvchini tahrirlash' : 'Yangi foydalanuvchi'"
      :subtitle="!isEdit
        ? `Xodim hisobini yarating. Telefon raqami login bo'ladi.`
        : ''"
      :crumbs="[{ label: 'Bosh sahifa', to: '/admin' }, { label: 'Foydalanuvchilar', to: '/admin/users' }]"
    >
      <button type="button" class="btn-ghost" @click="router.back()">
        <ArrowLeft class="w-4 h-4" /> Ortga
      </button>
    </PageHeader>

    <Skeleton v-if="loading" type="form" />

    <form v-else @submit.prevent="submit" class="space-y-5">

      <!-- 1) Role — visually dominant cards. Choosing wrong here has the
           biggest blast radius, so make it impossible to miss. -->
      <section class="card p-5 sm:p-6">
        <div class="flex items-start gap-3 mb-4">
          <span class="grid place-items-center w-8 h-8 rounded-lg bg-violet-100 text-violet-600 dark:bg-violet-500/20 dark:text-violet-300 shrink-0">
            <ShieldCheck class="w-4 h-4" />
          </span>
          <div class="min-w-0">
            <h3 class="font-semibold text-slate-900 dark:text-slate-100">Rol *</h3>
            <p class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Foydalanuvchining tizimdagi roli — huquqlar to'plamini belgilaydi.</p>
          </div>
        </div>
        <div class="grid sm:grid-cols-2 gap-2.5">
          <label v-for="r in ROLES" :key="r.value"
                 class="relative flex items-start gap-3 p-3.5 rounded-xl ring-1 cursor-pointer transition"
                 :class="form.role === r.value
                   ? `ring-2 ${r.ring}`
                   : 'ring-slate-200/70 dark:ring-slate-700/40 hover:ring-slate-300 dark:hover:ring-slate-600'">
            <input type="radio" :value="r.value" v-model="form.role" class="sr-only" />
            <span class="grid place-items-center w-10 h-10 rounded-lg shrink-0"
                  :class="r.iconBg">
              <component :is="r.icon" class="w-5 h-5" />
            </span>
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2">
                <span class="font-semibold text-sm text-slate-900 dark:text-slate-100">{{ r.label }}</span>
                <span v-if="form.role === r.value"
                      class="inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-300">
                  <Check class="w-3 h-3" /> Tanlandi
                </span>
              </div>
              <p class="text-xs text-slate-500 dark:text-slate-400 mt-1 leading-relaxed">{{ r.desc }}</p>
            </div>
          </label>
        </div>
        <p v-if="errors.role" class="mt-2 text-xs text-rose-600">{{ errors.role }}</p>
      </section>

      <!-- 2) Identity — phone, full name, email -->
      <section class="card p-5 sm:p-6">
        <div class="flex items-start gap-3 mb-4">
          <span class="grid place-items-center w-8 h-8 rounded-lg bg-sky-100 text-sky-600 dark:bg-sky-500/20 dark:text-sky-300 shrink-0">
            <UserIcon class="w-4 h-4" />
          </span>
          <div class="min-w-0">
            <h3 class="font-semibold text-slate-900 dark:text-slate-100">Shaxsiy ma'lumotlar</h3>
            <p class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Telefon raqami login sifatida ishlatiladi va o'zgartirib bo'lmaydi keyin.</p>
          </div>
        </div>

        <div class="grid sm:grid-cols-2 gap-4">
          <div class="sm:col-span-2">
            <label class="block text-[11px] font-bold uppercase tracking-wider text-slate-600 dark:text-slate-400 mb-1.5 inline-flex items-center gap-1.5">
              <Phone class="w-3 h-3" /> Telefon raqam *
            </label>
            <div class="relative">
              <span class="absolute inset-y-0 left-0 flex items-center px-3 rounded-l-xl bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 text-sm font-mono font-semibold border border-r-0 border-slate-200 dark:border-slate-700 pointer-events-none select-none">
                +998
              </span>
              <input :value="form.phone" type="tel" inputmode="tel" autocomplete="tel-national"
                     class="input font-mono !pl-[4.5rem]"
                     :class="errors.phone ? 'border-rose-500' : ''"
                     :placeholder="PLACEHOLDERS.phoneUzLocal"
                     @input="onPhoneInput" @blur="validateField('phone')" />
            </div>
            <p v-if="errors.phone" class="mt-1 text-xs text-rose-600">{{ errors.phone }}</p>
          </div>

          <div>
            <label class="block text-[11px] font-bold uppercase tracking-wider text-slate-600 dark:text-slate-400 mb-1.5 inline-flex items-center gap-1.5">
              <UserIcon class="w-3 h-3" /> F.I.Sh.
            </label>
            <input v-model="form.full_name" class="input" placeholder="Karimov Akmal Aliyevich" />
          </div>

          <div>
            <label class="block text-[11px] font-bold uppercase tracking-wider text-slate-600 dark:text-slate-400 mb-1.5 inline-flex items-center gap-1.5">
              <Mail class="w-3 h-3" /> Email
            </label>
            <input v-model="form.email" type="email" class="input"
                   :class="errors.email ? 'border-rose-500' : ''"
                   :placeholder="PLACEHOLDERS.email" @blur="validateField('email')" />
            <p v-if="errors.email" class="mt-1 text-xs text-rose-600">{{ errors.email }}</p>
          </div>
        </div>
      </section>

      <!-- 3) Security — password (create only) -->
      <section v-if="!isEdit" class="card p-5 sm:p-6">
        <div class="flex items-start gap-3 mb-4">
          <span class="grid place-items-center w-8 h-8 rounded-lg bg-rose-100 text-rose-600 dark:bg-rose-500/20 dark:text-rose-300 shrink-0">
            <Lock class="w-4 h-4" />
          </span>
          <div class="min-w-0">
            <h3 class="font-semibold text-slate-900 dark:text-slate-100">Xavfsizlik</h3>
            <p class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Parol kamida 8 belgi. Foydalanuvchi keyinroq o'zgartira oladi.</p>
          </div>
        </div>
        <label class="block text-[11px] font-bold uppercase tracking-wider text-slate-600 dark:text-slate-400 mb-1.5">
          Parol *
        </label>
        <div class="relative">
          <input v-model="form.password" :type="showPassword ? 'text' : 'password'"
                 minlength="8" class="input pr-10"
                 :class="errors.password ? 'border-rose-500' : ''"
                 placeholder="Kamida 8 belgi" />
          <button type="button" tabindex="-1"
                  class="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 rounded text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                  @click="showPassword = !showPassword">
            <EyeOff v-if="showPassword" class="w-4 h-4" />
            <Eye v-else class="w-4 h-4" />
          </button>
        </div>
        <p v-if="errors.password" class="mt-1 text-xs text-rose-600">{{ errors.password }}</p>
      </section>

      <!-- 4) Status & flags -->
      <section class="card p-5 sm:p-6 space-y-3">
        <div class="flex items-start gap-3">
          <span class="grid place-items-center w-8 h-8 rounded-lg bg-emerald-100 text-emerald-600 dark:bg-emerald-500/20 dark:text-emerald-300 shrink-0">
            <ToggleRight class="w-4 h-4" />
          </span>
          <div class="min-w-0">
            <h3 class="font-semibold text-slate-900 dark:text-slate-100">Holat</h3>
            <p class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Faol bo'lmagan foydalanuvchi tizimga kira olmaydi.</p>
          </div>
        </div>
        <label class="flex items-center gap-3 p-3 rounded-lg ring-1 ring-slate-200/70 dark:ring-slate-700/40 hover:ring-slate-300 dark:hover:ring-slate-600 cursor-pointer transition">
          <input v-model="form.is_active" type="checkbox" class="rounded" />
          <div class="flex-1 min-w-0">
            <div class="text-sm font-medium text-slate-900 dark:text-slate-100">Faol holatda</div>
            <div class="text-xs text-slate-500 dark:text-slate-400">Yoqilgan bo'lsa, foydalanuvchi tizimga kira oladi.</div>
          </div>
        </label>
        <label v-if="auth.isRootSuperadmin"
               class="flex items-center gap-3 p-3 rounded-lg ring-1 ring-indigo-200/60 dark:ring-indigo-700/30 bg-indigo-50/40 dark:bg-indigo-500/10 cursor-pointer">
          <input v-model="form.is_consulting" type="checkbox" class="rounded" />
          <div class="flex-1 min-w-0">
            <div class="text-sm font-medium text-slate-900 dark:text-slate-100 inline-flex items-center gap-2">
              <Briefcase class="w-3.5 h-3.5 text-indigo-500" /> Konsalting xodimi
            </div>
            <div class="text-xs text-slate-500 dark:text-slate-400">Arizalardagi konsalting agentligi maydonini ko'radi va filterlay oladi.</div>
          </div>
        </label>
      </section>

      <!-- 5) Per-user permissions — visible in BOTH create and edit -->
      <section v-if="visiblePermissions.length" class="card p-5 sm:p-6">
        <div class="flex items-start gap-3 mb-4">
          <span class="grid place-items-center w-8 h-8 rounded-lg bg-amber-100 text-amber-600 dark:bg-amber-500/20 dark:text-amber-300 shrink-0">
            <ShieldCheck class="w-4 h-4" />
          </span>
          <div class="min-w-0">
            <h3 class="font-semibold text-slate-900 dark:text-slate-100">Maxsus ruxsatlar</h3>
            <p class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Tanlangan rol bo'yicha standart yoqilgan. Kerak bo'lmaganlarni shu yerda o'chirib qo'ying.
            </p>
          </div>
        </div>
        <div class="grid sm:grid-cols-2 gap-2">
          <label v-for="p in visiblePermissions" :key="p.code"
                 class="flex items-start gap-2.5 p-3 rounded-lg border cursor-pointer transition-colors"
                 :class="isPermissionGranted(p.code)
                   ? 'border-emerald-200/70 dark:border-emerald-700/40 bg-emerald-50/40 dark:bg-emerald-500/5 hover:bg-emerald-50 dark:hover:bg-emerald-500/10'
                   : 'border-rose-200/70 dark:border-rose-700/40 bg-rose-50/40 dark:bg-rose-500/5 hover:bg-rose-50 dark:hover:bg-rose-500/10'">
            <input type="checkbox" class="mt-0.5 rounded"
                   :checked="isPermissionGranted(p.code)"
                   @change="togglePermissionDirect(p.code)" />
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-1.5">
                <span class="font-medium text-sm text-slate-900 dark:text-slate-100">{{ p.label }}</span>
                <span class="font-mono text-[10px] text-slate-400 dark:text-slate-500">{{ p.code }}</span>
              </div>
              <div class="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5 leading-relaxed">{{ p.description }}</div>
            </div>
            <span class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider shrink-0"
                  :class="isPermissionGranted(p.code)
                    ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-300'
                    : 'bg-rose-100 text-rose-700 dark:bg-rose-500/20 dark:text-rose-300'">
              <Check v-if="isPermissionGranted(p.code)" class="w-2.5 h-2.5" />
              <X v-else class="w-2.5 h-2.5" />
              {{ isPermissionGranted(p.code) ? 'Berildi' : "Olib qo'yildi" }}
            </span>
          </label>
        </div>
      </section>

      <!-- Submit -->
      <div class="card p-4 sm:p-5 flex flex-wrap gap-3">
        <button type="submit" class="btn-primary" :disabled="saving">
          <Save class="w-4 h-4" />
          {{ saving ? 'Saqlanmoqda...' : (isEdit ? 'Yangilash' : 'Yaratish') }}
        </button>
        <button type="button" class="btn-ghost" @click="router.push('/admin/users')">
          Bekor qilish
        </button>
      </div>
    </form>

    <!-- Reset password (edit mode only) -->
    <div v-if="isEdit && !loading" class="card p-5 sm:p-6 space-y-4">
      <div class="flex items-center justify-between gap-3">
        <div class="flex items-start gap-3 min-w-0">
          <span class="grid place-items-center w-8 h-8 rounded-lg bg-rose-100 text-rose-600 dark:bg-rose-500/20 dark:text-rose-300 shrink-0">
            <KeyRound class="w-4 h-4" />
          </span>
          <div class="min-w-0">
            <h3 class="font-semibold text-slate-900 dark:text-slate-100">Parolni qayta tiklash</h3>
            <p class="text-sm text-slate-600 dark:text-slate-400 mt-0.5">
              Hozirgi parol bekor qilinadi va yangisi o'rnatiladi.
            </p>
          </div>
        </div>
        <button type="button" class="btn-ghost text-sm shrink-0"
                @click="showResetSection = !showResetSection">
          {{ showResetSection ? 'Yopish' : "Yangi parol" }}
        </button>
      </div>

      <div v-if="showResetSection" class="space-y-3">
        <div class="relative">
          <input v-model="newPassword" :type="showPassword ? 'text' : 'password'"
                 minlength="8" class="input pr-10"
                 placeholder="Yangi parol (kamida 8 belgi)" />
          <button type="button" tabindex="-1"
                  class="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 rounded text-slate-400 hover:text-slate-600"
                  @click="showPassword = !showPassword">
            <EyeOff v-if="showPassword" class="w-4 h-4" />
            <Eye v-else class="w-4 h-4" />
          </button>
        </div>
        <button type="button" class="btn-primary" :disabled="!newPassword" @click="resetPassword">
          Parolni saqlash
        </button>
      </div>
    </div>
  </div>
</template>
