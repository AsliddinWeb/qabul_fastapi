<script setup lang="ts">
const config = useRuntimeConfig()
const apiBase = (config.public as any).apiBaseUrl || '/api/v1'
const appUrl = (config.public as any).appUrl || '/app'
const { open: openLeadModal } = useLeadModal()

useSeoMeta({
  title: 'Xalqaro Innovatsion Universiteti — XIU',
  description: "Bakalavr va magistratura yo'nalishlari. Xalqaro almashinuv dasturlari. Qarshi shahridagi zamonaviy xususiy universitet.",
})

interface Program {
  id: string
  name: string
  code: string
  branch_id: string
  branch_name?: string
  education_level_id: string
  education_level_name?: string
  education_form_id: string
  education_form_name?: string
  tuition_fee?: number | string
  study_duration_years?: number
  image_id?: string | null
}
interface Branch { id: string; name: string }

const programs = ref<Program[]>([])
const branches = ref<Branch[]>([])
const loading = ref(true)

const search = ref('')
const branchFilter = ref('')
const levelFilter = ref('')
const visibleCount = ref(9)

onMounted(async () => {
  try {
    const [progRes, branchRes] = await Promise.all([
      fetch(`${apiBase}/programs/programs?active_only=true`).then(r => r.ok ? r.json() : []),
      fetch(`${apiBase}/programs/branches?active_only=true`).then(r => r.ok ? r.json() : []),
    ])
    // Public marketing list hides extramural ("sirtqi") forms — same
    // filter we apply on the standalone /programs page.
    programs.value = (progRes as Program[]).filter(
      (p) => !((p.education_form_name || '').toLowerCase().includes('sirtqi')),
    )
    branches.value = branchRes
  } catch { /* ignore */ }
  finally { loading.value = false }
})

const levels = computed(() => {
  const m = new Map<string, string>()
  for (const p of programs.value) {
    if (p.education_level_id && p.education_level_name) m.set(p.education_level_id, p.education_level_name)
  }
  return Array.from(m.entries()).map(([id, name]) => ({ id, name }))
})

const filtered = computed(() => {
  const q = search.value.trim().toLowerCase()
  return programs.value.filter(p => {
    if (branchFilter.value && p.branch_id !== branchFilter.value) return false
    if (levelFilter.value && p.education_level_id !== levelFilter.value) return false
    if (q && !p.name.toLowerCase().includes(q) && !(p.code || '').toLowerCase().includes(q)) return false
    return true
  })
})
const visiblePrograms = computed(() => filtered.value.slice(0, visibleCount.value))
watch([search, branchFilter, levelFilter], () => { visibleCount.value = 9 })

function fmtPrice(v?: number | string): string {
  if (!v) return '—'
  const n = typeof v === 'string' ? parseFloat(v) : v
  if (!n || isNaN(n)) return '—'
  return Number(n).toLocaleString('uz-UZ').replace(/,/g, ' ')
}
function clearFilters() { search.value = ''; branchFilter.value = ''; levelFilter.value = '' }

const TONES = [
  { bg: 'rgb(238 242 255)', bgDark: 'rgb(67 56 202 / 0.18)',  fg: 'rgb(67 56 202)',  fgDark: 'rgb(165 180 252)' },
  { bg: 'rgb(255 251 235)', bgDark: 'rgb(180 83 9 / 0.18)',   fg: 'rgb(180 83 9)',   fgDark: 'rgb(252 211 77)' },
  { bg: 'rgb(236 253 245)', bgDark: 'rgb(4 120 87 / 0.18)',   fg: 'rgb(4 120 87)',   fgDark: 'rgb(110 231 183)' },
  { bg: 'rgb(255 241 242)', bgDark: 'rgb(190 18 60 / 0.18)',  fg: 'rgb(190 18 60)',  fgDark: 'rgb(253 164 175)' },
  { bg: 'rgb(240 249 255)', bgDark: 'rgb(7 89 133 / 0.18)',   fg: 'rgb(7 89 133)',   fgDark: 'rgb(125 211 252)' },
  { bg: 'rgb(253 244 255)', bgDark: 'rgb(134 25 143 / 0.18)', fg: 'rgb(134 25 143)', fgDark: 'rgb(240 171 252)' },
]
function tone(id: string) {
  let h = 0
  for (let i = 0; i < id.length; i++) h = (h * 31 + id.charCodeAt(i)) | 0
  return TONES[Math.abs(h) % TONES.length]
}

