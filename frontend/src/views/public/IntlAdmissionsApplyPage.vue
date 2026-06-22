<script setup lang="ts">
/**
 * International Admissions — public application form.
 *
 * Lives at /app/intl-apply (with a friendly /intl alias from nginx).
 * No auth required — submits multipart form-data directly to
 * /api/v1/international-admissions/apply with the six-layer
 * anti-spam stack on the server.
 *
 * EN / RU / UZ in-page; no i18n framework dependency to keep this
 * route as light as possible for first-time visitors.
 */
import { computed, onMounted, reactive, ref } from 'vue'
import { Globe, FileText, Image as ImageIcon, IdCard, Check, AlertTriangle } from 'lucide-vue-next'
import { http } from '@/api/http'

type Lang = 'en' | 'ru' | 'uz'

interface FormState {
  full_name: string
  country: string
  passport_number: string
  birth_date: string
  phone: string
  email: string
  program: 'Bachelor' | 'Master' | ''
  faculty_text: string
  faculty_code: string
  // Honeypot — display:none; must arrive empty to the server.
  website: string
  passport_file: File | null
  diploma_file: File | null
  photo_file: File | null
}

const lang = ref<Lang>('en')
const sessionToken = ref<string | null>(null)
const submitting = ref(false)
const submitted = ref<{ ref_number: string } | null>(null)
const errorMsg = ref<string | null>(null)

const form = reactive<FormState>({
  full_name: '', country: '', passport_number: '', birth_date: '',
  phone: '', email: '', program: '', faculty_text: '', faculty_code: '',
  website: '',
  passport_file: null, diploma_file: null, photo_file: null,
})

