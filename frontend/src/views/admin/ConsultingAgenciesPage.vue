<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  Plus, Pencil, Trash2, Loader2, Building2, AlertCircle, ToggleLeft, ToggleRight,
} from 'lucide-vue-next'
import { AxiosError } from 'axios'
import { consultingApi, type ConsultingAgency } from '@/api/consulting.api'
import { useAuthStore } from '@/stores/auth'
import { useToast } from '@/composables/useToast'
import { useConfirm } from '@/composables/useConfirm'
import PageHeader from '@/components/ui/PageHeader.vue'
import Skeleton from '@/components/ui/Skeleton.vue'

const auth = useAuthStore()
const router = useRouter()
const toast = useToast()
const { ask } = useConfirm()

const items = ref<ConsultingAgency[]>([])
const loading = ref(true)
const saving = ref(false)
const editingId = ref<string | null>(null)

const form = ref({ name: '', notes: '', is_active: true })

const isRoot = computed(() => auth.isRootSuperadmin)

onMounted(async () => {
  if (!isRoot.value) {
    router.replace('/admin')
    return
  }
  await load()
})

async function load() {
  loading.value = true
  try {
    items.value = await consultingApi.list(false)
  } catch (e) {
    handleErr(e, "Yuklab bo'lmadi")
  } finally {
    loading.value = false
  }
}

function startNew() {
  editingId.value = null
  form.value = { name: '', notes: '', is_active: true }
}

function startEdit(a: ConsultingAgency) {
  editingId.value = a.id
  form.value = { name: a.name, notes: a.notes || '', is_active: a.is_active }
}

async function save() {
  const name = form.value.name.trim()
  if (!name) {
    toast.error('Nom bo\'sh bo\'lishi mumkin emas')
    return
  }
  saving.value = true
  try {
    if (editingId.value) {
      await consultingApi.update(editingId.value, {
        name,
        notes: form.value.notes.trim() || null,
        is_active: form.value.is_active,
      })
      toast.success('Saqlandi')
    } else {
      await consultingApi.create({
        name,
        notes: form.value.notes.trim() || null,
        is_active: form.value.is_active,
      })
      toast.success('Qo\'shildi')
    }
    startNew()
    await load()
  } catch (e) {
    handleErr(e, "Saqlab bo'lmadi")
  } finally {
    saving.value = false
  }
}

async function remove(a: ConsultingAgency) {
  const ok = await ask({
    title: "O'chirish",
    message: `"${a.name}" konsalting agentligini o'chirilsinmi?`,
    confirmLabel: "O'chirish",
    tone: 'danger',
  })
  if (!ok) return
  try {
    await consultingApi.delete(a.id)
    toast.success("O'chirildi")
    await load()
  } catch (e) {
    handleErr(e, "O'chirib bo'lmadi")
  }
}

async function toggleActive(a: ConsultingAgency) {
  try {
    await consultingApi.update(a.id, { is_active: !a.is_active })
    await load()
  } catch (e) {
    handleErr(e, "O'zgartirib bo'lmadi")
  }
}

function handleErr(e: unknown, fallback: string) {
  const ax = e as AxiosError<{ error?: { message?: string } }>
  toast.error(ax.response?.data?.error?.message || fallback)
}
</script>

