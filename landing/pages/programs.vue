<script setup lang="ts">
const config = useRuntimeConfig()
const apiBase = (config.public as any).apiBaseUrl || '/api/v1'
const { open: openLeadModal } = useLeadModal()

useSeoMeta({
  title: "Yo'nalishlar — Xalqaro Innovatsion Universiteti",
  description: "XIU bakalavr va magistratura yo'nalishlarining to'liq ro'yxati. Filial, ta'lim darajasi va shakli bo'yicha filtrlang.",
})

// Mirrors the home-page Program shape so the same card markup works
// here. The standalone page exists because the home section caps the
// visible cards (visibleCount=9, "Yana N ta ko'rsatish"); deep-linking
// or scanning the whole catalogue needs the full list at once.
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
const formFilter = ref('')

// Sync filters to the URL query so back/forward + sharing work.
const route = useRoute()
const router = useRouter()

onMounted(async () => {
  // Hydrate from query string if present.
  search.value      = (route.query.q as string) || ''
  branchFilter.value = (route.query.branch as string) || ''
  levelFilter.value  = (route.query.level as string) || ''
  formFilter.value   = (route.query.form as string) || ''

  try {
    const [progRes, branchRes] = await Promise.all([
      fetch(`${apiBase}/programs/programs?active_only=true`).then(r => r.ok ? r.json() : []),
      fetch(`${apiBase}/programs/branches?active_only=true`).then(r => r.ok ? r.json() : []),
    ])
    programs.value = progRes
    branches.value = branchRes
  } catch { /* ignore */ }
  finally { loading.value = false }
})

watch([search, branchFilter, levelFilter, formFilter], (vals) => {
  const [q, b, l, f] = vals
  router.replace({
    query: {
      ...(q ? { q } : {}),
      ...(b ? { branch: b } : {}),
      ...(l ? { level: l } : {}),
      ...(f ? { form: f } : {}),
    },
  })
})

const levels = computed(() => {
  const m = new Map<string, string>()
  for (const p of programs.value) {
    if (p.education_level_id && p.education_level_name) m.set(p.education_level_id, p.education_level_name)
  }
  return Array.from(m.entries()).map(([id, name]) => ({ id, name }))
})

const forms = computed(() => {
  const m = new Map<string, string>()
  for (const p of programs.value) {
    if (p.education_form_id && p.education_form_name) m.set(p.education_form_id, p.education_form_name)
  }
  return Array.from(m.entries()).map(([id, name]) => ({ id, name }))
})

const filtered = computed(() => {
  const q = search.value.trim().toLowerCase()
  return programs.value.filter(p => {
    if (branchFilter.value && p.branch_id !== branchFilter.value) return false
    if (levelFilter.value && p.education_level_id !== levelFilter.value) return false
    if (formFilter.value && p.education_form_id !== formFilter.value) return false
    if (q && !p.name.toLowerCase().includes(q) && !(p.code || '').toLowerCase().includes(q)) return false
    return true
  })
})

const hasFilters = computed(() => !!(search.value || branchFilter.value || levelFilter.value || formFilter.value))

function fmtPrice(v?: number | string): string {
  if (!v) return '—'
  const n = typeof v === 'string' ? parseFloat(v) : v
  if (!n || isNaN(n)) return '—'
  return Number(n).toLocaleString('uz-UZ').replace(/,/g, ' ')
}
function clearFilters() {
  search.value = ''
  branchFilter.value = ''
  levelFilter.value = ''
  formFilter.value = ''
}

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
</script>

<template>
  <main>
    <!-- Hero strip — slimmer than home, just orients the visitor -->
    <section class="relative overflow-hidden border-b"
             :style="{ background: 'rgb(var(--bg-soft))', borderColor: 'rgb(var(--border))' }">
      <div class="container-x py-10 sm:py-14">
        <div class="flex items-center gap-2 text-xs mb-3" :style="{ color: 'rgb(var(--fg-muted))' }">
          <NuxtLink to="/" class="hover:underline">Bosh sahifa</NuxtLink>
          <span>·</span>
          <span :style="{ color: 'rgb(var(--fg))' }">Yo'nalishlar</span>
        </div>
        <span class="eyebrow mb-2 sm:mb-3">Yo'nalishlar katalogi</span>
        <h1 class="display-2 mt-2">
          {{ loading ? '...' : programs.length }} ta faol yo'nalish
        </h1>
        <p class="lead mt-3 sm:mt-4 max-w-2xl">
          Bakalavr, magistratura. Kunduzgi, sirtqi va kechki ta'lim shakllari. Filtrlardan foydalanib mos yo'nalishni tanlang.
        </p>
      </div>
    </section>

    <!-- Filters + list -->
    <section :style="{ background: 'rgb(var(--bg))' }">
      <div class="container-x py-8 sm:py-12">

        <!-- Filter bar -->
        <div class="card p-2 mb-5 sm:mb-6 flex flex-col sm:flex-row gap-2"
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

          <!-- Level chips (desktop) -->
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

          <select
            v-model="formFilter"
            class="h-11 px-3 rounded-xl text-sm border-0 focus:outline-none cursor-pointer min-w-0"
            :style="{ color: 'rgb(var(--fg))', background: 'rgb(var(--bg-soft))' }"
          >
            <option value="">Hamma shakllar</option>
            <option v-for="f in forms" :key="f.id" :value="f.id">{{ f.name }}</option>
          </select>

          <button v-if="hasFilters" class="btn-ghost btn-sm shrink-0" @click="clearFilters">
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

        <!-- Results count line -->
        <div v-if="!loading" class="flex items-center justify-between mb-4 sm:mb-5 text-xs"
             :style="{ color: 'rgb(var(--fg-muted))' }">
          <span>
            <strong :style="{ color: 'rgb(var(--fg))' }" class="tabular-nums">{{ filtered.length }}</strong>
            ta yo'nalish topildi<template v-if="hasFilters"> · filtrlar bo'yicha</template>
          </span>
          <span v-if="hasFilters" class="hidden sm:inline">{{ programs.length }} ta jami</span>
        </div>

        <!-- Skeleton -->
        <div v-if="loading" class="grid sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
          <div v-for="i in 9" :key="`sk-${i}`" class="card p-6 space-y-5">
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
          <button v-if="hasFilters" class="btn-secondary btn-sm" @click="clearFilters">
            Filterlarni tozalash
          </button>
        </div>

        <!-- Full grid — every filtered result, no slice. -->
        <div v-else class="grid sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
          <article
            v-for="(p, idx) in filtered" :key="p.id"
            class="card-hover p-5 sm:p-6 cursor-pointer group reveal-card overflow-hidden min-w-0"
            :style="{ animationDelay: `${Math.min(idx, 12) * 30}ms` }"
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
      </div>
    </section>
  </main>
</template>
