<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { FolderOpen, File, ChevronRight, Plus, Trash2, Search, Edit3, Save, X, FolderPlus, FilePlus, ArrowLeft, Copy, Pencil, Eye, Columns2, Code2, FileText } from 'lucide-vue-next'
import MarkdownIt from 'markdown-it'
import type { Settings } from '../composables/useSettings'

let hljs: typeof import('highlight.js').default | null = null
import('highlight.js').then(m => { hljs = m.default })

const props = defineProps<{ settings: Settings }>()

interface TreeItem { name: string; type: 'dir' | 'file'; children?: number; size?: number; mtime?: number; path: string }

const BASE = window.location.origin
const configured = ref(false)
const vaultPath = ref('')
const pathInput = ref('')
const configError = ref('')
const tree = ref<TreeItem[]>([])
const currentDir = ref('')
const dirStack = ref<string[]>([])
const openFile = ref('')
const fileContent = ref('')
const editContent = ref('')
const saving = ref(false)
const dirty = ref(false)
const searchQuery = ref('')
const searchResults = ref<{ path: string; match: string; snippet?: string }[]>([])
const searching = ref(false)
const creating = ref<'file' | 'dir' | ''>('')
const newName = ref('')
const editorEl = ref<HTMLTextAreaElement | null>(null)
const previewEl = ref<HTMLElement | null>(null)

// View mode: 'source' | 'preview' | 'split'
const viewMode = ref<'source' | 'preview' | 'split'>('split')

// Auto-save timer
let autoSaveTimer: ReturnType<typeof setTimeout>
const autoSaved = ref(false)

// Context menu state
const ctxMenu = ref(false)
const ctxX = ref(0)
const ctxY = ref(0)
const ctxItem = ref<TreeItem | null>(null)

// Inline rename
const renamingPath = ref('')
const renameValue = ref('')

const copyBtnHtml = (lang: string) =>
  `<div class="code-header"><span class="code-lang">${lang}</span><button class="code-copy-btn" onclick="navigator.clipboard.writeText(this.closest('pre').querySelector('code').textContent).then(()=>{this.textContent='✓ 已复制';setTimeout(()=>this.textContent='复制',1500)})">复制</button></div>`

const md = new MarkdownIt({
  html: true, linkify: true, typographer: true, breaks: true,
  highlight(str: string, lang: string) {
    if (hljs && lang && hljs.getLanguage(lang)) {
      try { return copyBtnHtml(lang) + hljs.highlight(str, { language: lang }).value } catch {}
    }
    return copyBtnHtml(lang || 'code') + str
  }
})

// Always render from editContent (which is synced on file open)
const renderedMd = computed(() => {
  const src = editContent.value
  return src ? md.render(src) : ''
})

// Enable task-list checkboxes
md.core.ruler.after('inline', 'task-lists', (state) => {
  const tokens = state.tokens
  for (let i = 0; i < tokens.length; i++) {
    if (tokens[i].type !== 'inline') continue
    const content = tokens[i].content
    if (/^\[(x| )\]\s/.test(content)) {
      const checked = content[1] === 'x'
      tokens[i].content = content.slice(4)
      tokens[i].children = md.parseInline(tokens[i].content, state.env)[0]?.children || []
      // Mark the parent li
      for (let j = i - 1; j >= 0; j--) {
        if (tokens[j].type === 'list_item_open') {
          tokens[j].attrSet('class', 'task-list-item')
          // Prepend checkbox html
          const checkToken = new state.Token('html_inline', '', 0)
          checkToken.content = `<input type="checkbox" disabled ${checked ? 'checked' : ''} class="task-checkbox" /> `
          tokens[i].children?.unshift(checkToken)
          break
        }
      }
    }
  }
})

const breadcrumbs = computed(() => {
  const crumbs = [{ label: 'Vault', path: '' }]
  if (!currentDir.value) return crumbs
  let p = ''
  for (const part of currentDir.value.split('/')) {
    p = p ? p + '/' + part : part
    crumbs.push({ label: part, path: p })
  }
  return crumbs
})

