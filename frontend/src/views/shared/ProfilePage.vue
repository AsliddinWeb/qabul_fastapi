<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { Eye, EyeOff } from 'lucide-vue-next'
import { AxiosError } from 'axios'
import { authApi } from '@/api/auth.api'
import { useAuthStore } from '@/stores/auth'
import { http } from '@/api/http'
import { password as vPassword } from '@/utils/validators'
import Skeleton from '@/components/ui/Skeleton.vue'

const auth = useAuthStore()

const me = ref<{
  id: string
  phone: string
  email: string | null
  full_name: string | null
  role: string
  is_active: boolean
  is_phone_verified: boolean
  last_login_at: string | null
  created_at: string
}>()
const loading = ref(true)

const form = reactive({
  full_name: '',
  email: '',
})
const saving = ref(false)
const message = ref<{ type: 'ok' | 'err'; text: string } | null>(null)

async function load() {
  loading.value = true
  try {
    me.value = await authApi.me() as any
    form.full_name = me.value?.full_name || ''
    form.email     = me.value?.email     || ''
  } finally {
    loading.value = false
  }
}

async function save() {
  if (!me.value) return
  saving.value = true
  message.value = null
  try {
    // Note: PATCH /users/{id} requires users.update permission. SuperAdmin/Admin
    // can edit anyone; other roles editing themselves currently goes through
    // the same endpoint. (Phase 13: dedicated /users/me PATCH for self-edit.)
    await http.patch(`/users/${me.value.id}`, {
      full_name: form.full_name || null,
      email: form.email || null,
    })
    message.value = { type: 'ok', text: "Ma'lumotlar saqlandi" }
    // Update local state in place instead of re-fetching the whole profile.
    me.value = { ...me.value, full_name: form.full_name || null, email: form.email || null }
    if (auth.user) {
      auth.user.full_name = form.full_name
      localStorage.setItem('user', JSON.stringify(auth.user))
    }
  } catch (e) {
    const ax = e as AxiosError<{ error?: { message?: string } }>
    message.value = {
      type: 'err',
      text: ax.response?.data?.error?.message || "Saqlab bo'lmadi",
    }
  } finally {
    saving.value = false
  }
}

onMounted(load)

// ---- Password change (self-service) ----
const pw = reactive({ current: '', next: '', confirm: '' })
const pwShow = reactive({ current: false, next: false, confirm: false })
const pwSaving = ref(false)
const pwMessage = ref<{ type: 'ok' | 'err'; text: string } | null>(null)

async function changePassword() {
  pwMessage.value = null
  if (!pw.current) {
    pwMessage.value = { type: 'err', text: "Joriy parolni kiriting" }
    return
  }
  if (vPassword(pw.next)) {
    pwMessage.value = { type: 'err', text: "Yangi parol kamida 8 belgi bo'lishi kerak" }
    return
  }
  if (pw.next !== pw.confirm) {
    pwMessage.value = { type: 'err', text: "Yangi parollar mos kelmadi" }
    return
  }
  pwSaving.value = true
  try {
    await authApi.changePassword(pw.current, pw.next)
    pwMessage.value = { type: 'ok', text: "Parol yangilandi" }
    pw.current = pw.next = pw.confirm = ''
  } catch (e) {
    const ax = e as AxiosError<{ error?: { message?: string } }>
    pwMessage.value = { type: 'err', text: ax.response?.data?.error?.message || "Parolni yangilab bo'lmadi" }
  } finally {
    pwSaving.value = false
  }
}

const roleLabel = computed(() => {
  const map: Record<string, string> = {
    superadmin: 'Bosh administrator',
    admin:      'Administrator',
    operator:   'Operator',
    director:   'Direktor',
    accountant: 'Buxgalter',
    applicant:  'Abituriyent',
  }
  return map[me.value?.role || ''] || me.value?.role || ''
})

const initials = computed(() => {
  const name = me.value?.full_name?.trim()
  if (name) return name.split(/\s+/).slice(0, 2).map(w => w[0]).join('').toUpperCase()
  return (me.value?.phone || '?').slice(-2)
})
</script>

