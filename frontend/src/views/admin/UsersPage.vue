<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { Plus, Users as UsersIcon, Pencil, Trash2, Power, PowerOff, KeyRound, MoreVertical, Eye, Download } from 'lucide-vue-next'
import { AxiosError } from 'axios'
import { adminApi, type UserRead } from '@/api/admin.api'
import { downloadCsv } from '@/api/http'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import Dropdown from '@/components/ui/Dropdown.vue'
import { ROLE } from '@/utils/labels'
import { useToast } from '@/composables/useToast'
import { useConfirm } from '@/composables/useConfirm'
import type { Role } from '@/types'
import Skeleton from '@/components/ui/Skeleton.vue'
import PageHeader from '@/components/ui/PageHeader.vue'

const router = useRouter()
const toast = useToast()
const { ask } = useConfirm()

const items = ref<UserRead[]>([])
const total = ref(0)
const loading = ref(false)

const filters = reactive<{ role: Role | ''; search: string; page: number; size: number }>({
  role: '',
  search: '',
  page: 1,
  size: 20,
})

async function load() {
  loading.value = true
  try {
    const res = await adminApi.users.list({
      role: filters.role || undefined,
      search: filters.search || undefined,
      page: filters.page,
      size: filters.size,
    })
    items.value = res.items
    total.value = res.total
  } catch (e) {
    const ax = e as AxiosError<{ error?: { message?: string } }>
    toast.error(ax.response?.data?.error?.message || "Yuklab bo'lmadi")
  } finally {
    loading.value = false
  }
}

let searchTimer: ReturnType<typeof setTimeout> | null = null
watch(() => filters.search, () => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => { filters.page = 1; load() }, 300)
})
watch(() => filters.role, () => { filters.page = 1; load() })
watch(() => filters.page, load)
onMounted(load)

async function toggleActive(u: UserRead) {
  try {
    await adminApi.users.update(u.id, { is_active: !u.is_active })
    toast.success(!u.is_active ? "Faollashtirildi" : "Faolsizlantirildi")
    await load()
  } catch (e) {
    const ax = e as AxiosError<{ error?: { message?: string } }>
    toast.error(ax.response?.data?.error?.message || "Xatolik")
  }
}

async function resetPassword(u: UserRead) {
  const pwd = window.prompt(`${u.full_name || u.phone} uchun yangi parol (kamida 8 belgi):`)
  if (!pwd) return
  if (pwd.length < 8) { toast.error('Parol kamida 8 belgi bo\'lsin'); return }
  try {
    await adminApi.users.resetPassword(u.id, pwd)
    toast.success('Parol tiklandi')
  } catch (e) {
    const ax = e as AxiosError<{ error?: { message?: string } }>
    toast.error(ax.response?.data?.error?.message || 'Xatolik')
  }
}

async function deleteUser(u: UserRead) {
  const ok = await ask({
    title: "Foydalanuvchini o'chirish",
    message: `${u.full_name || u.phone} o'chirilsinmi? Bu amalni qaytarib bo'lmaydi.`,
    confirmLabel: "O'chirish",
    tone: 'danger',
  })
  if (!ok) return
  try {
    await adminApi.users.delete(u.id)
    toast.success("O'chirildi")
    await load()
  } catch (e) {
    const ax = e as AxiosError<{ error?: { message?: string } }>
    toast.error(ax.response?.data?.error?.message || "O'chirib bo'lmadi")
  }
}

const lastPage = () => Math.max(1, Math.ceil(total.value / filters.size))

const exporting = ref(false)
async function exportCsv() {
  exporting.value = true
  try {
    await downloadCsv('/users/export.csv', {
      role: filters.role || undefined,
      search: filters.search || undefined,
    })
    toast.success("CSV yuklab olindi")
  } catch (e) {
    const ax = e as AxiosError<{ detail?: string }>
    toast.error(ax.response?.data?.detail || "Eksport qilib bo'lmadi")
  } finally {
    exporting.value = false
  }
}
</script>

