<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import {
  ArrowLeft, Shield, FilePlus2, FileEdit, Trash2, Activity,
  Clock, Globe, MonitorSmartphone, User as UserIcon, Hash,
  ArrowRight,
} from 'lucide-vue-next'
import { http } from '@/api/http'
import {
  AUDIT_ACTIONS, AUDIT_ENTITY_TYPES, ROLE, APPLICATION_STATUS,
  CONTRACT_STATUS, PAYMENT_STATUS, ADMISSION_TYPE, CONTRACT_TYPE,
  auditCategory, fieldLabel, tr,
} from '@/utils/labels'
import Skeleton from '@/components/ui/Skeleton.vue'

interface AuditLog {
  id: string
  user_id: string | null
  action: string
  entity_type: string | null
  entity_id: string | null
  changes: any
  ip_address: string | null
  user_agent: string | null
  created_at: string
  user_full_name: string | null
  user_phone: string | null
  user_role: string | null
}

const route = useRoute()
const router = useRouter()
const id = computed(() => route.params.id as string)
const log = ref<AuditLog | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)

async function load() {
  loading.value = true
  error.value = null
  try {
    const res = await http.get<AuditLog>(`/audit/${id.value}`)
    log.value = res.data
  } catch (e: any) {
    const status = e?.response?.status
    error.value =
      status === 404 ? "Audit yozuvi topilmadi" :
      status === 403 ? "Bu yozuvni ko'rish uchun ruxsat yo'q" :
      e?.response?.data?.error?.message ||
      "Audit yozuvini yuklab bo'lmadi"
  } finally {
    loading.value = false
  }
}
onMounted(load)

// === Action category visuals ===
const CAT_ICON = { create: FilePlus2, update: FileEdit, delete: Trash2, status: Activity, other: Shield }
const CAT_COLOR: Record<string, string> = {
  create: 'from-emerald-500 to-teal-600',
  update: 'from-indigo-500 to-violet-600',
  delete: 'from-rose-500 to-red-600',
  status: 'from-amber-500 to-orange-600',
  other:  'from-slate-600 to-slate-800',
}

const cat = computed(() => log.value ? auditCategory(log.value.action) : 'other')

const userDisplay = computed(() => {
  const l = log.value
  if (!l) return '—'
  return l.user_full_name || l.user_phone || (l.user_id ? l.user_id.slice(0, 8) + '…' : '—')
})

function fmtTime(iso: string): string {
  return new Date(iso).toLocaleString('uz-UZ', {
    day: '2-digit', month: 'long', year: 'numeric',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  })
}

// === Change diff: detect "from → to" patterns ===
type DiffRow = { field: string; from: any; to: any; kind: 'change' | 'set' | 'info' }

function isObj(v: any): v is Record<string, any> {
  return v !== null && typeof v === 'object' && !Array.isArray(v)
}

const STATUS_MAPS: Record<string, Record<string, string>> = {
  status: APPLICATION_STATUS,
  application_status: APPLICATION_STATUS,
  contract_status: CONTRACT_STATUS,
  payment_status: PAYMENT_STATUS,
  admission_type: ADMISSION_TYPE,
  type: CONTRACT_TYPE,
  role: ROLE,
}

function prettyValue(field: string, val: any): string {
  if (val === null || val === undefined || val === '') return '—'
  if (typeof val === 'boolean') return val ? "Ha" : "Yo'q"
  if (typeof val === 'string' && STATUS_MAPS[field]) {
    return STATUS_MAPS[field][val] || val
  }
  if (typeof val === 'object') return JSON.stringify(val)
  return String(val)
}

const diffRows = computed<DiffRow[]>(() => {
  const c = log.value?.changes
  if (!c || !isObj(c)) return []
  const rows: DiffRow[] = []
  for (const [field, val] of Object.entries(c)) {
    if (isObj(val) && ('from' in val || 'to' in val)) {
      rows.push({ field, from: val.from, to: val.to, kind: 'change' })
    } else {
      rows.push({ field, from: null, to: val, kind: 'set' })
    }
  }
  return rows
})