const fileName = computed(() => openFile.value ? openFile.value.split('/').pop() || '' : '')
const isMd = computed(() => fileName.value.toLowerCase().endsWith('.md'))

watch(editContent, () => {
  if (!openFile.value) return
  dirty.value = true
  autoSaved.value = false
  clearTimeout(autoSaveTimer)
  autoSaveTimer = setTimeout(async () => {
    if (dirty.value && openFile.value) {
      await saveFile()
      autoSaved.value = true
      setTimeout(() => { autoSaved.value = false }, 2000)
    }
  }, 3000)
})

const editorStats = computed(() => {
  const text = editContent.value || fileContent.value
  if (!text) return { lines: 0, words: 0, chars: 0 }
  const lines = text.split('\n').length
  const chars = text.length
  const words = text.trim() ? text.trim().split(/\s+/).length : 0
  return { lines, words, chars }
})

// ---- Config ----
async function checkConfig() {
  try {
    const res = await fetch(`${BASE}/vault/config`)
    const data = await res.json()
    if (data.path) { configured.value = true; vaultPath.value = data.path; loadTree('') }
    else if (props.settings.vaultPath) { await setVault(props.settings.vaultPath) }
  } catch {}
}

async function setVault(path: string) {
  configError.value = ''
  try {
    const res = await fetch(`${BASE}/vault/config`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path })
    })
    const data = await res.json()
    if (data.ok) { configured.value = true; vaultPath.value = data.path; props.settings.vaultPath = path; loadTree('') }
    else { configError.value = data.error || '配置失败' }
  } catch { configError.value = '连接失败' }
}

// ---- Tree ----
async function loadTree(dir: string) {
  currentDir.value = dir
  try {
    const res = await fetch(`${BASE}/vault/tree?path=${encodeURIComponent(dir)}`)
    const items: any[] = await res.json()
    tree.value = items.map((it: any) => ({ ...it, path: dir ? dir + '/' + it.name : it.name }))
  } catch {}
}

function enterDir(item: TreeItem) { dirStack.value.push(currentDir.value); loadTree(item.path) }
function goBack() { loadTree(dirStack.value.pop() ?? '') }

function goToBreadcrumb(path: string) {
  dirStack.value = []
  const parts = path.split('/').filter(Boolean)
  let p = ''
  for (let i = 0; i < parts.length - 1; i++) { dirStack.value.push(p); p = p ? p + '/' + parts[i] : parts[i] }
  loadTree(path)
}

// ---- File ops ----
async function openMd(item: TreeItem) {
  if (dirty.value && openFile.value) {
    await saveFile()
  }
  try {
    const res = await fetch(`${BASE}/vault/read?path=${encodeURIComponent(item.path)}`)
    const text = await res.text()
    fileContent.value = text; editContent.value = text; openFile.value = item.path; dirty.value = false
  } catch {}
}

async function saveFile() {
  saving.value = true
  try {
    await fetch(`${BASE}/vault/write`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: openFile.value, content: editContent.value })
    })
    fileContent.value = editContent.value; dirty.value = false
  } catch {} finally { saving.value = false }
}

async function createItem() {
  const name = newName.value.trim()
  if (!name) return
  const path = currentDir.value ? currentDir.value + '/' + name : name
  try {
    if (creating.value === 'dir') {
      await fetch(`${BASE}/vault/mkdir`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ path }) })
    } else {
      const fn = name.includes('.') ? name : name + '.md'
      const fp = currentDir.value ? currentDir.value + '/' + fn : fn
      await fetch(`${BASE}/vault/write`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ path: fp, content: '' }) })
    }
    creating.value = ''; newName.value = ''; loadTree(currentDir.value)
  } catch {}
}

async function deleteItem(item: TreeItem) {
  try {
    await fetch(`${BASE}/vault/delete`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ path: item.path }) })
    if (openFile.value === item.path) { openFile.value = ''; fileContent.value = ''; editContent.value = '' }
    loadTree(currentDir.value)
  } catch {}
}

