<script setup lang="ts">
/**
 * International admission detail — single application view with stage
 * progression timeline, document previews, and operator notes.
 */
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import { AxiosError } from 'axios'
import {
  ArrowLeft, Globe, FileText, Save, Check, X as XIcon,
  ArrowRight, RotateCcw, AlertTriangle, Trash2, Phone, Mail, MapPin,
} from 'lucide-vue-next'
import {
  internationalApi, STAGE_LABELS, STAGE_TONES,
  type IntlApplication,
} from '@/api/international.api'
import { useToast } from '@/composables/useToast'
import { useConfirm } from '@/composables/useConfirm'
import PageHeader from '@/components/ui/PageHeader.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import FilePreview from '@/components/ui/FilePreview.vue'

const route = useRoute()
const router = useRouter()
const toast = useToast()
const { ask } = useConfirm()

const id = computed(() => route.params.id as string)
const data = ref<IntlApplication | null>(null)
const loading = ref(true)
const saving = ref(false)
const notes = ref('')

async function load() {
  loading.value = true
  try {
    data.value = await internationalApi.get(id.value)
    notes.value = data.value.notes || ''
  } catch (e) {
    const ax = e as AxiosError<{ detail?: string }>
    toast.error(ax.response?.data?.detail || "Yuklab bo'lmadi")
  } finally {
    loading.value = false
  }
}

onMounted(load)

async function advance(direction: 'next' | 'back') {
  if (!data.value) return
  try {
    data.value = await internationalApi.advance(id.value, direction)
    toast.success(direction === 'next' ? "Keyingi bosqich" : "Oldingi bosqich")
  } catch (e) {
    const ax = e as AxiosError<{ detail?: string }>
    toast.error(ax.response?.data?.detail || "Xato")
  }
}

async function reject() {
  if (!data.value) return
  const reason = window.prompt("Rad etish sababi (ixtiyoriy):") || ''
  const ok = await ask({
    title: "Arizani rad etish",
    message: `${data.value.full_name} ning arizasi rad etilsinmi?`,
    confirmLabel: "Rad etish", tone: 'danger',
  })
  if (!ok) return
  try {
    data.value = await internationalApi.reject(id.value, reason || undefined)
    toast.success("Rad etildi")
  } catch (e) {
    const ax = e as AxiosError<{ detail?: string }>
    toast.error(ax.response?.data?.detail || "Xato")
  }
}

async function unreject() {
  if (!data.value) return
  try {
    data.value = await internationalApi.unreject(id.value)
    toast.success("Tiklandi")
  } catch (e) {
    const ax = e as AxiosError<{ detail?: string }>
    toast.error(ax.response?.data?.detail || "Xato")
  }
}

async function saveNotes() {
  if (!data.value) return
  saving.value = true
  try {
    data.value = await internationalApi.updateNotes(id.value, notes.value || null)
    toast.success("Izoh saqlandi")
  } catch (e) {
    const ax = e as AxiosError<{ detail?: string }>
    toast.error(ax.response?.data?.detail || "Xato")
  } finally {
    saving.value = false
  }
}

async function deleteRow() {
  if (!data.value) return
  const ok = await ask({
    title: "Arizani o'chirish",
    message: "Bu arizani butunlay o'chirib tashlaysizmi? Bu amalni qaytarib bo'lmaydi.",
    confirmLabel: "O'chirish", tone: 'danger',
  })
  if (!ok) return
  try {
    await internationalApi.delete(id.value)
    toast.success("O'chirildi")
    router.push('/admin/international-admissions')
  } catch (e) {
    const ax = e as AxiosError<{ detail?: string }>
    toast.error(ax.response?.data?.detail || "Xato")
  }
}
</script>