// ===== i18n =====
const STRINGS: Record<Lang, Record<string, string>> = {
  en: {
    brand: "International Innovation University", brandSub: "International Admissions Office",
    heroH: "Study in Uzbekistan at XIU",
    heroP: "Submit your application for Bachelor's and Master's programs. Our admissions team will review your documents and guide you through every step — from offer letter to visa invitation.",
    s1: "1 · Apply", s2: "2 · Document review", s3: "3 · Conditional Offer",
    s4: "4 · Contract", s5: "5 · Payment 30–50%", s6: "6 · Admission + Invitation",
    formH: "Application Form",
    formSub: "All fields marked with * are required. Uploads accept PDF, JPG or PNG.",
    secPersonal: "Personal Information", secProgram: "Program Choice", secDocs: "Documents",
    fName: "Full Name", fCountry: "Country", fPassport: "Passport Number",
    fDob: "Date of Birth", fPhone: "Phone (WhatsApp)", fEmail: "Email",
    fProgram: "Program", fFaculty: "Faculty",
    bachelor: "Bachelor", master: "Master", choose: "— Select —",
    fUpPass: "Passport", fUpDip: "Diploma / Certificate", fUpPhoto: "Photo (3x4)",
    upHint: "Click to upload (PDF / JPG / PNG)", submit: "Submit Application",
    fac1: "Information Technologies", fac2: "Business & Economics", fac3: "Engineering",
    fac4: "Medicine", fac5: "Law", fac6: "International Relations",
    fac7: "Philology & Languages", fac8: "Architecture & Design",
    okH: "Application submitted!",
    okP: "Thank you. Your application has been received by the XIU admissions office. We will contact you on WhatsApp and email.",
    another: "Submit another",
    errGeneric: "Unable to submit. Please try again in a moment.",
    errSubmitting: "Submitting…",
    footnote: "© XIU International Admissions Office",
  },
  ru: {
    brand: "Международный инновационный университет", brandSub: "Отдел международного приёма",
    heroH: "Учитесь в Узбекистане в XIU",
    heroP: "Подайте заявку на программы бакалавриата и магистратуры. Наша приёмная комиссия проверит документы и проведёт вас через каждый этап — от письма-предложения до приглашения на визу.",
    s1: "1 · Заявка", s2: "2 · Проверка документов", s3: "3 · Условное предложение",
    s4: "4 · Договор", s5: "5 · Оплата 30–50%", s6: "6 · Зачисление + приглашение",
    formH: "Форма заявки",
    formSub: "Поля со * обязательны. Загрузка: PDF, JPG или PNG.",
    secPersonal: "Личные данные", secProgram: "Выбор программы", secDocs: "Документы",
    fName: "ФИО", fCountry: "Страна", fPassport: "Номер паспорта",
    fDob: "Дата рождения", fPhone: "Телефон (WhatsApp)", fEmail: "Эл. почта",
    fProgram: "Программа", fFaculty: "Факультет",
    bachelor: "Бакалавриат", master: "Магистратура", choose: "— Выберите —",
    fUpPass: "Паспорт", fUpDip: "Диплом / сертификат", fUpPhoto: "Фото (3x4)",
    upHint: "Нажмите для загрузки (PDF / JPG / PNG)", submit: "Отправить заявку",
    fac1: "Информационные технологии", fac2: "Бизнес и экономика", fac3: "Инженерия",
    fac4: "Медицина", fac5: "Право", fac6: "Международные отношения",
    fac7: "Филология и языки", fac8: "Архитектура и дизайн",
    okH: "Заявка отправлена!",
    okP: "Спасибо. Ваша заявка получена приёмной комиссией XIU. Мы свяжемся с вами в WhatsApp и по эл. почте.",
    another: "Подать ещё",
    errGeneric: "Не удалось отправить. Попробуйте через минуту.",
    errSubmitting: "Отправка…",
    footnote: "© XIU Международный отдел приёма",
  },
  uz: {
    brand: "Xalqaro Innovatsiya Universiteti", brandSub: "Xalqaro qabul bo'limi",
    heroH: "XIU'da O'zbekistonda tahsil oling",
    heroP: "Bakalavr va magistratura dasturlariga ariza topshiring. Qabul bo'limimiz hujjatlaringizni tekshiradi va sizni har bir bosqichdan — taklif xatidan viza taklifnomasigacha — yo'naltiradi.",
    s1: "1 · Ariza", s2: "2 · Hujjat tekshiruvi", s3: "3 · Shartli taklif",
    s4: "4 · Shartnoma", s5: "5 · To'lov 30–50%", s6: "6 · Qabul + Taklifnoma",
    formH: "Ariza shakli",
    formSub: "* belgili maydonlar majburiy. Yuklash: PDF, JPG yoki PNG.",
    secPersonal: "Shaxsiy ma'lumotlar", secProgram: "Dastur tanlovi", secDocs: "Hujjatlar",
    fName: "To'liq ism", fCountry: "Davlat", fPassport: "Pasport raqami",
    fDob: "Tug'ilgan sana", fPhone: "Telefon (WhatsApp)", fEmail: "Email",
    fProgram: "Dastur", fFaculty: "Fakultet",
    bachelor: "Bakalavr", master: "Magistr", choose: "— Tanlang —",
    fUpPass: "Pasport", fUpDip: "Diplom / sertifikat", fUpPhoto: "Surat (3x4)",
    upHint: "Yuklash uchun bosing (PDF / JPG / PNG)", submit: "Arizani yuborish",
    fac1: "Axborot texnologiyalari", fac2: "Biznes va iqtisodiyot", fac3: "Muhandislik",
    fac4: "Tibbiyot", fac5: "Huquqshunoslik", fac6: "Xalqaro munosabatlar",
    fac7: "Filologiya va tillar", fac8: "Arxitektura va dizayn",
    okH: "Ariza yuborildi!",
    okP: "Rahmat. Arizangiz XIU qabul bo'limiga yetib bordi. Siz bilan WhatsApp va email orqali bog'lanamiz.",
    another: "Yana ariza topshirish",
    errGeneric: "Yuborib bo'lmadi. Birozdan keyin qaytadan urinib ko'ring.",
    errSubmitting: "Yuborilmoqda…",
    footnote: "© XIU Xalqaro qabul bo'limi",
  },
}
const t = computed(() => STRINGS[lang.value])

const COUNTRIES = [
  'Afghanistan','Bangladesh','Egypt','India','Indonesia','Kazakhstan',
  'Kyrgyzstan','Malaysia','Nigeria','Pakistan','Russia','Tajikistan',
  'Turkey','Turkmenistan','Other',
]
const FACULTIES: Array<{ code: string; key: string }> = [
  { code: 'fac1', key: 'fac1' }, { code: 'fac2', key: 'fac2' },
  { code: 'fac3', key: 'fac3' }, { code: 'fac4', key: 'fac4' },
  { code: 'fac5', key: 'fac5' }, { code: 'fac6', key: 'fac6' },
  { code: 'fac7', key: 'fac7' }, { code: 'fac8', key: 'fac8' },
]