// Action description in plain Uzbek (verbose explanation)
const actionExplanation = computed(() => {
  const l = log.value
  if (!l) return ''
  const ent = tr(AUDIT_ENTITY_TYPES, l.entity_type || '').toLowerCase()
  const who = userDisplay.value
  const role = l.user_role ? `(${tr(ROLE, l.user_role)})` : ''

  switch (l.action) {
    case 'application.create':
      return `${who} ${role} yangi ariza topshirdi.`
    case 'application.create_by_staff':
      return `${who} ${role} abituriyent nomidan ariza yaratdi.`
    case 'application.review':
      return `${who} ${role} arizani ko'rib chiqdi va qaror qildi.`
    case 'application.start_review':
      return `${who} ${role} arizani ko'rib chiqishga oldi.`
    case 'application.withdraw':
      return `${who} ${role} arizani qaytarib oldi.`
    case 'contract.create':
      return `${who} ${role} yangi shartnoma yaratdi va PDF generatsiya qilindi.`
    case 'contract.sign':
      return `${who} ${role} shartnomani imzolanganga o'tkazdi.`
    case 'contract.cancel':
      return `${who} ${role} shartnomani bekor qildi.`
    case 'payment.create':
      return `${who} ${role} yangi to'lov yozuvini qo'shdi.`
    case 'payment.confirm':
      return `${who} ${role} to'lovni tasdiqladi.`
    case 'payment.refund':
      return `${who} ${role} to'lovni qaytardi.`
    case 'payment.fail':
      return `${who} ${role} to'lovni "bajarilmadi" holatiga o'tkazdi.`
    case 'user.create':
      return `${who} ${role} yangi foydalanuvchini yaratdi.`
    case 'user.update':
      return `${who} ${role} foydalanuvchi ma'lumotlarini tahrirladi.`
    case 'user.delete':
      return `${who} ${role} foydalanuvchini o'chirdi.`
    case 'user.reset_password':
      return `${who} ${role} foydalanuvchining parolini tikladi.`
    case 'applicant.create_by_operator':
      return `${who} ${role} yangi abituriyentni qo'shdi.`
    default:
      return `${who} ${role} ${ent} bilan amal bajardi.`
  }
})

const entityLink = computed(() => {
  const l = log.value
  if (!l?.entity_id || !l.entity_type) return null
  // For delete actions the entity no longer exists — navigating to it
  // would just 404, so we hide the button. The diff table already shows
  // the snapshot we captured at delete time.
  if (cat.value === 'delete') return null
  const map: Record<string, string> = {
    applications: `/admin/applications/${l.entity_id}`,
    applicants:   `/admin/applicants/${l.entity_id}`,
    contracts:    `/admin/contracts`,
    payments:     `/admin/payments`,
    users:        `/admin/users`,
  }
  return map[l.entity_type] || null
})

// Pull a few snapshot fields out for prominent display on delete actions.
// The diff table already lists everything, but for deletions we want the
// person who got removed to be the FIRST thing the reader sees.
const deletedSnapshot = computed(() => {
  if (cat.value !== 'delete') return null
  const c = log.value?.changes
  if (!c || typeof c !== 'object') return null
  const name = c.applicant_full_name as string | undefined
  const phone = c.applicant_phone as string | undefined
  const num = c.application_number as string | undefined
  if (!name && !phone && !num) return null
  return { name, phone, number: num }
})
</script>