<template>
  <div class="max-w-4xl mx-auto space-y-5">
    <PageHeader
      title="Konsalting agentliklari"
      subtitle="Sayt orqali ariza kim orqali kelganini kuzatish uchun. Faqat root superadmin boshqaradi."
    />

    <div v-if="!isRoot"
         class="card p-6 flex items-start gap-3 bg-rose-50 dark:bg-rose-500/10 border-l-4 border-rose-500">
      <AlertCircle class="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
      <div>
        <div class="font-semibold text-rose-900 dark:text-rose-200">Ruxsat yo'q</div>
        <p class="text-xs text-rose-800 dark:text-rose-300 mt-1">
          Bu bo'lim faqat root superadmin uchun.
        </p>
      </div>
    </div>

    <template v-else>
      <!-- Add/Edit form -->
      <section class="card p-5 space-y-4">
        <h2 class="font-semibold text-slate-900 dark:text-slate-100 inline-flex items-center gap-2">
          <Building2 class="w-4 h-4 text-indigo-500" />
          {{ editingId ? "Tahrirlash" : "Yangi agentlik" }}
        </h2>

        <div class="grid sm:grid-cols-2 gap-4">
          <div class="sm:col-span-2">
            <label class="label">Nomi <span class="text-rose-500">*</span></label>
            <input v-model="form.name" class="input" placeholder="Masalan: GoldenWay Consulting" />
          </div>
          <div class="sm:col-span-2">
            <label class="label">Izoh</label>
            <textarea v-model="form.notes" class="input" rows="2"
                      placeholder="Ichki eslatma (ixtiyoriy)" />
          </div>
          <label class="inline-flex items-center gap-2 cursor-pointer">
            <input v-model="form.is_active" type="checkbox" class="w-4 h-4 rounded" />
            <span class="text-sm text-slate-700 dark:text-slate-300">Faol</span>
          </label>
        </div>

        <div class="flex justify-end gap-2 pt-3 border-t border-slate-100 dark:border-slate-800">
          <button v-if="editingId" class="btn-secondary" @click="startNew">Bekor qilish</button>
          <button class="btn-primary" :disabled="saving" @click="save">
            <Loader2 v-if="saving" class="w-4 h-4 animate-spin" />
            <Plus v-else-if="!editingId" class="w-4 h-4" />
            <Pencil v-else class="w-4 h-4" />
            {{ saving ? "Saqlanmoqda..." : (editingId ? "Saqlash" : "Qo'shish") }}
          </button>
        </div>
      </section>

      <!-- List -->
      <section class="card p-5">
        <h2 class="font-semibold text-slate-900 dark:text-slate-100 mb-4">
          Mavjud agentliklar
          <span class="text-xs font-normal text-slate-400 ml-1">({{ items.length }})</span>
        </h2>

        <div v-if="loading" class="space-y-2">
          <Skeleton v-for="i in 3" :key="i" class="h-14" />
        </div>

        <div v-else-if="!items.length" class="text-center py-10">
          <Building2 class="w-10 h-10 text-slate-300 dark:text-slate-600 mx-auto mb-2" />
          <p class="text-sm text-slate-500">Hali bironta agentlik qo'shilmagan</p>
        </div>

        <ul v-else class="divide-y divide-slate-100 dark:divide-slate-800/60">
          <li v-for="a in items" :key="a.id" class="py-3 flex items-center gap-3">
            <button
              class="grid place-items-center w-8 h-8 rounded-lg shrink-0 transition-colors"
              :class="a.is_active
                ? 'text-emerald-600 bg-emerald-50 dark:bg-emerald-500/10 hover:bg-emerald-100'
                : 'text-slate-400 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700'"
              :title="a.is_active ? 'Faol — bosib o\'chirish' : 'Faol emas — bosib yoqish'"
              @click="toggleActive(a)"
            >
              <ToggleRight v-if="a.is_active" class="w-4 h-4" />
              <ToggleLeft v-else class="w-4 h-4" />
            </button>

            <div class="flex-1 min-w-0">
              <div class="text-sm font-medium text-slate-900 dark:text-slate-100 truncate">
                {{ a.name }}
              </div>
              <div v-if="a.notes" class="text-xs text-slate-500 dark:text-slate-400 truncate mt-0.5">
                {{ a.notes }}
              </div>
            </div>

            <button class="icon-btn" title="Tahrirlash" @click="startEdit(a)">
              <Pencil class="w-4 h-4" />
            </button>
            <button class="icon-btn icon-btn-danger" title="O'chirish" @click="remove(a)">
              <Trash2 class="w-4 h-4" />
            </button>
          </li>
        </ul>
      </section>
    </template>
  </div>
</template>

<style scoped>
.label {
  @apply block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1;
}
.btn-secondary {
  @apply inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800;
}
.icon-btn {
  @apply grid place-items-center w-8 h-8 rounded-lg text-slate-500 hover:text-slate-900 hover:bg-slate-100 dark:hover:bg-slate-800 dark:hover:text-slate-100 transition-colors;
}
.icon-btn-danger {
  @apply hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-500/10 dark:hover:text-rose-400;
}
</style>
