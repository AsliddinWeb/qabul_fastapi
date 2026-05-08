<script setup lang="ts">
import { onMounted, reactive, ref, watch, nextTick } from 'vue'
import { Plus, Pencil, Trash2, MapPin } from 'lucide-vue-next'
import { AxiosError } from 'axios'
import { adminApi, type CountryRead, type RegionRead } from '@/api/admin.api'
import EmptyState from '@/components/ui/EmptyState.vue'
import { useToast } from '@/composables/useToast'
import { useConfirm } from '@/composables/useConfirm'
import Skeleton from '@/components/ui/Skeleton.vue'
import PageHeader from '@/components/ui/PageHeader.vue'

const toast = useToast()
const { ask } = useConfirm()
const nameInput = ref<HTMLInputElement | null>(null)

const countries = ref<CountryRead[]>([])
const items = ref<RegionRead[]>([])
const loading = ref(true)
const filterCountry = ref<string>('')

const showForm = ref(false)
const editing = ref<RegionRead | null>(null)
const error = ref<string | null>(null)
const saving = ref(false)
const form = reactive({ name: '', country_id: '' })

async function loadCountries() {
  countries.value = await adminApi.countries.list()
  if (!filterCountry.value && countries.value.length) {
    filterCountry.value = countries.value[0].id
  }
}

async function load() {
  loading.value = true
  try {
    items.value = await adminApi.regions.list(filterCountry.value || undefined)
  } finally {
    loading.value = false
  }
}

watch(filterCountry, () => {
  load()
})

onMounted(async () => {
  await loadCountries()
  await load()
})

function openCreate() {
  editing.value = null
  form.name = ''
  form.country_id = filterCountry.value || (countries.value[0]?.id ?? '')
  error.value = null
  showForm.value = true
  nextTick(() => nameInput.value?.focus())
}

function openEdit(it: RegionRead) {
  editing.value = it
  form.name = it.name
  form.country_id = it.country_id
  error.value = null
  showForm.value = true
  nextTick(() => nameInput.value?.focus())
}

async function submit() {
  if (!form.name.trim() || !form.country_id) {
    error.value = "Nom va davlat majburiy"
    return
  }
  saving.value = true
  error.value = null
  try {
    if (editing.value) {
      await adminApi.regions.update(editing.value.id, { name: form.name.trim(), country_id: form.country_id })
      toast.success("Yangilandi")
    } else {
      await adminApi.regions.create({ name: form.name.trim(), country_id: form.country_id })
      toast.success("Qo'shildi")
    }
    showForm.value = false
    await load()
  } catch (e) {
    const ax = e as AxiosError<{ error?: { message?: string } }>
    error.value = ax.response?.data?.error?.message || "Saqlab bo'lmadi"
    toast.error(error.value!)
  } finally {
    saving.value = false
  }
}

async function remove(it: RegionRead) {
  const ok = await ask({
    title: "Viloyatni o'chirish",
    message: `"${it.name}" o'chirilsinmi? Tumanlar bog'langan bo'lsa, o'chirib bo'lmaydi.`,
    confirmLabel: "O'chirish",
    tone: 'danger',
  })
  if (!ok) return
  try {
    await adminApi.regions.delete(it.id)
    toast.success("O'chirildi")
    await load()
  } catch (e) {
    const ax = e as AxiosError<{ error?: { message?: string } }>
    toast.error(ax.response?.data?.error?.message || "O'chirib bo'lmadi (tumanlar bog'langan)")
  }
}

function countryName(id: string) {
  return countries.value.find((c) => c.id === id)?.name || ''
}
</script>

<template>
  <div class="space-y-6">
    <PageHeader
      title="Viloyatlar"
      subtitle="Davlatlar bo'yicha viloyatlar va shaharlar"
      :crumbs="[{ label: 'Bosh sahifa', to: '/admin' }, { label: 'Geografiya' }]"
    >
      <button class="btn-primary" @click="openCreate">
        <Plus class="w-4 h-4" /> Yangi viloyat
      </button>
    </PageHeader>

    <div class="card p-4">
      <label class="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Davlat</label>
      <select v-model="filterCountry" class="input max-w-xs">
        <option v-for="c in countries" :key="c.id" :value="c.id">{{ c.name }}</option>
      </select>
    </div>

    <div v-if="showForm" class="card p-5">
      <h2 class="text-sm font-semibold text-slate-900 dark:text-slate-100 mb-3">
        {{ editing ? "Tahrirlash" : "Yangi viloyat" }}
      </h2>
      <div v-if="error" class="text-sm rounded-lg p-3 mb-3 bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-300">
        {{ error }}
      </div>
      <div class="grid sm:grid-cols-2 gap-3">
        <div>
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Davlat *</label>
          <select v-model="form.country_id" class="input">
            <option v-for="c in countries" :key="c.id" :value="c.id">{{ c.name }}</option>
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Nomi *</label>
          <input ref="nameInput" v-model="form.name" class="input" />
        </div>
      </div>
      <div class="flex gap-2 mt-4">
        <button class="btn-primary" :disabled="saving" @click="submit">
          {{ saving ? 'Saqlanmoqda...' : (editing ? "Yangilash" : "Yaratish") }}
        </button>
        <button class="btn-ghost" @click="showForm = false">Bekor qilish</button>
      </div>
    </div>

    <Skeleton v-if="loading" type="list" />
    <div v-else-if="!items.length" class="card p-6">
      <EmptyState :icon="MapPin" title="Viloyatlar yo'q" />
    </div>
    <div v-else class="card">
      <table class="data-table">
        <thead>
          <tr>
            <th>Nomi</th>
            <th>Davlat</th>
            <th class="w-28 text-right">Amallar</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="it in items" :key="it.id">
            <td class="text-slate-900 dark:text-slate-100">{{ it.name }}</td>
            <td class="text-slate-600 dark:text-slate-400">{{ countryName(it.country_id) }}</td>
            <td class="text-right">
              <div class="inline-flex gap-1">
                <button class="p-1.5 rounded hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 dark:text-slate-400"
                        title="Tahrirlash" @click="openEdit(it)">
                  <Pencil class="w-4 h-4" />
                </button>
                <button class="p-1.5 rounded hover:bg-red-100 dark:hover:bg-red-900/30 text-red-600 dark:text-red-400"
                        title="O'chirish" @click="remove(it)">
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
