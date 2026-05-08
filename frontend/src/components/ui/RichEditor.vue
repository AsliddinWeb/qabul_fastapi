<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useEditor, EditorContent } from '@tiptap/vue-3'
import { Extension } from '@tiptap/core'
import StarterKit from '@tiptap/starter-kit'
import Underline from '@tiptap/extension-underline'
import TextAlign from '@tiptap/extension-text-align'
import Placeholder from '@tiptap/extension-placeholder'
import Table from '@tiptap/extension-table'
import TableRow from '@tiptap/extension-table-row'
import TableCell from '@tiptap/extension-table-cell'
import TableHeader from '@tiptap/extension-table-header'
import TextStyle from '@tiptap/extension-text-style'
import Color from '@tiptap/extension-color'
import Highlight from '@tiptap/extension-highlight'
import FontFamily from '@tiptap/extension-font-family'
import Link from '@tiptap/extension-link'
import {
  Bold, Italic, Underline as UnderlineIcon, Strikethrough,
  Heading1, Heading2, Heading3,
  List, ListOrdered, Quote,
  AlignLeft, AlignCenter, AlignRight, AlignJustify,
  Table as TableIcon, Trash2, Undo2, Redo2,
  Minus, Type as TypeIcon, Palette, Highlighter,
  Link as LinkIcon, Eraser, Subscript, Superscript,
} from 'lucide-vue-next'

const props = defineProps<{
  modelValue: string
  placeholder?: string
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
}>()

