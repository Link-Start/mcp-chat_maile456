<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'

type NoteTag = 'note' | 'idea' | 'todo'
type FilterTag = 'all' | NoteTag

interface Note {
  id: string
  text: string
  tag: NoteTag
  pinned: boolean
  done: boolean
  createdAt: number
}

const TAG_META: Record<NoteTag, { label: string; color: string }> = {
  note: { label: '笔记', color: '#9aa0a6' },
  idea: { label: '想法', color: '#8ab4f8' },
  todo: { label: '待办', color: '#f9ab00' },
}

const STORAGE_KEY = 'mcp-notes'

const notes = ref<Note[]>([])
const open = ref(false)
const input = ref('')
const inputTag = ref<NoteTag>('note')
const filterTag = ref<FilterTag>('all')
const search = ref('')
const editingId = ref('')
const editText = ref('')
const inputEl = ref<HTMLTextAreaElement | null>(null)
const editEl = ref<HTMLTextAreaElement | null>(null)
const panelEl = ref<HTMLElement | null>(null)
const fabEl = ref<HTMLElement | null>(null)

const dragIdx = ref(-1)
const dropIdx = ref(-1)

try {
  const saved = localStorage.getItem(STORAGE_KEY)
  if (saved) {
    const parsed = JSON.parse(saved)
    notes.value = parsed.map((n: any) => ({
      id: n.id || Date.now().toString(36),
      text: n.text || '',
      tag: (n.tag && ['note','idea','todo'].includes(n.tag)) ? n.tag : 'note',
      pinned: !!n.pinned,
      done: !!n.done,
      createdAt: n.createdAt || Date.now(),
    }))
  }
} catch {}

watch(notes, (v) => {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(v)) } catch {}
}, { deep: true })

const filtered = computed(() => {
  let list = notes.value
  if (filterTag.value !== 'all') {
    list = list.filter(n => n.tag === filterTag.value)
  }
  if (search.value.trim()) {
    const q = search.value.toLowerCase()
    list = list.filter(n => n.text.toLowerCase().includes(q))
  }
  return [...list].sort((a, b) => (b.pinned ? 1 : 0) - (a.pinned ? 1 : 0))
})

const totalCount = computed(() => notes.value.length)
const todoCount = computed(() => notes.value.filter(n => n.tag === 'todo' && !n.done).length)
const doneCount = computed(() => notes.value.filter(n => n.tag === 'todo' && n.done).length)
const tagCounts = computed(() => ({
  all: notes.value.length,
  note: notes.value.filter(n => n.tag === 'note').length,
  idea: notes.value.filter(n => n.tag === 'idea').length,
  todo: notes.value.filter(n => n.tag === 'todo').length,
}))

function genId() {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 6)
}

function relTime(ts: number): string {
  const diff = Math.floor((Date.now() - ts) / 1000)
  if (diff < 60) return '刚刚'
  if (diff < 3600) return Math.floor(diff / 60) + '分钟前'
  if (diff < 86400) return Math.floor(diff / 3600) + '小时前'
  if (diff < 604800) return Math.floor(diff / 86400) + '天前'
  return new Date(ts).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}


function addNote() {
  const text = input.value.trim()
  if (!text) return
  notes.value.unshift({ id: genId(), text, tag: inputTag.value, pinned: false, done: false, createdAt: Date.now() })
  input.value = ''
  nextTick(() => autoGrow(inputEl.value))
}

function remove(id: string) {
  notes.value = notes.value.filter(n => n.id !== id)
  if (editingId.value === id) editingId.value = ''
}

function clearDone() {
  notes.value = notes.value.filter(n => !(n.tag === 'todo' && n.done))
}

function togglePin(n: Note) { n.pinned = !n.pinned }
function toggleDone(n: Note) { n.done = !n.done }

function cycleTag(n: Note) {
  const tags: NoteTag[] = ['note', 'idea', 'todo']
  n.tag = tags[(tags.indexOf(n.tag) + 1) % tags.length]
}

function startEdit(n: Note) {
  editingId.value = n.id
  editText.value = n.text
  nextTick(() => {
    editEl.value?.focus()
    autoGrow(editEl.value)
  })
}

