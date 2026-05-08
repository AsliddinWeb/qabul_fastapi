<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { LayoutDashboard, Users, ClipboardList, Plus, BarChart3 } from 'lucide-vue-next'
import { usePanelsStore } from '@/stores/panels'

const route = useRoute()
const panels = usePanelsStore()

interface NavTab {
  to: string
  label: string
  icon: any
  highlight?: boolean
}

const tabs = computed<NavTab[]>(() => {
  const k = panels.currentPanel?.key
  if (k === 'operator') {
    return [
      { to: '/operator',                 label: 'Bosh',     icon: LayoutDashboard },
      { to: '/operator/leads',           label: "Lead'lar", icon: Users },
      { to: '/operator/leads/new',       label: 'Yangi',    icon: Plus, highlight: true },
      { to: '/operator/leads/board',     label: 'Kanban',   icon: LayoutDashboard },
      { to: '/operator/stats',           label: 'Stats',    icon: BarChart3 },
    ]
  }
  if (k === 'admin') {
    return [
      { to: '/admin',                  label: 'Bosh',     icon: LayoutDashboard },
      { to: '/admin/leads',            label: 'Leadlar',  icon: Users },
      { to: '/admin/applications/new', label: 'Yangi',    icon: Plus, highlight: true },
      { to: '/admin/applicants',       label: 'Abit.',    icon: Users },
      { to: '/admin/applications',     label: 'Arizalar', icon: ClipboardList },
    ]
  }
  if (k === 'applicant') {
    return [
      { to: '/applicant',         label: 'Bosh',         icon: LayoutDashboard },
      { to: '/applicant/profile', label: 'Ma\'lumot',    icon: Users },
      { to: '/applicant/programs', label: "Yo'nalishlar", icon: ClipboardList },
    ]
  }
  return [
    { to: panels.currentPanel?.to || '/', label: 'Bosh', icon: LayoutDashboard },
  ]
})

function isActive(to: string): boolean {
  const p = route.path
  // Most specific match wins for "Bosh" (exact), others use prefix
  if (to.endsWith('/operator') || to.endsWith('/admin') || to.endsWith('/applicant')) {
    return p === to
  }
  return p === to || p.startsWith(to + '/')
}
</script>

<template>
  <nav
    aria-label="Mobile navigation"
    class="md:hidden fixed bottom-0 inset-x-0 z-30 bg-white/95 dark:bg-slate-900/95 backdrop-blur border-t border-slate-200 dark:border-slate-800
           safe-bottom shadow-[0_-2px_8px_rgba(15,23,42,0.04)]"
  >
    <ul class="grid items-end px-2 py-1.5"
        :style="{ gridTemplateColumns: `repeat(${tabs.length}, minmax(0, 1fr))` }">
      <li v-for="t in tabs" :key="t.to" class="contents">
        <RouterLink
          :to="t.to"
          class="relative flex flex-col items-center justify-center gap-0.5 py-1.5 rounded-xl transition-colors"
          :class="t.highlight
            ? 'text-white'
            : isActive(t.to)
              ? 'text-brand-600 dark:text-brand-300'
              : 'text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100'"
        >
          <span v-if="t.highlight"
                class="grid place-items-center w-12 h-12 rounded-full bg-gradient-to-br from-brand-500 to-violet-500 text-white shadow-lg shadow-brand-500/25 -mt-6">
            <component :is="t.icon" class="w-5 h-5" />
          </span>
          <component v-else :is="t.icon" class="w-5 h-5" />
          <span class="text-[10px] font-medium leading-none tracking-tight"
                :class="t.highlight ? 'text-slate-700 dark:text-slate-300' : ''">
            {{ t.label }}
          </span>
          <span
            v-if="!t.highlight && isActive(t.to)"
            class="absolute -top-0.5 left-1/2 -translate-x-1/2 w-6 h-0.5 rounded-full bg-brand-500 dark:bg-brand-400"
          />
        </RouterLink>
      </li>
    </ul>
  </nav>
</template>

<style scoped>
.safe-bottom {
  padding-bottom: env(safe-area-inset-bottom, 0);
}
</style>
