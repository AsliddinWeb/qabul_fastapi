<script setup lang="ts">
import { reactive, ref, onMounted } from 'vue'
import { AxiosError } from 'axios'
import { landingApi } from '@/api/landing.api'
import FileUpload from '@/components/ui/FileUpload.vue'
import { useToast } from '@/composables/useToast'

const toast = useToast()
const loading = ref(true)
const saving = ref(false)

// Landingdagi DEFAULTS bilan bir xil — bo'sh bazada shu qiymatlar tahrirlanadi.
function defaults() {
  return {
    hero: {
      badge: 'Qabul 2026 — 2027 ochiq',
      subtitle: "Bakalavr va magistratura yo'nalishlari. Xalqaro almashinuv dasturlari. Qarshi shahridagi zamonaviy xususiy universitet.",
      image_main: null as string | null,
      image_inset: null as string | null,
      stat_value: '8000+', stat_label: 'Iqtidorli talabalar',
    },
    stats: [
      { value: '8000+', label: 'Iqtidorli talabalar' },
      { value: '180+', label: "Ilmiy darajali o'qituvchilar" },
      { value: '20+', label: "Bakalavr yo'nalishlari" },
      { value: '4+', label: "Magistratura yo'nalishlari" },
    ],
    about: {
      eyebrow: 'Universitet haqida',
      heading: 'Xalqaro innovatsion universiteti',
      text: "Qarshi shahridagi nodavlat oliy ta'lim muassasasi. Bakalavr va magistratura yo'nalishlarida zamonaviy va innovatsion ta'lim beruvchi universitet.",
      image: null as string | null,
      cells: [
        { icon: 'ph-graduation-cap', hue: 'a', title: 'Bakalavr va magistratura', text: "4 yillik bakalavr va 2 yillik magistratura dasturlari, kunduzgi ta'lim shaklida.", link: '' },
        { icon: 'ph-globe-hemisphere-east', hue: 'b', title: 'Xalqaro hamkorlik', text: "Rossiya, Qozog'iston va boshqa davlatlar oliy ta'lim muassasalari bilan ikki tomonlama almashinuv dasturlari.", link: '' },
        { icon: 'ph-lightbulb-filament', hue: 'c', title: "Dual ta'lim", text: "S Promax Plast Premium zavodi bilan hamkorlikda dual ta'lim yo'lga qo'yilgan — talaba o'qish bilan birga real ishlab chiqarishda tajriba oladi.", link: 'https://spromaxplast.uz/' },
      ],
    },
    qabul: {
      eyebrow: 'Qabul tartibi',
      heading: "Qabul qanday o'tadi",
      text: "Ariza qoldirganingizdan keyin qabul komissiyasi o'zi bog'lanadi va jarayonni oxirigacha kuzatib boradi.",
      steps: [
        { icon: 'ph-cursor-click', title: 'Ariza qoldiring', text: "Formani to'ldiring yoki qabul komissiyasiga telefon qiling." },
        { icon: 'ph-files', title: 'Hujjatlarni topshiring', text: "Pasport, ma'lumotnoma va o'rta ta'lim hujjatingiz nusxasi." },
        { icon: 'ph-chats-circle', title: "Suhbatdan o'ting", text: "Tanlagan yo'nalishingiz bo'yicha qisqa suhbat va yo'naltirish." },
        { icon: 'ph-signature', title: 'Shartnoma imzolang', text: "To'lov shartlari kelishiladi va siz talabalikka qabul qilinasiz." },
      ],
    },
    hamkorlik: {
      heading: 'Diplomni bu yerda oling, tajribani chet elda va ishlab chiqarishda',
      text: "Rossiya, Qozog'iston va boshqa davlatlar oliy ta'lim muassasalari bilan ikki tomonlama almashinuv dasturlari, hamda S Promax Plast Premium (PVC panel zavodi) bilan hamkorlikda dual ta'lim yo'lga qo'yilgan.",
      image: null as string | null,
      partners: [
        { label: 'Rossiya', href: '' },
        { label: "Qozog'iston", href: '' },
        { label: 'Boshqa hamkor davlatlar', href: '' },
        { label: 'S Promax Plast — PVC panel zavodi', href: 'https://spromaxplast.uz/' },
      ],
    },
  }
}

const form = reactive<any>(defaults())