function saveEdit(n: Note) {
  const trimmed = editText.value.trim()
  if (trimmed) n.text = trimmed
  editingId.value = ''
}

function autoGrow(el: HTMLTextAreaElement | null) {
  if (!el) return
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 180) + 'px'
}

function onDragStart(idx: number, e: DragEvent) {
  dragIdx.value = idx
  if (e.dataTransfer) {
    e.dataTransfer.effectAllowed = 'move'
    e.dataTransfer.setData('text/plain', '')
  }
}
function onDragOver(idx: number, e: DragEvent) {
  e.preventDefault()
  if (e.dataTransfer) e.dataTransfer.dropEffect = 'move'
  dropIdx.value = idx
}
function onDragLeave() { dropIdx.value = -1 }
function onDrop(idx: number) {
  if (dragIdx.value < 0 || dragIdx.value === idx) { dragIdx.value = -1; dropIdx.value = -1; return }
  const arr = [...notes.value]
  const [item] = arr.splice(dragIdx.value, 1)
  arr.splice(idx, 0, item)
  notes.value = arr
  dragIdx.value = -1
  dropIdx.value = -1
}
function onDragEnd() { dragIdx.value = -1; dropIdx.value = -1 }

async function togglePanel() {
  open.value = !open.value
  if (open.value) {
    await nextTick()
    inputEl.value?.focus()
  }
}

function onDocClick(e: MouseEvent) {
  if (!open.value) return
  const t = e.target as Node
  if (panelEl.value?.contains(t) || fabEl.value?.contains(t)) return
  open.value = false
}
function onKey(e: KeyboardEvent) {
  // Ctrl+N / Cmd+N toggle panel
  if ((e.ctrlKey || e.metaKey) && e.key === 'n' && !e.shiftKey && !e.altKey) {
    e.preventDefault()
    togglePanel()
    return
  }
  if (e.key === 'Escape') {
    if (editingId.value) { editingId.value = ''; return }
    if (open.value) open.value = false
  }
}

onMounted(() => {
  document.addEventListener('mousedown', onDocClick)
  document.addEventListener('keydown', onKey)
})
onBeforeUnmount(() => {
  document.removeEventListener('mousedown', onDocClick)
  document.removeEventListener('keydown', onKey)
})
</script>