function iconUrl(image_id: string | null | undefined): string | null {
  return image_id ? `${apiBase}/files/${image_id}/public` : null
}

const stats = [
  { value: '8000+', label: 'Iqtidorli talabalar' },
  { value: '180+',  label: "Ilmiy daraja ega o'qituvchilar" },
  { value: '20+',   label: "Bakalavr yo'nalishlari" },
  { value: '4+',    label: "Magistratura yo'nalishlari" },
]
</script>

<template>
  <span id="home" class="block scroll-mt-header"></span>

  <!-- ============================ HERO ============================ -->
  <section class="relative overflow-hidden">
    <!-- Animated blurred blobs -->
    <div class="hero-blob hero-blob-a"
         :style="{ background: 'radial-gradient(closest-side, rgb(var(--brand) / 0.30), transparent 70%)' }"></div>
    <div class="hero-blob hero-blob-b"
         :style="{ background: 'radial-gradient(closest-side, rgb(var(--accent) / 0.22), transparent 70%)' }"></div>
    <div class="hero-blob hero-blob-c"
         style="background: radial-gradient(closest-side, rgb(217 70 239 / 0.18), transparent 70%);"></div>

    <!-- Slowly rotating conic ring -->
    <div class="hero-conic" aria-hidden="true"></div>

    <!-- Subtle dot grid -->
    <div class="absolute inset-0 -z-10 pointer-events-none opacity-50 dark:opacity-30"
         style="background-image: radial-gradient(circle, rgb(var(--fg-muted) / 0.16) 1px, transparent 1.4px); background-size: 30px 30px; mask-image: radial-gradient(ellipse 70% 55% at 50% 30%, black, transparent 80%); -webkit-mask-image: radial-gradient(ellipse 70% 55% at 50% 30%, black, transparent 80%);"></div>

    <!-- Top shimmer line -->
    <div class="absolute top-0 inset-x-0 h-px overflow-hidden pointer-events-none">
      <div class="hero-shimmer"
           style="background: linear-gradient(90deg, transparent, rgb(var(--brand)) 30%, rgb(var(--accent)) 50%, rgb(var(--brand)) 70%, transparent);"></div>
    </div>

    <div class="container-x relative pt-12 pb-16 sm:pt-20 sm:pb-24 lg:pt-32 lg:pb-32 text-center">
      <span class="eyebrow mb-5 sm:mb-7 hero-fade">
        <span class="inline-block w-1.5 h-1.5 rounded-full hero-pulse" :style="{ background: 'rgb(var(--accent))' }"></span>
        Qabul 2026 — 2027 ochiq
      </span>

      <h1 class="display-1 mt-3 max-w-4xl mx-auto hero-fade" style="animation-delay: 80ms;">
        Xalqaro <span class="gradient-text-anim">Innovatsion</span><br />
        Universiteti
      </h1>

      <p class="lead mx-auto mt-5 sm:mt-7 hero-fade" style="animation-delay: 160ms; max-width: 38rem;">
        Bakalavr va magistratura yo'nalishlari. Xalqaro almashinuv dasturlari.
        Qarshi shahridagi zamonaviy xususiy universitet.
      </p>

      <div class="mt-7 sm:mt-10 flex flex-col xs:flex-row items-center justify-center gap-3 hero-fade" style="animation-delay: 240ms;">
        <button class="btn-primary btn-lg w-full xs:w-auto" @click="openLeadModal()">
          Ariza qoldirish
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M5 12h14M12 5l7 7-7 7" />
          </svg>
        </button>
        <a href="#programs" class="btn-secondary btn-lg w-full xs:w-auto">Yo'nalishlar</a>
      </div>

      <!-- Stats — centered card grid -->
      <div class="mt-12 sm:mt-16 lg:mt-24 grid grid-cols-2 lg:grid-cols-4 gap-2.5 sm:gap-4 max-w-4xl mx-auto hero-fade"
           style="animation-delay: 320ms;">
        <div v-for="(s, i) in stats" :key="i"
             class="card px-3 py-4 sm:px-5 sm:py-7 text-center transition-all duration-300 hover:-translate-y-1 hover:border-[rgb(var(--brand)/0.30)]"
             :style="{ boxShadow: 'var(--shadow-sm)' }">
          <div class="text-2xl sm:text-4xl lg:text-[42px] font-bold tabular-nums tracking-tight"
               :style="{ color: 'rgb(var(--fg))', letterSpacing: '-0.035em' }">
            {{ s.value }}
          </div>
          <div class="mt-1.5 sm:mt-2 text-[10px] sm:text-[11px] uppercase tracking-[0.10em] sm:tracking-[0.14em] font-bold leading-tight"
               :style="{ color: 'rgb(var(--fg-muted))' }">
            {{ s.label }}
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- ============================ PROGRAMS ============================ -->
  <section id="programs" class="scroll-mt-header relative section-divider overflow-hidden"
           :style="{ background: 'rgb(var(--bg-soft))' }">
    <div class="container-x py-14 sm:py-20 lg:py-28">
      <!-- Section heading -->
      <div class="mb-7 sm:mb-10">
        <span class="eyebrow mb-3 sm:mb-4">Yo'nalishlar</span>
        <h2 class="display-3 mt-3">
          {{ filtered.length || 0 }} ta faol yo'nalish
        </h2>
        <p class="lead mt-3 sm:mt-4">
          Bakalavr va magistratura yo'nalishlari. Sizga mos yo'nalishni filtrlardan toping.
        </p>
      </div>

      <!-- Filter bar -->
      <div class="card p-2 mb-6 sm:mb-8 flex flex-col sm:flex-row gap-2"
           :style="{ boxShadow: 'var(--shadow-sm)' }">
        <div class="relative flex-1 min-w-0">
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
               class="absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none"
               :style="{ color: 'rgb(var(--fg-muted))' }">
            <circle cx="11" cy="11" r="8" /><path d="m21 21-4.3-4.3" />
          </svg>
          <input
            v-model="search"
            class="w-full h-11 pl-10 pr-4 rounded-xl text-sm bg-transparent border-0 focus:outline-none"
            :style="{ color: 'rgb(var(--fg))' }"
            placeholder="Yo'nalish nomini kiriting..."
          />
        </div>

        <!-- Level chips (desktop only) -->
        <div class="hidden sm:flex items-center gap-1 rounded-xl p-1"
             :style="{ background: 'rgb(var(--bg-soft))' }">
          <button
            class="px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all duration-200 whitespace-nowrap"
            :style="!levelFilter
              ? { background: 'rgb(var(--card))', color: 'rgb(var(--fg))', boxShadow: 'var(--shadow-sm)' }
              : { color: 'rgb(var(--fg-muted))' }"
            @click="levelFilter = ''"
          >Hammasi</button>
          <button
            v-for="l in levels" :key="l.id"
            class="px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all duration-200 whitespace-nowrap"
            :style="levelFilter === l.id
              ? { background: 'rgb(var(--card))', color: 'rgb(var(--fg))', boxShadow: 'var(--shadow-sm)' }
              : { color: 'rgb(var(--fg-muted))' }"
            @click="levelFilter = l.id"
          >{{ l.name }}</button>
        </div>

        <select
          v-model="branchFilter"
          class="h-11 px-3 rounded-xl text-sm border-0 focus:outline-none cursor-pointer min-w-0"
          :style="{ color: 'rgb(var(--fg))', background: 'rgb(var(--bg-soft))' }"
        >
          <option value="">Hamma filiallar</option>
          <option v-for="b in branches" :key="b.id" :value="b.id">{{ b.name }}</option>
        </select>

        <button v-if="search || branchFilter || levelFilter"
                class="btn-ghost btn-sm shrink-0" @click="clearFilters">
          Tozalash
        </button>
      </div>

      <!-- Mobile level pills -->
      <div class="sm:hidden mb-5 -mx-4 px-4 overflow-x-auto pb-1">
        <div class="flex items-center gap-2 w-max">
          <button
            class="px-4 py-1.5 rounded-full text-xs font-semibold whitespace-nowrap transition-all"
            :style="!levelFilter
              ? { background: 'rgb(var(--brand))', color: 'white' }
              : { background: 'rgb(var(--card))', color: 'rgb(var(--fg-soft))', border: '1px solid rgb(var(--border))' }"
            @click="levelFilter = ''"
          >Hammasi</button>
          <button
            v-for="l in levels" :key="l.id"
            class="px-4 py-1.5 rounded-full text-xs font-semibold whitespace-nowrap transition-all"
            :style="levelFilter === l.id
              ? { background: 'rgb(var(--brand))', color: 'white' }
              : { background: 'rgb(var(--card))', color: 'rgb(var(--fg-soft))', border: '1px solid rgb(var(--border))' }"
            @click="levelFilter = l.id"
          >{{ l.name }}</button>
        </div>
      </div>

      <!-- Skeleton -->
      <div v-if="loading" class="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <div v-for="i in 6" :key="`sk-${i}`" class="card p-6 space-y-5">
          <div class="flex items-start justify-between gap-3">
            <div class="w-12 h-12 rounded-xl skel"></div>
            <div class="space-y-1.5">
              <div class="h-3 w-16 skel ml-auto"></div>
              <div class="h-2 w-10 skel ml-auto"></div>
            </div>
          </div>
          <div class="space-y-2">
            <div class="h-5 w-full skel"></div>
            <div class="h-5 w-2/3 skel"></div>
          </div>
          <div class="h-3 w-1/2 skel"></div>
          <div class="flex items-center justify-between pt-4" :style="{ borderTop: '1px solid rgb(var(--border))' }">
            <div class="h-5 w-28 skel"></div>
            <div class="h-3 w-12 skel"></div>
          </div>
        </div>
      </div>

      <!-- Empty -->
      <div v-else-if="!filtered.length" class="card p-16 text-center">
        <p class="text-base mb-4" :style="{ color: 'rgb(var(--fg-soft))' }">Yo'nalish topilmadi</p>
        <button class="btn-secondary btn-sm" @click="clearFilters">Filterlarni tozalash</button>
      </div>

      <!-- Programs grid -->
      <div v-else class="grid sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
        <article
          v-for="(p, idx) in visiblePrograms" :key="p.id"
          class="card-hover p-5 sm:p-6 cursor-pointer group reveal-card overflow-hidden min-w-0"
          :style="{ animationDelay: `${idx * 50}ms` }"
          @click="openLeadModal(p.id)"
        >
          <div class="flex items-start justify-between gap-3 mb-4 sm:mb-5">
            <div class="grid place-items-center w-11 h-11 sm:w-12 sm:h-12 rounded-xl shrink-0 overflow-hidden transition-transform duration-300 group-hover:scale-105"
                 :style="{ background: tone(p.id).bg, color: tone(p.id).fg }">
              <img v-if="iconUrl(p.image_id)" :src="iconUrl(p.image_id)!" :alt="p.name"
                   class="w-full h-full object-cover" loading="lazy"
                   @error="(e) => ((e.target as HTMLImageElement).style.display='none')" />
              <svg v-else xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                <path d="M22 10v6M2 10l10-5 10 5-10 5z" />
                <path d="M6 12v5c3 3 9 3 12 0v-5" />
              </svg>
            </div>
            <div class="text-right min-w-0 flex-1">
              <div class="text-[10px] uppercase tracking-[0.10em] font-bold truncate"
                   :style="{ color: 'rgb(var(--fg-muted))' }">
                {{ p.education_level_name || 'Bakalavr' }}
              </div>
              <div class="text-[10px] font-mono mt-1 truncate" :style="{ color: 'rgb(var(--fg-muted))' }">{{ p.code }}</div>
            </div>
          </div>

          <h3 class="text-[16px] sm:text-[17px] font-bold mb-2 leading-snug min-h-[2.6rem] sm:min-h-[3rem] line-clamp-2"
              :style="{ color: 'rgb(var(--fg))' }">
            {{ p.name }}
          </h3>

          <div class="text-[12px] sm:text-[13px] mb-4 sm:mb-5 truncate" :style="{ color: 'rgb(var(--fg-muted))' }">
            <span v-if="p.branch_name">{{ p.branch_name }}</span>
            <span v-if="p.education_form_name"> · {{ p.education_form_name }}</span>
            <span v-if="p.study_duration_years"> · {{ p.study_duration_years }} yil</span>
          </div>

          <div class="flex items-center justify-between gap-2 pt-3.5 sm:pt-4"
               :style="{ borderTop: '1px solid rgb(var(--border))' }">
            <div class="text-[14px] sm:text-[15px] font-bold tabular-nums min-w-0 truncate" :style="{ color: 'rgb(var(--fg))' }">
              {{ fmtPrice(p.tuition_fee) }}
              <span class="text-[10px] sm:text-xs font-normal ml-0.5" :style="{ color: 'rgb(var(--fg-muted))' }">so'm/yil</span>
            </div>
            <span class="text-[12px] sm:text-[13px] font-semibold inline-flex items-center gap-1 transition-all duration-200 group-hover:gap-2 shrink-0"
                  :style="{ color: tone(p.id).fg }">
              Ariza
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <path d="M5 12h14M12 5l7 7-7 7" />
              </svg>
            </span>
          </div>
        </article>
      </div>

      <!-- The home section is a "preview" — every program lives on
           /programs with its own filters and shareable URL. Send curious
           visitors there instead of expanding inline. -->
      <div v-if="!loading && filtered.length" class="mt-10 text-center">
        <NuxtLink to="/programs" class="btn-secondary">
          Barcha {{ programs.length }} ta yo'nalishni ko'rish
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="ml-1">
            <path d="M5 12h14M12 5l7 7-7 7" />
          </svg>
        </NuxtLink>
      </div>
    </div>
  </section>

  <!-- ============================ ABOUT ============================ -->
  <section id="about" class="scroll-mt-header relative section-divider overflow-hidden">
    <div class="container-x py-14 sm:py-20 lg:py-28">
      <div class="grid lg:grid-cols-12 gap-8 lg:gap-16">
        <div class="lg:col-span-5">
          <span class="eyebrow mb-3 sm:mb-4">Universitet haqida</span>
          <h2 class="display-3 mt-3">
            Yangi avlod<br /><span class="gradient-text">Universiteti</span>
          </h2>
          <p class="lead mt-4 sm:mt-6">
            Qarshi shahridagi xususiy oliy ta'lim muassasasi. Bakalavr va magistratura
            yo'nalishlarida keng imkoniyatlar yaratuvchi zamonaviy universitet.
          </p>
          <div class="mt-6 sm:mt-8 flex flex-col xs:flex-row gap-3">
            <a :href="`${appUrl}/auth/login`" class="btn-primary w-full xs:w-auto">Ariza topshirish</a>
            <a href="#programs" class="btn-secondary w-full xs:w-auto">Yo'nalishlar</a>
          </div>
        </div>

        <div class="lg:col-span-7 space-y-3">
          <div v-for="(item, i) in [
            { title: 'Bakalavr va magistratura', desc: '4 yillik bakalavr va 2 yillik magistratura dasturlari, kunduzgi ta\'lim shaklida.' },
            { title: 'Xalqaro hamkorlik', desc: 'Janubiy Koreya, Yaponiya va boshqa davlatlar oliy ta\'lim muassasalari bilan ikki tomonlama almashinuv dasturlari.' },
            { title: 'Innovatsion ta\'lim', desc: 'Loyiha asosida o\'qitish, real biznes keyslar, 4 til ichida o\'qish imkoniyati.' },
          ]" :key="i" class="group card p-5 sm:p-6 flex items-start gap-4 sm:gap-5 transition-all duration-300 hover:border-[rgb(var(--brand)/0.3)]">
            <div class="grid place-items-center w-11 h-11 rounded-xl shrink-0 transition-transform duration-300 group-hover:scale-105"
                 :style="{ background: 'rgb(var(--brand) / 0.08)' }">
              <span class="text-sm font-bold tabular-nums tracking-tight"
                    :style="{ color: 'rgb(var(--brand))' }">
                0{{ i + 1 }}
              </span>
            </div>
            <div class="min-w-0 flex-1">
              <h3 class="font-bold text-[17px] mb-1.5 tracking-tight" :style="{ color: 'rgb(var(--fg))' }">{{ item.title }}</h3>
              <p class="text-sm leading-relaxed" :style="{ color: 'rgb(var(--fg-soft))' }">{{ item.desc }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- ============================ CONTACT ============================ -->
  <section id="contact" class="scroll-mt-header relative section-divider overflow-hidden"
           :style="{ background: 'rgb(var(--bg-soft))' }">
    <div class="container-x py-14 sm:py-20 lg:py-28">
      <div class="grid lg:grid-cols-12 gap-8 lg:gap-16">
        <div class="lg:col-span-5">
          <span class="eyebrow mb-3 sm:mb-4">Bog'lanish</span>
          <h2 class="display-3 mt-3">Aloqa</h2>
          <p class="lead mt-4 sm:mt-6">
            To'g'ridan-to'g'ri bog'laning yoki ariza qoldiring —
            qaytib o'zimiz aloqaga chiqamiz.
          </p>
          <p class="mt-4 inline-flex items-center gap-2 text-sm font-medium"
             :style="{ color: 'rgb(var(--fg-soft))' }">
            <span class="inline-block w-1.5 h-1.5 rounded-full" :style="{ background: 'rgb(var(--accent))' }"></span>
            Du–Sh, 9:00 — 18:00
          </p>

          <div class="mt-6 sm:mt-8">
            <button class="btn-accent btn-lg w-full xs:w-auto" @click="openLeadModal()">
              Ariza qoldirish
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <path d="M5 12h14M12 5l7 7-7 7" />
              </svg>
            </button>
          </div>
        </div>

        <div class="lg:col-span-7 space-y-2.5">
          <a v-for="c in [
            { type: 'tel',  href: 'tel:+998554061515',                                          label: 'Telefon',   value: '+998 55 406 15 15',                                tone: 'indigo' },
            { type: 'mail', href: 'mailto:info@xiuedu.uz',                                      label: 'Email',     value: 'info@xiuedu.uz',                                   tone: 'amber' },
            { type: 'tg',   href: 'https://t.me/xalqaro_innovatsion_universiteti',              label: 'Telegram',  value: '@xalqaro_innovatsion',                             tone: 'sky' },
            { type: 'map',  href: 'https://maps.google.com/?q=Qarshi+I.Karimov+ko%27chasi+405', label: 'Manzil',    value: 'Qarshi sh., I.Karimov ko‘chasi, 405-uy',           tone: 'rose' },
          ]" :key="c.type"
            :href="c.href" :target="c.type === 'tel' || c.type === 'mail' ? '_self' : '_blank'" rel="noopener"
            class="card-hover px-4 sm:px-5 py-3.5 sm:py-4 flex items-center gap-3 sm:gap-4 group">
            <span class="grid place-items-center w-10 h-10 sm:w-11 sm:h-11 rounded-xl shrink-0 transition-transform duration-300 group-hover:scale-105"
                  :style="{
                    background: c.tone === 'indigo' ? 'rgb(238 242 255)' :
                                c.tone === 'amber'  ? 'rgb(255 251 235)' :
                                c.tone === 'sky'    ? 'rgb(240 249 255)' :
                                                      'rgb(255 241 242)',
                    color:      c.tone === 'indigo' ? 'rgb(67 56 202)' :
                                c.tone === 'amber'  ? 'rgb(180 83 9)' :
                                c.tone === 'sky'    ? 'rgb(7 89 133)' :
                                                      'rgb(190 18 60)',
                  }">
              <svg v-if="c.type === 'tel'" xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.13.96.37 1.9.72 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.91.35 1.85.59 2.81.72A2 2 0 0 1 22 16.92z" />
              </svg>
              <svg v-else-if="c.type === 'mail'" xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z M22 6 12 13 2 6" />
              </svg>
              <svg v-else-if="c.type === 'tg'" xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                <path d="M22.05 1.577c-.393-.016-.784.08-1.117.235-.484.186-21.79 8.413-22.62 8.711-.83.298-.83 1.27 0 1.568.32.115 4.286 1.659 5.95 2.301a1 1 0 0 0 .708-.005l9.66-3.836c.295-.117.566.158.404.42L9.05 18.92c-.123.158-.07.39.106.477l9.07 4.45c.38.186.838-.012.99-.42L23.86 2.96c.21-.563-.282-1.404-.81-1.382z" />
              </svg>
              <svg v-else xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" /><circle cx="12" cy="10" r="3" />
              </svg>
            </span>
            <div class="min-w-0 flex-1 overflow-hidden">
              <div class="text-[10px] uppercase tracking-[0.10em] font-bold mb-0.5"
                   :style="{ color: 'rgb(var(--fg-muted))' }">
                {{ c.label }}
              </div>
              <div class="font-semibold text-[14px] sm:text-[15px] truncate transition-colors group-hover:text-[rgb(var(--brand))]"
                   :style="{ color: 'rgb(var(--fg))' }">
                {{ c.value }}
              </div>
            </div>
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
                 class="shrink-0 opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0 transition-all duration-200"
                 :style="{ color: 'rgb(var(--fg-muted))' }">
              <path d="M5 12h14M12 5l7 7-7 7" />
            </svg>
          </a>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