onMounted(async () => {
  try {
    const res = await landingApi.get()
    const d = res.data || {}
    if (d.hero) Object.assign(form.hero, d.hero)
    if (Array.isArray(d.stats) && d.stats.length) form.stats = d.stats
    if (d.about) {
      const cells = d.about.cells
      Object.assign(form.about, d.about)
      if (Array.isArray(cells) && cells.length) form.about.cells = cells
    }
    if (d.qabul) {
      const steps = d.qabul.steps
      Object.assign(form.qabul, d.qabul)
      if (Array.isArray(steps) && steps.length) form.qabul.steps = steps
    }
    if (d.hamkorlik) {
      const partners = d.hamkorlik.partners
      Object.assign(form.hamkorlik, d.hamkorlik)
      if (Array.isArray(partners) && partners.length) form.hamkorlik.partners = partners
    }
  } catch { /* bo'sh — default qoladi */ }
  finally { loading.value = false }
})

async function save() {
  saving.value = true
  try {
    await landingApi.update(JSON.parse(JSON.stringify(form)))
    toast.success('Bosh sahifa kontenti saqlandi')
  } catch (e) {
    const ax = e as AxiosError<{ error?: { message?: string } }>
    toast.error(ax.response?.data?.error?.message || "Saqlab bo'lmadi")
  } finally {
    saving.value = false
  }
}

function resetDefaults() {
  Object.assign(form, defaults())
  toast.success("Standart qiymatlar tiklandi (saqlashni unutmang)")
}

function addStat() { if (form.stats.length < 6) form.stats.push({ value: '', label: '' }) }
function addPartner() { form.hamkorlik.partners.push({ label: '', href: '' }) }
</script>

