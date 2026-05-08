<script setup lang="ts">
import { onMounted, reactive, ref, nextTick } from 'vue'
import { Plus, Pencil, Trash2 } from 'lucide-vue-next'
import { AxiosError } from 'axios'
import EmptyState from '@/components/ui/EmptyState.vue'
import { useToast } from '@/composables/useToast'
import { useConfirm } from '@/composables/useConfirm'
import Skeleton from '@/components/ui/Skeleton.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import type { FunctionalComponent } from 'vue'

interface NamedItem {
  id: string
  name: string
  is_active?: boolean
}

interface CatalogApi {
  list: () => Promise<NamedItem[]>
  create: (payload: any) => Promise<NamedItem>
  update: (id: string, payload: any) => Promise<NamedItem>
  delete: (id: string) => Promise<unknown>
}

const props = defineProps<{
  title: string
  subtitle?: string
  emptyTitle: string
  icon: FunctionalComponent
  api: CatalogApi
  /** Show is_active toggle column. Default false. */
  withActive?: boolean
}>()

const items = ref<NamedItem[]>([])
const loading = ref(true)
const editing = ref<NamedItem | null>(null)
const showForm = ref(false)
const fieldErrors = ref<{ name?: string }>({})
const saving = ref(false)
const nameInput = ref<HTMLInputElement | null>(null)

const form = reactive<{ name: string; is_active: boolean }>({
  name: '',
  is_active: true,
})

const toast = useToast()
const { ask } = useConfirm()

async function load() {
  loading.value = true
  try {
    items.value = await props.api.list()
  } catch (e) {
    const ax = e as AxiosError<{ error?: { message?: string } }>
    toast.error(ax.response?.data?.error?.message || "Yuklab bo'lmadi")
  } finally {
    loading.value = false
  }
}

onMounted(load)

function openCreate() {
  editing.value = null
  form.name = ''
  form.is_active = true
  fieldErrors.value = {}
  showForm.value = true
  nextTick(() => nameInput.value?.focus())
}

function openEdit(it: NamedItem) {
  editing.value = it
  form.name = it.name
  form.is_active = it.is_active ?? true
  fieldErrors.value = {}
  showForm.value = true
  nextTick(() => nameInput.value?.focus())
}

function cancelForm() {
  showForm.value = false
  editing.value = null
  fieldErrors.value = {}
}

function validate(): boolean {
  fieldErrors.value = {}
  if (!form.name.trim()) {
    fieldErrors.value.name = "Nomi majburiy"
    return false
  }
  if (form.name.trim().length < 2) {
    fieldErrors.value.name = "Kamida 2 ta belgi"
    return false
  }
  return true
}

async function submit() {
  if (!validate()) return
  saving.value = true
  try {
    const payload: any = { name: form.name.trim() }
    if (props.withActive) payload.is_active = form.is_active
    if (editing.value) {
      await props.api.update(editing.value.id, payload)
      toast.success("Yangilandi")
    } else {
      await props.api.create(payload)
      toast.success("Qo'shildi")
    }
    await load()
    showForm.value = false
  } catch (e) {
    const ax = e as AxiosError<{ error?: { message?: string } }>
    const msg = ax.response?.data?.error?.message || "Saqlab bo'lmadi"
    fieldErrors.value.name = msg
    toast.error(msg)
  } finally {
    saving.value = false
  }
}

async function toggleActive(it: NamedItem) {
  if (!props.withActive) return
  try {
    await props.api.update(it.id, { is_active: !it.is_active })
    toast.success(!it.is_active ? "Faollashtirildi" : "Faolsizlantirildi")
    await load()
  } catch (e) {
    const ax = e as AxiosError<{ error?: { message?: string } }>
    toast.error(ax.response?.data?.error?.message || "Xatolik")
  }
}

async function remove(it: NamedItem) {
  const ok = await ask({
    title: "O'chirish",
    message: `"${it.name}" o'chirilsinmi? Bu amalni qaytarib bo'lmaydi.`,
    confirmLabel: "O'chirish",
    tone: 'danger',
  })
  if (!ok) return
  try {
    await props.api.delete(it.id)
    toast.success("O'chirildi")
    await load()
  } catch (e) {
    const ax = e as AxiosError<{ error?: { message?: string } }>
    toast.error(
      ax.response?.data?.error?.message
        || "O'chirib bo'lmadi (bog'langan ma'lumotlar mavjud bo'lishi mumkin)",
    )
  }
}
</script>

<template>
  <div>
    <PageHeader
      :title="title"
      :subtitle="(subtitle ? subtitle + ' · ' : '') + 'Jami ' + items.length"
      :crumbs="[{ label: 'Bosh sahifa', to: '/admin' }, { label: 'Kataloglar' }]"
    >
      <button class="btn-primary" @click="openCreate">
        <Plus class="w-4 h-4" /> Yangi qo'shish
      </button>
    </PageHeader>

    <form v-if="showForm" class="card p-5" @submit.prevent="submit">
      <h2 class="text-sm font-semibold text-slate-900 dark:text-slate-100 mb-3">
        {{ editing ? "Tahrirlash" : "Yangi yozuv" }}
      </h2>
      <div class="space-y-3">
        <div>
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Nomi *</label>
          <input
            ref="nameInput"
            v-model="form.name"
            class="input"
            :class="fieldErrors.name ? 'border-red-500' : ''"
            @input="fieldErrors.name = undefined"
          />
          <p v-if="fieldErrors.name" class="mt-1 text-xs text-red-600 dark:text-red-400">
            {{ fieldErrors.name }}
          </p>
        </div>
        <label v-if="withActive" class="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
          <input v-model="form.is_active" type="checkbox" class="rounded" />
          <span>Faol</span>
        </label>
        <div class="flex gap-2 pt-2">
          <button type="submit" class="btn-primary" :disabled="saving">
            {{ saving ? 'Saqlanmoqda...' : (editing ? "Yangilash" : "Yaratish") }}
          </button>
          <button type="button" class="btn-ghost" @click="cancelForm">Bekor qilish</button>
        </div>
      </div>
    </form>

    <Skeleton v-if="loading" type="list" />
    <div v-else-if="!items.length" class="card p-6">
      <EmptyState :icon="icon" :title="emptyTitle">
        <button class="btn-primary mt-4 inline-flex" @click="openCreate">
          <Plus class="w-4 h-4" /> Birinchi yozuvni yaratish
        </button>
      </EmptyState>
    </div>
    <div v-else class="card">
      <table class="data-table">
        <thead>
          <tr>
            <th>Nomi</th>
            <th v-if="withActive" class="w-32">Holati</th>
            <th class="w-32 text-right">Amallar</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="it in items" :key="it.id">
            <td class="text-slate-900 dark:text-slate-100">{{ it.name }}</td>
            <td v-if="withActive">
              <button
                class="badge cursor-pointer"
                :class="it.is_active
                  ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300'
                  : 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400'"
                :title="it.is_active ? 'Faolsizlantirish' : 'Faollashtirish'"
                @click="toggleActive(it)"
              >
                {{ it.is_active ? 'Faol' : 'Faol emas' }}
              </button>
            </td>
            <td class="text-right">
              <div class="inline-flex gap-1">
                <button class="icon-btn" title="Tahrirlash" @click="openEdit(it)">
                  <Pencil class="w-4 h-4" />
                </button>
                <button class="icon-btn-danger" title="O'chirish" @click="remove(it)">
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