/* =================== Hero animated background =================== */
.hero-blob {
  position: absolute;
  border-radius: 9999px;
  filter: blur(72px);
  pointer-events: none;
  z-index: -10;
  will-change: transform;
}
.hero-blob-a {
  top: -120px; left: -120px;
  width: 360px; height: 360px;
  animation: hero-drift-a 22s ease-in-out infinite;
}
.hero-blob-b {
  bottom: -120px; right: -120px;
  width: 400px; height: 400px;
  animation: hero-drift-b 26s ease-in-out infinite;
}
.hero-blob-c {
  top: 30%; left: 50%;
  width: 300px; height: 300px;
  margin-left: -150px;
  opacity: 0.7;
  animation: hero-drift-c 28s ease-in-out infinite;
}
@media (min-width: 640px) {
  .hero-blob-a { top: -160px; left: -160px; width: 640px; height: 640px; }
  .hero-blob-b { bottom: -200px; right: -160px; width: 720px; height: 720px; }
  .hero-blob-c { width: 480px; height: 480px; margin-left: -240px; }
}
@keyframes hero-drift-a {
  0%, 100% { transform: translate(0, 0) scale(1); }
  50%      { transform: translate(120px, 80px) scale(1.1); }
}
@keyframes hero-drift-b {
  0%, 100% { transform: translate(0, 0) scale(1); }
  50%      { transform: translate(-100px, -60px) scale(1.05); }
}
@keyframes hero-drift-c {
  0%, 100% { transform: translate(-50%, 0) scale(1); }
  50%      { transform: translate(-30%, -40px) scale(1.15); }
}

