<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { AxiosError } from 'axios'
import { ArrowLeft, Save, Eye, Pencil, Code2, FileCode2 } from 'lucide-vue-next'
import { contractsApi } from '@/api/contracts.api'
import RichEditor from '@/components/ui/RichEditor.vue'
import Skeleton from '@/components/ui/Skeleton.vue'

const route = useRoute()
const router = useRouter()

const id = computed(() => route.params.id as string | undefined)
const isCreate = computed(() => !id.value)

// === Split storage: body editable in TipTap, CSS edited as raw text ===
const form = ref({
  name: '',
  body_two_party: '<p></p>',
  body_three_party: '<p></p>',
  is_active: false,
})

// Per-tab extracted CSS that the editor injects to render styled preview.
const cssTwo = ref('')
const cssThree = ref('')

const partyTab = ref<'two' | 'three'>('two')
const viewTab = ref<'edit' | 'preview' | 'css' | 'html'>('edit')

// === HTML <-> editor body conversion ===

/** Extract CSS from <style> tags and the inner-body HTML from a (possibly full) HTML doc. */
function splitDoc(html: string): { css: string; body: string } {
  if (!html) return { css: '', body: '<p></p>' }
  const styleRe = /<style[^>]*>([\s\S]*?)<\/style>/gi
  let css = ''
  let body = html
  let m: RegExpExecArray | null
  while ((m = styleRe.exec(html)) !== null) {
    css += (css ? '\n' : '') + m[1].trim()
  }
  body = body.replace(styleRe, '').trim()
  // If full doc, extract <body> inner
  const bodyRe = /<body[^>]*>([\s\S]*?)<\/body>/i
  const bm = body.match(bodyRe)
  if (bm) body = bm[1].trim()
  // Strip <!DOCTYPE>, <html>, <head> wrappers if any leftover
  body = body
    .replace(/<!doctype[^>]*>/gi, '')
    .replace(/<\/?(html|head|meta|title|link)[^>]*>/gi, '')
    .trim()
  if (!body) body = '<p></p>'
  return { css, body }
}

/** Reassemble the full template HTML for storage (so WeasyPrint sees the styles). */
function joinDoc(css: string, body: string): string {
  if (!css.trim()) return body
  return `<!DOCTYPE html>
<html lang="uz">
<head>
<meta charset="UTF-8">
<style>
${css}
</style>
</head>
<body>
${body}
</body>
</html>`
}

/** Scope CSS rules to `.rich-content` so the editor preview matches the PDF output. */
function scopeCSS(css: string, scope = '.rich-content'): string {
  if (!css) return ''
  return css.replace(/(^|\})([^{}]+)\{/g, (_m, brace: string, selector: string) => {
    const scoped = selector
      .split(',')
      .map((s) => {
        const t = s.trim()
        if (!t) return t
        if (t.startsWith('@')) return t
        if (t === 'body' || t === 'html') return scope
        if (t.startsWith(scope)) return t
        return `${scope} ${t}`
      })
      .join(', ')
    return `${brace}${scoped}{`
  })
}

// === Inject the active tab's scoped CSS as a managed <style> tag ===
const STYLE_ID = 'xiu-tpl-runtime-style'
function applyRuntimeStyles(css: string) {
  let el = document.getElementById(STYLE_ID) as HTMLStyleElement | null
  if (!el) {
    el = document.createElement('style')
    el.id = STYLE_ID
    document.head.appendChild(el)
  }
  el.textContent = scopeCSS(css)
}

const activeCSS = computed(() => (partyTab.value === 'two' ? cssTwo.value : cssThree.value))
watch(activeCSS, (v) => applyRuntimeStyles(v), { immediate: true })

onBeforeUnmount(() => {
  const el = document.getElementById(STYLE_ID)
  if (el) el.remove()
})

const twoEditor = ref<InstanceType<typeof RichEditor> | null>(null)
const threeEditor = ref<InstanceType<typeof RichEditor> | null>(null)