// ===== Setup =====
onMounted(async () => {
  document.title = 'XIU — International Admissions'
  await loadSession()
})

async function loadSession() {
  try {
    const res = await http.get<{ token: string }>(
      '/international-admissions/apply/session',
      { headers: { 'Cache-Control': 'no-store' } },
    )
    sessionToken.value = res.data?.token || null
  } catch {
    // Form will surface its own error if the user actually submits without a token.
    sessionToken.value = null
  }
}

function pickFaculty(e: Event) {
  const sel = e.target as HTMLSelectElement
  form.faculty_text = sel.value
  const opt = sel.selectedOptions[0]
  form.faculty_code = opt ? (opt.getAttribute('data-code') || 'other') : 'other'
}

function onFile(field: 'passport_file' | 'diploma_file' | 'photo_file', e: Event) {
  const inp = e.target as HTMLInputElement
  form[field] = inp.files?.[0] || null
}

async function onSubmit() {
  errorMsg.value = null
  if (!sessionToken.value) {
    errorMsg.value = t.value.errGeneric
    await loadSession()
    return
  }
  if (!form.passport_file || !form.diploma_file || !form.photo_file) {
    errorMsg.value = `${t.value.fUpPass} / ${t.value.fUpDip} / ${t.value.fUpPhoto}`
    return
  }
  submitting.value = true
  try {
    const fd = new FormData()
    fd.set('full_name',       form.full_name)
    fd.set('country',         form.country)
    fd.set('passport_number', form.passport_number)
    fd.set('birth_date',      form.birth_date)
    fd.set('phone',           form.phone)
    fd.set('email',           form.email)
    fd.set('program',         form.program)
    fd.set('faculty_text',    form.faculty_text)
    fd.set('faculty_code',    form.faculty_code || 'other')
    fd.set('language',        lang.value)
    fd.set('session_token',   sessionToken.value)
    fd.set('website',         form.website)   // honeypot (will be '' for real users)
    fd.append('passport_file', form.passport_file)
    fd.append('diploma_file',  form.diploma_file)
    fd.append('photo_file',    form.photo_file)

    // NB: don't set Content-Type yourself — axios needs to compute
    // the multipart boundary from the FormData instance.
    const res = await http.post<{ ref_number: string; id: string }>(
      '/international-admissions/apply',
      fd,
    )
    submitted.value = { ref_number: res.data.ref_number }
    window.scrollTo({ top: 0, behavior: 'smooth' })
  } catch (e: any) {
    const data = e?.response?.data
    const msg = data?.detail || data?.error?.message || t.value.errGeneric
    errorMsg.value = typeof msg === 'string' ? msg : t.value.errGeneric
    await loadSession()   // refresh the time-trap token after a failure
  } finally {
    submitting.value = false
  }
}

function resetForm() {
  Object.assign(form, {
    full_name: '', country: '', passport_number: '', birth_date: '',
    phone: '', email: '', program: '', faculty_text: '', faculty_code: '',
    website: '',
    passport_file: null, diploma_file: null, photo_file: null,
  })
  submitted.value = null
  errorMsg.value = null
  loadSession()
}
</script>

