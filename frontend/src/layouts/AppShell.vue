<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import { Menu as MenuIcon, Search, PanelLeftClose, PanelLeftOpen, Maximize2, Minimize2 } from 'lucide-vue-next'
import ProfileMenu from '@/components/ui/ProfileMenu.vue'
import ThemeButton from '@/components/ui/ThemeButton.vue'
import NotificationBell from '@/components/ui/NotificationBell.vue'
import SidebarNav from '@/components/ui/SidebarNav.vue'
import ToastHost from '@/components/ui/ToastHost.vue'
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'
import MobileBottomNav from '@/components/ui/MobileBottomNav.vue'
import InstallPrompt from '@/components/ui/InstallPrompt.vue'
import { usePanelsStore } from '@/stores/panels'
import { useAuthStore } from '@/stores/auth'
import { useUIStore } from '@/stores/ui'
import { adminApi } from '@/api/admin.api'

const panels = usePanelsStore()
const auth = useAuthStore()
const ui = useUIStore()
const route = useRoute()
const router = useRouter()
const sidebarOpen = ref(false)
const search = ref('')
const todayNew = ref<number | null>(null)

const isAdmin = computed(() => ['admin', 'superadmin'].includes(auth.user?.role || ''))

onMounted(async () => {
  if (!isAdmin.value) return
  try {
    const stats = await adminApi.applications.stats()
    todayNew.value = (stats as any)?.topshirildi ?? 0
  } catch { /* ignore */ }
})

function onSearchSubmit() {
  const q = search.value.trim()
  if (!q) return
  if (isAdmin.value) router.push({ path: '/admin/applications', query: { q } })
}

const isFullscreen = ref(false)
function toggleFullscreen() {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen?.().catch(() => {})
    isFullscreen.value = true
  } else {
    document.exitFullscreen?.().catch(() => {})
    isFullscreen.value = false
  }
}
if (typeof document !== 'undefined') {
  document.addEventListener('fullscreenchange', () => {
    isFullscreen.value = !!document.fullscreenElement
  })
}
</script>

