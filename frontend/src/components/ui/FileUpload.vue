<script setup lang="ts">
import { ref } from 'vue'
import { Upload, FileText, ImageIcon, X as XIcon, Loader2 } from 'lucide-vue-next'
import { http } from '@/api/http'

const props = defineProps<{
  modelValue: string | null
  label?: string
  hint?: string
  subdir?: string
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', v: string | null): void
  (e: 'uploaded', meta: { id: string; original_name: string; mime_type: string; url: string }): void
}>()

const fileMeta = ref<{ id: string; original_name: string; mime_type: string; size_bytes: number; url: string } | null>(null)
const uploading = ref(false)
const error = ref<string | null>(null)
const inputEl = ref<HTMLInputElement | null>(null)

async function onPick(e: Event) {
  const f = (e.target as HTMLInputElement).files?.[0]
  if (!f) return
  await upload(f)
  if (inputEl.value) inputEl.value.value = ''
}

async function onDrop(e: DragEvent) {
  e.preventDefault()
  const f = e.dataTransfer?.files?.[0]
  if (f) await upload(f)
}

async function upload(file: File) {
  error.value = null
  uploading.value = true
  try {
    const fd = new FormData()
    fd.append('file', file)
    if (props.subdir) fd.append('subdir', props.subdir)
    const res = await http.post('/files/upload', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    fileMeta.value = res.data
    emit('update:modelValue', res.data.id)
    emit('uploaded', res.data)
  } catch (e: any) {
    const msg = e?.response?.data?.detail || e?.response?.data?.error?.message || "Yuklab bo'lmadi"
    error.value = String(msg)
  } finally {
    uploading.value = false
  }
}

function clear() {
  fileMeta.value = null
  emit('update:modelValue', null)
}

function fmtSize(b: number): string {
  if (b < 1024) return `${b} B`
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} KB`
  return `${(b / 1024 / 1024).toFixed(2)} MB`
}
</script>

<template>
  <div>
    <label v-if="label" class="field-label">{{ label }}</label>

    <div v-if="!modelValue && !uploading"
         class="relative rounded-xl border-2 border-dashed border-slate-200 dark:border-slate-700
                hover:border-slate-300 dark:hover:border-slate-600 transition-colors
                bg-slate-50/40 dark:bg-slate-900/40 p-4 text-center cursor-pointer"
         @dragover.prevent
         @drop="onDrop"
         @click="inputEl?.click()">
      <input ref="inputEl" type="file" class="hidden"
             accept="application/pdf,image/jpeg,image/png,image/webp,image/heic,image/heif"
             @change="onPick" />
      <Upload class="w-5 h-5 text-slate-400 mx-auto mb-1" />
      <div class="text-sm font-medium text-slate-700 dark:text-slate-300">Faylni shu yerga tashlang yoki bosing</div>
      <div class="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">PDF yoki rasm (JPG/PNG/WEBP) · max 25 MB</div>
    </div>

    <div v-else-if="uploading"
         class="rounded-xl border border-slate-200 dark:border-slate-700 p-3 flex items-center gap-3 bg-slate-50 dark:bg-slate-800/40">
      <Loader2 class="w-4 h-4 animate-spin text-slate-500" />
      <div class="text-sm text-slate-600 dark:text-slate-400">Yuklanmoqda...</div>
    </div>

    <div v-else
         class="rounded-xl border border-slate-200 dark:border-slate-700 p-3 flex items-center gap-3 bg-white dark:bg-slate-900">
      <component :is="fileMeta?.mime_type?.startsWith('image/') ? ImageIcon : FileText"
                 class="w-5 h-5 text-slate-500 shrink-0" />
      <div class="min-w-0 flex-1">
        <div class="text-sm font-medium text-slate-900 dark:text-slate-100 truncate">
          {{ fileMeta?.original_name || 'Yuklangan fayl' }}
        </div>
        <div v-if="fileMeta" class="text-[11px] text-slate-500 dark:text-slate-400">
          {{ fileMeta.mime_type }} · {{ fmtSize(fileMeta.size_bytes) }}
        </div>
        <div v-else class="text-[11px] text-slate-500 dark:text-slate-400">
          Avval yuklangan fayl
        </div>
      </div>
      <a v-if="fileMeta?.url" :href="fileMeta.url" target="_blank" rel="noopener"
         class="icon-btn" title="Ochish">
        <FileText class="w-4 h-4" />
      </a>
      <button type="button" class="icon-btn-danger" title="Olib tashlash" @click="clear">
        <XIcon class="w-4 h-4" />
      </button>
    </div>

    <p v-if="error" class="field-error">{{ error }}</p>
    <p v-if="hint && !error" class="field-hint">{{ hint }}</p>
  </div>
</template>