<template>
  <div class="min-h-screen bg-slate-50 dark:bg-slate-950 font-sans antialiased">
    <!-- Brand header — matches operator hero gradient -->
    <header class="relative overflow-hidden text-white shadow-lg"
            style="background: linear-gradient(135deg, #3f56ef 0%, #5b6cf5 50%, #8b5cf6 100%);">
      <div class="absolute inset-0 opacity-30 pointer-events-none"
           style="background-image: radial-gradient(circle at 15% 100%, rgba(255,255,255,.18) 0%, transparent 50%), radial-gradient(circle at 85% 0%, rgba(255,255,255,.12) 0%, transparent 55%);"></div>
      <div class="relative max-w-6xl mx-auto px-6 py-5 flex items-center gap-4">
        <div class="flex items-center gap-3">
          <span class="grid place-items-center w-11 h-11 rounded-xl bg-white/15 backdrop-blur ring-1 ring-white/25 font-bold text-sm tracking-tight">
            XIU
          </span>
          <div class="leading-tight">
            <div class="font-bold tracking-tight">{{ t.brand }}</div>
            <div class="text-[11px] opacity-80 mt-0.5">{{ t.brandSub }}</div>
          </div>
        </div>
        <div class="ml-auto inline-flex bg-white/15 backdrop-blur rounded-lg p-0.5 text-xs font-bold">
          <button v-for="l in (['en','ru','uz'] as const)" :key="l"
                  class="px-3 py-1.5 rounded-md transition-colors"
                  :class="lang === l
                    ? 'bg-white text-brand-700'
                    : 'text-white/80 hover:text-white'"
                  @click="lang = l">
            {{ l.toUpperCase() }}
          </button>
        </div>
      </div>
    </header>

    <main class="max-w-6xl mx-auto px-4 sm:px-6 py-8 pb-16">
      <!-- Hero -->
      <section class="relative overflow-hidden rounded-2xl text-white shadow-card mb-7 p-6 sm:p-9"
               style="background: linear-gradient(135deg, #3f56ef 0%, #5b6cf5 50%, #8b5cf6 100%);">
        <div class="absolute inset-0 opacity-30 pointer-events-none"
             style="background-image: radial-gradient(circle at 20% 100%, rgba(255,255,255,.18) 0%, transparent 50%), radial-gradient(circle at 80% 0%, rgba(255,255,255,.14) 0%, transparent 55%);"></div>
        <div class="relative">
          <div class="inline-flex items-center gap-2 text-[11px] uppercase tracking-wider opacity-85 mb-2">
            <Globe class="w-3.5 h-3.5" /> International
          </div>
          <h1 class="text-2xl sm:text-3xl font-bold tracking-tight max-w-2xl">{{ t.heroH }}</h1>
          <p class="text-white/85 max-w-xl mt-2 text-sm sm:text-base">{{ t.heroP }}</p>
          <div class="mt-5 flex flex-wrap gap-2">
            <span v-for="i in 6" :key="i"
                  class="inline-flex items-center px-3 py-1.5 rounded-full text-[12px] font-semibold bg-white/15 ring-1 ring-white/25 backdrop-blur">
              {{ (t as any)['s' + i] }}
            </span>
          </div>
        </div>
      </section>

      <!-- Form / Success -->
      <div class="card max-w-3xl mx-auto p-6 sm:p-8">
        <template v-if="!submitted">
          <h2 class="text-xl font-bold text-slate-900 dark:text-slate-100">{{ t.formH }}</h2>
          <p class="text-sm text-slate-500 dark:text-slate-400 mt-1 mb-5">{{ t.formSub }}</p>

          <div v-if="errorMsg"
               class="flex items-start gap-2 p-3 rounded-lg bg-rose-50 dark:bg-rose-500/10 ring-1 ring-rose-200 dark:ring-rose-700/40 text-rose-700 dark:text-rose-300 text-sm mb-4">
            <AlertTriangle class="w-4 h-4 shrink-0 mt-0.5" />
            <div>{{ errorMsg }}</div>
          </div>

          <form @submit.prevent="onSubmit" autocomplete="off" novalidate>
            <!-- Honeypot — off-screen; bots fill, humans never see. -->
            <input v-model="form.website" type="text" tabindex="-1" autocomplete="off"
                   aria-hidden="true"
                   style="position:absolute;left:-9999px;width:0;height:0;opacity:0;pointer-events:none">

            <!-- Personal -->
            <div class="space-y-4">
              <div class="flex items-center gap-3 pt-2 pb-1 border-b border-slate-200 dark:border-slate-800">
                <span class="inline-block w-4 h-0.5 bg-brand-500"></span>
                <span class="text-[11px] uppercase tracking-[0.08em] font-bold text-brand-700 dark:text-brand-300">
                  {{ t.secPersonal }}
                </span>
              </div>

              <div>
                <label class="field-label">{{ t.fName }} <span class="text-rose-500">*</span></label>
                <input v-model="form.full_name" required class="input"
                       autocomplete="name" maxlength="200" placeholder="As written in passport">
              </div>

              <div class="grid sm:grid-cols-2 gap-4">
                <div>
                  <label class="field-label">{{ t.fCountry }} <span class="text-rose-500">*</span></label>
                  <select v-model="form.country" required class="input">
                    <option value="">{{ t.choose }}</option>
                    <option v-for="c in COUNTRIES" :key="c" :value="c">{{ c }}</option>
                  </select>
                </div>
                <div>
                  <label class="field-label">{{ t.fPassport }} <span class="text-rose-500">*</span></label>
                  <input v-model="form.passport_number" required class="input font-mono"
                         maxlength="40" placeholder="e.g. AA1234567">
                </div>
                <div>
                  <label class="field-label">{{ t.fDob }} <span class="text-rose-500">*</span></label>
                  <input v-model="form.birth_date" type="date" required class="input"
                         :max="new Date().toISOString().slice(0,10)" autocomplete="bday">
                </div>
                <div>
                  <label class="field-label">{{ t.fPhone }} <span class="text-rose-500">*</span></label>
                  <input v-model="form.phone" required class="input font-mono"
                         maxlength="30" placeholder="+998 90 123 45 67" autocomplete="tel">
                </div>
              </div>

              <div>
                <label class="field-label">{{ t.fEmail }} <span class="text-rose-500">*</span></label>
                <input v-model="form.email" type="email" required class="input"
                       maxlength="120" placeholder="you@example.com" autocomplete="email">
              </div>
            </div>

            <!-- Program -->
            <div class="space-y-4 mt-7">
              <div class="flex items-center gap-3 pt-2 pb-1 border-b border-slate-200 dark:border-slate-800">
                <span class="inline-block w-4 h-0.5 bg-brand-500"></span>
                <span class="text-[11px] uppercase tracking-[0.08em] font-bold text-brand-700 dark:text-brand-300">
                  {{ t.secProgram }}
                </span>
              </div>
              <div class="grid sm:grid-cols-2 gap-4">
                <div>
                  <label class="field-label">{{ t.fProgram }} <span class="text-rose-500">*</span></label>
                  <select v-model="form.program" required class="input">
                    <option value="">{{ t.choose }}</option>
                    <option value="Bachelor">{{ t.bachelor }}</option>
                    <option value="Master">{{ t.master }}</option>
                  </select>
                </div>
                <div>
                  <label class="field-label">{{ t.fFaculty }} <span class="text-rose-500">*</span></label>
                  <select required class="input" @change="pickFaculty">
                    <option value="">{{ t.choose }}</option>
                    <option v-for="f in FACULTIES" :key="f.code"
                            :value="(t as any)[f.key]" :data-code="f.code">
                      {{ (t as any)[f.key] }}
                    </option>
                  </select>
                </div>
              </div>
            </div>

            <!-- Documents -->
            <div class="space-y-4 mt-7">
              <div class="flex items-center gap-3 pt-2 pb-1 border-b border-slate-200 dark:border-slate-800">
                <span class="inline-block w-4 h-0.5 bg-brand-500"></span>
                <span class="text-[11px] uppercase tracking-[0.08em] font-bold text-brand-700 dark:text-brand-300">
                  {{ t.secDocs }}
                </span>
              </div>
              <div class="grid sm:grid-cols-3 gap-4">
                <label class="block">
                  <span class="field-label block">{{ t.fUpPass }} <span class="text-rose-500">*</span></span>
                  <div class="rounded-xl border-2 border-dashed p-4 text-center cursor-pointer transition"
                       :class="form.passport_file
                         ? 'border-emerald-400 bg-emerald-50 dark:bg-emerald-500/10'
                         : 'border-slate-200 dark:border-slate-700 hover:border-brand-400 hover:bg-brand-50/40 dark:hover:bg-brand-500/10'">
                    <IdCard class="w-5 h-5 mx-auto mb-1.5"
                            :class="form.passport_file ? 'text-emerald-600 dark:text-emerald-300' : 'text-slate-400 dark:text-slate-500'" />
                    <div class="text-[12px] font-medium"
                         :class="form.passport_file
                           ? 'text-emerald-700 dark:text-emerald-300 font-semibold'
                           : 'text-slate-500 dark:text-slate-400'">
                      <span v-if="form.passport_file" class="inline-flex items-center gap-1">
                        <Check class="w-3 h-3" /> {{ form.passport_file.name }}
                      </span>
                      <span v-else>{{ t.upHint }}</span>
                    </div>
                    <input type="file" class="hidden"
                           accept=".pdf,.jpg,.jpeg,.png"
                           @change="onFile('passport_file', $event)">
                  </div>
                </label>

                <label class="block">
                  <span class="field-label block">{{ t.fUpDip }} <span class="text-rose-500">*</span></span>
                  <div class="rounded-xl border-2 border-dashed p-4 text-center cursor-pointer transition"
                       :class="form.diploma_file
                         ? 'border-emerald-400 bg-emerald-50 dark:bg-emerald-500/10'
                         : 'border-slate-200 dark:border-slate-700 hover:border-brand-400 hover:bg-brand-50/40 dark:hover:bg-brand-500/10'">
                    <FileText class="w-5 h-5 mx-auto mb-1.5"
                              :class="form.diploma_file ? 'text-emerald-600 dark:text-emerald-300' : 'text-slate-400 dark:text-slate-500'" />
                    <div class="text-[12px] font-medium"
                         :class="form.diploma_file
                           ? 'text-emerald-700 dark:text-emerald-300 font-semibold'
                           : 'text-slate-500 dark:text-slate-400'">
                      <span v-if="form.diploma_file" class="inline-flex items-center gap-1">
                        <Check class="w-3 h-3" /> {{ form.diploma_file.name }}
                      </span>
                      <span v-else>{{ t.upHint }}</span>
                    </div>
                    <input type="file" class="hidden"
                           accept=".pdf,.jpg,.jpeg,.png"
                           @change="onFile('diploma_file', $event)">
                  </div>
                </label>

                <label class="block">
                  <span class="field-label block">{{ t.fUpPhoto }} <span class="text-rose-500">*</span></span>
                  <div class="rounded-xl border-2 border-dashed p-4 text-center cursor-pointer transition"
                       :class="form.photo_file
                         ? 'border-emerald-400 bg-emerald-50 dark:bg-emerald-500/10'
                         : 'border-slate-200 dark:border-slate-700 hover:border-brand-400 hover:bg-brand-50/40 dark:hover:bg-brand-500/10'">
                    <ImageIcon class="w-5 h-5 mx-auto mb-1.5"
                               :class="form.photo_file ? 'text-emerald-600 dark:text-emerald-300' : 'text-slate-400 dark:text-slate-500'" />
                    <div class="text-[12px] font-medium"
                         :class="form.photo_file
                           ? 'text-emerald-700 dark:text-emerald-300 font-semibold'
                           : 'text-slate-500 dark:text-slate-400'">
                      <span v-if="form.photo_file" class="inline-flex items-center gap-1">
                        <Check class="w-3 h-3" /> {{ form.photo_file.name }}
                      </span>
                      <span v-else>{{ t.upHint }}</span>
                    </div>
                    <input type="file" class="hidden"
                           accept=".jpg,.jpeg,.png"
                           @change="onFile('photo_file', $event)">
                  </div>
                </label>
              </div>
            </div>

            <button type="submit"
                    class="btn-primary w-full mt-7 py-3.5 text-base font-semibold"
                    :disabled="submitting">
              {{ submitting ? t.errSubmitting : t.submit }}
            </button>
          </form>
        </template>

        <!-- Success card -->
        <div v-else class="text-center py-6">
          <div class="grid place-items-center w-16 h-16 rounded-full mx-auto mb-5 text-white shadow-lg"
               style="background: linear-gradient(135deg, #10b981, #34d399);">
            <Check class="w-8 h-8" />
          </div>
          <h2 class="text-2xl font-bold text-slate-900 dark:text-slate-100">{{ t.okH }}</h2>
          <p class="text-slate-500 dark:text-slate-400 mt-2 max-w-md mx-auto">{{ t.okP }}</p>
          <div class="inline-block mt-5 px-5 py-2.5 rounded-xl font-mono font-bold text-brand-700 dark:text-brand-300 bg-brand-50 dark:bg-brand-500/10 ring-1 ring-brand-200 dark:ring-brand-700/40 tracking-wider">
            {{ submitted.ref_number }}
          </div>
          <div class="mt-6">
            <button class="btn-ghost" @click="resetForm">{{ t.another }}</button>
          </div>
        </div>
      </div>

      <p class="text-center text-xs text-slate-400 dark:text-slate-500 mt-6">
        {{ t.footnote }} · qabul.xiuedu.uz
      </p>
    </main>
  </div>
</template>