/* Slowly rotating conic ring */
.hero-conic {
  position: absolute;
  top: 0; left: 50%;
  width: 800px; height: 800px;
  margin-left: -400px; margin-top: -400px;
  border-radius: 9999px;
  pointer-events: none;
  z-index: -10;
  background: conic-gradient(
    from 0deg,
    transparent 0deg,
    rgb(var(--brand) / 0.15) 60deg,
    transparent 120deg,
    rgb(var(--accent) / 0.12) 200deg,
    transparent 260deg,
    rgb(var(--brand) / 0.15) 320deg,
    transparent 360deg
  );
  filter: blur(48px);
  animation: hero-spin 60s linear infinite;
  opacity: 0.65;
}
@media (min-width: 640px) {
  .hero-conic { width: 1200px; height: 1200px; margin-left: -600px; margin-top: -600px; }
}
@keyframes hero-spin {
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
}

/* Top hairline shimmer */
.hero-shimmer {
  position: absolute;
  top: 0; left: 0;
  width: 200%;
  height: 100%;
  animation: hero-shimmer 6s ease-in-out infinite;
}
@keyframes hero-shimmer {
  0%   { transform: translateX(-50%); }
  100% { transform: translateX(0); }
}

/* Pulsing eyebrow dot */
.hero-pulse {
  animation: hero-pulse 2s ease-in-out infinite;
}
@keyframes hero-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgb(var(--accent) / 0.5); }
  50%      { box-shadow: 0 0 0 6px rgb(var(--accent) / 0); }
}

