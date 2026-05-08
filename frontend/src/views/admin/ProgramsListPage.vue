<script setup lang="ts">
import { onMounted, ref, watch, computed } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import {
  Plus, GraduationCap, Pencil, Trash2, Power, PowerOff,
  Search, Building2, Layers, BookOpen, LayoutGrid, List as ListIcon,
} from 'lucide-vue-next'
import { AxiosError } from 'axios'
import { adminApi, type ProgramRead, type BranchRead } from '@/api/admin.api'
import EmptyState from '@/components/ui/EmptyState.vue'
import { useToast } from '@/composables/useToast'
import { useConfirm } from '@/composables/useConfirm'
import Skeleton from '@/components/ui/Skeleton.vue'
import PageHeader from '@/components/ui/PageHeader.vue'

const router = useRouter()
const toast = useToast()
const { ask } = useConfirm()

const items = ref<ProgramRead[]>([])
const branches = ref<BranchRead[]>([])
const loading = ref(true)
const filterBranch = ref<string>('')
const onlyActive = ref(false)
const searchQuery = ref('')
const view = ref<'grid' | 'list'>('grid')

const filtered = computed(() => {
  let list = items.value
  if (searchQuery.value.trim()) {
    const q = searchQuery.value.toLowerCase()
    list = list.filter((p) =>
      p.name.toLowerCase().includes(q) ||
      p.code.toLowerCase().includes(q) ||
      (p.branch_name || '').toLowerCase().includes(q),
    )
  }
  return list
})

async function load() {
  loading.value = true
  try {
    items.value = await adminApi.programs.list({
      branch_id: filterBranch.value || undefined,
      active_only: onlyActive.value,
    })
  } catch (e) {
    const ax = e as AxiosError<{ error?: { message?: string } }>
    toast.error(ax.response?.data?.error?.message || "Yuklab bo'lmadi")
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  branches.value = await adminApi.branches.list(false)
  await load()
})

watch([filterBranch, onlyActive], () => load())

async function toggleActive(p: ProgramRead) {
  try {
    await adminApi.programs.update(p.id, { is_active: !p.is_active })
    toast.success(!p.is_active ? "Faollashtirildi" : "Faolsizlantirildi")
    await load()
  } catch (e) {
    const ax = e as AxiosError<{ error?: { message?: string } }>
    toast.error(ax.response?.data?.error?.message || "Xatolik")
  }
}

async function remove(p: ProgramRead) {
  const ok = await ask({
    title: "Yo'nalishni o'chirish",
    message: `"${p.name}" o'chirilsinmi? Arizalar bog'langan bo'lsa, o'chirib bo'lmaydi.`,
    confirmLabel: "O'chirish",
    tone: 'danger',
  })
  if (!ok) return
  try {
    await adminApi.programs.delete(p.id)
    toast.success("O'chirildi")
    await load()
  } catch (e) {
    const ax = e as AxiosError<{ error?: { message?: string } }>
    toast.error(ax.response?.data?.error?.message || "O'chirib bo'lmadi (bog'langan ma'lumotlar bor)")
  }
}

function fmtTuition(v: number | string): string {
  const n = typeof v === 'string' ? parseFloat(v) : v
  if (!n || isNaN(n)) return '—'
  return Number(n).toLocaleString('uz-UZ').replace(/,/g, ' ')
}

// Color map for branch chips — cycle by branch_id hash for visual variety
const BRANCH_COLORS = [
  'from-blue-500 to-blue-600',
  'from-purple-500 to-purple-600',
  'from-pink-500 to-rose-600',
  'from-emerald-500 to-teal-600',
  'from-amber-500 to-orange-600',
]
function branchGradient(branch_id: string): string {
  const hash = branch_id.split('').reduce((a, c) => a + c.charCodeAt(0), 0)
  return BRANCH_COLORS[hash % BRANCH_COLORS.length]
}
</script>