<template>
  <Skeleton v-if="loading" type="detail" />

  <div v-else-if="error" class="card p-6 text-rose-600 dark:text-rose-400">{{ error }}</div>

  <div v-else-if="log" class="space-y-5">
    <button class="inline-flex items-center gap-1 text-sm text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-slate-100"
            @click="router.push('/admin/audit')">
      <ArrowLeft class="w-4 h-4" /> Audit jurnaliga qaytish
    </button>

    <!-- Hero -->
    <div class="card overflow-hidden">
      <div class="bg-gradient-to-r p-6 text-white" :class="CAT_COLOR[cat]">
        <div class="flex items-start gap-4">
          <div class="grid place-items-center w-12 h-12 rounded-xl bg-white/15 ring-1 ring-white/20 shrink-0">
            <component :is="CAT_ICON[cat]" class="w-6 h-6" />
          </div>
          <div class="min-w-0">
            <div class="text-[11px] uppercase tracking-wider opacity-80">Audit yozuvi</div>
            <h1 class="text-xl sm:text-2xl font-bold mt-0.5">
              {{ AUDIT_ACTIONS[log.action] || log.action }}
            </h1>
            <div class="mt-2 flex flex-wrap items-center gap-1.5">
              <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-white/20 ring-1 ring-white/20">
                {{ tr(AUDIT_ENTITY_TYPES, log.entity_type || '') }}
              </span>
              <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono bg-white/15 ring-1 ring-white/15">
                {{ log.action }}
              </span>
              <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-white/15 ring-1 ring-white/15">
                <Clock class="w-3 h-3" /> {{ fmtTime(log.created_at) }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- Plain explanation -->
      <div class="px-6 py-5 border-t border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/40">
        <p class="text-sm text-slate-700 dark:text-slate-300 leading-relaxed">{{ actionExplanation }}</p>

        <!-- Deleted-entity snapshot: surface the applicant identity at the
             top since the original object is gone and there's nothing to
             navigate to. -->
        <div v-if="deletedSnapshot"
             class="mt-4 p-4 rounded-xl bg-white dark:bg-slate-900 ring-1 ring-rose-200/60 dark:ring-rose-500/20">
          <div class="text-[11px] uppercase tracking-wider font-bold text-rose-600 dark:text-rose-400 mb-2 inline-flex items-center gap-1.5">
            <Trash2 class="w-3 h-3" />
            O'chirilgan ariza ma'lumotlari
          </div>
          <dl class="grid sm:grid-cols-3 gap-3 text-sm">
            <div v-if="deletedSnapshot.name">
              <dt class="text-[11px] uppercase tracking-wider text-slate-500 dark:text-slate-400">Abituriyent F.I.Sh.</dt>
              <dd class="mt-0.5 font-semibold text-slate-900 dark:text-slate-100 break-words">{{ deletedSnapshot.name }}</dd>
            </div>
            <div v-if="deletedSnapshot.phone">
              <dt class="text-[11px] uppercase tracking-wider text-slate-500 dark:text-slate-400">Telefon</dt>
              <dd class="mt-0.5 font-mono text-slate-900 dark:text-slate-100">{{ deletedSnapshot.phone }}</dd>
            </div>
            <div v-if="deletedSnapshot.number">
              <dt class="text-[11px] uppercase tracking-wider text-slate-500 dark:text-slate-400">Ariza raqami</dt>
              <dd class="mt-0.5 font-mono text-slate-900 dark:text-slate-100">{{ deletedSnapshot.number }}</dd>
            </div>
          </dl>
        </div>
      </div>
    </div>

    <!-- Two-column body -->
    <div class="grid lg:grid-cols-3 gap-5">
      <!-- LEFT: changes diff -->
      <div class="lg:col-span-2 space-y-5">
        <section class="card p-5">
          <h2 class="section-title inline-flex items-center gap-2 mb-4">
            <span class="icon-bubble-sm bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300">
              <FileEdit class="w-4 h-4" />
            </span>
            O'zgarishlar
          </h2>

          <div v-if="!diffRows.length" class="text-sm text-slate-500 dark:text-slate-400 p-3 rounded-xl bg-slate-50 dark:bg-slate-800/40">
            Bu yozuv uchun batafsil ma'lumot saqlanmagan.
          </div>

          <div v-else class="overflow-x-auto">
            <table class="w-full text-sm">
              <thead>
                <tr class="text-[11px] uppercase tracking-wider text-slate-500 dark:text-slate-400 border-b border-slate-200 dark:border-slate-800">
                  <th class="text-left font-semibold py-2 pr-3 w-44">Maydon</th>
                  <th class="text-left font-semibold py-2 pr-3">Edi</th>
                  <th class="w-6"></th>
                  <th class="text-left font-semibold py-2">Bo'ldi</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in diffRows" :key="row.field"
                    class="border-b border-slate-100 dark:border-slate-800/60 last:border-0">
                  <td class="py-2.5 pr-3 font-medium text-slate-900 dark:text-slate-100">
                    {{ fieldLabel(row.field) }}
                    <div class="text-[10px] font-mono text-slate-400">{{ row.field }}</div>
                  </td>
                  <td class="py-2.5 pr-3">
                    <span v-if="row.kind === 'change'"
                          class="inline-block px-2 py-0.5 rounded-md bg-rose-50 dark:bg-rose-900/20 text-rose-700 dark:text-rose-300 line-through">
                      {{ prettyValue(row.field, row.from) }}
                    </span>
                    <span v-else class="text-slate-400">—</span>
                  </td>
                  <td class="py-2.5 text-slate-300">
                    <ArrowRight class="w-3.5 h-3.5" />
                  </td>
                  <td class="py-2.5">
                    <span class="inline-block px-2 py-0.5 rounded-md bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-300 font-medium">
                      {{ prettyValue(row.field, row.to) }}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <!-- Raw JSON -->
        <section v-if="log.changes" class="card p-5">
          <h2 class="section-title inline-flex items-center gap-2 mb-3">
            <span class="icon-bubble-sm bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300">
              <Hash class="w-4 h-4" />
            </span>
            Texnik ma'lumot (xom)
          </h2>
          <pre class="text-xs font-mono p-3 rounded-xl bg-slate-50 dark:bg-slate-800/40 ring-1 ring-slate-200/60 dark:ring-slate-700/40 overflow-x-auto whitespace-pre-wrap">{{ JSON.stringify(log.changes, null, 2) }}</pre>
        </section>
      </div>

      <!-- RIGHT: actor + meta -->
      <div class="space-y-5">
        <section class="card p-5">
          <h2 class="section-title inline-flex items-center gap-2 mb-4">
            <span class="icon-bubble-sm bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300">
              <UserIcon class="w-4 h-4" />
            </span>
            Kim qildi
          </h2>
          <div class="space-y-3">
            <div>
              <div class="text-[11px] uppercase tracking-wider text-slate-500 dark:text-slate-400">F.I.Sh.</div>
              <div class="text-base font-semibold text-slate-900 dark:text-slate-100 mt-0.5">{{ userDisplay }}</div>
            </div>
            <div v-if="log.user_phone">
              <div class="text-[11px] uppercase tracking-wider text-slate-500 dark:text-slate-400">Telefon</div>
              <div class="font-mono text-sm text-slate-900 dark:text-slate-100 mt-0.5">{{ log.user_phone }}</div>
            </div>
            <div v-if="log.user_role">
              <div class="text-[11px] uppercase tracking-wider text-slate-500 dark:text-slate-400">Rol</div>
              <div class="mt-0.5"><span class="pill">{{ tr(ROLE, log.user_role) }}</span></div>
            </div>
            <div v-if="log.user_id">
              <div class="text-[11px] uppercase tracking-wider text-slate-500 dark:text-slate-400">UUID</div>
              <div class="font-mono text-[11px] text-slate-500 dark:text-slate-400 mt-0.5 break-all">{{ log.user_id }}</div>
            </div>
          </div>
        </section>

        <section class="card p-5">
          <h2 class="section-title inline-flex items-center gap-2 mb-4">
            <span class="icon-bubble-sm bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300">
              <Globe class="w-4 h-4" />
            </span>
            Kontekst
          </h2>
          <div class="space-y-3 text-sm">
            <div class="flex items-start gap-2">
              <Clock class="w-4 h-4 text-slate-400 mt-0.5 shrink-0" />
              <div>
                <div class="text-[11px] uppercase tracking-wider text-slate-500 dark:text-slate-400">Vaqt</div>
                <div class="text-slate-900 dark:text-slate-100">{{ fmtTime(log.created_at) }}</div>
              </div>
            </div>
            <div v-if="log.ip_address" class="flex items-start gap-2">
              <Globe class="w-4 h-4 text-slate-400 mt-0.5 shrink-0" />
              <div>
                <div class="text-[11px] uppercase tracking-wider text-slate-500 dark:text-slate-400">IP-manzil</div>
                <div class="font-mono text-slate-900 dark:text-slate-100">{{ log.ip_address }}</div>
              </div>
            </div>
            <div v-if="log.user_agent" class="flex items-start gap-2">
              <MonitorSmartphone class="w-4 h-4 text-slate-400 mt-0.5 shrink-0" />
              <div class="min-w-0">
                <div class="text-[11px] uppercase tracking-wider text-slate-500 dark:text-slate-400">Brauzer / qurilma</div>
                <div class="text-xs text-slate-700 dark:text-slate-300 break-all">{{ log.user_agent }}</div>
              </div>
            </div>
          </div>
        </section>

        <section v-if="log.entity_id" class="card p-5">
          <h2 class="section-title inline-flex items-center gap-2 mb-3">
            <span class="icon-bubble-sm bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300">
              <Hash class="w-4 h-4" />
            </span>
            Obyekt
          </h2>
          <div class="space-y-2">
            <div>
              <div class="text-[11px] uppercase tracking-wider text-slate-500 dark:text-slate-400">Turi</div>
              <div class="mt-0.5"><span class="pill">{{ tr(AUDIT_ENTITY_TYPES, log.entity_type || '') }}</span></div>
            </div>
            <div>
              <div class="text-[11px] uppercase tracking-wider text-slate-500 dark:text-slate-400">UUID</div>
              <div class="font-mono text-[11px] text-slate-500 dark:text-slate-400 mt-0.5 break-all">{{ log.entity_id }}</div>
            </div>
            <RouterLink v-if="entityLink" :to="entityLink" class="btn-outline btn-sm w-full justify-center mt-2">
              Obyektga o'tish
            </RouterLink>
            <div v-else-if="cat === 'delete'"
                 class="mt-2 text-[11px] text-slate-500 dark:text-slate-400 leading-relaxed">
              Bu obyekt o'chirilgan — yuqorida saqlangan ma'lumotlar
              audit hisobotidagi yagona qaydlardir.
            </div>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>
