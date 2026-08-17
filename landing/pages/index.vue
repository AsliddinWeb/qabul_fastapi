<script setup lang="ts">
import { onBeforeUnmount } from 'vue'

const config = useRuntimeConfig()
const apiBase = (config.public as any).apiBaseUrl || '/api/v1'
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

// Soha rangi (logotip spektri) — yo'nalish nomidan aniqlanadi, aks holda id hash.
const HUES = ['blue', 'green', 'gold', 'magenta', 'crimson', 'indigo']
function hueOf(p: Program): string {
  const n = (p.name || '').toLowerCase()
  if (n.includes('axborot') || n.includes('kompyuter') || n.includes('dasturiy') || n.includes('texnolog')) return 'blue'
  if (n.includes('boshlang')) return 'green'
  if (n.includes('buxgalter') || n.includes('audit') || n.includes('moliya')) return 'gold'
  if (n.includes('filolog') || n.includes('til') || n.includes('tarjima')) return 'magenta'
  if (n.includes('iqtisod') || n.includes('menejment') || n.includes('marketing')) return 'crimson'
  let h = 0
  for (let i = 0; i < (p.id || '').length; i++) h = (h * 31 + p.id.charCodeAt(i)) | 0
  return HUES[Math.abs(h) % HUES.length]
}

const stats = [
  { value: '8000+', label: 'Iqtidorli talabalar' },
  { value: '180+',  label: "Ilmiy darajali o'qituvchilar" },
  { value: '20+',   label: "Bakalavr yo'nalishlari" },
  { value: '4+',    label: "Magistratura yo'nalishlari" },
]
const statList = stats.map(s => {
  const m = String(s.value).match(/^(\d+)(.*)$/)
  return { n: m ? parseInt(m[1], 10) : 0, suffix: m ? m[2] : '', label: s.label }
})

// ---- Motion: reveal + count-up + oqim chizig'i + karta yorug'ligi ----
let observers: IntersectionObserver[] = []
function countUp(el: HTMLElement) {
  const t = parseInt(el.dataset.count || '0', 10)
  const sfx = el.dataset.suffix || ''
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches
  if (reduce || !t) { el.textContent = t + sfx; return }
  let t0: number | null = null
  const dur = 1400
  function fr(ts: number) {
    if (t0 === null) t0 = ts
    const p = Math.min((ts - t0) / dur, 1)
    const e = 1 - Math.pow(1 - p, 3)
    el.textContent = Math.round(t * e) + sfx
    if (p < 1) requestAnimationFrame(fr)
  }
  requestAnimationFrame(fr)
}

onMounted(() => {
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches
  const rvEls = document.querySelectorAll('.xrd .rv')
  const counters = document.querySelectorAll<HTMLElement>('.xrd [data-count]')
  const flow = document.querySelector('.xrd .flow')

  if (!('IntersectionObserver' in window)) {
    rvEls.forEach(e => e.classList.add('in'))
    counters.forEach(countUp)
    flow?.classList.add('in')
  } else {
    const io = new IntersectionObserver((ents, obs) => {
      ents.forEach(en => { if (en.isIntersecting) { en.target.classList.add('in'); obs.unobserve(en.target) } })
    }, { threshold: 0.16, rootMargin: '0px 0px -8% 0px' })
    rvEls.forEach(e => io.observe(e)); observers.push(io)

    const cio = new IntersectionObserver((ents, obs) => {
      ents.forEach(en => { if (en.isIntersecting) { countUp(en.target as HTMLElement); obs.unobserve(en.target) } })
    }, { threshold: 0.5 })
    counters.forEach(e => cio.observe(e)); observers.push(cio)

    if (flow) {
      const fio = new IntersectionObserver((ents, obs) => {
        ents.forEach(en => { if (en.isIntersecting) { en.target.classList.add('in'); obs.unobserve(en.target) } })
      }, { threshold: 0.35 })
      fio.observe(flow); observers.push(fio)
    }
  }

  // Kartada kursor ortidan yuruvchi yorug'lik — delegatsiya (dinamik kartalar uchun ham)
  if (matchMedia('(hover: hover)').matches && !reduce) {
    const wrap = document.querySelector<HTMLElement>('.xrd .progs')
    wrap?.addEventListener('pointermove', (e) => {
      const card = (e.target as HTMLElement).closest<HTMLElement>('.prog')
      if (!card) return
      const r = card.getBoundingClientRect()
      card.style.setProperty('--mx', ((e.clientX - r.left) / r.width) * 100 + '%')
      card.style.setProperty('--my', ((e.clientY - r.top) / r.height) * 100 + '%')
    })
  }
})
onBeforeUnmount(() => { observers.forEach(o => o.disconnect()) })
</script>