<template>
  <Skeleton v-if="loading" type="detail" />

  <div v-else-if="data" class="space-y-5 max-w-5xl mx-auto">
    <PageHeader
      :title="data.full_name"
      :subtitle="`${data.ref_number} · ${data.country}`"
      :crumbs="[
        { label: 'Bosh sahifa', to: '/admin' },
        { label: 'Xalqaro qabul', to: '/admin/international-admissions' },
      ]"
    >
      <button type="button" class="btn-ghost" @click="router.back()">
        <ArrowLeft class="w-4 h-4" /> Ortga
      </button>
    </PageHeader>

    <!-- Status banner -->
    <div v-if="data.rejected"
         class="card p-4 ring-1 ring-rose-200 dark:ring-rose-700/40 bg-rose-50/40 dark:bg-rose-500/10 flex items-start gap-3">
      <AlertTriangle class="w-5 h-5 text-rose-500 shrink-0 mt-0.5" />
      <div class="flex-1">
        <div class="font-semibold text-rose-700 dark:text-rose-300">Ariza rad etilgan</div>
        <div v-if="data.rejection_reason" class="text-sm text-rose-600 dark:text-rose-400 mt-1">{{ data.rejection_reason }}</div>
      </div>
      <button class="btn-outline btn-sm" @click="unreject"><RotateCcw class="w-3.5 h-3.5" /> Tiklash</button>
    </div>

    <!-- Stage timeline -->
    <section class="card p-4 sm:p-6">
      <h3 class="font-semibold text-slate-900 dark:text-slate-100 mb-4">Qabul jarayoni bosqichlari</h3>
      <ol class="grid grid-cols-1 sm:grid-cols-6 gap-2">
        <li v-for="(label, i) in STAGE_LABELS" :key="i"
            class="flex sm:flex-col items-center sm:items-stretch gap-2 p-2.5 rounded-lg ring-1"
            :class="i < data.stage
              ? 'ring-emerald-200/60 dark:ring-emerald-700/30 bg-emerald-50/40 dark:bg-emerald-500/10'
              : i === data.stage
                ? 'ring-amber-200/60 dark:ring-amber-700/30 bg-amber-50/40 dark:bg-amber-500/10'
                : 'ring-slate-200/60 dark:ring-slate-700/40 bg-slate-50/30 dark:bg-slate-800/30 opacity-70'">
          <div class="grid place-items-center w-7 h-7 rounded-md text-white text-xs font-bold shrink-0"
               :class="i < data.stage
                 ? 'bg-emerald-500'
                 : i === data.stage
                   ? 'bg-amber-500'
                   : 'bg-slate-300 dark:bg-slate-700'">
            <Check v-if="i < data.stage" class="w-3.5 h-3.5" />
            <span v-else>{{ i+1 }}</span>
          </div>
          <div class="text-[11px] font-semibold leading-snug sm:text-center"
               :class="i < data.stage
                 ? 'text-emerald-700 dark:text-emerald-300'
                 : i === data.stage
                   ? 'text-amber-700 dark:text-amber-300'
                   : 'text-slate-500 dark:text-slate-400'">
            {{ label }}
          </div>
        </li>
      </ol>

      <div v-if="!data.rejected" class="mt-5 flex flex-wrap items-center gap-2">
        <button class="btn-outline btn-sm" :disabled="data.stage === 0" @click="advance('back')">
          ← Oldingi
        </button>
        <button class="btn-primary" :disabled="data.stage >= 5" @click="advance('next')">
          Keyingi bosqich <ArrowRight class="w-4 h-4" />
        </button>
        <button class="btn-outline btn-sm !text-rose-600 !ring-rose-200 dark:!ring-rose-700/40"
                @click="reject">
          <XIcon class="w-3.5 h-3.5" /> Rad etish
        </button>
      </div>
    </section>

    <!-- Identity + program -->
    <section class="card p-4 sm:p-6 grid sm:grid-cols-2 gap-x-6 gap-y-3">
      <div>
        <div class="text-[10px] uppercase tracking-wider font-bold text-slate-500 dark:text-slate-400 mb-1">F.I.Sh.</div>
        <div class="text-base font-semibold text-slate-900 dark:text-slate-100">{{ data.full_name }}</div>
      </div>
      <div>
        <div class="text-[10px] uppercase tracking-wider font-bold text-slate-500 dark:text-slate-400 mb-1">Davlat</div>
        <div class="text-base text-slate-900 dark:text-slate-100">{{ data.country }}</div>
      </div>
      <div>
        <div class="text-[10px] uppercase tracking-wider font-bold text-slate-500 dark:text-slate-400 mb-1">Pasport</div>
        <div class="font-mono text-slate-900 dark:text-slate-100">{{ data.passport_number }}</div>
      </div>
      <div>
        <div class="text-[10px] uppercase tracking-wider font-bold text-slate-500 dark:text-slate-400 mb-1">Tug'ilgan sana</div>
        <div class="text-slate-900 dark:text-slate-100">{{ data.birth_date }}</div>
      </div>
      <div>
        <div class="text-[10px] uppercase tracking-wider font-bold text-slate-500 dark:text-slate-400 mb-1 inline-flex items-center gap-1.5">
          <Phone class="w-3 h-3" /> Telefon (WhatsApp)
        </div>
        <a :href="`tel:${data.phone}`" class="font-mono text-brand-700 dark:text-brand-300 hover:underline">{{ data.phone }}</a>
      </div>
      <div>
        <div class="text-[10px] uppercase tracking-wider font-bold text-slate-500 dark:text-slate-400 mb-1 inline-flex items-center gap-1.5">
          <Mail class="w-3 h-3" /> Email
        </div>
        <a :href="`mailto:${data.email}`" class="text-brand-700 dark:text-brand-300 hover:underline">{{ data.email }}</a>
      </div>
      <div>
        <div class="text-[10px] uppercase tracking-wider font-bold text-slate-500 dark:text-slate-400 mb-1">Dastur</div>
        <div class="text-slate-900 dark:text-slate-100">{{ data.program }}</div>
      </div>
      <div>
        <div class="text-[10px] uppercase tracking-wider font-bold text-slate-500 dark:text-slate-400 mb-1">Fakultet</div>
        <div class="text-slate-900 dark:text-slate-100">{{ data.faculty_text }}</div>
      </div>
    </section>

    <!-- Documents -->
    <section class="card p-4 sm:p-6">
      <h3 class="font-semibold text-slate-900 dark:text-slate-100 mb-4 inline-flex items-center gap-2">
        <FileText class="w-4 h-4 text-brand-500" /> Yuklangan hujjatlar
      </h3>
      <div class="grid sm:grid-cols-3 gap-3">
        <div>
          <div class="text-xs font-medium text-slate-500 dark:text-slate-400 mb-1.5">Pasport</div>
          <FilePreview :file-id="data.passport_file_id" />
        </div>
        <div>
          <div class="text-xs font-medium text-slate-500 dark:text-slate-400 mb-1.5">Diplom / Sertifikat</div>
          <FilePreview :file-id="data.diploma_file_id" />
        </div>
        <div>
          <div class="text-xs font-medium text-slate-500 dark:text-slate-400 mb-1.5">Surat (3x4)</div>
          <FilePreview :file-id="data.photo_file_id" />
        </div>
      </div>
    </section>

    <!-- Operator notes -->
    <section class="card p-4 sm:p-6">
      <h3 class="font-semibold text-slate-900 dark:text-slate-100 mb-3">Operator izohi</h3>
      <textarea v-model="notes" rows="3" class="input"
                placeholder="Ichki izoh — abituriyentga ko'rinmaydi"></textarea>
      <div class="mt-3 flex justify-end">
        <button class="btn-primary btn-sm" :disabled="saving" @click="saveNotes">
          <Save class="w-3.5 h-3.5" /> {{ saving ? 'Saqlanyapti…' : 'Izohni saqlash' }}
        </button>
      </div>
    </section>

    <!-- Submission audit -->
    <section class="card p-4 sm:p-6 text-xs text-slate-500 dark:text-slate-400 space-y-1">
      <div><strong class="text-slate-700 dark:text-slate-300">Topshirilgan:</strong> {{ new Date(data.created_at).toLocaleString('uz-UZ') }}</div>
      <div v-if="data.submitter_ip"><strong class="text-slate-700 dark:text-slate-300">IP:</strong> <span class="font-mono">{{ data.submitter_ip }}</span></div>
      <div v-if="data.language"><strong class="text-slate-700 dark:text-slate-300">Sayt tili:</strong> {{ data.language.toUpperCase() }}</div>
    </section>

    <div class="flex justify-end">
      <button class="btn-outline btn-sm !text-rose-600 !ring-rose-200 dark:!ring-rose-700/40"
              @click="deleteRow">
        <Trash2 class="w-3.5 h-3.5" /> Arizani o'chirish
      </button>
    </div>
  </div>
</template>
