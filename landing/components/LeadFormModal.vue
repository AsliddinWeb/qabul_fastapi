<script setup lang="ts">
import { ref, reactive, computed, watch, onMounted, onBeforeUnmount } from 'vue'

const { isOpen, preselectedProgramId, close } = useLeadModal()
const config = useRuntimeConfig()
const apiBase = (config.public as any).apiBaseUrl || '/api/v1'

interface ProgramOpt {
  id: string
  name: string
  code: string
  branch_id: string
  branch_name?: string
  education_level_name?: string
}
const programs = ref<ProgramOpt[]>([])
const programsLoaded = ref(false)

const form = reactive({
  full_name: '',
  phone: '',
  program_id: '' as string | '',
  _hp: '',
  _t: 0 as number,
})
const errors = ref<Record<string, string>>({})
const touched = ref<Record<string, boolean>>({})
const sending = ref(false)
const successId = ref<string | null>(null)
const successStatus = ref<'created' | 'merged' | 'duplicate' | null>(null)
const successMessage = ref<string>('')

function formatPhone(value: string): string {
  const digits = value.replace(/\D/g, '')
  if (!digits) return ''
  let n = digits
  if (!n.startsWith('998')) n = '998' + n.slice(0, 9)
  n = n.slice(0, 12)
  const cc = n.slice(0, 3); const op = n.slice(3, 5)
  const a = n.slice(5, 8); const b = n.slice(8, 10); const c = n.slice(10, 12)
  let out = '+' + cc
  if (op) out += ' ' + op; if (a) out += ' ' + a
  if (b) out += ' ' + b; if (c) out += ' ' + c
  return out
}
function compactPhone(v: string): string {
  const d = v.replace(/\D/g, '')
  return d ? '+' + d : ''
}