<template>
  <div class="max-w-5xl mx-auto space-y-6">
    <div>
      <h1 class="text-2xl font-bold text-slate-900 dark:text-slate-100">Mening profilim</h1>
      <p class="mt-1 text-sm text-slate-600 dark:text-slate-400">
        Shaxsiy ma'lumotlar va tizim ma'lumotlari.
      </p>
    </div>

    <Skeleton v-if="loading" type="detail" />

    <template v-else-if="me">
      <!-- Identity card -->
      <section class="card p-6 flex items-center gap-4">
        <div class="w-16 h-16 rounded-full bg-brand-600 text-white grid place-items-center font-bold text-xl">
          {{ initials }}
        </div>
        <div class="min-w-0">
          <div class="text-lg font-semibold text-slate-900 dark:text-slate-100 truncate">
            {{ me.full_name || me.phone }}
          </div>
          <div class="text-sm text-slate-500 dark:text-slate-400">{{ me.phone }}</div>
          <div class="mt-1 inline-flex items-center text-xs px-2 py-0.5 rounded-full bg-brand-50 text-brand-700 dark:bg-brand-900/40 dark:text-brand-200">
            {{ roleLabel }}
          </div>
        </div>
      </section>

      <!-- Editable info -->
      <section class="card p-6 space-y-4">
        <h2 class="font-semibold text-slate-900 dark:text-slate-100">Ma'lumotlarni tahrirlash</h2>

        <div v-if="message" class="text-sm rounded-lg p-3"
             :class="message.type === 'ok'
               ? 'bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-300'
               : 'bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-300'">
          {{ message.text }}
        </div>

        <div class="grid sm:grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">F.I.O.</label>
            <input v-model="form.full_name" class="input" placeholder="Familiya Ism Otasining ismi" />
          </div>
          <div>
            <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Email</label>
            <input v-model="form.email" type="email" class="input" />
          </div>
        </div>

        <button class="btn-primary" :disabled="saving" @click="save">
          {{ saving ? 'Saqlanmoqda...' : 'Saqlash' }}
        </button>
      </section>

      <!-- Password change -->
      <section class="card p-6 space-y-4">
        <div>
          <h2 class="font-semibold text-slate-900 dark:text-slate-100">Parolni o'zgartirish</h2>
          <p class="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Xavfsizlik uchun avval joriy parolingizni kiriting.
          </p>
        </div>

        <div v-if="pwMessage" class="text-sm rounded-lg p-3"
             :class="pwMessage.type === 'ok'
               ? 'bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-300'
               : 'bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-300'">
          {{ pwMessage.text }}
        </div>

        <form class="space-y-4" @submit.prevent="changePassword">
          <div>
            <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Joriy parol</label>
            <div class="relative">
              <input v-model="pw.current" :type="pwShow.current ? 'text' : 'password'"
                     autocomplete="current-password" class="input pr-10" placeholder="••••••••" />
              <button type="button" tabindex="-1"
                      class="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                      :title="pwShow.current ? 'Yashirish' : 'Ko\'rsatish'"
                      @click="pwShow.current = !pwShow.current">
                <EyeOff v-if="pwShow.current" class="w-4 h-4" />
                <Eye v-else class="w-4 h-4" />
              </button>
            </div>
          </div>
          <div class="grid sm:grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Yangi parol</label>
              <div class="relative">
                <input v-model="pw.next" :type="pwShow.next ? 'text' : 'password'"
                       autocomplete="new-password" class="input pr-10" placeholder="Kamida 8 belgi" />
                <button type="button" tabindex="-1"
                        class="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                        :title="pwShow.next ? 'Yashirish' : 'Ko\'rsatish'"
                        @click="pwShow.next = !pwShow.next">
                  <EyeOff v-if="pwShow.next" class="w-4 h-4" />
                  <Eye v-else class="w-4 h-4" />
                </button>
              </div>
            </div>
            <div>
              <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Yangi parolni takrorlang</label>
              <div class="relative">
                <input v-model="pw.confirm" :type="pwShow.confirm ? 'text' : 'password'"
                       autocomplete="new-password" class="input pr-10" placeholder="••••••••" />
                <button type="button" tabindex="-1"
                        class="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                        :title="pwShow.confirm ? 'Yashirish' : 'Ko\'rsatish'"
                        @click="pwShow.confirm = !pwShow.confirm">
                  <EyeOff v-if="pwShow.confirm" class="w-4 h-4" />
                  <Eye v-else class="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
          <button type="submit" class="btn-primary" :disabled="pwSaving">
            {{ pwSaving ? 'Yangilanmoqda...' : 'Parolni yangilash' }}
          </button>
        </form>
      </section>

      <!-- Account info -->
      <section class="card p-6 space-y-3">
        <h2 class="font-semibold text-slate-900 dark:text-slate-100">Hisob ma'lumotlari</h2>
        <dl class="grid sm:grid-cols-2 gap-3 text-sm">
          <div>
            <dt class="text-slate-500 dark:text-slate-400">Telefon</dt>
            <dd class="text-slate-900 dark:text-slate-100">{{ me.phone }}</dd>
          </div>
          <div>
            <dt class="text-slate-500 dark:text-slate-400">Telefon tasdiqlangan</dt>
            <dd>
              <span class="badge"
                :class="me.is_phone_verified
                  ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300'
                  : 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300'">
                {{ me.is_phone_verified ? 'Ha' : "Yo'q" }}
              </span>
            </dd>
          </div>
          <div>
            <dt class="text-slate-500 dark:text-slate-400">Holati</dt>
            <dd>
              <span class="badge"
                :class="me.is_active
                  ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300'
                  : 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-400'">
                {{ me.is_active ? 'Faol' : 'Faol emas' }}
              </span>
            </dd>
          </div>
          <div>
            <dt class="text-slate-500 dark:text-slate-400">Oxirgi kirish</dt>
            <dd class="text-slate-900 dark:text-slate-100">
              {{ me.last_login_at ? new Date(me.last_login_at).toLocaleString('uz-UZ') : '—' }}
            </dd>
          </div>
        </dl>
      </section>
    </template>
  </div>
</template>