// ====== Custom FontSize extension (extends TextStyle) ======
const FontSize = Extension.create({
  name: 'fontSize',
  addOptions() {
    return { types: ['textStyle'] as string[] }
  },
  addGlobalAttributes() {
    return [
      {
        types: this.options.types,
        attributes: {
          fontSize: {
            default: null,
            parseHTML: (el: HTMLElement) => el.style.fontSize?.replace(/['"]+/g, '') || null,
            renderHTML: (attrs: any) => attrs.fontSize ? { style: `font-size: ${attrs.fontSize}` } : {},
          },
        },
      },
    ]
  },
  addCommands() {
    return {
      setFontSize:
        (size: string) =>
        ({ chain }: any) =>
          chain().setMark('textStyle', { fontSize: size }).run(),
      unsetFontSize:
        () =>
        ({ chain }: any) =>
          chain().setMark('textStyle', { fontSize: null }).removeEmptyTextStyle().run(),
    } as any
  },
})

// ====== Custom LineHeight extension (applies to paragraph/heading) ======
const LineHeight = Extension.create({
  name: 'lineHeight',
  addOptions() {
    return { types: ['paragraph', 'heading'] as string[] }
  },
  addGlobalAttributes() {
    return [
      {
        types: this.options.types,
        attributes: {
          lineHeight: {
            default: null,
            parseHTML: (el: HTMLElement) => el.style.lineHeight || null,
            renderHTML: (attrs: any) => attrs.lineHeight ? { style: `line-height: ${attrs.lineHeight}` } : {},
          },
        },
      },
    ]
  },
  addCommands() {
    return {
      setLineHeight:
        (lh: string) =>
        ({ commands }: any) => {
          let result = false
          for (const t of (this.options.types as string[])) {
            if (commands.updateAttributes(t, { lineHeight: lh })) result = true
          }
          return result
        },
    } as any
  },
})

const editor = useEditor({
  content: props.modelValue,
  extensions: [
    StarterKit.configure({ heading: { levels: [1, 2, 3] } }),
    Underline,
    TextStyle,
    Color,
    Highlight.configure({ multicolor: true }),
    FontFamily,
    FontSize,
    LineHeight,
    TextAlign.configure({ types: ['heading', 'paragraph'] }),
    Placeholder.configure({ placeholder: props.placeholder || 'Shartnoma matnini shu yerda yozing...' }),
    Table.configure({ resizable: true }),
    TableRow,
    TableHeader,
    TableCell,
    Link.configure({ openOnClick: false, HTMLAttributes: { rel: 'noopener noreferrer' } }),
  ],
  editorProps: {
    attributes: {
      class: 'rich-content focus:outline-none min-h-[480px] px-8 py-6 leading-relaxed',
    },
  },
  onUpdate: ({ editor }) => {
    emit('update:modelValue', editor.getHTML())
  },
})

watch(
  () => props.modelValue,
  (val) => {
    if (!editor.value) return
    if (editor.value.getHTML() === val) return
    editor.value.commands.setContent(val, false)
  },
)

onBeforeUnmount(() => editor.value?.destroy())

defineExpose({
  insertText(text: string) {
    editor.value?.chain().focus().insertContent(text).run()
  },
})

// === Toolbar models ===
const FONT_FAMILIES: { v: string; label: string }[] = [
  { v: '', label: 'Default' },
  { v: 'Inter, sans-serif',                label: 'Inter' },
  { v: 'Arial, Helvetica, sans-serif',     label: 'Arial' },
  { v: '"Times New Roman", Times, serif',  label: 'Times New Roman' },
  { v: 'Georgia, serif',                   label: 'Georgia' },
  { v: 'Calibri, sans-serif',              label: 'Calibri' },
  { v: 'Tahoma, sans-serif',               label: 'Tahoma' },
  { v: 'Verdana, sans-serif',              label: 'Verdana' },
  { v: '"Courier New", Courier, monospace', label: 'Courier New' },
  { v: '"Trebuchet MS", sans-serif',       label: 'Trebuchet MS' },
]
const FONT_SIZES = ['8px', '9px', '10px', '11px', '12px', '14px', '16px', '18px', '20px', '24px', '28px', '32px', '36px', '48px']
const LINE_HEIGHTS = [
  { v: '', label: 'Default' },
  { v: '1',    label: '1.0' },
  { v: '1.15', label: '1.15' },
  { v: '1.5',  label: '1.5' },
  { v: '1.75', label: '1.75' },
  { v: '2',    label: '2.0' },
]
const TEXT_COLORS  = ['#000000','#1f2937','#475569','#dc2626','#ea580c','#ca8a04','#16a34a','#0284c7','#7c3aed','#db2777']
const HILITE_COLORS = ['transparent','#fef08a','#fde68a','#fecaca','#bbf7d0','#bfdbfe','#e9d5ff','#fbcfe8']

const currentFontFamily = computed(() => editor.value?.getAttributes('textStyle')?.fontFamily || '')
const currentFontSize   = computed(() => editor.value?.getAttributes('textStyle')?.fontSize || '')
const currentLineHeight = computed(() => {
  const ed = editor.value
  if (!ed) return ''
  return ed.getAttributes('paragraph')?.lineHeight || ed.getAttributes('heading')?.lineHeight || ''
})

function setFontFamily(v: string) {
  if (!editor.value) return
  if (v) editor.value.chain().focus().setFontFamily(v).run()
  else editor.value.chain().focus().unsetFontFamily().run()
}
function setFontSize(v: string) {
  if (!editor.value) return
  if (v) (editor.value as any).chain().focus().setFontSize(v).run()
  else (editor.value as any).chain().focus().unsetFontSize().run()
}
function setLH(v: string) {
  if (!editor.value) return
  if (v) (editor.value as any).chain().focus().setLineHeight(v).run()
  else (editor.value as any).chain().focus().updateAttributes('paragraph', { lineHeight: null }).updateAttributes('heading', { lineHeight: null }).run()
}
function setColor(c: string) {
  if (!editor.value) return
  editor.value.chain().focus().setColor(c).run()
}
function unsetColor() {
  editor.value?.chain().focus().unsetColor().run()
}
function setHighlight(c: string) {
  if (!editor.value) return
  if (c === 'transparent') editor.value.chain().focus().unsetHighlight().run()
  else editor.value.chain().focus().toggleHighlight({ color: c }).run()
}
function clearFormatting() {
  editor.value?.chain().focus().unsetAllMarks().clearNodes().run()
}
function addLink() {
  const url = window.prompt('URL kiriting (https://...)')
  if (!url) return
  editor.value?.chain().focus().setLink({ href: url }).run()
}
function removeLink() {
  editor.value?.chain().focus().unsetLink().run()
}

const headingLevels: { level: 1 | 2 | 3; icon: any }[] = [
  { level: 1, icon: Heading1 },
  { level: 2, icon: Heading2 },
  { level: 3, icon: Heading3 },
]

const colorMenu = ref(false)
const hiliteMenu = ref(false)
const fontMenu = ref(false)
const sizeMenu = ref(false)
const lhMenu = ref(false)

function closeAllMenus() {
  colorMenu.value = false; hiliteMenu.value = false
  fontMenu.value = false; sizeMenu.value = false; lhMenu.value = false
}
function toggle(name: 'color' | 'hilite' | 'font' | 'size' | 'lh') {
  const open = ({
    color:  colorMenu.value,
    hilite: hiliteMenu.value,
    font:   fontMenu.value,
    size:   sizeMenu.value,
    lh:     lhMenu.value,
  } as any)[name] as boolean
  closeAllMenus()
  if (!open) {
    if (name === 'color')  colorMenu.value = true
    if (name === 'hilite') hiliteMenu.value = true
    if (name === 'font')   fontMenu.value = true
    if (name === 'size')   sizeMenu.value = true
    if (name === 'lh')     lhMenu.value = true
  }
}
</script>

<template>
  <div class="rich-editor border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden bg-white dark:bg-slate-900">
    <!-- Toolbar -->
    <div v-if="editor"
         class="sticky top-0 z-10 flex flex-wrap items-center gap-0.5 p-1.5
                border-b border-slate-200 dark:border-slate-800
                bg-white/95 dark:bg-slate-900/95 backdrop-blur"
         @click.stop>
      <!-- History -->
      <button class="tb-btn" :disabled="!editor.can().undo()" @click="editor.chain().focus().undo().run()" title="Ortga (Cmd+Z)">
        <Undo2 class="w-4 h-4" />
      </button>
      <button class="tb-btn" :disabled="!editor.can().redo()" @click="editor.chain().focus().redo().run()" title="Oldinga (Cmd+Shift+Z)">
        <Redo2 class="w-4 h-4" />
      </button>

      <span class="tb-divider" />

      <!-- Font family -->
      <div class="relative">
        <button type="button" class="tb-select" @click="toggle('font')" title="Font">
          <TypeIcon class="w-3.5 h-3.5 text-slate-500" />
          <span class="truncate max-w-[100px]">
            {{ FONT_FAMILIES.find((f) => f.v === currentFontFamily)?.label || 'Font' }}
          </span>
        </button>
        <div v-if="fontMenu" class="tb-menu w-44">
          <button v-for="f in FONT_FAMILIES" :key="f.v"
                  class="tb-menu-item"
                  :class="{ 'tb-menu-active': currentFontFamily === f.v }"
                  :style="f.v ? { fontFamily: f.v } : {}"
                  @click="setFontFamily(f.v); fontMenu = false">
            {{ f.label }}
          </button>
        </div>
      </div>

      <!-- Font size -->
      <div class="relative">
        <button type="button" class="tb-select" @click="toggle('size')" title="Hajm">
          <span class="text-[11px] font-mono">{{ currentFontSize?.replace('px','') || '–' }}</span>
        </button>
        <div v-if="sizeMenu" class="tb-menu w-20 max-h-64 overflow-auto">
          <button class="tb-menu-item" :class="{ 'tb-menu-active': !currentFontSize }" @click="setFontSize(''); sizeMenu = false">
            Default
          </button>
          <button v-for="s in FONT_SIZES" :key="s"
                  class="tb-menu-item"
                  :class="{ 'tb-menu-active': currentFontSize === s }"
                  @click="setFontSize(s); sizeMenu = false">
            {{ s.replace('px', '') }}
          </button>
        </div>
      </div>

      <!-- Line height -->
      <div class="relative">
        <button type="button" class="tb-select" @click="toggle('lh')" title="Qator oraligi">
          <span class="text-[11px]">↕ {{ LINE_HEIGHTS.find((l) => l.v === currentLineHeight)?.label || '–' }}</span>
        </button>
        <div v-if="lhMenu" class="tb-menu w-24">
          <button v-for="l in LINE_HEIGHTS" :key="l.v"
                  class="tb-menu-item"
                  :class="{ 'tb-menu-active': currentLineHeight === l.v }"
                  @click="setLH(l.v); lhMenu = false">
            {{ l.label }}
          </button>
        </div>
      </div>

      <span class="tb-divider" />

      <!-- Inline formatting -->
      <button class="tb-btn" :class="{ 'tb-active': editor.isActive('bold') }" @click="editor.chain().focus().toggleBold().run()" title="Qalin">
        <Bold class="w-4 h-4" />
      </button>
      <button class="tb-btn" :class="{ 'tb-active': editor.isActive('italic') }" @click="editor.chain().focus().toggleItalic().run()" title="Qiya">
        <Italic class="w-4 h-4" />
      </button>
      <button class="tb-btn" :class="{ 'tb-active': editor.isActive('underline') }" @click="editor.chain().focus().toggleUnderline().run()" title="Tagchi">
        <UnderlineIcon class="w-4 h-4" />
      </button>
      <button class="tb-btn" :class="{ 'tb-active': editor.isActive('strike') }" @click="editor.chain().focus().toggleStrike().run()" title="Chizilgan">
        <Strikethrough class="w-4 h-4" />
      </button>

      <!-- Color -->
      <div class="relative">
        <button type="button" class="tb-btn" @click="toggle('color')" title="Matn rangi">
          <Palette class="w-4 h-4" />
        </button>
        <div v-if="colorMenu" class="tb-menu p-2 w-44">
          <div class="grid grid-cols-5 gap-1.5">
            <button v-for="c in TEXT_COLORS" :key="c" :title="c"
                    class="w-7 h-7 rounded-md border border-slate-200 dark:border-slate-700 hover:scale-110 transition"
                    :style="{ backgroundColor: c }"
                    @click="setColor(c); colorMenu = false" />
          </div>
          <button class="mt-2 w-full text-left text-xs text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800 rounded px-2 py-1"
                  @click="unsetColor(); colorMenu = false">
            Tozalash
          </button>
        </div>
      </div>

      <!-- Highlight -->
      <div class="relative">
        <button type="button" class="tb-btn" @click="toggle('hilite')" title="Belgilash">
          <Highlighter class="w-4 h-4" />
        </button>
        <div v-if="hiliteMenu" class="tb-menu p-2 w-40">
          <div class="grid grid-cols-4 gap-1.5">
            <button v-for="c in HILITE_COLORS" :key="c" :title="c === 'transparent' ? 'Olib tashlash' : c"
                    class="w-7 h-7 rounded-md border border-slate-200 dark:border-slate-700 hover:scale-110 transition"
                    :style="{ backgroundColor: c === 'transparent' ? 'transparent' : c, backgroundImage: c === 'transparent' ? 'linear-gradient(45deg,#ef4444 50%,transparent 50%)' : '' }"
                    @click="setHighlight(c); hiliteMenu = false" />
          </div>
        </div>
      </div>

      <span class="tb-divider" />

      <!-- Headings -->
      <button
        v-for="h in headingLevels"
        :key="h.level"
        class="tb-btn"
        :class="{ 'tb-active': editor.isActive('heading', { level: h.level }) }"
        :title="`Sarlavha ${h.level}`"
        @click="editor.chain().focus().toggleHeading({ level: h.level }).run()"
      >
        <component :is="h.icon" class="w-4 h-4" />
      </button>

      <span class="tb-divider" />

      <!-- Lists -->
      <button class="tb-btn" :class="{ 'tb-active': editor.isActive('bulletList') }" @click="editor.chain().focus().toggleBulletList().run()" title="Belgilangan ro'yxat">
        <List class="w-4 h-4" />
      </button>
      <button class="tb-btn" :class="{ 'tb-active': editor.isActive('orderedList') }" @click="editor.chain().focus().toggleOrderedList().run()" title="Raqamli ro'yxat">
        <ListOrdered class="w-4 h-4" />
      </button>
      <button class="tb-btn" :class="{ 'tb-active': editor.isActive('blockquote') }" @click="editor.chain().focus().toggleBlockquote().run()" title="Iqtibos">
        <Quote class="w-4 h-4" />
      </button>
      <button class="tb-btn" @click="editor.chain().focus().setHorizontalRule().run()" title="Ajratuvchi chiziq">
        <Minus class="w-4 h-4" />
      </button>

      <span class="tb-divider" />

      <!-- Alignment -->
      <button class="tb-btn" :class="{ 'tb-active': editor.isActive({ textAlign: 'left' }) }" @click="editor.chain().focus().setTextAlign('left').run()" title="Chap">
        <AlignLeft class="w-4 h-4" />
      </button>
      <button class="tb-btn" :class="{ 'tb-active': editor.isActive({ textAlign: 'center' }) }" @click="editor.chain().focus().setTextAlign('center').run()" title="Markaz">
        <AlignCenter class="w-4 h-4" />
      </button>
      <button class="tb-btn" :class="{ 'tb-active': editor.isActive({ textAlign: 'right' }) }" @click="editor.chain().focus().setTextAlign('right').run()" title="O'ng">
        <AlignRight class="w-4 h-4" />
      </button>
      <button class="tb-btn" :class="{ 'tb-active': editor.isActive({ textAlign: 'justify' }) }" @click="editor.chain().focus().setTextAlign('justify').run()" title="Tekislash">
        <AlignJustify class="w-4 h-4" />
      </button>

      <span class="tb-divider" />

      <!-- Link / clear -->
      <button class="tb-btn" :class="{ 'tb-active': editor.isActive('link') }" @click="addLink" title="Havola qo'shish">
        <LinkIcon class="w-4 h-4" />
      </button>
      <button class="tb-btn" :disabled="!editor.isActive('link')" @click="removeLink" title="Havolani olib tashlash">
        <LinkIcon class="w-4 h-4 line-through" />
      </button>
      <button class="tb-btn" @click="clearFormatting" title="Formatlashni tozalash">
        <Eraser class="w-4 h-4" />
      </button>

      <span class="tb-divider" />

      <!-- Table -->
      <button class="tb-btn" @click="editor.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run()" title="Jadval qo'shish">
        <TableIcon class="w-4 h-4" />
      </button>
      <button class="tb-btn" :disabled="!editor.can().deleteTable()" @click="editor.chain().focus().deleteTable().run()" title="Jadvalni o'chirish">
        <Trash2 class="w-4 h-4" />
      </button>
    </div>

    <!-- A4-like editing surface -->
    <div class="rich-page bg-slate-100 dark:bg-slate-950 px-2 sm:px-4 py-4 max-h-[700px] overflow-auto">
      <div class="mx-auto max-w-[820px] bg-white dark:bg-slate-900 shadow-sm rounded-md">
        <EditorContent :editor="editor" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.tb-btn {
  @apply inline-flex items-center justify-center w-8 h-8 rounded-md
         text-slate-700 dark:text-slate-300
         hover:bg-slate-200/70 dark:hover:bg-slate-800
         disabled:opacity-40 disabled:pointer-events-none
         transition-colors;
}
.tb-active {
  @apply bg-slate-900 text-white dark:bg-white dark:text-slate-900;
}
.tb-divider {
  @apply w-px h-5 bg-slate-200 dark:bg-slate-800 mx-1;
}
.tb-select {
  @apply inline-flex items-center gap-1 h-8 px-2 rounded-md text-xs
         text-slate-700 dark:text-slate-300
         hover:bg-slate-200/70 dark:hover:bg-slate-800
         transition-colors;
}
.tb-menu {
  @apply absolute z-30 mt-1 left-0 rounded-lg bg-white dark:bg-slate-900
         border border-slate-200 dark:border-slate-700 shadow-lg p-1;
}
.tb-menu-item {
  @apply block w-full text-left text-sm px-2.5 py-1.5 rounded-md
         hover:bg-slate-100 dark:hover:bg-slate-800
         text-slate-800 dark:text-slate-100;
}
.tb-menu-active {
  @apply bg-slate-100 dark:bg-slate-800;
}
</style>

<style>
.rich-editor .ProseMirror { color: #0f172a; font-size: 0.95rem; }
.rich-editor .ProseMirror h1 { font-size: 1.6rem; font-weight: 700; margin: 1rem 0 0.5rem; }
.rich-editor .ProseMirror h2 { font-size: 1.3rem; font-weight: 600; margin: 0.9rem 0 0.4rem; }
.rich-editor .ProseMirror h3 { font-size: 1.1rem; font-weight: 600; margin: 0.7rem 0 0.3rem; }
.rich-editor .ProseMirror p { margin: 0.5rem 0; }
.rich-editor .ProseMirror ul { list-style: disc; padding-left: 1.5rem; margin: 0.5rem 0; }
.rich-editor .ProseMirror ol { list-style: decimal; padding-left: 1.5rem; margin: 0.5rem 0; }
.rich-editor .ProseMirror li { margin: 0.25rem 0; }
.rich-editor .ProseMirror blockquote { border-left: 3px solid #cbd5e1; padding-left: 0.75rem; color: #475569; margin: 0.75rem 0; }
.rich-editor .ProseMirror hr { border: 0; border-top: 1px solid #e2e8f0; margin: 1rem 0; }
.rich-editor .ProseMirror table { border-collapse: collapse; width: 100%; margin: 0.75rem 0; }
.rich-editor .ProseMirror th, .rich-editor .ProseMirror td {
  border: 1px solid #cbd5e1; padding: 6px 8px; vertical-align: top;
}
.rich-editor .ProseMirror th { background: #f1f5f9; font-weight: 600; text-align: left; }
.rich-editor .ProseMirror a { color: #4f46e5; text-decoration: underline; }
.rich-editor .ProseMirror p.is-editor-empty:first-child::before {
  content: attr(data-placeholder);
  color: #94a3b8;
  float: left;
  height: 0;
  pointer-events: none;
}
.rich-editor .ProseMirror:focus { outline: none; }

/* Dark mode */
html.dark .rich-editor .ProseMirror { color: #f1f5f9; }
html.dark .rich-editor .ProseMirror blockquote { border-left-color: #475569; color: #cbd5e1; }
html.dark .rich-editor .ProseMirror hr { border-top-color: #334155; }
html.dark .rich-editor .ProseMirror th, html.dark .rich-editor .ProseMirror td { border-color: #475569; }
html.dark .rich-editor .ProseMirror th { background: #1e293b; }
html.dark .rich-editor .ProseMirror a { color: #818cf8; }
html.dark .rich-editor .ProseMirror p.is-editor-empty:first-child::before { color: #64748b; }
</style>