const loading = ref(false)
const saving = ref(false)
const message = ref<{ type: 'ok' | 'err'; text: string } | null>(null)

// Backend-rendered placeholders (see contracts/service.py:_build_context).
// Both new (KONTRAKT_RAQAMI) and old Django-style aliases (ID, KONTRAKT_SUMMASI ...) are supported.
const PLACEHOLDERS_TWO: { v: string; label: string }[] = [
  { v: 'KONTRAKT_RAQAMI',   label: 'Shartnoma raqami' },
  { v: 'YONALISH_SERIYA',   label: "Yo'nalish seriyasi" },
  { v: 'ID',                label: 'Qisqa ID' },
  { v: 'SANA',              label: 'Sana' },
  { v: 'FILIAL',            label: 'Filial' },
  { v: 'TALABA_ISMI',       label: 'Talaba F.I.Sh.' },
  { v: 'TELEFON',           label: 'Talaba telefoni' },
  { v: 'PASSPORT_SERIYA',   label: 'Pasport seriya' },
  { v: 'PINFL',             label: 'PINFL' },
  { v: 'YASHASH_MANZILI',   label: 'Yashash manzili' },
  { v: 'TALABA_MANZILI',    label: 'Talaba manzili (alias)' },
  { v: 'TALIM_DARAJASI',    label: "Ta'lim darajasi" },
  { v: 'TALIM_SHAKLI',      label: "Ta'lim shakli" },
  { v: 'OQISH_MUDDATI',     label: "O'qish muddati" },
  { v: 'OQUV_KURSI',        label: "O'quv kursi" },
  { v: 'YONALISH',          label: "Yo'nalish" },
  { v: 'YILLIK_TOLOV',      label: "Yillik to'lov (so'm)" },
  { v: 'KONTRAKT_SUMMASI',  label: "Kontrakt summasi (alias)" },
  { v: 'BITIRUV_YILI',      label: 'Bitiruv yili' },
  { v: 'QABUL_TURI',        label: 'Qabul turi' },
  { v: 'SHARTNOMA_SERIYASI', label: 'Shartnoma seriyasi' },
  { v: 'qr_code',           label: 'QR-kod (rasmda)' },
]

const PLACEHOLDERS_THREE: { v: string; label: string }[] = [
  ...PLACEHOLDERS_TWO,
  { v: 'OTA_ONA_ISMI',     label: "Ota-ona F.I.Sh." },
  { v: 'OTA_ONA_TELEFON',  label: 'Ota-ona telefon' },
]

const SAMPLE: Record<string, string> = {
  KONTRAKT_RAQAMI: 'C-2026-A1B2C3D4',
  ID: 'A1B2C3D4',
  YONALISH_SERIYA: '2026-BK',
  TALABA_ISMI: "VALIYEV ALI AKBAR O'G'LI",
  TELEFON: '+998 90 123 45 67',
  PASSPORT_SERIYA: 'AA1234567',
  PINFL: '50101015240015',
  YASHASH_MANZILI: "Toshkent shahri, Mirzo Ulug'bek tumani",
  TALABA_MANZILI: "Toshkent shahri, Mirzo Ulug'bek tumani",
  FILIAL: 'Qarshi',
  YONALISH: "Iqtisodiyot (tarmoqlari va sohalari bo'yicha)",
  TALIM_DARAJASI: 'Bakalavr',
  TALIM_SHAKLI: 'Kunduzgi',
  OQISH_MUDDATI: '4 yil',
  OQUV_KURSI: '1-kurs',
  YILLIK_TOLOV: '12 000 000',
  KONTRAKT_SUMMASI: '12 000 000',
  BITIRUV_YILI: '2030',
  QABUL_TURI: '1-kurs (Yangi qabul)',
  SHARTNOMA_SERIYASI: '2026-BK',
  SANA: '24.04.2026',
  OTA_ONA_ISMI: 'VALIYEV AKBAR',
  OTA_ONA_TELEFON: '+998 90 765 43 21',
  qr_code: '',
}

function placeholderText(v: string): string {
  return `{{${v}}}`
}

