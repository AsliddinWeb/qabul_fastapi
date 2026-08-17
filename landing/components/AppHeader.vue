<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'

const { isDark, toggle } = useTheme()
const config = useRuntimeConfig()
const appUrl = (config.public as any).appUrl || '/app'
const loginUrl = `${appUrl}/auth/login`

const mobileOpen = ref(false)
const stuck = ref(false)
let io: IntersectionObserver | null = null
let sentinel: HTMLElement | null = null

const links = [
  { id: 'programs',  label: "Yo'nalishlar" },
  { id: 'about',     label: 'Universitet' },
  { id: 'qabul',     label: 'Qabul tartibi' },
  { id: 'hamkorlik', label: 'Hamkorlik' },
  { id: 'contact',   label: 'Aloqa' },
]

const route = useRoute()
const router = useRouter()

function go(id: string) {
  mobileOpen.value = false
  if (route.path !== '/') {
    router.push(id === 'home' ? '/' : { path: '/', hash: `#${id}` })
    return
  }
  if (id === 'home') { window.scrollTo({ top: 0, behavior: 'smooth' }); return }
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

// is-stuck — scroll listener o'rniga IntersectionObserver (brief §7)
onMounted(() => {
  sentinel = document.createElement('div')
  sentinel.style.cssText = 'position:absolute;top:0;left:0;width:1px;height:1px;pointer-events:none'
  document.body.prepend(sentinel)
  io = new IntersectionObserver((ents) => { stuck.value = !ents[0].isIntersecting }, { threshold: 0 })
  io.observe(sentinel)
})
onBeforeUnmount(() => { io?.disconnect(); sentinel?.remove() })
</script>

<template>
  <header class="xrd nav" :class="{ 'is-stuck': stuck }">
    <div class="shell nav__in">
      <a class="brand" href="#home" @click.prevent="go('home')" aria-label="Bosh sahifa">
        <img src="/logo.webp" alt="XIU logotipi" width="38" height="38" loading="eager" />
        <span><b>Xalqaro innovatsion</b><small>Universiteti</small></span>
      </a>

      <nav class="nav__links" aria-label="Asosiy menyu">
        <a v-for="l in links" :key="l.id" :href="`#${l.id}`" @click.prevent="go(l.id)">{{ l.label }}</a>
      </nav>

      <div class="nav__act">
        <button class="icon-btn" type="button" :aria-label="isDark ? 'Kunduzgi rejim' : 'Tungi rejim'" @click="toggle">
          <i :class="isDark ? 'ph ph-sun' : 'ph ph-moon'" aria-hidden="true"></i>
        </button>
        <a class="btn btn--primary" :href="loginUrl">Ariza topshirish <i class="ph ph-arrow-right" aria-hidden="true"></i></a>
        <button class="icon-btn nav__burger" type="button" :aria-label="mobileOpen ? 'Menyuni yopish' : 'Menyuni ochish'"
                :aria-expanded="mobileOpen" @click="mobileOpen = !mobileOpen">
          <i :class="mobileOpen ? 'ph ph-x' : 'ph ph-list'" aria-hidden="true"></i>
        </button>
      </div>
    </div>

    <div class="mobile-menu" :class="{ 'is-open': mobileOpen }">
      <a v-for="l in links" :key="l.id" :href="`#${l.id}`" @click.prevent="go(l.id)">{{ l.label }}</a>
      <a class="btn btn--primary" :href="loginUrl">Ariza topshirish</a>
    </div>
  </header>
</template>