<template>
  <div class="min-h-screen flex bg-slate-50 dark:bg-slate-950">
    <!-- Sidebar (collapsible) -->
    <aside
      class="fixed inset-y-0 left-0 z-30 bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800
             transition-[width,transform] duration-200 ease-out
             flex flex-col md:relative md:translate-x-0"
      :class="[
        ui.sidebarCollapsed ? 'w-[68px]' : 'w-64',
        sidebarOpen ? 'translate-x-0 w-64' : '-translate-x-full md:translate-x-0',
      ]"
    >
      <!-- Brand only — collapse toggle moved to topbar -->
      <div class="h-16 flex items-center px-3 border-b border-slate-200 dark:border-slate-800">
        <RouterLink to="/" class="flex items-center gap-2.5 group min-w-0 flex-1"
                    :class="ui.sidebarCollapsed ? 'justify-center' : ''">
          <span class="w-9 h-9 rounded-xl bg-brand-600 grid place-items-center text-white font-bold shadow-sm shrink-0">
            X
          </span>
          <div v-if="!ui.sidebarCollapsed" class="leading-tight min-w-0">
            <div class="font-bold text-slate-900 dark:text-slate-100 tracking-tight truncate">XIU Qabul</div>
            <div v-if="panels.currentPanel"
                 class="text-[10px] text-slate-500 dark:text-slate-400 -mt-0.5 uppercase tracking-wider truncate">
              {{ panels.currentPanel.label }}
            </div>
          </div>
        </RouterLink>
      </div>

      <SidebarNav :items="panels.nav" @navigate="sidebarOpen = false" />

      <div v-if="!ui.sidebarCollapsed" class="px-4 py-3 border-t border-slate-200 dark:border-slate-800 text-[11px] text-slate-400 dark:text-slate-500">
        XIU Qabul · v0.1
      </div>
    </aside>

    <!-- Mobile overlay -->
    <div
      v-if="sidebarOpen"
      class="fixed inset-0 bg-black/40 z-20 md:hidden"
      @click="sidebarOpen = false"
    />

    <!-- Main column -->
    <div class="flex-1 flex flex-col min-w-0">
      <!-- Topbar -->
      <header class="sticky top-0 z-10 h-16 bg-white/85 dark:bg-slate-900/85 backdrop-blur border-b border-slate-200 dark:border-slate-800 flex items-center px-3 md:px-5 gap-3">
        <!-- Mobile: hamburger to open sidebar drawer -->
        <button
          class="md:hidden p-2 -ml-1 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-200"
          @click="sidebarOpen = !sidebarOpen"
        >
          <MenuIcon class="w-5 h-5" />
        </button>

        <!-- Desktop: collapse/expand sidebar toggle (just before search) -->
        <button
          class="hidden md:grid place-items-center w-10 h-10 -ml-1 rounded-lg text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          :title="ui.sidebarCollapsed ? 'Sidebarni ochish' : 'Sidebarni yopish'"
          @click="ui.toggleSidebar()"
        >
          <component :is="ui.sidebarCollapsed ? PanelLeftOpen : PanelLeftClose" class="w-5 h-5" />
        </button>

        <h2 class="md:hidden text-base font-medium text-slate-900 dark:text-slate-100 truncate flex-1 min-w-0">
          {{ (route.meta?.title as string) || '' }}
        </h2>

        <!-- Search (md+) — bigger, more polished -->
        <form class="hidden md:block flex-1 max-w-xl" @submit.prevent="onSearchSubmit">
          <div class="relative group">
            <Search class="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none transition-colors group-focus-within:text-brand-500" />
            <input v-model="search" type="text"
                   class="w-full h-11 pl-11 pr-12 rounded-xl bg-slate-100/70 dark:bg-slate-800/60
                          text-sm text-slate-900 dark:text-slate-100
                          placeholder:text-slate-400 dark:placeholder:text-slate-500
                          ring-1 ring-transparent focus:ring-brand-300 dark:focus:ring-brand-600
                          focus:bg-white dark:focus:bg-slate-900 focus:outline-none transition-all"
                   placeholder="Qidirish..." />
            <kbd class="hidden sm:inline-flex absolute right-3 top-1/2 -translate-y-1/2 items-center gap-0.5 px-1.5 py-0.5 rounded text-[10px] font-mono font-medium text-slate-400 bg-white dark:bg-slate-900 ring-1 ring-slate-200 dark:ring-slate-700 pointer-events-none">
              ⌘K
            </kbd>
          </div>
        </form>

        <RouterLink v-if="isAdmin && todayNew !== null && todayNew > 0"
                    to="/admin/applications?status=topshirildi"
                    class="hidden lg:inline-flex items-center gap-2 h-10 px-3 rounded-lg
                           bg-brand-50 hover:bg-brand-100 ring-1 ring-brand-200/70
                           dark:bg-brand-500/10 dark:hover:bg-brand-500/20 dark:ring-brand-700/40
                           text-brand-700 dark:text-brand-300 transition-colors">
          <span class="text-xs font-medium">Yangi arizalar</span>
          <span class="text-xs font-bold tabular-nums px-1.5 py-0.5 rounded-md bg-brand-600 text-white">{{ todayNew }}</span>
        </RouterLink>

        <div class="flex items-center gap-1 ml-auto">
          <button
            class="hidden md:grid place-items-center w-10 h-10 rounded-lg text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
            :title="isFullscreen ? 'Kichraytirish' : 'To\'liq ekran'"
            @click="toggleFullscreen"
          >
            <component :is="isFullscreen ? Minimize2 : Maximize2" class="w-[18px] h-[18px]" />
          </button>
          <ThemeButton />
          <NotificationBell />
          <ProfileMenu />
        </div>
      </header>

      <main class="flex-1 p-4 md:p-6 pb-24 md:pb-6 overflow-y-auto">
        <div class="w-full">
          <RouterView />
        </div>
      </main>
    </div>

    <!-- Mobile bottom navigation (hidden on md+) -->
    <MobileBottomNav />

    <!-- PWA install prompt (auto-hides if not eligible) -->
    <InstallPrompt />

    <ToastHost />
    <ConfirmDialog />
  </div>
</template>
