<script setup lang="ts">
import { onMounted, reactive, ref, watch, nextTick } from 'vue'
import { Plus, Pencil, Trash2, MapPinned } from 'lucide-vue-next'
import { AxiosError } from 'axios'
import { adminApi, type DistrictRead, type RegionRead, type CountryRead } from '@/api/admin.api'
import EmptyState from '@/components/ui/EmptyState.vue'
import { useToast } from '@/composables/useToast'
import { useConfirm } from '@/composables/useConfirm'
import Skeleton from '@/components/ui/Skeleton.vue'
import PageHeader from '@/components/ui/PageHeader.vue'

const toast = useToast()
const { ask } = useConfirm()
const nameInput = ref<HTMLInputElement | null>(null)

const countries = ref<CountryRead[]>([])
const regions = ref<RegionRead[]>([])
const items = ref<DistrictRead[]>([])
const loading = ref(true)

const filterCountry = ref<string>('')
const filterRegion = ref<string>('')

const showForm = ref(false)
const editing = ref<DistrictRead | null>(null)
const error = ref<string | null>(null)
const saving = ref(false)
const form = reactive({ name: '', region_id: '' })

async function loadCountries() {
  countries.value = await adminApi.countries.list()
  if (!filterCountry.value && countries.value.length) {
    filterCountry.value = countries.value[0].id
  }
}

async function loadRegions() {
  regions.value = filterCountry.value
    ? await adminApi.regions.list(filterCountry.value)
    : []
  if (!filterRegion.value && regions.value.length) {
    filterRegion.value = regions.value[0].id
  } else if (regions.value.every((r) => r.id !== filterRegion.value)) {
    filterRegion.value = regions.value[0]?.id ?? ''
  }
}

async function load() {
  loading.value = true
  try {
    items.value = filterRegion.value
      ? await adminApi.districts.list(filterRegion.value)
      : []
  } finally {
    loading.value = false
  }
}

watch(filterCountry, async () => {
  await loadRegions()
  await load()
})

watch(filterRegion, () => {
  load()
})

onMounted(async () => {
  await loadCountries()
  await loadRegions()
  await load()
})

function openCreate() {
  editing.value = null
  form.name = ''
  form.region_id = filterRegion.value || (regions.value[0]?.id ?? '')
  error.value = null
  showForm.value = true
  nextTick(() => nameInput.value?.focus())
}

function openEdit(it: DistrictRead) {
  editing.value = it
  form.name = it.name
  form.region_id = it.region_id
  error.value = null
  showForm.value = true
  nextTick(() => nameInput.value?.focus())
}

async function submit() {
  if (!form.name.trim() || !form.region_id) {
    error.value = "Nom va viloyat majburiy"
    return
  }
  saving.value = true
  error.value = null
  try {
    const payload = { name: form.name.trim(), region_id: form.region_id }
    if (editing.value) {
      await adminApi.districts.update(editing.value.id, payload)
      toast.success("Yangilandi")
    } else {
      await adminApi.districts.create(payload)
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

async function remove(it: DistrictRead) {
  const ok = await ask({
    title: "Tumanni o'chirish",
    message: `"${it.name}" o'chirilsinmi?`,
    confirmLabel: "O'chirish",
    tone: 'danger',
  })
  if (!ok) return
  try {
    await adminApi.districts.delete(it.id)
    toast.success("O'chirildi")
    await load()
  } catch (e) {
    const ax = e as AxiosError<{ error?: { message?: string } }>
    toast.error(ax.response?.data?.error?.message || "O'chirib bo'lmadi")
  }
}
</script>

<template>
  <div class="space-y-6">
    <PageHeader
      title="Tumanlar"
      subtitle="Viloyatlar bo'yicha tumanlar"
      :crumbs="[{ label: 'Bosh sahifa', to: '/admin' }, { label: 'Geografiya' }]"
    >
      <button class="btn-primary" @click="openCreate" :disabled="!regions.length">
        <Plus class="w-4 h-4" /> Yangi tuman
      </button>
    </PageHeader>

    <div class="card p-4 grid sm:grid-cols-2 gap-3">
      <div>
        <label class="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Davlat</label>
        <select v-model="filterCountry" class="input">
          <option v-for="c in countries" :key="c.id" :value="c.id">{{ c.name }}</option>
        </select>
      </div>
      <div>
        <label class="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Viloyat</label>
        <select v-model="filterRegion" class="input" :disabled="!regions.length">
          <option v-for="r in regions" :key="r.id" :value="r.id">{{ r.name }}</option>
        </select>
      </div>
    </div>

    <div v-if="showForm" class="card p-5">
      <h2 class="text-sm font-semibold text-slate-900 dark:text-slate-100 mb-3">
        {{ editing ? "Tahrirlash" : "Yangi tuman" }}
      </h2>
      <div v-if="error" class="text-sm rounded-lg p-3 mb-3 bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-300">
        {{ error }}
      </div>
      <div class="grid sm:grid-cols-2 gap-3">
        <div>
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Viloyat *</label>
          <select v-model="form.region_id" class="input">
            <option v-for="r in regions" :key="r.id" :value="r.id">{{ r.name }}</option>
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
      <EmptyState :icon="MapPinned" title="Tumanlar yo'q" />
    </div>
    <div v-else class="card">
      <table class="data-table">
        <thead>
          <tr>
            <th>Nomi</th>
            <th class="w-28 text-right">Amallar</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="it in items" :key="it.id">
            <td class="text-slate-900 dark:text-slate-100">{{ it.name }}</td>
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
