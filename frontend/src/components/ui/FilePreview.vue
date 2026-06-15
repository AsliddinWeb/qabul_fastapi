<script setup lang="ts">
/**
 * Visual preview for an already-uploaded file by id.
 *
 * Decides what to render from the file's mime_type:
 *   - image/*  → 160px thumbnail loaded from /files/{id}/download?token=…
 *                + lightbox on click
 *   - pdf      → big PDF tile with the filename; click opens in new tab
 *   - other    → generic doc tile
 *
 * Used by:
 *   - FileUpload (when modelValue is pre-set on load — formerly showed
 *     a generic "Avval yuklangan fayl" line)
 *   - ApplicantDetailPage diplom/transfer-diplom rows
 *
 * No upload/delete — see FileUpload for the editable counterpart.
 */
import { computed, onMounted, ref, watch } from 'vue'
import { FileText, FileImage, FileQuestion, ExternalLink, Loader2, X as XIcon } from 'lucide-vue-next'
import { filesApi, authedDownloadUrl, type FileMeta } from '@/api/files.api'

const props = defineProps<{
  fileId: string | null | undefined
  /** Label rendered above the preview. */
  label?: string
  /** "compact" shrinks the card; useful inside grids. */
  size?: 'normal' | 'compact'
}>()

const meta = ref<FileMeta | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)
const lightboxOpen = ref(false)

const isImage = computed(() => meta.value?.mime_type?.startsWith('image/') ?? false)
const isPdf = computed(() => meta.value?.mime_type === 'application/pdf')

const downloadUrl = computed<string | null>(() => {
  if (!props.fileId) return null
  return authedDownloadUrl(props.fileId)
})

