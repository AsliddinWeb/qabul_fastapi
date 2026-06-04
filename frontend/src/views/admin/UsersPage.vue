<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import {
  Plus, Users as UsersIcon, Pencil, Trash2, Power, PowerOff, KeyRound,
  MoreVertical, Download, Search, X as XIcon, Filter as FilterIcon, Phone,
  CheckCircle2, XCircle, Clock,
} from 'lucide-vue-next'
import { AxiosError } from 'axios'
import { adminApi, type UserRead } from '@/api/admin.api'
import { downloadCsv } from '@/api/http'
import EmptyState from '@/components/ui/EmptyState.vue'
import Dropdown from '@/components/ui/Dropdown.vue'
import { ROLE } from '@/utils/labels'
import { useToast } from '@/composables/useToast'
import { useConfirm } from '@/composables/useConfirm'
import { useUrlFilters } from '@/composables/useUrlFilters'
import { useBulkSelect } from '@/composables/useBulkSelect'
import BulkActionBar from '@/components/ui/BulkActionBar.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import { formatPhone } from '@/utils/validators'

const router = useRouter()
const toast = useToast()
const { ask } = useConfirm()

const items = ref<UserRead[]>([])
const total = ref(0)
const loading = ref(false)

const bulk = useBulkSelect<UserRead>(() => items.value)
const bulkBusy = ref(false)

// Filters live in the URL → back/forward restores them.
const { filters, clear: clearAllFilters } = useUrlFilters({
  role: '' as string,
  is_active: '' as string,   // '' | 'true' | 'false'
  search: '' as string,
  page: 1,
  size: 20,
})

const activeFilterCount = computed(() => {
  let n = 0
  if (filters.role) n++
  if (filters.is_active) n++
  return n
})

async function load() {
  loading.value = true
  try {
    const res = await adminApi.users.list({
      role: filters.role || undefined,
      is_active: filters.is_active === 'true' ? true : filters.is_active === 'false' ? false : undefined,
      search: filters.search || undefined,
      page: filters.page,
      size: filters.size,
    })
    items.value = res.items
    bulk.clear()
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
watch(() => [filters.role, filters.is_active], () => { filters.page = 1; load() })
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
  if (pwd.length < 8) { toast.error("Parol kamida 8 belgi bo'lsin"); return }
  try {
    await adminApi.users.resetPassword(u.id, pwd)
    toast.success("Parol tiklandi")
  } catch (e) {
    const ax = e as AxiosError<{ error?: { message?: string } }>
    toast.error(ax.response?.data?.error?.message || "Xatolik")
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
      is_active: filters.is_active === 'true' ? true : filters.is_active === 'false' ? false : undefined,
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

// ---- Visuals ----
const ROLE_TONE: Record<string, string> = {
  superadmin: 'bg-violet-100 text-violet-700 dark:bg-violet-500/20 dark:text-violet-300',
  admin:      'bg-indigo-100 text-indigo-700 dark:bg-indigo-500/20 dark:text-indigo-300',
  operator:   'bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-300',
  director:   'bg-sky-100 text-sky-700 dark:bg-sky-500/20 dark:text-sky-300',
  accountant: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-300',
  applicant:  'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300',
}

const AVATAR_TONES = [
  'from-violet-500 to-indigo-600', 'from-emerald-500 to-teal-600',
  'from-amber-500 to-orange-600', 'from-sky-500 to-blue-600',
  'from-rose-500 to-pink-600', 'from-cyan-500 to-teal-600',
]
function avatarTone(id: string): string {
  let h = 0
  for (let i = 0; i < id.length; i++) h = (h * 31 + id.charCodeAt(i)) | 0
  return AVATAR_TONES[Math.abs(h) % AVATAR_TONES.length]
}
function initials(name?: string | null, phone?: string | null): string {
  if (name) {
    const parts = name.trim().split(/\s+/)
    return (parts[0]?.[0] || '') + (parts[1]?.[0] || '')
  }
  return (phone || '').slice(-2)
}

function fmtLastLogin(iso: string | null | undefined): string {
  if (!iso) return 'Hech qachon kirmagan'
  const d = new Date(iso)
  const diff = Date.now() - d.getTime()
  if (diff < 60_000) return 'Hozir online'
  if (diff < 3600_000) return `${Math.floor(diff / 60_000)} daq oldin`
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)} soat oldin`
  if (diff < 7 * 86_400_000) return `${Math.floor(diff / 86_400_000)} kun oldin`
  return d.toLocaleDateString('uz-UZ', { day: '2-digit', month: 'short', year: 'numeric' })
}

const ROLE_OPTIONS = [
  { value: '',           label: 'Hammasi' },
  { value: 'superadmin', label: 'Bosh administrator' },
  { value: 'admin',      label: 'Administrator' },
  { value: 'operator',   label: 'Operator' },
  { value: 'director',   label: 'Direktor' },
  { value: 'accountant', label: 'Buxgalter' },
  { value: 'applicant',  label: 'Abituriyent' },
]

async function bulkSetActive(active: boolean) {
  const ids = bulk.selectedIds.value
  if (!ids.length) return
  bulkBusy.value = true
  try {
    const res = await adminApi.users.bulkSetActive(ids, active)
    toast.success(
      `${res.updated} ta ${active ? 'faollashtirildi' : 'faolsizlantirildi'}` +
      (res.skipped ? `, ${res.skipped} ta o'tkazib yuborildi` : ''),
    )
    await load()
  } catch (e) {
    const ax = e as AxiosError<{ error?: { message?: string }; detail?: string }>
    toast.error(ax.response?.data?.error?.message || ax.response?.data?.detail || "Xatolik")
  } finally {
    bulkBusy.value = false
  }
}