async function duplicateItem(item: TreeItem) {
  const ext = item.name.includes('.') ? '.' + item.name.split('.').pop() : ''
  const base = item.name.replace(ext, '')
  const newPath = (item.path.replace(item.name, '')) + base + ' 副本' + ext
  try {
    if (item.type === 'file') {
      const res = await fetch(`${BASE}/vault/read?path=${encodeURIComponent(item.path)}`)
      const content = await res.text()
      await fetch(`${BASE}/vault/write`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ path: newPath, content }) })
    }
    loadTree(currentDir.value)
  } catch {}
}

function startRename(item: TreeItem) {
  renamingPath.value = item.path
  renameValue.value = item.name
  nextTick(() => {
    const el = document.querySelector('.rename-input') as HTMLInputElement
    if (el) { el.focus(); el.setSelectionRange(0, item.name.lastIndexOf('.') > 0 ? item.name.lastIndexOf('.') : item.name.length) }
  })
}

async function doRename() {
  if (!renamingPath.value || !renameValue.value.trim()) { renamingPath.value = ''; return }
  const dir = renamingPath.value.includes('/') ? renamingPath.value.substring(0, renamingPath.value.lastIndexOf('/')) : ''
  const newPath = dir ? dir + '/' + renameValue.value.trim() : renameValue.value.trim()
  if (newPath === renamingPath.value) { renamingPath.value = ''; return }
  try {
    await fetch(`${BASE}/vault/rename`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ from: renamingPath.value, to: newPath })
    })
    if (openFile.value === renamingPath.value) openFile.value = newPath
    renamingPath.value = ''; loadTree(currentDir.value)
  } catch { renamingPath.value = '' }
}

function copyPath(item: TreeItem) {
  navigator.clipboard.writeText(item.path).catch(() => {})
}

// ---- Context menu ----
function showCtxMenu(e: MouseEvent, item: TreeItem) {
  e.preventDefault()
  ctxItem.value = item
  ctxX.value = e.clientX; ctxY.value = e.clientY
  ctxMenu.value = true
}

function ctxAction(action: string) {
  const item = ctxItem.value
  ctxMenu.value = false
  if (!item) return
  switch (action) {
    case 'newFile': creating.value = 'file'; break
    case 'newFolder': creating.value = 'dir'; break
    case 'rename': startRename(item); break
    case 'duplicate': duplicateItem(item); break
    case 'copyPath': copyPath(item); break
    case 'delete': if (confirm(`删除 ${item.name}？`)) deleteItem(item); break
    case 'openInDir':
      if (item.type === 'dir') enterDir(item)
      break
  }
}

function closeCtxMenu() { ctxMenu.value = false }

// ---- Search ----
let searchTimer: ReturnType<typeof setTimeout>
watch(searchQuery, (q) => {
  clearTimeout(searchTimer)
  if (!q.trim()) { searchResults.value = []; return }
  searchTimer = setTimeout(async () => {
    searching.value = true
    try {
      const res = await fetch(`${BASE}/vault/search?q=${encodeURIComponent(q)}`)
      searchResults.value = await res.json()
    } catch {} finally { searching.value = false }
  }, 300)
})

function openSearchResult(r: { path: string }) {
  openMd({ name: r.path.split('/').pop()!, type: 'file', path: r.path })
  searchQuery.value = ''
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1048576).toFixed(1) + ' MB'
}

// ---- Keyboard shortcuts ----
function onKeyDown(e: KeyboardEvent) {
  if ((e.ctrlKey || e.metaKey) && e.key === 's' && openFile.value) {
    e.preventDefault(); saveFile()
  }
}

function onDocClick() { ctxMenu.value = false }

onMounted(() => {
  checkConfig()
  document.addEventListener('keydown', onKeyDown)
  document.addEventListener('click', onDocClick)
})
onBeforeUnmount(() => {
  document.removeEventListener('keydown', onKeyDown)
  document.removeEventListener('click', onDocClick)
})
</script>