async function load() {
  if (!props.fileId) {
    meta.value = null
    return
  }
  loading.value = true
  error.value = null
  try {
    meta.value = await filesApi.meta(props.fileId)
  } catch (e: any) {
    error.value = e?.response?.status === 404
      ? "Fayl topilmadi (yo'q yoki o'chirilgan)"
      : "Fayl ma'lumotini olib bo'lmadi"
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(() => props.fileId, load)

function fmtSize(b: number): string {
  if (b < 1024) return `${b} B`
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} KB`
  return `${(b / 1024 / 1024).toFixed(2)} MB`
}

function openLightbox() {
  if (!isImage.value) return
  lightboxOpen.value = true
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') lightboxOpen.value = false
}
</script>

<template>
  <div>
    <label v-if="label" class="field-label">{{ label }}</label>

    <!-- Empty (no file_id) -->
    <div v-if="!fileId"
         class="rounded-lg border border-dashed border-slate-200 dark:border-slate-700 p-3 text-center"
         :class="size === 'compact' ? 'text-xs' : 'text-sm'">
      <FileQuestion class="w-5 h-5 text-slate-400 mx-auto mb-1" />
      <div class="text-slate-500 dark:text-slate-400">Fayl yuklanmagan</div>
    </div>

    <div v-else-if="loading"
         class="rounded-lg border border-slate-200 dark:border-slate-700 p-3 flex items-center gap-2 bg-slate-50 dark:bg-slate-900/40">
      <Loader2 class="w-4 h-4 animate-spin text-slate-400" />
      <span class="text-xs text-slate-500">Yuklanmoqda...</span>
    </div>

    <div v-else-if="error"
         class="rounded-lg border border-amber-200 dark:border-amber-700/40 p-3 text-xs text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-500/10">
      {{ error }}
    </div>

    <!-- Image thumbnail -->
    <div v-else-if="isImage && downloadUrl"
         class="group rounded-lg overflow-hidden ring-1 ring-slate-200 dark:ring-slate-700 bg-slate-50 dark:bg-slate-900/60">
      <button type="button" class="block w-full focus:outline-none focus:ring-2 focus:ring-brand-500"
              @click="openLightbox">
        <img :src="downloadUrl" :alt="meta?.original_name || 'image'"
             class="w-full object-contain bg-checkerboard"
             :class="size === 'compact' ? 'max-h-32' : 'max-h-48'" />
      </button>
      <div class="p-2 border-t border-slate-100 dark:border-slate-800 flex items-center gap-2 text-[11px]">
        <FileImage class="w-3.5 h-3.5 text-slate-400 shrink-0" />
        <span class="truncate flex-1 text-slate-700 dark:text-slate-300">{{ meta?.original_name }}</span>
        <span class="text-slate-400 dark:text-slate-500 shrink-0" v-if="meta">{{ fmtSize(meta.size_bytes) }}</span>
        <a :href="downloadUrl" target="_blank" rel="noopener"
           class="icon-btn !w-6 !h-6" title="Yangi oynada ochish">
          <ExternalLink class="w-3 h-3" />
        </a>
      </div>
    </div>

    <!-- PDF tile -->
    <a v-else-if="isPdf && downloadUrl" :href="downloadUrl" target="_blank" rel="noopener"
       class="block rounded-lg ring-1 ring-rose-200 dark:ring-rose-700/40 bg-gradient-to-br from-rose-50 to-rose-100/60 dark:from-rose-500/10 dark:to-rose-500/5 hover:ring-rose-300 dark:hover:ring-rose-600 transition p-3 flex items-center gap-3"
       title="PDF ni yangi oynada ochish">
      <div class="w-10 h-12 rounded grid place-items-center bg-rose-600 text-white text-[10px] font-bold shrink-0">PDF</div>
      <div class="min-w-0 flex-1">
        <div class="text-sm font-medium text-slate-900 dark:text-slate-100 truncate">{{ meta?.original_name }}</div>
        <div class="text-[11px] text-slate-500 dark:text-slate-400" v-if="meta">
          {{ fmtSize(meta.size_bytes) }} · PDF hujjat
        </div>
      </div>
      <ExternalLink class="w-4 h-4 text-rose-500 shrink-0" />
    </a>

    <!-- Generic file tile -->
    <a v-else-if="downloadUrl" :href="downloadUrl" target="_blank" rel="noopener"
       class="block rounded-lg ring-1 ring-slate-200 dark:ring-slate-700 bg-white dark:bg-slate-900 hover:ring-slate-300 dark:hover:ring-slate-600 transition p-3 flex items-center gap-3">
      <FileText class="w-5 h-5 text-slate-500 shrink-0" />
      <div class="min-w-0 flex-1">
        <div class="text-sm font-medium text-slate-900 dark:text-slate-100 truncate">{{ meta?.original_name }}</div>
        <div class="text-[11px] text-slate-500 dark:text-slate-400" v-if="meta">
          {{ meta.mime_type }} · {{ fmtSize(meta.size_bytes) }}
        </div>
      </div>
      <ExternalLink class="w-4 h-4 text-slate-400 shrink-0" />
    </a>

    <!-- Image lightbox. Plain inline modal — clicking the backdrop or
         pressing Escape closes. Z-50 keeps it above the rest of the UI. -->
    <Teleport to="body">
      <div v-if="lightboxOpen && isImage && downloadUrl"
           class="fixed inset-0 z-50 bg-black/85 backdrop-blur-sm grid place-items-center p-4"
           @click.self="lightboxOpen = false"
           @keydown="onKeydown" tabindex="0" ref="lightboxRef">
        <button type="button"
                class="absolute top-4 right-4 w-10 h-10 rounded-full bg-white/10 hover:bg-white/20 text-white grid place-items-center"
                @click="lightboxOpen = false" title="Yopish (Esc)">
          <XIcon class="w-5 h-5" />
        </button>
        <img :src="downloadUrl" :alt="meta?.original_name || ''"
             class="max-w-full max-h-full object-contain rounded-lg shadow-2xl" />
        <a v-if="downloadUrl" :href="downloadUrl" target="_blank" rel="noopener"
           class="absolute bottom-4 right-4 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/10 hover:bg-white/20 text-white text-xs font-medium">
          <ExternalLink class="w-3.5 h-3.5" /> Yangi oynada ochish
        </a>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
/* Checkered background so transparent PNGs (e.g. passport scans with
   white margins removed) read as "image area" not "missing render". */
.bg-checkerboard {
  background-image:
    linear-gradient(45deg, rgba(0,0,0,0.04) 25%, transparent 25%),
    linear-gradient(-45deg, rgba(0,0,0,0.04) 25%, transparent 25%),
    linear-gradient(45deg, transparent 75%, rgba(0,0,0,0.04) 75%),
    linear-gradient(-45deg, transparent 75%, rgba(0,0,0,0.04) 75%);
  background-size: 16px 16px;
  background-position: 0 0, 0 8px, 8px -8px, -8px 0;
}
</style>