<template>
  <div class="notes-fab-root">
    <Transition name="notes-pop">
      <div
        v-if="open"
        ref="panelEl"
        class="fixed bottom-6 right-[76px] z-[60] w-[480px] h-[calc(100vh-5rem)] flex flex-col rounded-2xl bg-[#1a1b1e] border border-white/[0.06] shadow-2xl overflow-hidden"
        style="backdrop-filter: blur(20px)"
      >
        <!-- Header -->
        <div class="px-5 pt-4 pb-2 shrink-0">
          <div class="flex items-center justify-between mb-3">
            <span class="text-[15px] font-semibold text-zinc-100">Notes</span>
            <button class="text-zinc-500 hover:text-zinc-200 transition-colors p-1.5 -mr-1 rounded-lg hover:bg-white/5" @click="open = false">
              <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6L6 18M6 6l12 12" stroke-linecap="round"/></svg>
            </button>
          </div>
          <!-- Tag filter tabs -->
          <div class="flex items-center gap-1">
            <button
              v-for="t in (['all','note','idea','todo'] as FilterTag[])" :key="t"
              @click="filterTag = t"
              class="text-[11px] px-2.5 py-1 rounded-lg transition-all flex items-center gap-1"
              :class="filterTag === t
                ? 'text-zinc-100 bg-white/[0.08]'
                : 'text-zinc-500 hover:text-zinc-400 hover:bg-white/[0.03]'"
            >
              <span v-if="t !== 'all'" class="inline-block w-1.5 h-1.5 rounded-full" :style="{ background: TAG_META[t].color }" />
              {{ t === 'all' ? '全部' : TAG_META[t].label }}
              <span class="text-zinc-600 tabular-nums">{{ tagCounts[t] }}</span>
            </button>
          </div>
        </div>

        <!-- Search -->
        <div class="px-4 pb-2 shrink-0" v-if="totalCount > 3">
          <div class="flex items-center gap-2 bg-white/[0.04] rounded-lg px-3 py-1.5">
            <svg class="w-3.5 h-3.5 text-zinc-500 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35" stroke-linecap="round"/>
            </svg>
            <input v-model="search" placeholder="搜索..." class="flex-1 bg-transparent outline-none text-[13px] text-zinc-300 placeholder-zinc-600 py-0.5" />
            <button v-if="search" @click="search = ''" class="text-zinc-500 hover:text-zinc-300">
              <svg class="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6L6 18M6 6l12 12" stroke-linecap="round"/></svg>
            </button>
          </div>
        </div>

        <!-- Composer -->
        <div class="px-4 pb-3 shrink-0">
          <div class="bg-[#232528] rounded-xl overflow-hidden focus-within:ring-1 focus-within:ring-white/10 transition">
            <textarea
              ref="inputEl"
              v-model="input"
              @keydown.enter.exact.prevent="addNote"
              @input="autoGrow(inputEl)"
              placeholder="Ctrl+N 快速打开 · Enter 保存 · Shift+Enter 换行"
              rows="2"
              class="w-full bg-transparent outline-none text-[13px] text-zinc-100 placeholder-zinc-600 resize-none leading-relaxed max-h-[180px] px-3.5 pt-3 pb-1"
            />
            <div class="flex items-center justify-between px-2.5 pb-2">
              <div class="flex items-center gap-0.5">
                <button
                  v-for="t in (['note','idea','todo'] as NoteTag[])" :key="t"
                  @click="inputTag = t"
                  class="text-[11px] px-2 py-0.5 rounded-md transition-all"
                  :class="inputTag === t
                    ? 'text-zinc-100 bg-white/[0.08]'
                    : 'text-zinc-500 hover:text-zinc-400 hover:bg-white/[0.03]'"
                >
                  <span class="inline-block w-1.5 h-1.5 rounded-full mr-1" :style="{ background: TAG_META[t].color }" />{{ TAG_META[t].label }}
                </button>
              </div>
              <button
                @click="addNote"
                :disabled="!input.trim()"
                class="text-[12px] px-3 py-1 rounded-lg transition-all"
                :class="input.trim() ? 'text-[#8ab4f8] hover:bg-[#8ab4f8]/10' : 'text-zinc-600 cursor-default'"
              >
                <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14M12 5v14" stroke-linecap="round"/></svg>
              </button>
            </div>
          </div>
        </div>

        <!-- Notes list -->
        <div class="flex-1 min-h-0 overflow-y-auto px-3 pb-3 notes-scroll">
          <TransitionGroup name="note-list" tag="div">
            <div
              v-for="(n, idx) in filtered" :key="n.id"
              :draggable="editingId !== n.id"
              @dragstart="onDragStart(idx, $event)"
              @dragover="onDragOver(idx, $event)"
              @dragleave="onDragLeave"
              @drop="onDrop(idx)"
              @dragend="onDragEnd"
              class="note-card group mb-1.5 rounded-xl overflow-hidden"
              :class="[
                dragIdx === idx ? 'opacity-20 scale-[0.96]' : '',
                dropIdx === idx && dragIdx !== idx ? 'drop-target' : '',
              ]"
            >
              <div class="flex min-h-0">
                <div class="w-[3px] shrink-0" :style="{ background: n.done ? '#3f3f46' : (TAG_META[n.tag]?.color || '#9aa0a6') }" />
                <div class="flex-1 px-3 py-2.5 cursor-grab active:cursor-grabbing">
                  <!-- Edit mode -->
                  <div v-if="editingId === n.id" @click.stop>
                    <textarea
                      ref="editEl"
                      v-model="editText"
                      @keydown.enter.exact.prevent="saveEdit(n)"
                      @keydown.escape.prevent="editingId = ''"
                      @input="autoGrow(editEl)"
                      rows="2"
                      class="w-full bg-[#232528] rounded-lg px-3 py-2 outline-none text-[13px] text-zinc-100 resize-none leading-relaxed max-h-[180px] ring-1 ring-white/10"
                    />
                    <div class="flex justify-end gap-1.5 mt-2">
                      <button @click="editingId = ''" class="text-[11px] text-zinc-500 hover:text-zinc-300 px-2.5 py-1 rounded-md hover:bg-white/5 transition">取消</button>
                      <button @click="saveEdit(n)" class="text-[11px] text-[#8ab4f8] px-2.5 py-1 rounded-md hover:bg-[#8ab4f8]/10 transition">保存</button>
                    </div>
                  </div>

                  <!-- Display mode -->
                  <div v-else>
                    <div class="flex items-start gap-2">
                      <button v-if="n.tag === 'todo'" @click.stop="toggleDone(n)" class="shrink-0 mt-0.5 w-4 h-4 rounded border transition-all flex items-center justify-center"
                        :class="n.done ? 'bg-[#f9ab00] border-[#f9ab00]' : 'border-zinc-600 hover:border-[#f9ab00]'">
                        <svg v-if="n.done" class="w-2.5 h-2.5 text-[#1a1b1e]" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.5">
                          <path d="M5 12l5 5L20 7" stroke-linecap="round" stroke-linejoin="round"/>
                        </svg>
                      </button>
                      <div class="flex-1 min-w-0" @dblclick="startEdit(n)">
                        <p
                          class="text-[13px] leading-relaxed whitespace-pre-wrap break-words select-text"
                          :class="n.done ? 'text-zinc-600 line-through' : 'text-zinc-300'"
                        >{{ n.text }}</p>
                      </div>
                      <div v-if="n.pinned" class="shrink-0 mt-1">
                        <svg class="w-3 h-3 text-[#8ab4f8]" viewBox="0 0 24 24" fill="currentColor"><path d="M16 2v2l-2 1v5l2 1v2h-5v7l-1 1-1-1v-7H4v-2l2-1V5L4 4V2z"/></svg>
                      </div>
                    </div>
                    <!-- Footer -->
                    <div class="flex items-center justify-between mt-1.5">
                      <div class="flex items-center gap-1.5">
                        <button @click.stop="cycleTag(n)" class="text-[10px] px-1.5 py-0.5 rounded transition-colors hover:bg-white/5"
                          :style="{ color: TAG_META[n.tag]?.color || '#9aa0a6' }">
                          {{ TAG_META[n.tag]?.label || '笔记' }}
                        </button>
                        <span class="text-[10px] text-zinc-600 tabular-nums">{{ relTime(n.createdAt) }}</span>
                      </div>
                      <div class="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button @click.stop="togglePin(n)" class="p-1 rounded hover:bg-white/5 transition-colors" :title="n.pinned ? '取消置顶' : '置顶'">
                          <svg class="w-3 h-3" :class="n.pinned ? 'text-[#8ab4f8]' : 'text-zinc-600'" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M16 2v2l-2 1v5l2 1v2h-5v7l-1 1-1-1v-7H4v-2l2-1V5L4 4V2z"/>
                          </svg>
                        </button>
                        <button @click.stop="startEdit(n)" class="p-1 rounded hover:bg-white/5 transition-colors text-zinc-600 hover:text-zinc-300" title="编辑">
                          <svg class="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" stroke-linecap="round" stroke-linejoin="round"/>
                            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" stroke-linecap="round" stroke-linejoin="round"/>
                          </svg>
                        </button>
                        <button @click.stop="remove(n.id)" class="p-1 rounded hover:bg-white/5 transition-colors text-zinc-600 hover:text-red-400" title="删除">
                          <svg class="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6L6 18M6 6l12 12" stroke-linecap="round"/></svg>
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </TransitionGroup>

          <!-- Clear done -->
          <div v-if="doneCount > 0 && (filterTag === 'all' || filterTag === 'todo')" class="flex justify-center pt-1 pb-2">
            <button @click="clearDone" class="text-[11px] text-zinc-500 hover:text-red-400 px-3 py-1 rounded-lg hover:bg-white/5 transition-colors">
              清除 {{ doneCount }} 项已完成
            </button>
          </div>

          <!-- Empty -->
          <div v-if="filtered.length === 0 && !search" class="flex flex-col items-center justify-center py-12 text-zinc-600">
            <svg class="w-8 h-8 mb-3 opacity-20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" stroke-linecap="round" stroke-linejoin="round"/>
              <polyline points="14 2 14 8 20 8" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <span class="text-[12px]">{{ filterTag === 'all' ? '随手记录你的想法' : '暂无' + (filterTag === 'todo' ? '待办' : filterTag === 'idea' ? '想法' : '笔记') }}</span>
          </div>
          <div v-if="filtered.length === 0 && search" class="flex flex-col items-center justify-center py-12 text-zinc-600">
            <span class="text-[12px]">没有找到匹配的笔记</span>
          </div>
        </div>
      </div>
    </Transition>

    <!-- FAB -->
    <button
      ref="fabEl"
      @click="togglePanel"
      class="fab-btn fixed bottom-6 right-6 z-[60] w-12 h-12 rounded-full shadow-lg flex items-center justify-center transition-all active:scale-95"
      :class="open ? 'bg-zinc-700 text-zinc-200' : 'bg-[#8ab4f8] text-[#1a1b1e] hover:bg-[#aecbfa]'"
      :title="open ? '收起' : 'Notes (Ctrl+N)'"
    >
      <svg v-if="!open" class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" stroke-linecap="round" stroke-linejoin="round"/>
        <polyline points="14 2 14 8 20 8" stroke-linecap="round" stroke-linejoin="round"/>
        <line x1="16" y1="13" x2="8" y2="13" stroke-linecap="round"/><line x1="16" y1="17" x2="8" y2="17" stroke-linecap="round"/>
      </svg>
      <svg v-else class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4">
        <path d="M18 6L6 18M6 6l12 12" stroke-linecap="round"/>
      </svg>
      <span
        v-if="todoCount > 0 && !open"
        class="absolute -top-1 -right-1 min-w-[18px] h-[18px] px-1 rounded-full bg-[#f9ab00] text-[#1a1b1e] text-[10px] font-bold flex items-center justify-center border-2 border-[#1a1b1e]"
      >{{ todoCount > 99 ? '99+' : todoCount }}</span>
    </button>
  </div>