function renderPreview(html: string): string {
  return html.replace(/\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}/g, (_m, name: string) => SAMPLE[name] ?? `{{${name}}}`)
}

const previewHtml = computed(() =>
  partyTab.value === 'two'
    ? renderPreview(form.value.body_two_party)
    : renderPreview(form.value.body_three_party),
)

const currentPlaceholders = computed(() =>
  partyTab.value === 'two' ? PLACEHOLDERS_TWO : PLACEHOLDERS_THREE,
)

const hasLegacyMarkup = computed(() => {
  const body = partyTab.value === 'two' ? form.value.body_two_party : form.value.body_three_party
  return /<div\s+[^>]*class\s*=/.test(body)
})

// If legacy markup is detected while user is on the rich-edit tab, jump to HTML
// so TipTap can never run its parser over the styled HTML and strip classes.
watch(hasLegacyMarkup, (legacy) => {
  if (legacy && viewTab.value === 'edit') viewTab.value = 'html'
})

function insertPlaceholder(v: string) {
  const editor = partyTab.value === 'two' ? twoEditor.value : threeEditor.value
  editor?.insertText(placeholderText(v))
}

async function load() {
  if (isCreate.value) return
  loading.value = true
  try {
    const tpl = await contractsApi.template(id.value as string)
    const two = splitDoc(tpl.body_two_party || '')
    const three = splitDoc(tpl.body_three_party || '')
    cssTwo.value = two.css
    cssThree.value = three.css
    form.value = {
      name: tpl.name,
      body_two_party: two.body,
      body_three_party: three.body,
      is_active: tpl.is_active,
    }
    // Legacy markup (with class-d divs) doesn't roundtrip well through TipTap;
    // open the HTML tab by default so the admin can edit raw HTML safely.
    if (/<div\s+[^>]*class\s*=/.test(two.body) || /<div\s+[^>]*class\s*=/.test(three.body)) {
      viewTab.value = 'html'
    }
  } finally {
    loading.value = false
  }
}

watch(id, load, { immediate: true })