<template>
  <div class="max-w-4xl mx-auto space-y-6 pb-16">
    <div class="flex items-start justify-between gap-4 flex-wrap">
      <div>
        <h1 class="text-2xl font-bold text-slate-900 dark:text-slate-100">Bosh sahifa (landing)</h1>
        <p class="mt-1 text-sm text-slate-600 dark:text-slate-400">
          Matnlar, statistika, rasmlar va hamkorlar — hammasi shu yerdan boshqariladi.
          Bo'sh qoldirilgan maydonlar standart qiymat bilan ko'rsatiladi.
        </p>
      </div>
      <div class="flex items-center gap-2 shrink-0">
        <button class="btn-ghost btn-sm" @click="resetDefaults">Standartga qaytarish</button>
        <button class="btn-primary" :disabled="saving" @click="save">{{ saving ? 'Saqlanmoqda…' : 'Saqlash' }}</button>
      </div>
    </div>

    <div v-if="loading" class="card p-16 text-center text-slate-500">Yuklanmoqda…</div>

    <template v-else>
      <!-- HERO -->
      <section class="card p-6 space-y-4">
        <h2 class="font-semibold text-slate-900 dark:text-slate-100">Hero (yuqori qism)</h2>
        <div class="grid sm:grid-cols-2 gap-4">
          <label class="block"><span class="lbl">Badge</span><input v-model="form.hero.badge" class="input" /></label>
          <div class="grid grid-cols-2 gap-3">
            <label class="block"><span class="lbl">Stat qiymat</span><input v-model="form.hero.stat_value" class="input" /></label>
            <label class="block"><span class="lbl">Stat izoh</span><input v-model="form.hero.stat_label" class="input" /></label>
          </div>
        </div>
        <label class="block"><span class="lbl">Tavsif (subtitle)</span><textarea v-model="form.hero.subtitle" rows="2" class="input"></textarea></label>
        <div class="grid sm:grid-cols-2 gap-4">
          <FileUpload v-model="form.hero.image_main" label="Asosiy rasm (1200×1250)" subdir="landing" />
          <FileUpload v-model="form.hero.image_inset" label="Kichik rasm (700×740)" subdir="landing" />
        </div>
      </section>

      <!-- STATISTIKA -->
      <section class="card p-6 space-y-4">
        <div class="flex items-center justify-between">
          <h2 class="font-semibold text-slate-900 dark:text-slate-100">Statistika</h2>
          <button class="btn-ghost btn-sm" @click="addStat">+ Qo'shish</button>
        </div>
        <div v-for="(s, i) in form.stats" :key="i" class="flex items-center gap-2">
          <input v-model="s.value" class="input w-32" placeholder="8000+" />
          <input v-model="s.label" class="input flex-1" placeholder="Izoh" />
          <button class="btn-ghost btn-sm" @click="form.stats.splice(i, 1)">O'chirish</button>
        </div>
      </section>

      <!-- UNIVERSITET -->
      <section class="card p-6 space-y-4">
        <h2 class="font-semibold text-slate-900 dark:text-slate-100">Universitet haqida</h2>
        <div class="grid sm:grid-cols-2 gap-4">
          <label class="block"><span class="lbl">Eyebrow</span><input v-model="form.about.eyebrow" class="input" /></label>
          <label class="block"><span class="lbl">Sarlavha</span><input v-model="form.about.heading" class="input" /></label>
        </div>
        <label class="block"><span class="lbl">Matn</span><textarea v-model="form.about.text" rows="2" class="input"></textarea></label>
        <FileUpload v-model="form.about.image" label="Bo'lim rasmi (1000×700)" subdir="landing" />
        <div class="space-y-3">
          <p class="lbl">Kartalar (3 ta)</p>
          <div v-for="(cell, i) in form.about.cells" :key="i" class="rounded-xl border p-3 space-y-2" :style="{ borderColor: 'rgb(var(--border))' }">
            <input v-model="cell.title" class="input" placeholder="Karta sarlavhasi" />
            <textarea v-model="cell.text" rows="2" class="input" placeholder="Matn"></textarea>
            <input v-model="cell.link" class="input" placeholder="Havola (ixtiyoriy, https://...)" />
          </div>
        </div>
      </section>

      <!-- QABUL TARTIBI -->
      <section class="card p-6 space-y-4">
        <h2 class="font-semibold text-slate-900 dark:text-slate-100">Qabul tartibi</h2>
        <div class="grid sm:grid-cols-2 gap-4">
          <label class="block"><span class="lbl">Eyebrow</span><input v-model="form.qabul.eyebrow" class="input" /></label>
          <label class="block"><span class="lbl">Sarlavha</span><input v-model="form.qabul.heading" class="input" /></label>
        </div>
        <label class="block"><span class="lbl">Matn</span><textarea v-model="form.qabul.text" rows="2" class="input"></textarea></label>
        <div class="space-y-3">
          <p class="lbl">Qadamlar</p>
          <div v-for="(st, i) in form.qabul.steps" :key="i" class="flex flex-col sm:flex-row gap-2">
            <input v-model="st.title" class="input sm:w-56" placeholder="Qadam sarlavhasi" />
            <input v-model="st.text" class="input flex-1" placeholder="Matn" />
          </div>
        </div>
      </section>

      <!-- HAMKORLIK -->
      <section class="card p-6 space-y-4">
        <h2 class="font-semibold text-slate-900 dark:text-slate-100">Xalqaro hamkorlik (band)</h2>
        <label class="block"><span class="lbl">Sarlavha</span><input v-model="form.hamkorlik.heading" class="input" /></label>
        <label class="block"><span class="lbl">Matn</span><textarea v-model="form.hamkorlik.text" rows="3" class="input"></textarea></label>
        <FileUpload v-model="form.hamkorlik.image" label="Band rasmi (1800×900)" subdir="landing" />
        <div class="space-y-3">
          <div class="flex items-center justify-between">
            <p class="lbl">Hamkorlar</p>
            <button class="btn-ghost btn-sm" @click="addPartner">+ Qo'shish</button>
          </div>
          <div v-for="(p, i) in form.hamkorlik.partners" :key="i" class="flex flex-col sm:flex-row gap-2">
            <input v-model="p.label" class="input flex-1" placeholder="Nomi (masalan: Rossiya yoki S Promax Plast)" />
            <input v-model="p.href" class="input sm:w-64" placeholder="Havola (ixtiyoriy)" />
            <button class="btn-ghost btn-sm" @click="form.hamkorlik.partners.splice(i, 1)">O'chirish</button>
          </div>
        </div>
      </section>

      <div class="flex justify-end">
        <button class="btn-primary" :disabled="saving" @click="save">{{ saving ? 'Saqlanmoqda…' : 'Saqlash' }}</button>
      </div>
    </template>
  </div>
</template>

<style scoped>
.lbl { display:block; font-size:.8rem; font-weight:600; margin-bottom:.35rem; color: rgb(var(--fg-soft)); }
</style>
