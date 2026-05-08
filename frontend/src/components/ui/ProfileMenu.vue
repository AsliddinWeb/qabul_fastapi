<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { authApi } from '@/api/auth.api'
import { ChevronDown, LogOut, User } from 'lucide-vue-next'
import Dropdown from '@/components/ui/Dropdown.vue'

const auth = useAuthStore()
const router = useRouter()

const initials = computed(() => {
  const name = auth.user?.full_name?.trim()
  if (name) return name.split(/\s+/).slice(0, 2).map(w => w[0]).join('').toUpperCase()
  return (auth.user?.phone || '?').slice(-2)
})

const roleLabel = computed(() => {
  const map: Record<string, string> = {
    superadmin: 'Bosh administrator',
    admin:      'Administrator',
    operator:   'Operator',
    director:   'Direktor',
    accountant: 'Buxgalter',
    applicant:  'Abituriyent',
  }
  return map[auth.user?.role || ''] || auth.user?.role || ''
})

const profilePath = computed(() => {
  switch (auth.user?.role) {
    case 'superadmin':
    case 'admin':      return '/admin/profile'
    case 'operator':   return '/operator/profile'
    case 'director':   return '/director/profile'
    case 'accountant': return '/accountant/profile'
    case 'applicant':  return '/applicant/profile'
    default:           return '/'
  }
})

async function logout() {
  try { if (auth.refreshToken) await authApi.logout(auth.refreshToken) } catch { /* ignore */ }
  auth.logout()
  router.push({ name: 'phone-login' })
}
</script>

<template>
  <Dropdown align="right">
    <template #trigger>
      <button class="flex items-center gap-2.5 rounded-lg p-1 pr-2 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors">
        <div class="w-9 h-9 rounded-full bg-brand-600 text-white grid place-items-center font-semibold text-sm">
          {{ initials }}
        </div>
        <div class="hidden md:flex md:flex-col md:items-start text-left leading-tight">
          <span class="text-sm font-medium text-slate-900 dark:text-slate-100">
            {{ auth.user?.full_name || auth.user?.phone }}
          </span>
          <span class="text-xs text-slate-500 dark:text-slate-400">{{ roleLabel }}</span>
        </div>
        <ChevronDown class="hidden md:block w-4 h-4 text-slate-400" />
      </button>
    </template>

    <div class="px-3 py-2 border-b border-slate-200 dark:border-slate-800">
      <div class="text-sm font-medium text-slate-900 dark:text-slate-100">
        {{ auth.user?.full_name || 'Foydalanuvchi' }}
      </div>
      <div class="text-xs text-slate-500 dark:text-slate-400">{{ auth.user?.phone }}</div>
      <div class="mt-1 inline-flex items-center text-xs px-2 py-0.5 rounded-full bg-brand-50 text-brand-700 dark:bg-brand-900/40 dark:text-brand-200">
        {{ roleLabel }}
      </div>
    </div>

    <RouterLink :to="profilePath" class="menu-item">
      <User class="w-4 h-4" />
      <span>Mening profilim</span>
    </RouterLink>

    <div class="menu-divider" />

    <button class="menu-item text-red-600 dark:text-red-400" @click="logout">
      <LogOut class="w-4 h-4" />
      <span>Tizimdan chiqish</span>
    </button>
  </Dropdown>
</template>
