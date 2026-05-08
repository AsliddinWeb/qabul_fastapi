<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { AxiosError } from 'axios'
import { CreditCard } from 'lucide-vue-next'
import { contractsApi, type ContractDetailed } from '@/api/contracts.api'
import { paymentsApi, type PaymentRead } from '@/api/payments.api'
import { staffApi } from '@/api/staff.api'
import { dictionariesApi, type DictionaryItem } from '@/api/dictionaries.api'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import Skeleton from '@/components/ui/Skeleton.vue'

const route = useRoute()
const router = useRouter()
const applicationId = computed(() => route.params.id as string)

const contract = ref<ContractDetailed | null>(null)
const payments = ref<PaymentRead[]>([])
const methods = ref<DictionaryItem[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

const newPayment = reactive({
  amount: '',
  payment_method_id: '',
  reference: '',
  notes: '',
})

async function load() {
  loading.value = true
  try {
    methods.value = await dictionariesApi.items('payment_methods')
    const application = await staffApi.applications.get(applicationId.value)

    // Backend doesn't expose "contract by application" directly — try to get one
    // by listing payments via contract id stored on the application's contract.
    // Since we don't have that endpoint, we rely on the operator having created
    // a contract; we can list payments only if we know contract_id. For demo
    // purposes, attempt to find a contract via the staff applications API.
    // (Phase 12 may add /contracts?application_id= filter.)
    void application
    error.value = "Ushbu ariza uchun shartnoma bog'lanmagan yoki API filterlash hali yo'q. Operator ko'rinishidan shartnomani oching va u yerdan to'lov yarating."
  } catch (e) {
    const ax = e as AxiosError<{ error?: { message?: string } }>
    error.value = ax.response?.data?.error?.message || "Yuklashda xatolik"
  } finally {
    loading.value = false
  }
}

async function loadFromContract(contractId: string) {
  contract.value = await contractsApi.get(contractId)
  payments.value = await paymentsApi.forContract(contractId)
}

async function submitPayment() {
  if (!contract.value) return
  if (!newPayment.amount || !newPayment.payment_method_id) {
    error.value = "Summa va to'lov turini kiriting"
    return
  }
  try {
    await paymentsApi.create({
      contract_id: contract.value.id,
      amount: newPayment.amount,
      payment_method_id: newPayment.payment_method_id,
      reference: newPayment.reference || null,
      notes: newPayment.notes || null,
    })
    Object.assign(newPayment, { amount: '', payment_method_id: '', reference: '', notes: '' })
    payments.value = await paymentsApi.forContract(contract.value.id)
  } catch (e) {
    const ax = e as AxiosError<{ error?: { message?: string } }>
    error.value = ax.response?.data?.error?.message || 'Xatolik'
  }
}

async function confirmPayment(p: PaymentRead) {
  await paymentsApi.confirm(p.id)
  if (contract.value) payments.value = await paymentsApi.forContract(contract.value.id)
}

async function failPayment(p: PaymentRead) {
  const r = prompt('Sabab (ixtiyoriy):')
  if (r === null) return
  await paymentsApi.fail(p.id, r || undefined)
  if (contract.value) payments.value = await paymentsApi.forContract(contract.value.id)
}

async function refundPayment(p: PaymentRead) {
  const r = prompt('Sabab (ixtiyoriy):')
  if (r === null) return
  await paymentsApi.refund(p.id, r || undefined)
  if (contract.value) payments.value = await paymentsApi.forContract(contract.value.id)
}

onMounted(async () => {
  // Direct mode: if route is /accountant/contracts/:contractId/payments, load by contract.
  if (route.params.contractId) {
    loading.value = true
    try {
      await loadFromContract(route.params.contractId as string)
    } finally {
      loading.value = false
    }
  } else {
    await load()
  }
})
</script>

<template>
  <div class="space-y-6">
    <button class="text-sm text-brand-600 hover:underline" @click="router.back()">‹ Ortga</button>

    <Skeleton v-if="loading" type="list" />

    <template v-else-if="contract">
      <div>
        <h1 class="text-2xl font-bold">Shartnoma {{ contract.contract_number }}</h1>
        <p class="text-sm text-slate-500">
          Jami: {{ Number(contract.total_amount).toLocaleString('uz-UZ') }} {{ contract.currency }} ·
          To'langan: {{ Number(contract.paid_amount).toLocaleString('uz-UZ') }} {{ contract.currency }}
        </p>
      </div>

      <div v-if="error" class="text-sm rounded-lg p-3 bg-red-50 text-red-700">{{ error }}</div>

      <section class="card p-5">
        <h2 class="font-semibold mb-3">Yangi to'lov qo'shish</h2>
        <div class="grid sm:grid-cols-5 gap-2">
          <input v-model="newPayment.amount" type="number" step="0.01" class="input" placeholder="Summa *" />
          <select v-model="newPayment.payment_method_id" class="input">
            <option value="">To'lov turi *</option>
            <option v-for="m in methods" :key="m.id" :value="m.id">{{ m.name_uz }}</option>
          </select>
          <input v-model="newPayment.reference" class="input" placeholder="Tranzaksiya №" />
          <input v-model="newPayment.notes" class="input" placeholder="Izoh" />
          <button class="btn-primary" @click="submitPayment">Qo'shish</button>
        </div>
      </section>

      <section class="card overflow-hidden">
        <table class="w-full text-sm">
          <thead class="bg-slate-50 text-left">
            <tr>
              <th class="px-4 py-3">Raqam</th>
              <th class="px-4 py-3">Summa</th>
              <th class="px-4 py-3">Status</th>
              <th class="px-4 py-3">Tranzaksiya</th>
              <th class="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr v-for="p in payments" :key="p.id">
              <td class="px-4 py-2 font-mono text-xs">{{ p.payment_number }}</td>
              <td class="px-4 py-2">{{ Number(p.amount).toLocaleString('uz-UZ') }}</td>
              <td class="px-4 py-2"><StatusBadge :status="p.status" /></td>
              <td class="px-4 py-2 text-xs text-slate-500">{{ p.reference || '—' }}</td>
              <td class="px-4 py-2 text-right space-x-3">
                <button v-if="p.status === 'pending'" class="text-xs text-green-600 hover:underline" @click="confirmPayment(p)">
                  Tasdiqlash
                </button>
                <button v-if="p.status === 'pending'" class="text-xs text-red-600 hover:underline" @click="failPayment(p)">
                  Rad
                </button>
                <button v-if="p.status === 'confirmed'" class="text-xs text-amber-600 hover:underline" @click="refundPayment(p)">
                  Qaytarish
                </button>
              </td>
            </tr>
          </tbody>
        </table>
        <EmptyState v-if="!payments.length" :icon="CreditCard" title="To'lovlar yo'q" />
      </section>
    </template>

    <div v-else-if="error" class="card p-6 text-sm text-slate-600">{{ error }}</div>
  </div>
</template>