<template>
  <div class="flex-1 flex overflow-hidden bg-[#1e1f20]">
    <!-- Context menu -->
    <Teleport to="body">
      <div v-if="ctxMenu" class="fixed z-[200] min-w-[200px] py-1.5 bg-[#2b2d31] border border-white/[0.08] rounded-xl shadow-2xl" :style="{ left: ctxX + 'px', top: ctxY + 'px' }" @click.stop>
        <button @click="ctxAction('newFile')" class="ctx-item"><FilePlus :size="14" class="text-zinc-500" /><span>新建笔记</span></button>
        <button @click="ctxAction('newFolder')" class="ctx-item"><FolderPlus :size="14" class="text-zinc-500" /><span>新建文件夹</span></button>
        <div class="h-px bg-white/[0.06] my-1 mx-2" />
        <button v-if="ctxItem?.type === 'file'" @click="ctxAction('duplicate')" class="ctx-item"><Copy :size="14" class="text-zinc-500" /><span>创建副本</span></button>
        <button @click="ctxAction('rename')" class="ctx-item"><Pencil :size="14" class="text-zinc-500" /><span>重命名</span></button>
        <button @click="ctxAction('copyPath')" class="ctx-item"><Copy :size="14" class="text-zinc-500" /><span>复制路径</span></button>
        <div class="h-px bg-white/[0.06] my-1 mx-2" />
        <button @click="ctxAction('delete')" class="ctx-item text-red-400 hover:!bg-red-500/10"><Trash2 :size="14" /><span>删除</span></button>
      </div>
    </Teleport>

    <!-- Setup screen -->
    <div v-if="!configured" class="flex-1 flex items-center justify-center">
      <div class="w-[420px] text-center">
        <div class="w-14 h-14 mx-auto mb-5 rounded-2xl bg-[#8ab4f8]/10 flex items-center justify-center">
          <FolderOpen :size="28" class="text-[#8ab4f8]" />
        </div>
        <h2 class="text-xl font-semibold text-zinc-100 mb-2">设置笔记目录</h2>
        <p class="text-sm text-zinc-500 mb-6">输入本地文件夹路径作为笔记库（兼容 Obsidian）</p>
        <div class="flex gap-2">
          <input v-model="pathInput" @keydown.enter="setVault(pathInput)"
            placeholder="例如 D:/Notes 或 C:/Users/你的名字/Documents/vault"
            class="flex-1 bg-[#232528] border border-white/[0.06] rounded-xl px-4 py-3 text-sm text-zinc-100 placeholder-zinc-600 outline-none focus:border-[#8ab4f8]/30" />
          <button @click="setVault(pathInput)" :disabled="!pathInput.trim()" class="px-5 py-3 bg-[#8ab4f8] text-[#1a1b1e] rounded-xl text-sm font-medium hover:bg-[#aecbfa] disabled:opacity-30 transition-colors">打开</button>
        </div>
        <p v-if="configError" class="text-red-400 text-xs mt-2">{{ configError }}</p>
      </div>
    </div>

    <!-- Main vault view -->
    <template v-else>
      <!-- Sidebar: file tree -->
      <div class="w-[260px] shrink-0 flex flex-col border-r border-white/[0.06] bg-[#131314]">
        <!-- Search -->
        <div class="px-3 pt-3 pb-2">
          <div class="flex items-center gap-2 bg-white/[0.04] rounded-lg px-3 py-1.5">
            <Search :size="14" class="text-zinc-500 shrink-0" />
            <input v-model="searchQuery" placeholder="搜索笔记..." class="flex-1 bg-transparent outline-none text-[13px] text-zinc-300 placeholder-zinc-600" />
            <button v-if="searchQuery" @click="searchQuery = ''" class="text-zinc-500 hover:text-zinc-300"><X :size="12" /></button>
          </div>
        </div>

        <!-- Search results -->
        <div v-if="searchQuery && searchResults.length" class="flex-1 overflow-y-auto px-2 pb-2">
          <div class="text-[10px] text-zinc-600 px-2 py-1">{{ searchResults.length }} 个结果</div>
          <button v-for="r in searchResults" :key="r.path" @click="openSearchResult(r)"
            class="w-full text-left px-3 py-2 rounded-lg hover:bg-white/[0.04] transition-colors">
            <div class="text-[12px] text-zinc-300 truncate">{{ r.path }}</div>
            <div v-if="r.snippet" class="text-[11px] text-zinc-600 truncate mt-0.5">{{ r.snippet }}</div>
          </button>
        </div>

        <!-- File tree -->
        <div v-else class="flex-1 overflow-y-auto px-2 pb-2 vault-scroll">
          <!-- Breadcrumbs -->
          <div class="flex items-center gap-0.5 px-2 py-2 text-[11px] text-zinc-500 flex-wrap">
            <template v-for="(bc, i) in breadcrumbs" :key="bc.path">
              <span v-if="i > 0" class="text-zinc-700">/</span>
              <button @click="goToBreadcrumb(bc.path)" class="hover:text-zinc-300 transition-colors truncate max-w-[80px]" :title="bc.label">{{ bc.label }}</button>
            </template>
          </div>

          <!-- Actions bar -->
          <div class="flex items-center gap-1 px-2 pb-2">
            <button v-if="currentDir" @click="goBack" class="p-1.5 rounded-lg hover:bg-white/[0.04] text-zinc-500 hover:text-zinc-300 transition-colors" title="返回上级">
              <ArrowLeft :size="14" />
            </button>
            <div class="flex-1" />
            <button @click="creating = creating === 'file' ? '' : 'file'" class="p-1.5 rounded-lg hover:bg-white/[0.04] text-zinc-500 hover:text-zinc-300 transition-colors" title="新建笔记">
              <FilePlus :size="14" />
            </button>
            <button @click="creating = creating === 'dir' ? '' : 'dir'" class="p-1.5 rounded-lg hover:bg-white/[0.04] text-zinc-500 hover:text-zinc-300 transition-colors" title="新建文件夹">
              <FolderPlus :size="14" />
            </button>
          </div>

          <!-- Create input -->
          <div v-if="creating" class="px-2 pb-2">
            <div class="flex items-center gap-1.5">
              <component :is="creating === 'dir' ? FolderPlus : FilePlus" :size="13" class="text-[#8ab4f8] shrink-0" />
              <input v-model="newName" @keydown.enter="createItem" @keydown.escape="creating = ''"
                :placeholder="creating === 'dir' ? '文件夹名' : '文件名 (.md)'"
                class="flex-1 bg-[#232528] rounded-md px-2 py-1 text-[12px] text-zinc-100 outline-none border border-[#8ab4f8]/30" autofocus />
              <button @click="createItem" class="text-[#8ab4f8] hover:text-[#aecbfa]"><Plus :size="14" /></button>
              <button @click="creating = ''" class="text-zinc-500 hover:text-zinc-300"><X :size="14" /></button>
            </div>
          </div>

          <!-- Items -->
          <div v-for="item in tree" :key="item.path"
            @click="item.type === 'dir' ? enterDir(item) : openMd(item)"
            @contextmenu="showCtxMenu($event, item)"
            class="group flex items-center gap-2 px-3 py-1.5 rounded-lg cursor-pointer transition-colors"
            :class="openFile === item.path ? 'bg-[#8ab4f8]/10 text-[#8ab4f8]' : 'hover:bg-white/[0.04] text-zinc-400'"
          >
            <FolderOpen v-if="item.type === 'dir'" :size="15" class="shrink-0 text-[#f9ab00]" />
            <File v-else :size="15" class="shrink-0" />
            <!-- Inline rename -->
            <template v-if="renamingPath === item.path">
              <input v-model="renameValue" @keydown.enter="doRename" @keydown.escape="renamingPath = ''" @blur="doRename" @click.stop
                class="rename-input flex-1 bg-[#232528] rounded-md px-1.5 py-0.5 text-[12px] text-zinc-100 outline-none border border-[#8ab4f8]/30 min-w-0" />
            </template>
            <template v-else>
              <span class="flex-1 text-[13px] truncate">{{ item.name }}</span>
              <span v-if="item.type === 'dir' && item.children" class="text-[10px] text-zinc-600">{{ item.children }}</span>
              <span v-if="item.type === 'file' && item.size !== undefined" class="text-[10px] text-zinc-600 opacity-0 group-hover:opacity-100">{{ formatSize(item.size) }}</span>
            </template>
          </div>

          <div v-if="tree.length === 0 && !creating" class="text-center py-10 text-zinc-600 text-[12px]">空文件夹</div>
        </div>

        <!-- Vault path footer -->
        <div class="px-3 py-2 border-t border-white/[0.04] text-[10px] text-zinc-600 truncate cursor-pointer hover:text-zinc-400 transition-colors" :title="vaultPath" @click="configured = false">
          {{ vaultPath }}
        </div>
      </div>

      <!-- Content area -->
      <div class="flex-1 flex flex-col min-w-0 overflow-hidden">
        <!-- No file open -->
        <div v-if="!openFile" class="flex-1 flex items-center justify-center">
          <div class="text-center text-zinc-600">
            <FileText :size="40" class="mx-auto mb-3 opacity-20" />
            <p class="text-sm">选择一个文件开始编辑</p>
            <p class="text-[11px] mt-1 text-zinc-700">右键文件可打开更多操作 · Ctrl+S 保存</p>
          </div>
        </div>

        <!-- File content -->
        <template v-else>
          <!-- File header bar -->
          <div class="flex items-center gap-3 px-5 py-2.5 border-b border-white/[0.06] shrink-0 bg-[#1e1f20]">
            <button @click="openFile = ''; dirty = false" class="p-1 rounded hover:bg-white/[0.04] text-zinc-500 hover:text-zinc-300 transition-colors">
              <ArrowLeft :size="16" />
            </button>
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2">
                <span class="text-sm font-medium text-zinc-200 truncate">{{ fileName }}</span>
                <span v-if="dirty" class="w-2 h-2 rounded-full bg-[#f9ab00] shrink-0" title="未保存" />
              </div>
              <div class="text-[10px] text-zinc-600 truncate">{{ openFile }}</div>
            </div>
            <!-- View mode toggle -->
            <div v-if="isMd" class="flex items-center bg-[#131314] rounded-lg p-0.5 gap-0.5">
              <button @click="viewMode = 'source'" :title="'源码'" class="p-1.5 rounded-md transition-colors" :class="viewMode === 'source' ? 'bg-white/[0.08] text-zinc-200' : 'text-zinc-500 hover:text-zinc-300'">
                <Code2 :size="14" />
              </button>
              <button @click="viewMode = 'split'" title="分栏" class="p-1.5 rounded-md transition-colors" :class="viewMode === 'split' ? 'bg-white/[0.08] text-zinc-200' : 'text-zinc-500 hover:text-zinc-300'">
                <Columns2 :size="14" />
              </button>
              <button @click="viewMode = 'preview'" title="预览" class="p-1.5 rounded-md transition-colors" :class="viewMode === 'preview' ? 'bg-white/[0.08] text-zinc-200' : 'text-zinc-500 hover:text-zinc-300'">
                <Eye :size="14" />
              </button>
            </div>
            <!-- Save button -->
            <button v-if="dirty" @click="saveFile" :disabled="saving" class="flex items-center gap-1 px-3 py-1.5 text-[12px] bg-[#8ab4f8] text-[#1a1b1e] rounded-lg hover:bg-[#aecbfa] disabled:opacity-50 transition-colors font-medium">
              <Save :size="13" /> {{ saving ? '...' : '保存' }}
            </button>
          </div>

          <!-- Editor / Preview split view -->
          <div class="flex-1 flex min-h-0 overflow-hidden">
            <!-- Source editor -->
            <div v-if="!isMd || viewMode !== 'preview'" class="flex-1 flex flex-col min-w-0 overflow-hidden" :class="isMd && viewMode === 'split' ? 'border-r border-white/[0.06]' : ''">
              <div class="flex-1 overflow-y-auto vault-scroll">
                <textarea
                  ref="editorEl"
                  v-model="editContent"
                  class="w-full min-h-full bg-transparent text-[13px] text-zinc-200 p-5 outline-none resize-none font-mono"
                  style="line-height: 1.75; tab-size: 2;"
                  spellcheck="false"
                  @keydown.tab.prevent="insertTab"
                />
              </div>
            </div>
            <!-- Preview pane -->
            <div v-if="isMd && viewMode !== 'source'" ref="previewEl" class="flex-1 overflow-y-auto vault-scroll">
              <div class="vault-md-body p-6 max-w-[720px] text-[14px]" style="line-height: 1.8" v-html="renderedMd" />
            </div>
          </div>

          <!-- Status bar -->
          <div class="flex items-center justify-between px-5 py-1.5 border-t border-white/[0.04] shrink-0 text-[10px] text-zinc-600 bg-[#1a1b1e] select-none">
            <div class="flex items-center gap-3">
              <span>{{ editorStats.lines }} 行</span>
              <span>{{ editorStats.words }} 词</span>
              <span>{{ editorStats.chars }} 字符</span>
            </div>
            <div class="flex items-center gap-2">
              <span v-if="autoSaved" class="text-emerald-500">已自动保存</span>
              <span v-else-if="dirty" class="text-[#f9ab00]">未保存</span>
              <span v-else class="text-zinc-700">已保存</span>
              <span class="text-zinc-700">{{ isMd ? 'Markdown' : fileName.split('.').pop()?.toUpperCase() }}</span>
            </div>
          </div>
        </template>
      </div>
    </template>
  </div>
