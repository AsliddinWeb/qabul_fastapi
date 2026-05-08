<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Bell, AlertTriangle, Inbox } from 'lucide-vue-next'
import { useAuthStore } from '@/stores/auth'
import { leadsApi, type Lead } from '@/api/leads.api'
import Dropdown from '@/components/ui/Dropdown.vue'

const auth = useAuthStore()
const router = useRouter()

type Alert = Lead & { last_alert_at: string | null }
const alerts = ref<Alert[]>([])
const loading = ref(false)
let timer: ReturnType<typeof setInterval> | null = null

const isStaff = computed(() => ['admin', 'superadmin', 'operator', 'director'].includes(auth.user?.role || ''))

async function refresh() {
  if (!isStaff.value) return
  loading.value = true
  try {
    alerts.value = await leadsApi.slaAlerts(24)
  } catch {
    alerts.value = []
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  refresh()
  // Re-poll every 60s while the page is active.
  timer = setInterval(refresh, 60_000)
})
onBeforeUnmount(() => { if (timer) clearInterval(timer) })

function relTime(iso: string | null): string {
  if (!iso) return '—'
  const d = new Date(iso); const diff = Date.now() - d.getTime()
  if (diff < 60_000) return 'Hozir'
  if (diff < 3600_000) return `${Math.floor(diff / 60_000)} daq`
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)} soat`
  return `${Math.floor(diff / 86_400_000)} kun`
}

function avatarInitials(s: string): string {
  const parts = (s || '').split(/\s+/).filter(Boolean)
  return ((parts[0]?.[0] || '') + (parts[1]?.[0] || '')).toUpperCase() || '—'
}

function open(a: Alert) {
  router.push(`/admin/leads/${a.id}`)
}
</script>

<template>
  <Dropdown align="right" :width="360">
    <template #trigger>
      <button class="relative grid place-items-center w-10 h-10 rounded-lg text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
              title="Bildirishnomalar">
        <Bell class="w-4 h-4" />
        <span v-if="alerts.length"
              class="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] px-1 rounded-full bg-rose-500 text-white text-[10px] font-bold grid place-items-center ring-2 ring-white dark:ring-slate-900 tabular-nums">
          {{ alerts.length > 99 ? '99+' : alerts.length }}
        </span>
      </button>
    </template>

    <!-- Negate Dropdown's p-1.5 padding so header/footer go edge-to-edge -->
    <div class="-m-1.5">
      <!-- Header -->
      <div class="px-4 py-3 border-b border-slate-200 dark:border-slate-800 flex items-start justify-between gap-3">
        <div class="min-w-0">
          <div class="text-sm font-semibold text-slate-900 dark:text-slate-100">Bildirishnomalar</div>
          <div class="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">Oxirgi 24 soat ichidagi SLA ogohlantirishlari</div>
        </div>
        <span v-if="alerts.length"
              class="shrink-0 text-[11px] font-bold px-2 py-0.5 rounded-full bg-rose-500 text-white tabular-nums">
          {{ alerts.length }}
        </span>
      </div>

      <!-- Loading -->
      <div v-if="loading" class="px-4 py-10 text-center text-xs text-slate-400">Yuklanmoqda...</div>

      <!-- Empty -->
      <div v-else-if="!alerts.length" class="px-4 py-10 text-center">
        <div class="grid place-items-center w-12 h-12 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-400 mx-auto mb-3">
          <Inbox class="w-5 h-5" />
        </div>
        <div class="text-sm font-medium text-slate-700 dark:text-slate-300">Hammasi joyida</div>
        <div class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">Hech qanday ogohlantirish yo'q</div>
      </div>

      <!-- List -->
      <ul v-else class="max-h-[400px] overflow-y-auto divide-y divide-slate-100 dark:divide-slate-800/60">
        <li v-for="a in alerts" :key="a.id"
            class="px-4 py-3 hover:bg-slate-50 dark:hover:bg-slate-800/60 cursor-pointer transition-colors flex items-start gap-3"
            @click="open(a)">
          <div class="grid place-items-center w-9 h-9 rounded-lg bg-amber-50 text-amber-600 dark:bg-amber-500/15 dark:text-amber-300 shrink-0">
            <AlertTriangle class="w-4 h-4" />
          </div>
          <div class="min-w-0 flex-1">
            <div class="flex items-center justify-between gap-2">
              <span class="text-sm font-semibold text-slate-900 dark:text-slate-100 truncate">{{ a.full_name }}</span>
              <span class="text-[10px] text-slate-500 dark:text-slate-400 shrink-0">{{ relTime(a.last_alert_at) }}</span>
            </div>
            <div class="text-[11px] text-slate-500 dark:text-slate-400 truncate mt-0.5">
              <span v-if="a.stage_name">{{ a.stage_name }} · </span>{{ a.phone }}
            </div>
            <div class="text-[11px] text-amber-600 dark:text-amber-400 font-medium mt-0.5">
              Bosqichda harakatsiz
            </div>
          </div>
        </li>
      </ul>

      <!-- Footer -->
      <div v-if="alerts.length" class="px-4 py-2.5 border-t border-slate-200 dark:border-slate-800">
        <button class="w-full text-xs font-medium text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-slate-100 transition-colors text-center"
                @click="router.push('/admin/leads')">
          Barcha leadlar →
        </button>
      </div>
    </div>
  </Dropdown>
</template>
