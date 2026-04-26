<script setup lang="ts">
import { ref } from 'vue'
import { Monitor, Type, Bell, Palette, Volume2, Keyboard, Plus, X, Check, Copy, Download, Upload, RotateCcw } from 'lucide-vue-next'
import type { Settings } from '../composables/useSettings'

defineOptions({ name: 'SettingsTab' })
const props = defineProps<{ settings: Settings }>()

const newPrompt = ref('')
const configCopied = ref(false)

function addPrompt() {
  const v = newPrompt.value.trim()
  if (v && !props.settings.quickPrompts.includes(v)) {
    props.settings.quickPrompts.push(v)
    newPrompt.value = ''
  }
}
function removePrompt(i: number) {
  props.settings.quickPrompts.splice(i, 1)
}
function resetPrompts() {
  props.settings.quickPrompts.splice(0, props.settings.quickPrompts.length, '继续', '确认', '好的', '重试')
}

const copilotConfig = `"chat.agent.maxRequests": 100000000,
"chat.tools.global.autoApprove": true,
"chat.tools.terminal.autoApprove": {
  ".*": true
},
"chat.instructionsFilesLocations": {
  ".github/instructions": true,
  ".claude/rules": true,
  "~/.copilot/instructions": true,
  "~/.claude/rules": true
}`

function copyConfig() {
  navigator.clipboard.writeText(copilotConfig).then(() => {
    configCopied.value = true
    setTimeout(() => { configCopied.value = false }, 2000)
  }).catch(() => {})
}

