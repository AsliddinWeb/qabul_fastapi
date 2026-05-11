<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { FileText, FileCheck2, X, Gift } from 'lucide-vue-next'
import { AxiosError } from 'axios'
import { contractsApi, type ContractDetailed } from '@/api/contracts.api'
import { referralsApi } from '@/api/referrals.api'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import { CONTRACT_STATUS, CONTRACT_TYPE, tr } from '@/utils/labels'
import { useToast } from '@/composables/useToast'
import { useConfirm } from '@/composables/useConfirm'
import Skeleton from '@/components/ui/Skeleton.vue'
import PageHeader from '@/components/ui/PageHeader.vue'

const route = useRoute()
const router = useRouter()
const id = computed(() => route.params.id as string)

// Accountants share this page (read-only) — hide action buttons.
const isReadOnly = computed(() => route.path.startsWith('/accountant/'))

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

const hasPdf = computed(() => !!data.value?.pdf_file_id && !!data.value?.signed_at)

async function openPdf() {
  await contractsApi.openPdf(id.value)
}

// === Apply referral bonuses as discount ===
const toast = useToast()
const { ask } = useConfirm()
const applyCount = ref(1)
const applying = ref(false)
const applyError = ref<string | null>(null)
const canApply = computed(() =>
  !isReadOnly.value &&
  !!data.value &&
  data.value.status === 'draft',
)
async function applyReferralDiscount() {
  if (!data.value || applyCount.value < 1) return
  applyError.value = null
  const ok = await ask({
    title: 'Referal chegirma',
    message: `${applyCount.value} ta faol bonus shu shartnoma summasidan chegirib qo'shiladi. Davom etamizmi?`,
    confirmLabel: "Qo'llash",
    tone: 'primary',
  })
  if (!ok) return
  applying.value = true
  try {
    const res = await referralsApi.applyToContract(data.value.id, applyCount.value)
    toast.success(`-${Number(res.discount).toLocaleString('uz-UZ')} so'm chegirildi`)
    applyCount.value = 1
    await load()
  } catch (e) {
    const ax = e as AxiosError<{ detail?: string }>
    applyError.value = ax.response?.data?.detail || "Qo'llab bo'lmadi"
  } finally {
    applying.value = false
  }
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
      <div v-else-if="!data.signed_at" class="text-sm text-slate-500">
        PDF imzolangandan so'ng yuklab olinishi mumkin. Avval shartnomani imzolang.
      </div>
      <div v-else class="text-sm text-slate-500">
        PDF generatsiya qilinmagan. Iltimos, qayta yarating yoki backend log'larini tekshiring.
      </div>
    </div>

    <!-- Referral bonus discount (draft contracts only) -->
    <div v-if="canApply" class="card p-5 sm:p-6 space-y-3 border-l-4 border-rose-400 dark:border-rose-500/70">
      <div class="flex items-start gap-3">
        <span class="grid place-items-center w-9 h-9 rounded-lg bg-rose-50 text-rose-600 dark:bg-rose-500/15 dark:text-rose-300 shrink-0">
          <Gift class="w-4 h-4" />
        </span>
        <div class="flex-1">
          <h2 class="font-semibold text-slate-900 dark:text-slate-100">Referal bonusni qo'llash</h2>
          <p class="text-xs text-slate-500 dark:text-slate-400 mt-0.5 leading-relaxed">
            Agar bu abituriyent kimnidir taklif qilgan bo'lib, bonuslari faol bo'lsa — shartnoma summasidan chegirib qo'shing.
            Har bir bonus <strong>500,000 so'm</strong>ga teng (sozlamalardan o'zgartiriladi).
          </p>
        </div>
      </div>
      <div v-if="applyError" class="text-xs rounded-lg p-2 bg-rose-50 dark:bg-rose-500/10 text-rose-700 dark:text-rose-300">
        {{ applyError }}
      </div>
      <div class="flex items-center gap-2">
        <input v-model.number="applyCount" type="number" min="1" max="100" class="input w-24" />
        <button class="btn-primary text-sm" :disabled="applying" @click="applyReferralDiscount">
          <Gift class="w-4 h-4" /> {{ applying ? "Qo'llanmoqda..." : "Qo'llash" }}
        </button>
      </div>
      <p class="text-[11px] text-slate-500 dark:text-slate-400 italic">
        Eslatma: faqat shartnoma <strong>draft</strong> holatda bo'lsa ishlaydi va abituriyent <strong>faol</strong> bonuslariga qarab tekshiriladi.
      </p>
    </div>

    <div v-if="!isReadOnly" class="card p-6 space-y-3">
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
