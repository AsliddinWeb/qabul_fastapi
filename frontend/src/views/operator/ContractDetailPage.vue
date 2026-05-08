<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { FileText, FileCheck2, X } from 'lucide-vue-next'
import { contractsApi, type ContractDetailed } from '@/api/contracts.api'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import { CONTRACT_STATUS, CONTRACT_TYPE, tr } from '@/utils/labels'
import Skeleton from '@/components/ui/Skeleton.vue'
import PageHeader from '@/components/ui/PageHeader.vue'

const route = useRoute()
const router = useRouter()
const id = computed(() => route.params.id as string)

const data = ref<ContractDetailed | null>(null)
const loading = ref(true)
const busy = ref(false)
const message = ref<string | null>(null)

async function load() {
  loading.value = true
  try {
    data.value = await contractsApi.get(id.value)
  } finally {
    loading.value = false
  }
}

onMounted(load)

async function sign() {
  if (!confirm("Shartnomani imzolanganga o'tkazasizmi?")) return
  busy.value = true
  try {
    await contractsApi.sign(id.value)
    message.value = "Shartnoma imzolandi"
    await load()
  } finally {
    busy.value = false
  }
}

async function cancel() {
  if (!confirm("Shartnomani bekor qilasizmi?")) return
  busy.value = true
  try {
    await contractsApi.cancel(id.value)
    message.value = "Shartnoma bekor qilindi"
    await load()
  } finally {
    busy.value = false
  }
}

const hasPdf = computed(() => !!data.value?.pdf_file_id)

async function openPdf() {
  await contractsApi.openPdf(id.value)
}
</script>

<template>
  <Skeleton v-if="loading" type="detail" />

  <div v-else-if="data" class="space-y-6">
    <PageHeader
      :title="`Shartnoma ${data.contract_number}`"
      :subtitle="`${tr(CONTRACT_TYPE, data.type)} · ${Number(data.total_amount).toLocaleString('uz-UZ')} ${data.currency}`"
      :crumbs="[{ label: 'Bosh sahifa' }, { label: 'Shartnomalar' }]"
    >
      <StatusBadge :status="data.status" :label="tr(CONTRACT_STATUS, data.status)" />
      <button type="button" class="btn-ghost" @click="router.back()">‹ Ortga</button>
    </PageHeader>

    <div v-if="message" class="text-sm rounded-lg p-3 bg-green-50 text-green-700">{{ message }}</div>

    <div class="card p-6 space-y-3">
      <h2 class="font-semibold">Tomonlar</h2>
      <ul class="divide-y divide-slate-100">
        <li v-for="p in data.parties" :key="p.id" class="py-3 text-sm">
          <div class="font-medium uppercase text-xs text-slate-500">{{ p.party_role }}</div>
          <div>{{ p.full_name }}</div>
          <div class="text-slate-500 text-xs">
            <span v-if="p.pinfl">JSHSHIR: {{ p.pinfl }}</span>
            <span v-if="p.passport_series && p.passport_number" class="ml-2">
              Pasport: {{ p.passport_series }} {{ p.passport_number }}
            </span>
            <span v-if="p.phone" class="ml-2">Tel: {{ p.phone }}</span>
          </div>
        </li>
      </ul>
    </div>

    <div class="card p-6">
      <h2 class="font-semibold mb-3">PDF hujjat</h2>
      <div v-if="hasPdf" class="flex items-center gap-3">
        <button type="button" class="btn-primary" @click="openPdf">
          <FileText class="w-4 h-4" /> PDF ni ochish
        </button>
      </div>
      <div v-else class="text-sm text-slate-500">
        PDF generatsiya qilinmagan. Iltimos, qayta yarating yoki backend log'larini tekshiring.
      </div>
    </div>

    <div class="card p-6 space-y-3">
      <h2 class="font-semibold">Amallar</h2>
      <div class="flex flex-wrap gap-3">
        <button v-if="data.status === 'draft'" class="btn-primary" :disabled="busy" @click="sign">
          <FileCheck2 class="w-4 h-4" /> Imzolangan deb belgilash
        </button>
        <button v-if="data.status !== 'cancelled' && data.status !== 'completed'"
                class="btn-ghost text-red-600" :disabled="busy" @click="cancel">
          Bekor qilish
        </button>
      </div>
    </div>
  </div>
</template>