function exportSettings() {
  const blob = new Blob([JSON.stringify(props.settings, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = 'mcp-chat-settings.json'; a.click()
  URL.revokeObjectURL(url)
}

function importSettings() {
  const input = document.createElement('input')
  input.type = 'file'; input.accept = '.json'
  input.onchange = () => {
    const file = input.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = () => {
      try {
        const data = JSON.parse(reader.result as string)
        Object.assign(props.settings, data)
      } catch {}
    }
    reader.readAsText(file)
  }
  input.click()
}
</script>

<template>
  <div class="flex-1 overflow-y-auto p-8">
    <div class="max-w-3xl mx-auto w-full space-y-6">

      <!-- System Status -->
      <section class="bg-dark-panel border border-dark-border rounded-xl p-5">
        <h3 class="flex items-center gap-2 text-sm font-semibold mb-4"><Monitor :size="16" class="text-blue-400" /> 系统状态</h3>
        <div class="grid grid-cols-2 gap-3">
          <div class="bg-dark-card border border-dark-border rounded-lg p-3">
            <div class="text-xs text-dark-muted mb-1">服务状态</div>
            <span class="text-xs px-2 py-0.5 bg-green-500/15 text-green-400 rounded-full">● 正常运行</span>
          </div>
          <div class="bg-dark-card border border-dark-border rounded-lg p-3">
            <div class="text-xs text-dark-muted mb-1">连接方式</div>
            <span class="text-xs px-2 py-0.5 bg-blue-500/15 text-blue-400 rounded-full">● 已连接</span>
          </div>
        </div>
      </section>

      <!-- UI Settings -->
      <section class="bg-dark-panel border border-dark-border rounded-xl p-5">
        <h3 class="flex items-center gap-2 text-sm font-semibold mb-4"><Type :size="16" class="text-blue-400" /> 界面设置</h3>
        <div class="space-y-4">
          <div class="flex items-center justify-between">
            <div><div class="text-sm">用户名</div><div class="text-xs text-dark-muted mt-0.5">显示在聊天中的名称</div></div>
            <input v-model="settings.username" type="text" placeholder="用户" class="bg-dark-card border border-dark-border rounded-lg px-3 py-1.5 text-sm text-dark-text w-36 focus:outline-none focus:border-blue-500/50 transition-colors" />
          </div>
          <div class="flex items-center justify-between">
            <div><div class="text-sm">Markdown 渲染</div><div class="text-xs text-dark-muted mt-0.5">将 AI 回复渲染为 Markdown 格式</div></div>
            <button
              class="w-10 h-[22px] rounded-full relative flex-shrink-0 transition-colors"
              :class="settings.markdown ? 'bg-blue-500' : 'bg-dark-border'"
              @click="settings.markdown = !settings.markdown"
            >
              <div class="w-4 h-4 rounded-full bg-white absolute top-[3px] transition-all" :class="settings.markdown ? 'left-[21px]' : 'left-[3px]'" />
            </button>
          </div>
          <div class="flex items-center justify-between">
            <div class="text-sm">字体大小</div>
            <div class="flex items-center gap-2">
              <input type="range" min="12" max="20" v-model.number="settings.fontSize" class="w-20 accent-blue-500" />
              <span class="text-xs text-dark-muted w-10 text-right font-mono">{{ settings.fontSize }}px</span>
            </div>
          </div>
        </div>
      </section>

      <!-- Notification -->
      <section class="bg-dark-panel border border-dark-border rounded-xl p-5">
        <h3 class="flex items-center gap-2 text-sm font-semibold mb-4"><Bell :size="16" class="text-blue-400" /> 通知提醒</h3>
        <div class="space-y-4">
          <div class="flex items-center justify-between">
            <div><div class="text-sm">提示音</div><div class="text-xs text-dark-muted mt-0.5">AI 等待回复时播放提示音</div></div>
            <button
              class="w-10 h-[22px] rounded-full relative flex-shrink-0 transition-colors"
              :class="settings.notifySound ? 'bg-blue-500' : 'bg-dark-border'"
              @click="settings.notifySound = !settings.notifySound"
            >
              <div class="w-4 h-4 rounded-full bg-white absolute top-[3px] transition-all" :class="settings.notifySound ? 'left-[21px]' : 'left-[3px]'" />
            </button>
          </div>
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2"><Volume2 :size="14" class="text-dark-muted" /><span class="text-sm">音量</span></div>
            <div class="flex items-center gap-2">
              <input type="range" min="0" max="100" v-model.number="settings.volume" :disabled="!settings.notifySound" class="w-20 accent-blue-500 disabled:opacity-30" />
              <span class="text-xs text-dark-muted w-10 text-right font-mono">{{ settings.volume }}%</span>
            </div>
          </div>
        </div>
      </section>

      <!-- Quick Prompts -->
      <section class="bg-dark-panel border border-dark-border rounded-xl p-5">
        <div class="flex items-center justify-between mb-4">
          <h3 class="flex items-center gap-2 text-sm font-semibold"><Palette :size="16" class="text-blue-400" /> 快捷回复</h3>
          <button @click="resetPrompts" class="flex items-center gap-1 text-[10px] text-dark-muted hover:text-dark-text transition-colors">
            <RotateCcw :size="10" /> 重置
          </button>
        </div>
        <div class="flex flex-wrap gap-2 mb-3">
          <span v-for="(p, i) in settings.quickPrompts" :key="i"
            class="group flex items-center gap-1 px-2.5 py-1 text-xs bg-dark-card border border-dark-border rounded-lg">
            {{ p }}
            <button @click="removePrompt(i)" class="text-dark-muted hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all ml-0.5">
              <X :size="10" />
            </button>
          </span>
        </div>
        <div class="flex gap-2">
          <input v-model="newPrompt" @keydown.enter="addPrompt" type="text" placeholder="添加新的快捷回复..."
            class="flex-1 bg-dark-card border border-dark-border rounded-lg px-3 py-1.5 text-xs text-dark-text focus:outline-none focus:border-blue-500/50 transition-colors" />
          <button @click="addPrompt" :disabled="!newPrompt.trim()"
            class="px-3 py-1.5 text-xs bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors disabled:opacity-30 disabled:cursor-not-allowed flex items-center gap-1">
            <Plus :size="12" /> 添加
          </button>
        </div>
      </section>

      <!-- Copilot config -->
      <section class="bg-dark-panel border border-dark-border rounded-xl p-5">
        <h3 class="flex items-center gap-2 text-sm font-semibold mb-3"><Keyboard :size="16" class="text-blue-400" /> Copilot 配置建议</h3>
        <div class="text-xs text-dark-muted mb-2">添加到 settings.json 可获得最佳体验</div>
        <div class="relative">
          <pre class="bg-dark-card border border-dark-border rounded-lg p-4 text-xs text-dark-text overflow-x-auto font-mono leading-relaxed">{{ copilotConfig }}</pre>
          <button @click="copyConfig"
            class="absolute top-2 right-2 px-2.5 py-1 text-xs rounded-lg transition-all flex items-center gap-1"
            :class="configCopied ? 'bg-green-500/20 text-green-400' : 'bg-blue-500/20 text-blue-400 hover:bg-blue-500/30'">
            <component :is="configCopied ? Check : Copy" :size="11" />
            {{ configCopied ? '已复制' : '复制' }}
          </button>
        </div>
      </section>

      <!-- Export -->
      <section class="bg-dark-panel border border-dark-border rounded-xl p-5">
        <h3 class="flex items-center gap-2 text-sm font-semibold mb-3"><Download :size="16" class="text-blue-400" /> 导入/导出配置</h3>
        <div class="text-xs text-dark-muted mb-3">导出当前设置或从文件导入</div>
        <div class="flex gap-2">
          <button @click="exportSettings" class="flex-1 py-2.5 text-sm bg-dark-card border border-dark-border rounded-lg hover:bg-dark-hover transition-colors text-dark-muted hover:text-dark-text flex items-center justify-center gap-1.5">
            <Upload :size="14" /> 导出
          </button>
          <button @click="importSettings" class="flex-1 py-2.5 text-sm bg-dark-card border border-dark-border rounded-lg hover:bg-dark-hover transition-colors text-dark-muted hover:text-dark-text flex items-center justify-center gap-1.5">
            <Download :size="14" /> 导入
          </button>
        </div>
      </section>

    </div>
  </div>
</template>