function validatePhone(v: string): string | null {
  const d = v.replace(/\D/g, '')
  if (!d) return "Telefon majburiy"
  if (d.length < 12) return "+998 XX XXX XX XX formatida"
  if (!d.startsWith('998')) return "+998 bilan boshlansin"
  if (d.length > 12) return "Raqam juda uzun"
  const op = d.slice(3, 5)
  const valid = ['90','91','93','94','95','97','98','99','77','88','33','55','50','71']
  if (!valid.includes(op)) return "Operator kodi noto'g'ri"
  return null
}
function validateName(v: string): string | null {
  const t = v.trim()
  if (!t) return "F.I.Sh. majburiy"
  if (t.length < 4) return "Kamida 4 belgi"
  if (t.length > 150) return "Juda uzun"
  if (!/^[a-zA-Zа-яА-ЯёЁўЎқҚғҒҳҲ'`’\s\-]+$/u.test(t)) return "Faqat harflar"
  if (!/\s/.test(t)) return "Familiya va ism kiriting"
  return null
}

function recompute(field: 'full_name' | 'phone') {
  const e = { ...errors.value }
  delete e[field]
  let err: string | null = null
  if (field === 'full_name') err = validateName(form.full_name)
  else if (field === 'phone') err = validatePhone(form.phone)
  if (err) e[field] = err
  errors.value = e
}

watch(() => form.full_name, () => { if (touched.value.full_name) recompute('full_name') })
watch(() => form.phone, () => { if (touched.value.phone) recompute('phone') })

function blur(field: 'full_name' | 'phone') {
  touched.value[field] = true
  recompute(field)
}

const isValid = computed(() =>
  !validateName(form.full_name) && !validatePhone(form.phone),
)

function onPhoneInput(e: Event) {
  form.phone = formatPhone((e.target as HTMLInputElement).value)
}

const programsByBranch = computed(() => {
  const groups: Record<string, { name: string; programs: ProgramOpt[] }> = {}
  for (const p of programs.value) {
    const k = p.branch_id || '_'
    if (!groups[k]) groups[k] = { name: p.branch_name || 'Filial', programs: [] }
    groups[k].programs.push(p)
  }
  return groups
})

async function loadPrograms() {
  if (programsLoaded.value) return
  try {
    const res = await fetch(`${apiBase}/programs/programs?active_only=true`)
    if (!res.ok) throw new Error('failed')
    programs.value = await res.json()
    programsLoaded.value = true
  } catch { programs.value = [] }
}

async function submit() {
  ;(['full_name', 'phone'] as const).forEach((f) => {
    touched.value[f] = true; recompute(f)
  })
  if (!isValid.value) return

  sending.value = true
  try {
    const payload = {
      full_name: form.full_name.trim(),
      phone: compactPhone(form.phone),
      program_id: form.program_id || null,
      source_code: 'web_form',
      _hp: form._hp,
      t: form._t,
    }
    const res = await fetch(`${apiBase}/leads/public`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    if (res.status === 429) { errors.value = { _form: "Juda ko'p so'rov. Birozdan keyin qayta urinib ko'ring." }; return }
    if (res.status === 410) { errors.value = { _form: "Forma muddati o'tdi. Sahifani yangilang." }; return }
    if (!res.ok) {
      const j = await res.json().catch(() => null)
      errors.value = { _form: j?.error?.message || j?.detail || "Xatolik. Keyinroq urinib ko'ring." }
      return
    }
    const result = await res.json()
    successStatus.value = result.status || 'created'
    successMessage.value = result.message || ''
    successId.value = 'ok'
  } catch {
    errors.value = { _form: "Tarmoq xatosi. Internetni tekshiring." }
  } finally { sending.value = false }
}

function reset() {
  Object.assign(form, { full_name: '', phone: '', program_id: '', _hp: '', _t: Date.now() })
  errors.value = {}; touched.value = {}; successId.value = null
  successStatus.value = null; successMessage.value = ''
}

watch(isOpen, async (v) => {
  if (v) {
    reset(); form._t = Date.now()
    if (preselectedProgramId.value) form.program_id = preselectedProgramId.value
    await loadPrograms()
    if (typeof document !== 'undefined') document.body.style.overflow = 'hidden'
  } else {
    if (typeof document !== 'undefined') document.body.style.overflow = ''
  }
})

function onEsc(e: KeyboardEvent) {
  if (e.key === 'Escape' && isOpen.value && !sending.value) close()
}
onMounted(() => { if (typeof document !== 'undefined') document.addEventListener('keydown', onEsc) })
onBeforeUnmount(() => { if (typeof document !== 'undefined') document.removeEventListener('keydown', onEsc) })
</script>

<template>
  <Teleport to="body">
    <Transition
      enter-active-class="transition-all duration-200 ease-out"
      leave-active-class="transition-all duration-150 ease-in"
      enter-from-class="opacity-0"
      leave-to-class="opacity-0"
    >
      <div
        v-if="isOpen"
        class="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-0 sm:p-4"
        style="background: rgb(2 6 23 / 0.65); backdrop-filter: blur(8px);"
        @click.self="!sending && close()"
      >
        <Transition
          enter-active-class="transition-all duration-300 ease-out"
          leave-active-class="transition-all duration-200 ease-in"
          enter-from-class="opacity-0 sm:scale-95 translate-y-8 sm:translate-y-0"
          leave-to-class="opacity-0 sm:scale-95 translate-y-8 sm:translate-y-0"
        >
          <div
            v-if="isOpen"
            class="relative w-full sm:max-w-md rounded-t-3xl sm:rounded-2xl shadow-2xl flex flex-col overflow-hidden"
            :style="{ background: 'rgb(var(--card))' }"
          >
            <!-- Header -->
            <div class="px-6 pt-6 pb-4 flex items-start justify-between gap-4 border-b"
                 :style="{ borderColor: 'rgb(var(--border))' }">
              <div>
                <h2 class="text-xl font-bold tracking-tight" :style="{ color: 'rgb(var(--fg))' }">
                  <template v-if="!successId">Ariza qoldirish</template>
                  <template v-else-if="successStatus === 'duplicate'">Allaqachon ro'yxatda</template>
                  <template v-else>Yuborildi</template>
                </h2>
                <p class="mt-1 text-sm" :style="{ color: 'rgb(var(--fg-soft))' }">
                  <template v-if="!successId">Operator aloqaga chiqadi</template>
                  <template v-else-if="successStatus === 'duplicate'">Sizga qayta arizaga ehtiyoj yo'q</template>
                  <template v-else>Operatorimiz qaytib qo'ng'iroq qiladi</template>
                </p>
              </div>
              <button
                class="grid place-items-center w-9 h-9 rounded-lg transition-colors shrink-0 disabled:opacity-50"
                :style="{ color: 'rgb(var(--fg-muted))', background: 'rgb(var(--bg-soft))' }"
                :disabled="sending"
                @click="close"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M18 6L6 18M6 6l12 12" />
                </svg>
              </button>
            </div>

            <!-- Body -->
            <div class="flex-1 px-6 py-5">
              <!-- Success -->
              <div v-if="successId" class="py-3">
                <div
                  class="inline-grid place-items-center w-12 h-12 rounded-full mb-4"
                  :class="successStatus === 'duplicate'
                    ? 'bg-amber-100 text-amber-600 dark:bg-amber-500/20 dark:text-amber-300'
                    : 'bg-emerald-100 text-emerald-600 dark:bg-emerald-500/20 dark:text-emerald-300'"
                >
                  <svg v-if="successStatus === 'duplicate'" xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="12" cy="12" r="10" /><path d="M12 8v4M12 16h.01" />
                  </svg>
                  <svg v-else xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M20 6 9 17l-5-5" />
                  </svg>
                </div>
                <p class="text-sm leading-relaxed" :style="{ color: 'rgb(var(--fg-soft))' }">
                  <template v-if="successStatus === 'duplicate'">
                    {{ successMessage || "Sizning arizangiz allaqachon ro'yxatda. Operator siz bilan tez orada bog'lanadi." }}
                  </template>
                  <template v-else>
                    Operatorimiz <strong :style="{ color: 'rgb(var(--fg))' }">1 ish kuni ichida</strong> raqam orqali bog'lanadi.
                  </template>
                </p>
              </div>

              <!-- Form -->
              <form v-else class="space-y-4" @submit.prevent="submit">
                <!-- Honeypot -->
                <input v-model="form._hp" type="text" name="website" tabindex="-1" autocomplete="off" class="hp-field" aria-hidden="true" />

                <!-- F.I.Sh. -->
                <div>
                  <label class="label" for="lf-name">F.I.Sh. <span class="text-rose-500">*</span></label>
                  <input
                    id="lf-name"
                    v-model="form.full_name"
                    type="text"
                    autocomplete="name"
                    class="input"
                    :class="errors.full_name ? 'error' : ''"
                    placeholder="Valiyev Ali Karimovich"
                    @blur="blur('full_name')"
                  />
                  <p v-if="errors.full_name" class="field-error">{{ errors.full_name }}</p>
                </div>

                <!-- Telefon -->
                <div>
                  <label class="label" for="lf-phone">Telefon <span class="text-rose-500">*</span></label>
                  <input
                    id="lf-phone"
                    :value="form.phone"
                    type="tel"
                    inputmode="tel"
                    autocomplete="tel"
                    class="input font-mono"
                    :class="errors.phone ? 'error' : ''"
                    placeholder="+998 94 202 55 11"
                    @input="onPhoneInput"
                    @blur="blur('phone')"
                  />
                  <p v-if="errors.phone" class="field-error">{{ errors.phone }}</p>
                </div>

                <!-- Yo'nalish (ixtiyoriy) -->
                <div>
                  <label class="label" for="lf-prog">
                    Yo'nalish <span class="font-normal opacity-60">(ixtiyoriy)</span>
                  </label>
                  <select id="lf-prog" v-model="form.program_id" class="input">
                    <option value="">— hali tanlamadim —</option>
                    <optgroup v-for="(grp, k) in programsByBranch" :key="k" :label="grp.name">
                      <option v-for="p in grp.programs" :key="p.id" :value="p.id">
                        {{ p.name }}
                      </option>
                    </optgroup>
                  </select>
                </div>

                <div v-if="errors._form"
                     class="rounded-xl px-3 py-2.5 text-sm"
                     style="background: rgb(244 63 94 / 0.10); color: rgb(190 18 60);">
                  {{ errors._form }}
                </div>
              </form>
            </div>

            <!-- Footer -->
            <div v-if="!successId"
                 class="px-6 py-3 border-t flex flex-col-reverse sm:flex-row items-stretch sm:items-center justify-between gap-2"
                 :style="{ background: 'rgb(var(--bg-soft))', borderColor: 'rgb(var(--border))' }">
              <button class="btn-ghost btn-sm" :disabled="sending" @click="close">Bekor</button>
              <button class="btn-primary" :disabled="sending || !isValid" type="button" @click="submit">
                <span v-if="sending" class="inline-flex items-center gap-2">
                  <svg class="animate-spin" xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M21 12a9 9 0 1 1-6.219-8.56" />
                  </svg>
                  Yuborilmoqda...
                </span>
                <span v-else>Yuborish</span>
              </button>
            </div>
            <div v-else class="px-6 py-3 border-t"
                 :style="{ background: 'rgb(var(--bg-soft))', borderColor: 'rgb(var(--border))' }">
              <button class="btn-secondary w-full" @click="close">Yopish</button>
            </div>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>