<template>
  <div class="xrd">
    <span id="home"></span>

    <!-- ===================== 1. HERO ===================== -->
    <section class="sec hero">
      <div class="aurora" aria-hidden="true">
        <div class="blob blob--1"></div><div class="blob blob--2"></div>
        <div class="blob blob--3"></div><div class="blob blob--4"></div>
      </div>

      <div class="shell hero__grid">
        <div>
          <span class="badge"><i class="ph-fill ph-star" aria-hidden="true"></i> Qabul 2026 — 2027 ochiq</span>
          <h1>
            <span class="w"><i style="--d:.18s">Xalqaro</i></span>
            <span class="w"><i style="--d:.28s"><em>Innovatsion</em></i></span>
            <span class="w"><i style="--d:.38s">Universiteti</i></span>
          </h1>
          <p class="hero__sub">
            Bakalavr va magistratura yo'nalishlari. Xalqaro almashinuv dasturlari.
            Qarshi shahridagi zamonaviy xususiy universitet.
          </p>
          <div class="hero__cta">
            <button class="btn btn--primary btn--lg" type="button" @click="openLeadModal()">
              Ariza qoldirish <i class="ph ph-arrow-right" aria-hidden="true"></i>
            </button>
            <a class="btn btn--ghost btn--lg" href="#programs">Yo'nalishlar</a>
            <a class="btn btn--ghost btn--lg" href="https://yotoqxona.xiuedu.uz/" target="_blank" rel="noopener noreferrer">
              <i class="ph ph-bed" aria-hidden="true"></i> Yotoqxona tizimi <i class="ph ph-arrow-up-right" aria-hidden="true"></i>
            </a>
          </div>
        </div>

        <div class="hero__media">
          <!-- TODO: universitetning haqiqiy fotosurati (1200x1250) -->
          <div class="hero__frame">
            <img src="https://picsum.photos/seed/xiu-qarshi-campus/1200/1250" alt="Universitet talabalari kampusda" fetchpriority="high" width="1200" height="1250" />
          </div>
          <!-- TODO: laboratoriya/auditoriya fotosurati (700x740) -->
          <div class="hero__inset">
            <img src="https://picsum.photos/seed/xiu-lecture-hall/700/740" alt="Zamonaviy auditoriya" loading="lazy" width="700" height="740" />
          </div>
          <div class="hero__stat">
            <b class="mono">8000+</b>
            <span>Iqtidorli talabalar</span>
          </div>
        </div>
      </div>
    </section>

    <!-- ===================== 2. STATISTIKA ===================== -->
    <section class="stats">
      <div class="shell">
        <div class="stats__row">
          <div v-for="(s, i) in statList" :key="i" class="stat rv" :style="{ '--i': i }">
            <b class="mono" :data-count="s.n" :data-suffix="s.suffix">{{ s.n }}{{ s.suffix }}</b>
            <span>{{ s.label }}</span>
          </div>
        </div>
      </div>
    </section>

    <!-- ===================== 3. YO'NALISHLAR ===================== -->
    <section class="sec" id="programs">
      <div class="shell">
        <div class="sec__head rv">
          <span class="eyebrow">Yo'nalishlar</span>
          <h2>{{ filtered.length || 0 }} ta faol yo'nalish</h2>
          <p>Bakalavr va magistratura yo'nalishlari. Sizga mos yo'nalishni filtrlardan toping.</p>
        </div>

        <div class="filters rv" role="group" aria-label="Yo'nalishlarni filtrlash">
          <div class="search">
            <i class="ph ph-funnel-simple" aria-hidden="true"></i>
            <input v-model="search" type="text" placeholder="Yo'nalish nomini kiriting..." aria-label="Qidiruv" />
          </div>
          <button class="chip" type="button" :aria-pressed="!levelFilter" @click="levelFilter = ''">Hammasi</button>
          <button v-for="l in levels" :key="l.id" class="chip" type="button"
                  :aria-pressed="levelFilter === l.id" @click="levelFilter = l.id">{{ l.name }}</button>
          <select v-if="branches.length" class="select" v-model="branchFilter" aria-label="Filial">
            <option value="">Hamma filiallar</option>
            <option v-for="b in branches" :key="b.id" :value="b.id">{{ b.name }}</option>
          </select>
        </div>

        <!-- Skeleton -->
        <div v-if="loading" class="progs">
          <div v-for="i in 6" :key="`sk-${i}`" class="prog" style="cursor:default">
            <div class="prog__top"><span class="skel" style="width:70px;height:14px"></span><span class="skel" style="width:44px;height:12px"></span></div>
            <span class="skel" style="width:100%;height:20px"></span>
            <span class="skel" style="width:60%;height:14px"></span>
            <div class="prog__foot"><span class="skel" style="width:110px;height:18px"></span><span class="skel" style="width:44px;height:14px"></span></div>
          </div>
        </div>

        <!-- Empty -->
        <div v-else-if="!filtered.length" class="empty">
          <i class="ph ph-funnel-simple" aria-hidden="true"></i>
          <b>Bu filtr bo'yicha yo'nalish topilmadi</b>
          <p>Boshqa filtrni tanlang yoki filtrlarni tozalang.</p>
          <div style="margin-top:1.25rem;display:flex;justify-content:center">
            <button class="btn btn--ghost" type="button" @click="clearFilters">Filtrlarni tozalash</button>
          </div>
        </div>

        <!-- Grid (filtr o'zgarganda FLIP bilan siljiydi) -->
        <TransitionGroup v-else name="flip" tag="div" class="progs">
          <article v-for="p in visiblePrograms" :key="p.id" class="prog" :data-hue="hueOf(p)"
                   tabindex="0" role="button" :aria-label="`${p.name} — ariza qoldirish`"
                   @click="openLeadModal(p.id)" @keydown.enter.prevent="openLeadModal(p.id)" @keydown.space.prevent="openLeadModal(p.id)">
            <div class="prog__top">
              <span class="prog__deg">{{ p.education_level_name || 'Bakalavr' }}</span>
              <span class="prog__code mono">{{ p.code }}</span>
            </div>
            <h3>{{ p.name }}</h3>
            <p class="prog__meta">
              <span v-if="p.branch_name">{{ p.branch_name }}</span>
              <span v-if="p.education_form_name"><i class="ph ph-sun-horizon" aria-hidden="true"></i>{{ p.education_form_name }}</span>
              <span v-if="p.study_duration_years"><i class="ph ph-calendar-blank" aria-hidden="true"></i>{{ p.study_duration_years }} yil</span>
            </p>
            <div class="prog__foot">
              <p class="prog__price"><b class="mono">{{ fmtPrice(p.tuition_fee) }}</b> <span>so'm/yil</span></p>
              <span class="prog__link">Ariza <i class="ph ph-arrow-right" aria-hidden="true"></i></span>
            </div>
          </article>
        </TransitionGroup>

        <div v-if="!loading && filtered.length > visibleCount" class="progs__more rv">
          <button class="btn btn--ghost btn--lg" type="button" @click="visibleCount += 9">
            Yana yo'nalishlarni ko'rish <i class="ph ph-arrow-right" aria-hidden="true"></i>
          </button>
        </div>
        <div v-else-if="!loading && filtered.length" class="progs__more rv">
          <a class="btn btn--ghost btn--lg" href="/programs">Barcha yo'nalishlarni ko'rish <i class="ph ph-arrow-right" aria-hidden="true"></i></a>
        </div>
      </div>
    </section>

    <!-- ===================== 4. UNIVERSITET (bento) ===================== -->
    <section class="sec" id="about">
      <div class="shell">
        <div class="sec__head rv">
          <span class="eyebrow">Universitet haqida</span>
          <h2>Xalqaro innovatsion universiteti</h2>
          <p>Qarshi shahridagi nodavlat oliy ta'lim muassasasi. Bakalavr va magistratura yo'nalishlarida zamonaviy va innovatsion ta'lim beruvchi universitet.</p>
        </div>

        <div class="bento">
          <!-- TODO: universitet binosi/kutubxona fotosurati (1000x700) -->
          <div class="cell cell--photo rv">
            <img src="https://picsum.photos/seed/xiu-library-building/1000/700" alt="Universitet o'quv binosi" loading="lazy" width="1000" height="700" />
          </div>
          <div class="cell cell--a rv" :style="{ '--i': 1 }">
            <div class="cell__ico"><i class="ph ph-graduation-cap" aria-hidden="true"></i></div>
            <h3>Bakalavr va magistratura</h3>
            <p>4 yillik bakalavr va 2 yillik magistratura dasturlari, kunduzgi ta'lim shaklida.</p>
          </div>
          <div class="cell cell--b rv" :style="{ '--i': 2 }">
            <div class="cell__ico"><i class="ph ph-globe-hemisphere-east" aria-hidden="true"></i></div>
            <h3>Xalqaro hamkorlik</h3>
            <p>Rossiya, Qozog'iston va boshqa davlatlar oliy ta'lim muassasalari bilan ikki tomonlama almashinuv dasturlari.</p>
          </div>
          <div class="cell cell--c rv" :style="{ '--i': 3 }">
            <div class="cell__ico"><i class="ph ph-lightbulb-filament" aria-hidden="true"></i></div>
            <h3>Dual ta'lim</h3>
            <p><a href="https://spromaxplast.uz/" target="_blank" rel="noopener noreferrer" style="color:var(--t-magenta);font-weight:600;text-decoration:underline">S Promax Plast Premium zavodi bilan hamkorlikda dual ta'lim yo'lga qo'yilgan</a> — talaba o'qish bilan birga real ishlab chiqarishda tajriba oladi.</p>
          </div>
        </div>
      </div>
    </section>

    <!-- ===================== 5. QABUL TARTIBI ===================== -->
    <section class="sec" id="qabul">
      <div class="shell">
        <div class="sec__head rv">
          <span class="eyebrow">Qabul tartibi</span>
          <h2>Qabul qanday o'tadi</h2>
          <p>Ariza qoldirganingizdan keyin qabul komissiyasi o'zi bog'lanadi va jarayonni oxirigacha kuzatib boradi.</p>
        </div>

        <div class="flow">
          <div class="flow__rail" aria-hidden="true"></div>
          <div class="step rv">
            <div class="step__dot"><i class="ph ph-cursor-click" aria-hidden="true"></i></div>
            <h3>Ariza qoldiring</h3>
            <p>Formani to'ldiring yoki qabul komissiyasiga telefon qiling.</p>
          </div>
          <div class="step rv" :style="{ '--i': 1 }">
            <div class="step__dot"><i class="ph ph-files" aria-hidden="true"></i></div>
            <h3>Hujjatlarni topshiring</h3>
            <p>Pasport, ma'lumotnoma va o'rta ta'lim hujjatingiz nusxasi.</p>
          </div>
          <div class="step rv" :style="{ '--i': 2 }">
            <div class="step__dot"><i class="ph ph-chats-circle" aria-hidden="true"></i></div>
            <h3>Suhbatdan o'ting</h3>
            <p>Tanlagan yo'nalishingiz bo'yicha qisqa suhbat va yo'naltirish.</p>
          </div>
          <div class="step rv" :style="{ '--i': 3 }">
            <div class="step__dot"><i class="ph ph-signature" aria-hidden="true"></i></div>
            <h3>Shartnoma imzolang</h3>
            <p>To'lov shartlari kelishiladi va siz talabalikka qabul qilinasiz.</p>
          </div>
        </div>
      </div>
    </section>

    <!-- ===================== 6. XALQARO HAMKORLIK ===================== -->
    <section class="sec" id="hamkorlik">
      <div class="shell">
        <div class="band rv">
          <!-- TODO: xalqaro almashinuv fotosurati (1800x900) -->
          <div class="band__img"><img src="https://picsum.photos/seed/xiu-international/1800/900" alt="Xalqaro almashinuv dasturi" loading="lazy" width="1800" height="900" /></div>
          <div class="band__scrim" aria-hidden="true"></div>
          <div class="band__in">
            <h2>Diplomni bu yerda oling, tajribani chet elda va ishlab chiqarishda</h2>
            <p>Rossiya, Qozog'iston va boshqa davlatlar oliy ta'lim muassasalari bilan ikki tomonlama almashinuv dasturlari, hamda <strong>S Promax Plast Premium (PVC panel zavodi)</strong> bilan hamkorlikda dual ta'lim yo'lga qo'yilgan.</p>
            <div class="band__countries">
              <span class="country"><i class="ph ph-map-pin" aria-hidden="true"></i>Rossiya</span>
              <span class="country"><i class="ph ph-map-pin" aria-hidden="true"></i>Qozog'iston</span>
              <span class="country"><i class="ph ph-globe-hemisphere-east" aria-hidden="true"></i>Boshqa hamkor davlatlar</span>
              <a class="country" href="https://spromaxplast.uz/" target="_blank" rel="noopener noreferrer"><i class="ph ph-arrow-up-right" aria-hidden="true"></i>S Promax Plast — PVC panel zavodi</a>
            </div>
            <div class="band__cta">
              <button class="btn btn--onphoto btn--lg" type="button" @click="openLeadModal()">
                Dastur haqida so'rash <i class="ph ph-arrow-right" aria-hidden="true"></i>
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ===================== 7. ALOQA ===================== -->
    <section class="sec" id="contact">
      <div class="shell">
        <div class="sec__head rv">
          <span class="eyebrow">Bog'lanish</span>
          <h2>Aloqa</h2>
          <p>Ariza qoldiring, qabul komissiyasi ish vaqti davomida o'zi aloqaga chiqadi.</p>
        </div>

        <div class="contact">
          <div class="info rv">
            <a class="info__item" href="tel:+998554061515">
              <div class="info__ico"><i class="ph ph-phone-call" aria-hidden="true"></i></div>
              <div><span>Telefon</span><b class="mono">+998 55 406 15 15</b></div>
            </a>
            <a class="info__item" href="https://www.instagram.com/xiu_edu.uz/" target="_blank" rel="noopener noreferrer">
              <div class="info__ico"><i class="ph ph-instagram-logo" aria-hidden="true"></i></div>
              <div><span>Instagram</span><b>@xiu_edu.uz</b></div>
            </a>
            <a class="info__item" href="https://t.me/xalqaro_innovatsion_universiteti" target="_blank" rel="noopener noreferrer">
              <div class="info__ico"><i class="ph ph-telegram-logo" aria-hidden="true"></i></div>
              <div><span>Telegram</span><b>@xalqaro_innovatsion_universiteti</b></div>
            </a>
            <div class="info__item">
              <div class="info__ico"><i class="ph ph-map-pin-line" aria-hidden="true"></i></div>
              <div><span>Manzil</span><p>Qarshi shahri, I. Karimov ko'chasi, 405-uy</p></div>
            </div>
          </div>

          <div class="rv" :style="{ '--i': 1 }">
            <div class="cta-card">
              <h3>Ariza qoldirish</h3>
              <p>Formani to'ldiring — qabul komissiyasi ish vaqti davomida siz bilan bog'lanadi.</p>
              <button class="btn btn--primary btn--lg" type="button" @click="openLeadModal()">
                Ariza qoldirish <i class="ph ph-arrow-right" aria-hidden="true"></i>
              </button>
            </div>
            <p class="hours"><i class="ph ph-clock" aria-hidden="true"></i> Ish vaqti: dushanbadan shanbagacha, 9:00 dan 18:00 gacha</p>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>
