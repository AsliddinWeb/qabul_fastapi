<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import type { NavEntry, NavLeaf } from '@/stores/panels'
import { useUIStore } from '@/stores/ui'
import { useSidebarCounts } from '@/stores/sidebarCounts'

const props = defineProps<{ items: NavEntry[] }>()
const emit = defineEmits<{ (e: 'navigate'): void }>()

const route = useRoute()
const ui = useUIStore()
const counts = useSidebarCounts()

function countFor(leaf: NavLeaf): number | null {
  return leaf.countKey ? counts.counts[leaf.countKey] : null
}
function fmtCount(n: number): string {
  // Show the exact figure (1 700, 12 345, 412) instead of abbreviating
  // to "1.7k" / "12k". Operators wanted the precise number visible at a
  // glance — "1.7k" hides whether it's 1 650 or 1 749. Manual regex
  // avoids the non-breaking space that toLocaleString('uz-UZ') emits.
  return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ' ')
}

// Flat list of all link targets in this nav tree.
const allLinks = computed(() => {
  const out: string[] = []
  for (const e of props.items) {
    if (e.type === 'leaf') out.push(e.to)
    else for (const c of e.items) out.push(c.to)
  }
  return out
})

// Active = link whose `to` is the longest prefix of the current path. This
// avoids both "/admin/leads" and "/admin/leads/board" lighting up at once.
const activePath = computed(() => {
  const p = route.path
  let best = ''
  for (const to of allLinks.value) {
    if (p === to || p.startsWith(to + '/')) {
      if (to.length > best.length) best = to
    }
  }
  return best
})

function isLeafActive(to: string): boolean {
  return to === activePath.value
}
</script>

<template>
  <nav class="flex-1 px-2 py-3 overflow-y-auto custom-scrollbar">
    <template v-for="entry in items" :key="entry.type === 'leaf' ? entry.to : entry.key">

      <!-- Top-level leaf -->
      <RouterLink
        v-if="entry.type === 'leaf'"
        :to="entry.to"
        :title="ui.sidebarCollapsed ? entry.label : ''"
        class="relative flex items-center rounded-lg text-sm font-medium transition-colors mb-0.5"
        :class="[
          ui.sidebarCollapsed ? 'justify-center px-0 py-2.5' : 'gap-3 px-3 py-2',
          isLeafActive(entry.to)
            ? 'bg-brand-50 text-brand-700 dark:bg-brand-500/15 dark:text-brand-200'
            : 'text-slate-700 hover:bg-slate-50 dark:text-slate-300 dark:hover:bg-slate-800/60',
        ]"
        @click="emit('navigate')"
      >
        <component :is="entry.icon"
                   class="w-[18px] h-[18px] shrink-0"
                   :class="isLeafActive(entry.to) ? 'text-brand-600 dark:text-brand-300' : 'text-slate-500 dark:text-slate-400'" />
        <span v-if="!ui.sidebarCollapsed" class="truncate flex-1">{{ entry.label }}</span>
        <span v-if="!ui.sidebarCollapsed && countFor(entry) != null"
              class="ml-1 px-1.5 py-0.5 rounded-md text-[10px] font-semibold tabular-nums bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 shrink-0">
          {{ fmtCount(countFor(entry) as number) }}
        </span>
        <span v-if="!ui.sidebarCollapsed && isLeafActive(entry.to)"
              class="absolute right-2 top-1/2 -translate-y-1/2 w-1 h-5 rounded-full bg-brand-500 dark:bg-brand-400"></span>
      </RouterLink>

      <!-- Group: caps header + flat children list (no accordion) -->
      <template v-else>
        <!-- Collapsed mode: just a divider, no header -->
        <div v-if="ui.sidebarCollapsed" class="my-2 mx-3 h-px bg-slate-200 dark:bg-slate-800"></div>

        <!-- Expanded mode: caps section header -->
        <div v-else class="px-3 pt-4 pb-1.5 text-[10px] font-semibold uppercase tracking-[0.1em] text-slate-400 dark:text-slate-500">
          {{ entry.label }}
        </div>

        <RouterLink
          v-for="child in entry.items"
          :key="child.to"
          :to="child.to"
          :title="ui.sidebarCollapsed ? child.label : ''"
          class="relative flex items-center rounded-lg text-sm font-medium transition-all mb-0.5"
          :class="[
            ui.sidebarCollapsed ? 'justify-center px-0 py-2.5' : 'gap-3 px-3 py-2',
            isLeafActive(child.to)
              ? 'bg-brand-50 text-brand-700 dark:bg-brand-500/15 dark:text-brand-200'
              : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-800/60 dark:hover:text-slate-100',
          ]"
          @click="emit('navigate')"
        >
          <!-- Child dash marker (expanded only) — turns into bullet when active -->
          <span v-if="!ui.sidebarCollapsed"
                aria-hidden="true"
                class="inline-block transition-all"
                :class="isLeafActive(child.to)
                  ? 'w-1.5 h-1.5 rounded-full bg-brand-500 dark:bg-brand-300'
                  : 'w-2 h-px bg-slate-300 dark:bg-slate-600'">
          </span>
          <component :is="child.icon"
                     class="w-[16px] h-[16px] shrink-0"
                     :class="isLeafActive(child.to) ? 'text-brand-600 dark:text-brand-300' : 'text-slate-400 dark:text-slate-500'" />
          <span v-if="!ui.sidebarCollapsed" class="truncate flex-1">{{ child.label }}</span>
          <span v-if="!ui.sidebarCollapsed && countFor(child) != null"
                class="ml-1 px-1.5 py-0.5 rounded-md text-[10px] font-semibold tabular-nums bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 shrink-0">
            {{ fmtCount(countFor(child) as number) }}
          </span>
          <span v-if="!ui.sidebarCollapsed && isLeafActive(child.to)"
                class="absolute right-2 top-1/2 -translate-y-1/2 w-1 h-5 rounded-full bg-brand-500 dark:bg-brand-400"></span>
        </RouterLink>
      </template>
    </template>
  </nav>
</template>

<style scoped>
.custom-scrollbar::-webkit-scrollbar { width: 6px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(148,163,184,.3); border-radius: 3px; }
.custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(148,163,184,.5); }
</style>