/* Animated gradient text */
.gradient-text-anim {
  background: linear-gradient(
    100deg,
    rgb(var(--brand-deep)) 0%,
    rgb(var(--brand)) 30%,
    rgb(var(--accent)) 55%,
    rgb(var(--brand)) 80%,
    rgb(var(--brand-deep)) 100%
  );
  background-size: 200% auto;
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  animation: gradient-pan 8s linear infinite;
}
@keyframes gradient-pan {
  0%   { background-position: 0% center; }
  100% { background-position: 200% center; }
}

/* Hero entrance */
.hero-fade {
  opacity: 0;
  transform: translateY(14px);
  animation: hero-fade-in 700ms cubic-bezier(0.22, 1, 0.36, 1) forwards;
}
@keyframes hero-fade-in {
  to { opacity: 1; transform: translateY(0); }
}

/* Card reveal stagger */
.reveal-card {
  opacity: 0;
  transform: translateY(12px);
  animation: card-reveal 600ms cubic-bezier(0.22, 1, 0.36, 1) forwards;
}
@keyframes card-reveal {
  to { opacity: 1; transform: translateY(0); }
}

@media (prefers-reduced-motion: reduce) {
  .hero-blob, .hero-conic, .hero-shimmer, .hero-pulse,
  .gradient-text-anim, .hero-fade, .reveal-card {
    animation: none !important;
  }
  .hero-fade, .reveal-card { opacity: 1; transform: none; }
}
</style>