async function save() {
  message.value = null
  if (!form.value.name.trim()) {
    message.value = { type: 'err', text: 'Shablon nomini kiriting' }
    return
  }
  saving.value = true
  try {
    const payload = {
      name: form.value.name,
      body_two_party: joinDoc(cssTwo.value, form.value.body_two_party),
      body_three_party: joinDoc(cssThree.value, form.value.body_three_party),
      is_active: form.value.is_active,
    }
    if (isCreate.value) {
      const created = await contractsApi.createTemplate(payload)
      router.push(`/admin/contract-templates/${created.id}`)
    } else {
      await contractsApi.updateTemplate(id.value as string, payload)
      message.value = { type: 'ok', text: 'Saqlandi' }
    }
  } catch (e) {
    const ax = e as AxiosError<{ error?: { message?: string } }>
    message.value = { type: 'err', text: ax.response?.data?.error?.message || "Saqlab bo'lmadi" }
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="space-y-5">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <button class="inline-flex items-center gap-1 text-sm text-brand-600 hover:underline mb-1" @click="router.back()">
          <ArrowLeft class="w-4 h-4" /> Ortga
        </button>
        <h1 class="text-2xl font-bold text-slate-900 dark:text-slate-100">
          {{ isCreate ? "Yangi shablon" : 'Shablonni tahrirlash' }}
        </h1>
        <p class="text-sm text-slate-600 dark:text-slate-400">
          Bitta shablon ichida 2-tomonlama va 3-tomonlama matnlar bo'ladi.
          Placeholder'larni chap paneldan bosib qo'shing.
        </p>
      </div>
      <button class="btn-primary" :disabled="saving" @click="save">
        <Save class="w-4 h-4" />
        {{ saving ? 'Saqlanmoqda...' : (isCreate ? 'Yaratish' : 'Saqlash') }}
      </button>
    </div>

    <div v-if="message" class="text-sm rounded-lg p-3"
         :class="message.type === 'ok'
           ? 'bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-300'
           : 'bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-300'">
      {{ message.text }}
    </div>

    <Skeleton v-if="loading" type="form" />

    <div v-else class="grid lg:grid-cols-[260px_1fr] gap-5">
      <aside class="card p-4 space-y-3 self-start sticky top-20 max-h-[calc(100vh-110px)] overflow-y-auto">
        <h3 class="font-semibold text-sm text-slate-900 dark:text-slate-100">Placeholder'lar</h3>
        <button
          v-for="v in currentPlaceholders"
          :key="v.v"
          type="button"
          class="w-full text-left text-xs px-2.5 py-1.5 rounded-md
                 bg-slate-100 hover:bg-brand-100 hover:text-brand-700
                 dark:bg-slate-800 dark:hover:bg-brand-900/40 dark:hover:text-brand-200
                 text-slate-800 dark:text-slate-200 transition-colors"
          @click="insertPlaceholder(v.v)"
        >
          <div class="font-medium">{{ v.label }}</div>
          <code class="text-[10px] opacity-70 block mt-0.5">{{ placeholderText(v.v) }}</code>
        </button>
      </aside>

      <div class="space-y-4 min-w-0">
        <section class="card p-5 grid sm:grid-cols-3 gap-3">
          <div class="sm:col-span-2">
            <label class="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Shablon nomi *</label>
            <input v-model="form.name" class="input" placeholder="Asosiy shablon" />
          </div>
          <label class="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300 self-end pb-2">
            <input v-model="form.is_active" type="checkbox" class="rounded" />
            <span>Faol shablon (boshqalarni o'chiradi)</span>
          </label>
        </section>

        <!-- 2-party / 3-party tabs -->
        <div class="flex items-center gap-1 border-b border-slate-200 dark:border-slate-800">
          <button
            class="px-4 py-2 text-sm font-medium border-b-2 -mb-px"
            :class="partyTab === 'two'
              ? 'border-brand-600 text-brand-700 dark:text-brand-300'
              : 'border-transparent text-slate-500 hover:text-slate-900'"
            @click="partyTab = 'two'"
          >2-tomonlama</button>
          <button
            class="px-4 py-2 text-sm font-medium border-b-2 -mb-px"
            :class="partyTab === 'three'
              ? 'border-brand-600 text-brand-700 dark:text-brand-300'
              : 'border-transparent text-slate-500 hover:text-slate-900'"
            @click="partyTab = 'three'"
          >3-tomonlama</button>
        </div>

        <!-- Edit / HTML / CSS / Preview tabs.
             Edit (TipTap) tab is hidden for legacy templates because TipTap strips
             arbitrary class attributes from <div> elements, breaking the styling. -->
        <div class="flex items-center gap-1">
          <button v-if="!hasLegacyMarkup"
            class="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs rounded"
            :class="viewTab === 'edit' ? 'bg-slate-900 text-white dark:bg-white dark:text-slate-900' : 'text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800'"
            @click="viewTab = 'edit'"
          ><Pencil class="w-3 h-3" /> Tahrirlash</button>
          <button
            class="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs rounded"
            :class="viewTab === 'html' ? 'bg-slate-900 text-white dark:bg-white dark:text-slate-900' : 'text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800'"
            @click="viewTab = 'html'"
          ><FileCode2 class="w-3 h-3" /> HTML</button>
          <button
            class="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs rounded"
            :class="viewTab === 'css' ? 'bg-slate-900 text-white dark:bg-white dark:text-slate-900' : 'text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800'"
            @click="viewTab = 'css'"
          ><Code2 class="w-3 h-3" /> CSS uslublari</button>
          <button
            class="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs rounded"
            :class="viewTab === 'preview' ? 'bg-slate-900 text-white dark:bg-white dark:text-slate-900' : 'text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800'"
            @click="viewTab = 'preview'"
          ><Eye class="w-3 h-3" /> Ko'rinishi</button>
        </div>

        <!-- Rich editor: only mounted when there's no legacy markup (otherwise TipTap mangles the HTML). -->
        <template v-if="!hasLegacyMarkup">
          <section v-show="viewTab === 'edit' && partyTab === 'two'">
            <RichEditor ref="twoEditor" v-model="form.body_two_party" />
          </section>
          <section v-show="viewTab === 'edit' && partyTab === 'three'">
            <RichEditor ref="threeEditor" v-model="form.body_three_party" />
          </section>
        </template>

        <section v-show="viewTab === 'html' && partyTab === 'two'" class="card p-4">
          <div class="text-xs text-slate-500 dark:text-slate-400 mb-2">
            <strong>2-tomonlama</strong> shablonning HTML matni (Jinja placeholderlari ishlatilishi mumkin: <code>&#123;&#123;TALABA_ISMI&#125;&#125;</code>).
          </div>
          <textarea v-model="form.body_two_party" class="input font-mono text-xs" rows="22" spellcheck="false"></textarea>
        </section>
        <section v-show="viewTab === 'html' && partyTab === 'three'" class="card p-4">
          <div class="text-xs text-slate-500 dark:text-slate-400 mb-2">
            <strong>3-tomonlama</strong> shablonning HTML matni.
          </div>
          <textarea v-model="form.body_three_party" class="input font-mono text-xs" rows="22" spellcheck="false"></textarea>
        </section>

        <section v-show="viewTab === 'css' && partyTab === 'two'" class="card p-4">
          <div class="text-xs text-slate-500 dark:text-slate-400 mb-2">
            <strong>2-tomonlama</strong> shablon uchun CSS uslublari (font, hajm, margin va h.k.). PDF render paytida ham qo'llaniladi.
          </div>
          <textarea v-model="cssTwo" class="input font-mono text-xs" rows="22" spellcheck="false"></textarea>
        </section>
        <section v-show="viewTab === 'css' && partyTab === 'three'" class="card p-4">
          <div class="text-xs text-slate-500 dark:text-slate-400 mb-2">
            <strong>3-tomonlama</strong> shablon uchun CSS uslublari.
          </div>
          <textarea v-model="cssThree" class="input font-mono text-xs" rows="22" spellcheck="false"></textarea>
        </section>

        <section v-show="viewTab === 'preview'">
          <div class="rich-editor border border-slate-200 dark:border-slate-800 rounded-xl bg-white dark:bg-slate-900 p-8 max-h-[700px] overflow-auto">
            <div class="rich-content" v-html="previewHtml" />
          </div>
        </section>
      </div>
    </div>
  </div>
</template>

<style>
.rich-content { color: #0f172a; font-size: 0.95rem; }
.rich-content h1 { font-size: 1.6rem; font-weight: 700; margin: 1rem 0 0.5rem; }
.rich-content h2 { font-size: 1.3rem; font-weight: 600; margin: 0.9rem 0 0.4rem; }
.rich-content h3 { font-size: 1.1rem; font-weight: 600; margin: 0.7rem 0 0.3rem; }
.rich-content p { margin: 0.5rem 0; }
.rich-content ul { list-style: disc; padding-left: 1.5rem; margin: 0.5rem 0; }
.rich-content ol { list-style: decimal; padding-left: 1.5rem; margin: 0.5rem 0; }
.rich-content blockquote { border-left: 3px solid #cbd5e1; padding-left: 0.75rem; color: #475569; }
.rich-content hr { border: 0; border-top: 1px solid #e2e8f0; margin: 1rem 0; }
.rich-content table { border-collapse: collapse; width: 100%; margin: 0.75rem 0; }
.rich-content th, .rich-content td { border: 1px solid #cbd5e1; padding: 6px 8px; }
.rich-content th { background: #f1f5f9; font-weight: 600; text-align: left; }

html.dark .rich-content { color: #f1f5f9; }
html.dark .rich-content blockquote { border-left-color: #475569; color: #cbd5e1; }
html.dark .rich-content hr { border-top-color: #334155; }
html.dark .rich-content th, html.dark .rich-content td { border-color: #475569; }
html.dark .rich-content th { background: #1e293b; }
</style>
