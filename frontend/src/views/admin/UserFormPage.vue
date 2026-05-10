<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, Save, Eye, EyeOff, KeyRound, ShieldCheck } from 'lucide-vue-next'
import { AxiosError } from 'axios'
import { adminApi, type UserCreatePayload } from '@/api/admin.api'
import type { Role } from '@/types'
import { useAuthStore } from '@/stores/auth'
import { useToast } from '@/composables/useToast'
import { useConfirm } from '@/composables/useConfirm'
import { PLACEHOLDERS, formatPhone, compactPhone, phoneUz as vPhone, email as vEmail, password as vPassword } from '@/utils/validators'
import Skeleton from '@/components/ui/Skeleton.vue'
import PageHeader from '@/components/ui/PageHeader.vue'

const route = useRoute()
const router = useRouter()
const toast = useToast()
const auth = useAuthStore()
const { ask } = useConfirm()

const id = computed(() => route.params.id as string | undefined)
const isEdit = computed(() => !!id.value)

const form = reactive<UserCreatePayload>({
  phone: '+998',
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

// Per-user permission revocation list (codes the role normally grants but the
// admin has switched off). Empty array = use role defaults.
const permissionsRevoked = ref<string[]>([])

// Whitelist of permissions the admin can toggle per user. Each item lists which
// roles have it by default — only those roles see the toggle in the UI.
interface TogglablePerm {
  code: string
  label: string
  description: string
  roles: Role[]
}
const TOGGLABLE_PERMISSIONS: TogglablePerm[] = [
  {
    code: 'contracts.sign',
    label: 'Shartnomalarni imzolash',
    description: 'Yaratilgan shartnomani "imzolangan" deb belgilash huquqi.',
    roles: ['superadmin', 'admin', 'operator'],
  },
  {
    code: 'contracts.create',
    label: 'Shartnoma yaratish',
    description: 'Ariza ostida yangi shartnoma yaratish huquqi.',
    roles: ['superadmin', 'admin', 'operator'],
  },
  {
    code: 'leads.convert',
    label: "Lead'ni arizaga o'tkazish",
    description: "Lead'dan ariza yaratish (konversiya).",
    roles: ['superadmin', 'admin', 'operator'],
  },
  {
    code: 'leads.delete',
    label: "Lead'larni o'chirish",
    description: "Lead'larni butunlay o'chirib tashlash.",
    roles: ['superadmin', 'admin'],
  },
  {
    code: 'payments.confirm',
    label: "To'lovlarni tasdiqlash",
    description: "Kutilayotgan to'lovlarni tasdiqlash.",
    roles: ['superadmin', 'admin', 'accountant'],
  },
  {
    code: 'payments.refund',
    label: "To'lovlarni qaytarish",
    description: "Tasdiqlangan to'lovni refund qilish.",
    roles: ['superadmin', 'admin', 'accountant'],
  },
  {
    code: 'applications.review',
    label: "Arizani ko'rib chiqish",
    description: "Arizani qabul/rad etish huquqi.",
    roles: ['superadmin', 'admin', 'operator'],
  },
]
const visiblePermissions = computed(() =>
  TOGGLABLE_PERMISSIONS.filter(p => p.roles.includes(form.role)),
)
function isPermissionGranted(code: string): boolean {
  return !permissionsRevoked.value.includes(code)
}
async function togglePermission(p: TogglablePerm) {
  const granted = isPermissionGranted(p.code)
  if (granted) {
    // Switching OFF — confirm with a clear consequence message.
    const ok = await ask({
      title: `${p.label}ni olib qo'yish?`,
      message: `${p.description}\n\nAgar olib qo'ysangiz, foydalanuvchi bu amalni bajara olmaydi va "Missing permission: ${p.code}" xatosini ko'radi.`,
      confirmLabel: "Olib qo'yish",
      tone: 'danger',
    })
    if (!ok) return
    permissionsRevoked.value = [...permissionsRevoked.value, p.code]
    toast.success(`Olib qo'yildi: ${p.label}. "Saqlash" tugmasini bosing.`)
  } else {
    // Switching ON — restore.
    permissionsRevoked.value = permissionsRevoked.value.filter(c => c !== p.code)
    toast.success(`Berildi: ${p.label}. "Saqlash" tugmasini bosing.`)
  }
}

onMounted(async () => {
  if (!isEdit.value) return
  loading.value = true
  try {
    const u = await adminApi.users.get(id.value as string)
    Object.assign(form, {
      phone: formatPhone(u.phone || ''),
      full_name: u.full_name || '',
      email: u.email || '',
      role: u.role,
      is_active: u.is_active,
      is_consulting: !!u.is_consulting,
      password: '', // never show
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
    case 'phone':    err = vPhone(form.phone); break
    case 'role':     err = form.role ? null : "Rolni tanlang"; break
    case 'password': err = !isEdit.value ? vPassword(form.password || '') : null; break
    case 'email':    err = vEmail(form.email || ''); break
  }
  if (err) ne[field] = err
  errors.value = ne
}

function onPhoneInput(e: Event) {
  form.phone = formatPhone((e.target as HTMLInputElement).value)
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
    // Strip phone formatting before sending — backend wants compact "+998..." form.
    // Empty email -> null (EmailStr can't parse "").
    const sendable = {
      ...form,
      phone: compactPhone(form.phone),
      email: form.email?.trim() ? form.email.trim() : null,
    }
    if (isEdit.value && id.value) {
      // Don't send password on update — use reset password flow instead.
      const { password, ...payload } = sendable
      await adminApi.users.update(id.value, {
        ...payload,
        permissions_revoked: permissionsRevoked.value,
      } as any)
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
      :subtitle="!isEdit ? `Tizim xodimi uchun hisob yarating. Abituriyentlar OTP orqali avtomatik ro'yxatdan o'tadi.` : ''"
      :crumbs="[{ label: 'Bosh sahifa', to: '/admin' }, { label: 'Foydalanuvchilar', to: '/admin/users' }]"
    >
      <button type="button" class="btn-ghost" @click="router.back()">
        <ArrowLeft class="w-4 h-4" /> Ortga
      </button>
    </PageHeader>

    <Skeleton v-if="loading" type="form" />

    <form v-else class="card p-6 space-y-5" @submit.prevent="submit">
      <div class="grid sm:grid-cols-2 gap-4">
        <div class="sm:col-span-2">
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Telefon raqam *</label>
          <input :value="form.phone" type="tel" inputmode="tel"
                 class="input font-mono"
                 :class="errors.phone ? 'border-red-500' : ''"
                 :placeholder="PLACEHOLDERS.phoneUz"
                 @input="onPhoneInput" @blur="validateField('phone')" />
          <p v-if="errors.phone" class="mt-1 text-xs text-red-600">{{ errors.phone }}</p>
        </div>
        <div>
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">F.I.Sh.</label>
          <input v-model="form.full_name" class="input" placeholder="Karimov Akmal Aliyevich" />
        </div>
        <div>
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Email</label>
          <input v-model="form.email" type="email" class="input"
                 :class="errors.email ? 'border-red-500' : ''"
                 :placeholder="PLACEHOLDERS.email" @blur="validateField('email')" />
          <p v-if="errors.email" class="mt-1 text-xs text-red-600">{{ errors.email }}</p>
        </div>
        <div>
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Rol *</label>
          <select v-model="form.role" class="input" :class="errors.role ? 'border-red-500' : ''">
            <option value="superadmin">Bosh administrator</option>
            <option value="admin">Administrator</option>
            <option value="operator">Operator</option>
            <option value="director">Direktor</option>
            <option value="accountant">Buxgalter</option>
          </select>
          <p v-if="errors.role" class="mt-1 text-xs text-red-600">{{ errors.role }}</p>
        </div>
        <div v-if="!isEdit">
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Parol *</label>
          <div class="relative">
            <input
              v-model="form.password"
              :type="showPassword ? 'text' : 'password'"
              minlength="8"
              class="input pr-10"
              :class="errors.password ? 'border-red-500' : ''"
              placeholder="Kamida 8 belgi"
            />
            <button type="button" tabindex="-1"
                    class="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 rounded text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                    @click="showPassword = !showPassword">
              <EyeOff v-if="showPassword" class="w-4 h-4" />
              <Eye v-else class="w-4 h-4" />
            </button>
          </div>
          <p v-if="errors.password" class="mt-1 text-xs text-red-600">{{ errors.password }}</p>
        </div>
        <label class="sm:col-span-2 flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
          <input v-model="form.is_active" type="checkbox" class="rounded" />
          <span>Faol holatda</span>
        </label>

        <label v-if="auth.isRootSuperadmin"
               class="sm:col-span-2 flex items-start gap-2.5 text-sm text-slate-700 dark:text-slate-300 p-3 rounded-lg bg-indigo-50/40 dark:bg-indigo-500/10 border border-indigo-200/60 dark:border-indigo-700/30">
          <input v-model="form.is_consulting" type="checkbox" class="mt-0.5 rounded" />
          <div>
            <div class="font-medium">Konsalting</div>
            <div class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Faqat shu belgili foydalanuvchilar arizalarda konsalting agentligi maydonini ko'radi va undan filterlanish imkoniyatiga ega bo'ladi.
            </div>
          </div>
        </label>
      </div>

      <!-- Per-user permissions (edit-mode only) -->
      <div v-if="isEdit && visiblePermissions.length"
           class="pt-4 border-t border-slate-200 dark:border-slate-800 space-y-3">
        <div class="flex items-start gap-2">
          <span class="grid place-items-center w-7 h-7 rounded-lg bg-emerald-50 text-emerald-600 dark:bg-emerald-500/20 dark:text-emerald-300 shrink-0 mt-0.5">
            <ShieldCheck class="w-3.5 h-3.5" />
          </span>
          <div>
            <h3 class="font-semibold text-slate-900 dark:text-slate-100">Maxsus ruxsatlar</h3>
            <p class="text-xs text-slate-500 dark:text-slate-400 mt-0.5 leading-relaxed">
              Default holatda barcha ruxsatlar yoqilgan. Kerak bo'lsa shaxsan olib qo'yishingiz mumkin.
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
                   @click.prevent="togglePermission(p)" />
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-1.5">
                <span class="font-medium text-sm text-slate-900 dark:text-slate-100">{{ p.label }}</span>
                <span class="font-mono text-[10px] text-slate-400 dark:text-slate-500">{{ p.code }}</span>
              </div>
              <div class="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5 leading-relaxed">{{ p.description }}</div>
            </div>
          </label>
        </div>
      </div>

      <div class="flex gap-3 pt-2 border-t border-slate-200 dark:border-slate-800">
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
    <div v-if="isEdit && !loading" class="card p-6 space-y-4">
      <div class="flex items-center justify-between">
        <div>
          <h3 class="font-semibold text-slate-900 dark:text-slate-100 inline-flex items-center gap-2">
            <KeyRound class="w-4 h-4" /> Parolni qayta tiklash
          </h3>
          <p class="text-sm text-slate-600 dark:text-slate-400 mt-1">
            Hozirgi parol bekor qilinadi va yangisi o'rnatiladi.
          </p>
        </div>
        <button type="button" class="btn-ghost text-sm"
                @click="showResetSection = !showResetSection">
          {{ showResetSection ? 'Yopish' : "Yangi parol o'rnatish" }}
        </button>
      </div>

      <div v-if="showResetSection" class="space-y-3">
        <div class="relative">
          <input
            v-model="newPassword"
            :type="showPassword ? 'text' : 'password'"
            minlength="8"
            class="input pr-10"
            placeholder="Yangi parol (kamida 8 belgi)"
          />
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