async function bulkDeleteSelected() {
  const ids = bulk.selectedIds.value
  if (!ids.length) return
  const ok = await ask({
    title: `${ids.length} ta foydalanuvchi o'chirilsinmi?`,
    message: "Foydalanuvchilarning hisobi va ularga tegishli bo'lgan ma'lumotlari cascade tarzda o'chiriladi. Superadmin'ni o'chirib bo'lmaydi.",
    confirmLabel: "O'chirish",
    tone: 'danger',
  })
  if (!ok) return
  bulkBusy.value = true
  try {
    const res = await adminApi.users.bulkDelete(ids)
    toast.success(`${res.deleted} ta o'chirildi${res.skipped ? `, ${res.skipped} ta o'tkazib yuborildi` : ''}`)
    await load()
  } catch (e) {
    const ax = e as AxiosError<{ error?: { message?: string }; detail?: string }>
    toast.error(ax.response?.data?.error?.message || ax.response?.data?.detail || "Xatolik")
  } finally {
    bulkBusy.value = false
  }
}
</script>

<template>
  <div>
    <PageHeader
      title="Foydalanuvchilar"
      :subtitle="`Tizimdagi xodim va abituriyentlar — jami ${total.toLocaleString('uz-UZ')} ta`"
      :crumbs="[{ label: 'Bosh sahifa', to: '/admin' }, { label: 'Sozlamalar' }]"
    >
      <button class="btn-outline" :disabled="exporting" @click="exportCsv">
        <Download class="w-4 h-4" /> {{ exporting ? '...' : 'CSV' }}
      </button>
      <RouterLink to="/admin/users/new" class="btn-primary">
        <Plus class="w-4 h-4" /> Yangi qo'shish
      </RouterLink>
    </PageHeader>

    <!-- Filter bar — URL-persisted -->
    <div class="card p-4 mb-4 flex flex-col gap-3">
      <div class="flex items-center justify-between gap-2">
        <div class="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 inline-flex items-center gap-2">
          <FilterIcon class="w-3.5 h-3.5" /> Filtrlar
          <span v-if="activeFilterCount" class="px-1.5 py-0.5 rounded-full bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300 text-[10px]">
            {{ activeFilterCount }}
          </span>
        </div>
        <button v-if="activeFilterCount || filters.search"
                class="text-xs text-slate-500 hover:text-slate-900 dark:hover:text-slate-100 inline-flex items-center gap-1"
                @click="clearAllFilters">
          <XIcon class="w-3 h-3" /> Tozalash
        </button>
      </div>
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <div class="lg:col-span-2">
          <label class="field-label">Qidirish</label>
          <div class="relative">
            <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
            <input v-model="filters.search" class="input pl-10" placeholder="Telefon yoki F.I.Sh..." />
          </div>
        </div>
        <div>
          <label class="field-label">Rol</label>
          <select v-model="filters.role" class="input">
            <option v-for="o in ROLE_OPTIONS" :key="o.value" :value="o.value">{{ o.label }}</option>
          </select>
        </div>
        <div>
          <label class="field-label">Holati</label>
          <select v-model="filters.is_active" class="input">
            <option value="">Hammasi</option>
            <option value="true">Faqat faollar</option>
            <option value="false">Faqat faolsiz</option>
          </select>
        </div>
      </div>
    </div>

    <!-- Loading / empty -->
    <Skeleton v-if="loading && !items.length" type="table" />
    <div v-else-if="!loading && !items.length" class="card p-6">
      <EmptyState :icon="UsersIcon" title="Foydalanuvchilar topilmadi"
                  subtitle="Filtrlarni tozalang yoki yangi foydalanuvchi qo'shing">
        <RouterLink to="/admin/users/new" class="btn-primary mt-4 inline-flex">
          <Plus class="w-4 h-4" /> Yangi qo'shish
        </RouterLink>
      </EmptyState>
    </div>

    <!-- Table -->
    <div v-else class="card overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="bg-slate-50 dark:bg-slate-900/60 border-b border-slate-200 dark:border-slate-800 text-[11px] uppercase tracking-wider text-slate-500 dark:text-slate-400">
            <tr>
              <th class="w-8 px-4 py-3.5">
                <input type="checkbox" class="rounded cursor-pointer"
                       :checked="bulk.allSelected.value"
                       :indeterminate.prop="bulk.partial.value"
                       @change="bulk.toggleAll()" />
              </th>
              <th class="text-left font-semibold px-5 py-3.5">Foydalanuvchi</th>
              <th class="text-left font-semibold px-4 py-3.5 w-44">Rol</th>
              <th class="text-left font-semibold px-4 py-3.5 w-28">Holati</th>
              <th class="text-left font-semibold px-4 py-3.5 w-44">Oxirgi kirish</th>
              <th class="text-right font-semibold px-5 py-3.5 w-32">Amal</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="u in items" :key="u.id"
                class="border-b border-slate-100 dark:border-slate-800/60 hover:bg-slate-50/70 dark:hover:bg-slate-800/30 transition-colors cursor-pointer"
                :class="bulk.isSelected(u.id) ? 'bg-brand-50/40 dark:bg-brand-500/10' : ''"
                @click="router.push(`/admin/users/${u.id}/edit`)">
              <td class="px-4 py-3.5" @click.stop>
                <input type="checkbox" class="rounded cursor-pointer"
                       :checked="bulk.isSelected(u.id)"
                       @change="bulk.toggle(u.id)" />
              </td>
              <!-- User cell — avatar + name + phone -->
              <td class="px-5 py-3.5">
                <div class="flex items-center gap-3">
                  <div class="grid place-items-center w-10 h-10 rounded-full bg-gradient-to-br text-white text-xs font-bold shrink-0 shadow-sm"
                       :class="avatarTone(u.id)">
                    {{ initials(u.full_name, u.phone) }}
                  </div>
                  <div class="min-w-0">
                    <div class="font-semibold text-slate-900 dark:text-slate-100 truncate">
                      {{ u.full_name || '—' }}
                    </div>
                    <div class="text-[11px] text-slate-500 dark:text-slate-400 inline-flex items-center gap-1 font-mono mt-0.5">
                      <Phone class="w-3 h-3" /> {{ formatPhone(u.phone) }}
                    </div>
                  </div>
                </div>
              </td>

              <!-- Role -->
              <td class="px-4 py-3.5">
                <span class="inline-flex items-center px-2.5 py-1 rounded-full text-[11px] font-semibold"
                      :class="ROLE_TONE[u.role] || ROLE_TONE.applicant">
                  {{ ROLE[u.role] || u.role }}
                </span>
              </td>

              <!-- Status -->
              <td class="px-4 py-3.5">
                <span class="inline-flex items-center gap-1.5 text-xs font-medium"
                      :class="u.is_active ? 'text-emerald-700 dark:text-emerald-300' : 'text-slate-500 dark:text-slate-400'">
                  <CheckCircle2 v-if="u.is_active" class="w-3.5 h-3.5" />
                  <XCircle v-else class="w-3.5 h-3.5" />
                  {{ u.is_active ? 'Faol' : 'Faol emas' }}
                </span>
              </td>

              <!-- Last login -->
              <td class="px-4 py-3.5">
                <span class="inline-flex items-center gap-1.5 text-xs"
                      :class="u.last_login_at ? 'text-slate-600 dark:text-slate-400' : 'text-slate-400 dark:text-slate-500'">
                  <Clock class="w-3 h-3" />
                  {{ fmtLastLogin(u.last_login_at) }}
                </span>
              </td>

              <!-- Actions -->
              <td class="px-5 py-3.5 text-right" @click.stop>
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
      </div>

      <!-- Pagination -->
      <div class="flex items-center justify-between p-4 border-t border-slate-100 dark:border-slate-800">
        <div class="text-xs text-slate-500 dark:text-slate-400">
          Sahifa <strong class="text-slate-700 dark:text-slate-300 tabular-nums">{{ filters.page }}</strong> / {{ lastPage() }}
          <span class="ml-2 text-slate-400 dark:text-slate-500">· Jami {{ total }} ta</span>
        </div>
        <div class="flex gap-2">
          <button class="btn-outline btn-sm" :disabled="filters.page <= 1" @click="filters.page--">‹ Oldingi</button>
          <button class="btn-outline btn-sm" :disabled="filters.page >= lastPage()" @click="filters.page++">Keyingi ›</button>
        </div>
      </div>
    </div>

    <BulkActionBar :count="bulk.count.value"
                   :label="`${bulk.count.value} ta foydalanuvchi tanlandi`"
                   @clear="bulk.clear()">
      <button type="button"
              class="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-semibold bg-emerald-500 hover:bg-emerald-600 text-white transition disabled:opacity-50"
              :disabled="bulkBusy"
              @click="bulkSetActive(true)">
        Faollashtirish
      </button>
      <button type="button"
              class="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-semibold bg-amber-500 hover:bg-amber-600 text-white transition disabled:opacity-50"
              :disabled="bulkBusy"
              @click="bulkSetActive(false)">
        Faolsizlantirish
      </button>
      <button type="button"
              class="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-semibold bg-rose-600 hover:bg-rose-700 text-white transition disabled:opacity-50"
              :disabled="bulkBusy"
              @click="bulkDeleteSelected">
        O'chirish
      </button>
    </BulkActionBar>
  </div>
</template>