</template>

<style scoped>
.fab-btn {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4), 0 2px 4px rgba(0, 0, 0, 0.2);
  transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1), background 0.2s, box-shadow 0.2s;
}
.fab-btn:hover {
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.5), 0 3px 6px rgba(0, 0, 0, 0.25);
}

.note-card {
  background: rgba(255, 255, 255, 0.02);
  transition: all 0.2s ease;
}
.note-card:hover {
  background: rgba(255, 255, 255, 0.05);
}
.note-card.drop-target {
  box-shadow: 0 -2px 0 0 #8ab4f8;
}

.notes-scroll::-webkit-scrollbar { width: 4px; }
.notes-scroll::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.08); border-radius: 99px; }

/* List transitions */
.note-list-enter-active { transition: all 0.25s cubic-bezier(0.34, 1.2, 0.64, 1); }
.note-list-leave-active { transition: all 0.2s ease-in; position: absolute; width: calc(100% - 0.5rem); }
.note-list-enter-from { opacity: 0; transform: translateY(-8px) scale(0.97); }
.note-list-leave-to { opacity: 0; transform: translateX(16px) scale(0.97); }
.note-list-move { transition: transform 0.25s ease; }

.notes-pop-enter-active {
  transition: opacity 0.18s ease-out, transform 0.22s cubic-bezier(0.34, 1.3, 0.64, 1);
  transform-origin: bottom right;
}
.notes-pop-leave-active {
  transition: opacity 0.14s ease-in, transform 0.14s ease-in;
  transform-origin: bottom right;
}
.notes-pop-enter-from {
  opacity: 0;
  transform: scale(0.88) translateY(12px);
}
.notes-pop-leave-to {
  opacity: 0;
  transform: scale(0.94) translateY(8px);
}
</style>
