<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'

const { isDark, toggle } = useTheme()
const config = useRuntimeConfig()
const appUrl = (config.public as any).appUrl || '/app'
const loginUrl = `${appUrl}/auth/login`

const scrolled = ref(false)
const mobileOpen = ref(false)
const activeId = ref<string>('home')

function onScroll() {
  scrolled.value = window.scrollY > 8
  const sections = ['contact', 'about', 'programs', 'home']
  for (const id of sections) {
    const el = document.getElementById(id)
    if (!el) continue
    if (el.getBoundingClientRect().top < 140) { activeId.value = id; break }
  }
}
onMounted(() => {
  onScroll()
  window.addEventListener('scroll', onScroll, { passive: true })
})
onBeforeUnmount(() => window.removeEventListener('scroll', onScroll))

const links = [
  { id: 'home',     label: 'Bosh sahifa' },
  { id: 'programs', label: "Yo'nalishlar" },
  { id: 'about',    label: 'Universitet' },
  { id: 'contact',  label: "Bog'lanish" },
]

const route = useRoute()
const router = useRouter()

function go(id: string) {
  mobileOpen.value = false
  // From a non-home page, anchor scrolls don't work — route to home
  // with the hash and let onMounted/onScroll handle the focus on land.
  if (route.path !== '/') {
    if (id === 'home') {
      router.push('/')
    } else {
      router.push({ path: '/', hash: `#${id}` })
    }
    return
  }
  if (id === 'home') {
    window.scrollTo({ top: 0, behavior: 'smooth' })
    return
  }
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}
</script>

<template>
  <header
    class="sticky top-0 z-30 transition-all duration-300"
    :style="{
      background: scrolled ? 'rgb(var(--bg) / 0.85)' : 'rgb(var(--bg) / 0.50)',
      backdropFilter: 'blur(16px) saturate(180%)',
      WebkitBackdropFilter: 'blur(16px) saturate(180%)',
      borderBottom: scrolled ? '1px solid rgb(var(--border))' : '1px solid transparent',
    }"
  >
    <div class="container-x flex items-center h-14 sm:h-[68px] gap-2 sm:gap-3">
      <!-- Brand -->
      <a href="#home" @click.prevent="go('home')" class="flex items-center gap-2.5 sm:gap-3 shrink-0 group min-w-0">
        <img src="/logo.webp" alt="XIU" class="w-9 h-9 sm:w-10 sm:h-10 rounded-xl shadow-sm transition-transform duration-300 group-hover:scale-105 object-contain shrink-0" loading="eager" />
        <div class="hidden md:flex flex-col leading-[1.05] tracking-tight">
          <span class="text-[13px] font-semibold" :style="{ color: 'rgb(var(--fg))' }">Xalqaro innovatsion</span>
          <span class="text-[13px] font-semibold" :style="{ color: 'rgb(var(--fg-muted))' }">Universiteti</span>
        </div>
      </a>

      <!-- Desktop nav -->
      <nav class="hidden lg:flex items-center mx-auto gap-0.5 p-1 rounded-full"
           :style="{ background: 'rgb(var(--bg-soft) / 0.7)' }">
        <a v-for="l in links" :key="l.id"
           :href="`#${l.id}`"
           class="relative px-4 py-1.5 text-[13px] font-medium rounded-full transition-all duration-200"
           :style="activeId === l.id
             ? { color: 'rgb(var(--fg))', background: 'rgb(var(--card))', boxShadow: 'var(--shadow-sm)' }
             : { color: 'rgb(var(--fg-muted))' }"
           @click.prevent="go(l.id)">
          {{ l.label }}
        </a>
      </nav>

      <!-- Right cluster -->
      <div class="ml-auto lg:ml-0 flex items-center gap-1 sm:gap-1.5">
        <!-- Theme toggle -->
        <button
          class="grid place-items-center w-9 h-9 rounded-full transition-all duration-200 hover:bg-[rgb(var(--bg-soft))] shrink-0"
          :title="isDark ? 'Kunduzgi rejim' : 'Tungi rejim'"
          @click="toggle"
          :style="{ color: 'rgb(var(--fg-muted))' }"
        >
          <Transition
            enter-active-class="transition-all duration-300"
            leave-active-class="transition-all duration-150"
            enter-from-class="opacity-0 rotate-[-90deg]"
            leave-to-class="opacity-0 rotate-[90deg]"
            mode="out-in"
          >
            <svg v-if="!isDark" key="moon" xmlns="http://www.w3.org/2000/svg" width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
            </svg>
            <svg v-else key="sun" xmlns="http://www.w3.org/2000/svg" width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="4" />
              <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41" />
            </svg>
          </Transition>
        </button>

        <a :href="loginUrl" class="btn-primary btn-sm sm:btn shrink-0">
          <span class="hidden xs:inline">Ariza topshirish</span>
          <span class="xs:hidden">Ariza</span>
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M5 12h14M12 5l7 7-7 7" />
          </svg>
        </a>

        <button
          class="lg:hidden grid place-items-center w-9 h-9 sm:w-10 sm:h-10 rounded-full transition-colors hover:bg-[rgb(var(--bg-soft))] shrink-0"
          :style="{ color: 'rgb(var(--fg-soft))' }"
          @click="mobileOpen = !mobileOpen"
        >
          <svg v-if="!mobileOpen" xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M4 6h16M4 12h16M4 18h16" />
          </svg>
          <svg v-else xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M18 6L6 18M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>

    <!-- Mobile drawer -->
    <Transition
      enter-active-class="transition-all duration-200 ease-out"
      leave-active-class="transition-all duration-150 ease-in"
      enter-from-class="opacity-0 -translate-y-2"
      leave-to-class="opacity-0 -translate-y-2"
    >
      <div v-if="mobileOpen" class="lg:hidden border-t backdrop-blur-md"
           :style="{ background: 'rgb(var(--bg) / 0.95)', borderColor: 'rgb(var(--border))' }">
        <nav class="container-x py-3 flex flex-col gap-0.5">
          <a v-for="l in links" :key="l.id"
             :href="`#${l.id}`"
             class="px-4 py-3 text-sm font-medium rounded-xl transition-colors"
             :style="activeId === l.id
               ? { color: 'rgb(var(--fg))', background: 'rgb(var(--bg-soft))' }
               : { color: 'rgb(var(--fg-muted))' }"
             @click.prevent="go(l.id)">
            {{ l.label }}
          </a>
        </nav>
      </div>
    </Transition>
  </header>
</template>