<template>
  <div>
    <PageHeader
      title="Yo'nalishlar"
      :subtitle="`Universitet o'qitadigan yo'nalishlar · ${filtered.length} / ${items.length}`"
      :crumbs="[{ label: 'Bosh sahifa', to: '/admin' }, { label: 'Ta\'lim' }]"
    >
      <RouterLink to="/admin/programs/new" class="btn-primary">
        <Plus class="w-4 h-4" /> Yangi yo'nalish
      </RouterLink>
    </PageHeader>

    <!-- Filter bar -->
    <div class="filter-bar">
      <div class="flex-1 min-w-[260px]">
        <label class="field-label">Qidirish</label>
        <div class="relative">
          <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
          <input v-model="searchQuery" class="input pl-10" placeholder="Yo'nalish nomi, kodi yoki filial..." />
        </div>
      </div>
      <div class="min-w-[180px]">
        <label class="field-label">Filial</label>
        <select v-model="filterBranch" class="input">
          <option value="">Hammasi</option>
          <option v-for="b in branches" :key="b.id" :value="b.id">{{ b.name }}</option>
        </select>
      </div>
      <label class="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300 pb-2">
        <input v-model="onlyActive" type="checkbox" class="rounded" />
        <span>Faqat faol</span>
      </label>
      <div class="flex items-center gap-1 ml-auto pb-1">
        <button class="icon-btn" :class="view === 'grid' ? 'bg-brand-50 text-brand-700 dark:bg-brand-900/30 dark:text-brand-300' : ''"
                title="Karta ko'rinishi" @click="view = 'grid'">
          <LayoutGrid class="w-4 h-4" />
        </button>
        <button class="icon-btn" :class="view === 'list' ? 'bg-brand-50 text-brand-700 dark:bg-brand-900/30 dark:text-brand-300' : ''"
                title="Ro'yxat ko'rinishi" @click="view = 'list'">
          <ListIcon class="w-4 h-4" />
        </button>
      </div>
    </div>

    <!-- Loading -->
    <Skeleton v-if="loading" type="list" />

    <!-- Empty -->
    <div v-else-if="!filtered.length" class="card p-6">
      <EmptyState :icon="GraduationCap" title="Yo'nalishlar topilmadi"
                  :subtitle="searchQuery || filterBranch ? 'Filterlarni o\'zgartirib ko\'ring' : 'Birinchi yo\'nalishni yarating'">
        <RouterLink to="/admin/programs/new" class="btn-primary mt-4 inline-flex">
          <Plus class="w-4 h-4" /> Yangi yo'nalish
        </RouterLink>
      </EmptyState>
    </div>

    <!-- Grid view -->
    <div v-else-if="view === 'grid'" class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <article v-for="p in filtered" :key="p.id"
               class="card-hover overflow-hidden flex flex-col"
               @click="router.push(`/admin/programs/${p.id}/edit`)"
               style="cursor: pointer">
        <!-- Gradient header with code -->
        <div class="relative h-24 bg-gradient-to-br p-4 flex items-end justify-between"
             :class="branchGradient(p.branch_id)">
          <div class="text-white">
            <div class="text-[11px] uppercase tracking-wider opacity-80">{{ p.branch_name }}</div>
            <div class="font-mono text-sm font-semibold">{{ p.code }}</div>
          </div>
          <div class="absolute top-3 right-3">
            <span class="badge"
                  :class="p.is_active
                    ? 'bg-white/20 text-white backdrop-blur'
                    : 'bg-white/10 text-white/60 backdrop-blur'">
              {{ p.is_active ? 'Faol' : 'Faol emas' }}
            </span>
          </div>
        </div>
        <div class="p-5 flex-1 flex flex-col">
          <h3 class="font-semibold text-slate-900 dark:text-slate-100 line-clamp-2 leading-snug min-h-[2.5rem]">
            {{ p.name }}
          </h3>
          <div class="mt-3 flex flex-wrap gap-1.5">
            <span class="pill"><Layers class="w-3 h-3" /> {{ p.education_level_name }}</span>
            <span class="pill"><BookOpen class="w-3 h-3" /> {{ p.education_form_name }}</span>
          </div>
          <div class="mt-4 pt-4 border-t border-slate-100 dark:border-slate-800 flex items-end justify-between gap-2">
            <div>
              <div class="text-[11px] text-slate-500 dark:text-slate-400 uppercase tracking-wider">Yillik to'lov</div>
              <div class="text-lg font-bold text-slate-900 dark:text-slate-100 leading-tight">
                {{ fmtTuition(p.tuition_fee) }} <span class="text-xs font-medium text-slate-500">so'm</span>
              </div>
              <div class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                {{ p.study_duration_years }} yil · {{ p.contract_series }}
              </div>
            </div>
            <div class="flex gap-1" @click.stop>
              <button class="icon-btn"
                      :title="p.is_active ? 'Faolsizlantirish' : 'Yoqish'" @click="toggleActive(p)">
                <Power v-if="!p.is_active" class="w-4 h-4" />
                <PowerOff v-else class="w-4 h-4" />
              </button>
              <RouterLink :to="`/admin/programs/${p.id}/edit`" class="icon-btn" title="Tahrirlash">
                <Pencil class="w-4 h-4" />
              </RouterLink>
              <button class="icon-btn-danger" title="O'chirish" @click="remove(p)">
                <Trash2 class="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </article>
    </div>

    <!-- List view -->
    <div v-else class="card">
      <table class="data-table">
        <thead>
          <tr>
            <th class="w-32">Kod</th>
            <th>Yo'nalish</th>
            <th class="w-44">Filial</th>
            <th class="w-44">Daraja · Shakl</th>
            <th class="w-44">Yillik to'lov</th>
            <th class="w-28">Holati</th>
            <th class="w-32 text-right">Amallar</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="p in filtered" :key="p.id"
              class="cursor-pointer"
              @click="router.push(`/admin/programs/${p.id}/edit`)">
            <td>
              <span class="pill font-mono">{{ p.code }}</span>
            </td>
            <td class="font-medium text-slate-900 dark:text-slate-100">{{ p.name }}</td>
            <td>
              <div class="flex items-center gap-2">
                <span class="w-2 h-2 rounded-full bg-gradient-to-br" :class="branchGradient(p.branch_id)"></span>
                <span class="text-sm text-slate-700 dark:text-slate-300">{{ p.branch_name }}</span>
              </div>
            </td>
            <td class="text-xs text-slate-600 dark:text-slate-400">
              {{ p.education_level_name }} · {{ p.education_form_name }}
            </td>
            <td class="font-mono text-slate-900 dark:text-slate-100 whitespace-nowrap">
              {{ fmtTuition(p.tuition_fee) }} <span class="text-xs text-slate-500">so'm</span>
              <div class="text-[11px] text-slate-500 mt-0.5">{{ p.study_duration_years }} yil</div>
            </td>
            <td>
              <span class="pill" :class="p.is_active ? 'pill-success' : ''">
                <span class="w-1.5 h-1.5 rounded-full" :class="p.is_active ? 'bg-green-500' : 'bg-slate-400'"></span>
                {{ p.is_active ? 'Faol' : 'Faol emas' }}
              </span>
            </td>
            <td class="text-right" @click.stop>
              <div class="inline-flex gap-1">
                <button class="icon-btn"
                        :title="p.is_active ? 'Faolsizlantirish' : 'Yoqish'" @click="toggleActive(p)">
                  <Power v-if="!p.is_active" class="w-4 h-4" />
                  <PowerOff v-else class="w-4 h-4" />
                </button>
                <RouterLink :to="`/admin/programs/${p.id}/edit`" class="icon-btn" title="Tahrirlash">
                  <Pencil class="w-4 h-4" />
                </RouterLink>
                <button class="icon-btn-danger" title="O'chirish" @click="remove(p)">
                  <Trash2 class="w-4 h-4" />
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