</template>

<script lang="ts">
function insertTab(e: Event) {
  const el = e.target as HTMLTextAreaElement
  const start = el.selectionStart
  const end = el.selectionEnd
  const val = el.value
  el.value = val.substring(0, start) + '  ' + val.substring(end)
  el.selectionStart = el.selectionEnd = start + 2
  el.dispatchEvent(new Event('input'))
}
</script>

<style scoped>
.ctx-item {
  display: flex; align-items: center; gap: 8px; width: 100%;
  padding: 6px 14px; font-size: 13px; color: #c4c7c5;
  transition: background 0.15s;
}
.ctx-item:hover { background: rgba(255,255,255,0.06); }

.vault-scroll::-webkit-scrollbar { width: 5px; }
.vault-scroll::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.08); border-radius: 99px; }

.vault-md-body { color: #d4d4d4; word-wrap: break-word; }

/* Headings */
.vault-md-body :deep(h1) { font-size: 1.8em; font-weight: 700; margin: 1.2em 0 0.6em; color: #f0f0ef; border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 0.3em; }
.vault-md-body :deep(h2) { font-size: 1.45em; font-weight: 600; margin: 1.1em 0 0.5em; color: #e8e8e7; border-bottom: 1px solid rgba(255,255,255,0.04); padding-bottom: 0.2em; }
.vault-md-body :deep(h3) { font-size: 1.2em; font-weight: 600; margin: 1em 0 0.4em; color: #ddd; }
.vault-md-body :deep(h4) { font-size: 1.05em; font-weight: 600; margin: 0.8em 0 0.3em; color: #ccc; }
.vault-md-body :deep(h5) { font-size: 0.95em; font-weight: 600; margin: 0.8em 0 0.3em; color: #bbb; }
.vault-md-body :deep(h6) { font-size: 0.9em; font-weight: 600; margin: 0.8em 0 0.3em; color: #aaa; }

/* Text */
.vault-md-body :deep(p) { margin: 0.6em 0; }
.vault-md-body :deep(strong) { color: #f0f0ef; font-weight: 600; }
.vault-md-body :deep(em) { color: #c0c4cc; font-style: italic; }
.vault-md-body :deep(del) { color: #666; text-decoration: line-through; }
.vault-md-body :deep(a) { color: #8ab4f8; text-decoration: underline; text-underline-offset: 2px; }
.vault-md-body :deep(a:hover) { color: #aecbfa; }

/* Code */
.vault-md-body :deep(code) { background: rgba(255,255,255,0.07); padding: 0.15em 0.4em; border-radius: 4px; font-size: 0.88em; color: #e8ab6a; }
.vault-md-body :deep(pre) { background: #0d0d0e; border: 1px solid rgba(255,255,255,0.06); border-radius: 8px; overflow-x: auto; margin: 1em 0; }
.vault-md-body :deep(pre code) { background: none; padding: 1em; display: block; font-size: 13px; line-height: 1.7; color: #d4d4d4; }

/* Blockquote */
.vault-md-body :deep(blockquote) { border-left: 3px solid #8ab4f8; padding: 0.3em 0 0.3em 1em; margin: 0.8em 0; color: #9aa0a6; background: rgba(138,180,248,0.03); border-radius: 0 6px 6px 0; }
.vault-md-body :deep(blockquote p) { margin: 0.3em 0; }

/* Lists */
.vault-md-body :deep(ul), .vault-md-body :deep(ol) { padding-left: 1.5em; margin: 0.6em 0; }
.vault-md-body :deep(ul) { list-style-type: disc; }
.vault-md-body :deep(ol) { list-style-type: decimal; }
.vault-md-body :deep(li) { margin: 0.3em 0; }
.vault-md-body :deep(li > p) { margin: 0.2em 0; }

/* Task checkboxes */
.vault-md-body :deep(.task-list-item) { list-style: none; margin-left: -1.5em; padding-left: 0; }
.vault-md-body :deep(.task-checkbox) {
  appearance: none; -webkit-appearance: none;
  width: 16px; height: 16px; border: 1.5px solid #555; border-radius: 3px;
  vertical-align: middle; margin-right: 6px; position: relative; top: -1px;
  cursor: default; background: transparent;
}
.vault-md-body :deep(.task-checkbox:checked) {
  background: #8ab4f8; border-color: #8ab4f8;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 16 16' fill='%231a1b1e' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M12.207 4.793a1 1 0 010 1.414l-5 5a1 1 0 01-1.414 0l-2-2a1 1 0 011.414-1.414L6.5 9.086l4.293-4.293a1 1 0 011.414 0z'/%3E%3C/svg%3E");
  background-size: 14px; background-position: center; background-repeat: no-repeat;
}

/* Table */
.vault-md-body :deep(table) { border-collapse: collapse; width: 100%; margin: 1em 0; font-size: 0.92em; }
.vault-md-body :deep(th) { border: 1px solid rgba(255,255,255,0.1); padding: 0.6em 0.8em; text-align: left; background: rgba(255,255,255,0.04); font-weight: 600; color: #e0e0e0; }
.vault-md-body :deep(td) { border: 1px solid rgba(255,255,255,0.06); padding: 0.5em 0.8em; text-align: left; }
.vault-md-body :deep(tr:hover td) { background: rgba(255,255,255,0.02); }

/* HR */
.vault-md-body :deep(hr) { border: none; border-top: 1px solid rgba(255,255,255,0.08); margin: 2em 0; }

/* Images */
.vault-md-body :deep(img) { max-width: 100%; border-radius: 8px; margin: 0.8em 0; }

/* Code header */
.vault-md-body :deep(.code-header) { display: flex; justify-content: space-between; align-items: center; padding: 0.5em 1em; border-bottom: 1px solid rgba(255,255,255,0.06); background: rgba(255,255,255,0.02); }
.vault-md-body :deep(.code-lang) { font-size: 11px; color: #777; text-transform: uppercase; letter-spacing: 0.5px; }
.vault-md-body :deep(.code-copy-btn) { font-size: 11px; color: #8ab4f8; cursor: pointer; background: none; border: none; padding: 2px 8px; border-radius: 4px; }
.vault-md-body :deep(.code-copy-btn:hover) { background: rgba(138,180,248,0.12); }
</style>