<template>
  <div>
    <PageHeader
      title="Foydalanuvchilar"
      :subtitle="`Tizimdagi xodim va abituriyentlar · Jami ${total}`"
      :crumbs="[{ label: 'Bosh sahifa', to: '/admin' }, { label: 'Sozlamalar' }]"
    >
      <button class="btn-outline" :disabled="exporting" @click="exportCsv">
        <Download class="w-4 h-4" /> {{ exporting ? '...' : 'CSV' }}
      </button>
      <RouterLink to="/admin/users/new" class="btn-primary">
        <Plus class="w-4 h-4" /> Yangi qo'shish
      </RouterLink>
    </PageHeader>

    <div class="filter-bar">
      <div class="flex-1 min-w-[260px]">
        <label class="field-label">Qidirish</label>
        <input v-model="filters.search" class="input" placeholder="Telefon yoki F.I.Sh..." />
      </div>
      <div class="min-w-[200px]">
        <label class="field-label">Rol</label>
        <select v-model="filters.role" class="input">
          <option value="">Hammasi</option>
          <option value="superadmin">Bosh administrator</option>
          <option value="admin">Administrator</option>
          <option value="operator">Operator</option>
          <option value="director">Direktor</option>
          <option value="accountant">Buxgalter</option>
          <option value="applicant">Abituriyent</option>
        </select>
      </div>
    </div>

    <div class="card">
      <table class="data-table">
        <thead>
          <tr>
            <th>F.I.Sh. / Telefon</th>
            <th>Rol</th>
            <th>Holati</th>
            <th class="w-32 text-right">Amallar</th>
          </tr>
        </thead>
        <tbody>
          <template v-if="loading">
            <tr v-for="i in 6" :key="`sk-row-${i}`" class="border-b border-slate-100 dark:border-slate-800/60">
              <td v-for="c in 4" :key="`sk-${i}-${c}`" class="px-5 py-4">
                <div class="skeleton h-3 rounded" :class="c === 1 ? 'w-3/4' : 'w-1/2'" />
              </td>
            </tr>
          </template>
          <tr v-else-if="!items.length">
            <td colspan="4" class="p-0">
              <EmptyState :icon="UsersIcon" title="Foydalanuvchilar topilmadi" />
            </td>
          </tr>
          <tr v-for="u in items" :key="u.id"
              class="cursor-pointer"
              @click="router.push(`/admin/users/${u.id}/edit`)">
            <td>
              <div class="font-medium text-slate-900 dark:text-slate-100">{{ u.full_name || '—' }}</div>
              <div class="text-xs text-slate-500 dark:text-slate-400">{{ u.phone }}</div>
            </td>
            <td><StatusBadge :status="u.role" :label="ROLE[u.role] || u.role" /></td>
            <td>
              <span class="badge"
                    :class="u.is_active
                      ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300'
                      : 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400'">
                {{ u.is_active ? 'Faol' : 'Faol emas' }}
              </span>
            </td>
            <td class="text-right" @click.stop>
              <div class="inline-flex items-center gap-1.5">
                <RouterLink :to="`/admin/users/${u.id}/edit`" class="btn-outline btn-sm">
                  <Pencil class="w-3.5 h-3.5" /> Tahrirlash
                </RouterLink>
                <Dropdown align="right">
                  <template #trigger>
                    <button class="icon-btn" title="Ko'proq amallar">
                      <MoreVertical class="w-4 h-4" />
                    </button>
                  </template>
                  <button class="menu-item" @click="toggleActive(u)">
                    <Power v-if="!u.is_active" class="w-4 h-4 text-emerald-500" />
                    <PowerOff v-else class="w-4 h-4 text-amber-500" />
                    {{ u.is_active ? 'Faolsizlantirish' : 'Faollashtirish' }}
                  </button>
                  <button class="menu-item" @click="resetPassword(u)">
                    <KeyRound class="w-4 h-4 text-indigo-500" /> Parolni tiklash
                  </button>
                  <div class="menu-divider"></div>
                  <button class="menu-item !text-rose-600 dark:!text-rose-400 hover:!bg-rose-50 dark:hover:!bg-rose-900/30"
                          @click="deleteUser(u)">
                    <Trash2 class="w-4 h-4" /> O'chirish
                  </button>
                </Dropdown>
              </div>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-if="items.length" class="flex items-center justify-between p-4 border-t border-slate-100 dark:border-slate-800">
        <div class="text-xs text-slate-500 dark:text-slate-400">
          Sahifa <strong class="text-slate-700 dark:text-slate-300">{{ filters.page }}</strong> / {{ lastPage() }}
        </div>
        <div class="flex gap-2">
          <button class="btn-outline btn-sm" :disabled="filters.page <= 1" @click="filters.page--">‹ Oldingi</button>
          <button class="btn-outline btn-sm" :disabled="filters.page >= lastPage()" @click="filters.page++">Keyingi ›</button>
        </div>
      </div>
    </div>
  </div>
</template>
