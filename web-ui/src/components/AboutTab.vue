<script setup lang="ts">
import { Zap, Globe, MessageSquare, Wifi, Keyboard, RefreshCw } from 'lucide-vue-next'
defineOptions({ name: 'AboutTab' })
defineProps<{ connected: boolean; sessionCount: number; waitingCount: number }>()

const shortcuts = [
  { keys: 'Ctrl+Enter', desc: '提交回复' },
  { keys: 'Ctrl+V', desc: '粘贴图片' },
  { keys: 'Alt+1~4', desc: '切换标签页' },
]

function reload() { window.location.reload() }
</script>

<template>
  <div class="flex-1 flex items-center justify-center p-8">
    <div class="w-full max-w-lg space-y-5">
      <!-- Hero card -->
      <div class="bg-dark-panel border border-dark-border rounded-2xl p-8 text-center shadow-2xl">
        <div class="flex justify-center mb-5">
          <div class="w-20 h-20 rounded-2xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center shadow-lg shadow-blue-500/20">
            <Zap :size="36" class="text-white" />
          </div>
        </div>
        <h2 class="text-2xl font-bold text-white mb-1">MCP Chat</h2>
        <div class="text-sm text-dark-muted mb-6">多会话实时通信平台</div>

        <!-- Stats -->
        <div class="grid grid-cols-3 gap-3 mb-6">
          <div class="bg-dark-card border border-dark-border rounded-xl p-3">
            <div class="text-lg font-bold text-white">{{ sessionCount }}</div>
            <div class="text-[10px] text-dark-muted mt-0.5">会话数</div>
          </div>
          <div class="bg-dark-card border border-dark-border rounded-xl p-3">
            <div class="text-lg font-bold" :class="waitingCount > 0 ? 'text-green-400' : 'text-white'">{{ waitingCount }}</div>
            <div class="text-[10px] text-dark-muted mt-0.5">待回复</div>
          </div>
          <div class="bg-dark-card border border-dark-border rounded-xl p-3">
            <div class="text-lg font-bold" :class="connected ? 'text-green-400' : 'text-yellow-400'">
              <Wifi :size="18" class="mx-auto" />
            </div>
            <div class="text-[10px] text-dark-muted mt-0.5">{{ connected ? 'WS' : 'HTTP' }}</div>
          </div>
        </div>

        <!-- Info -->
        <div class="bg-dark-card border border-dark-border rounded-xl p-4 text-left space-y-2.5 text-sm">
          <div class="flex justify-between"><span class="text-dark-muted">版本</span><span class="text-dark-text font-mono">v1.0.0</span></div>
          <div class="flex justify-between"><span class="text-dark-muted">协议</span><span class="text-dark-text">MCP (Model Context Protocol)</span></div>
          <div class="flex justify-between items-center"><span class="text-dark-muted">服务地址</span><span class="text-dark-text font-mono text-xs">127.0.0.1:8080</span></div>
          <div class="flex justify-between items-center">
            <span class="text-dark-muted">连接状态</span>
            <span class="text-xs px-2 py-0.5 rounded-full" :class="connected ? 'bg-green-500/15 text-green-400' : 'bg-yellow-500/15 text-yellow-400'">{{ connected ? '● WebSocket' : '● HTTP 轮询' }}</span>
          </div>
        </div>
      </div>

      <!-- Keyboard shortcuts -->
      <div class="bg-dark-panel border border-dark-border rounded-xl p-5">
        <h3 class="flex items-center gap-2 text-sm font-semibold mb-3"><Keyboard :size="14" class="text-blue-400" /> 快捷键</h3>
        <div class="space-y-2">
          <div v-for="s in shortcuts" :key="s.keys" class="flex items-center justify-between text-sm">
            <span class="text-dark-muted">{{ s.desc }}</span>
            <kbd class="bg-dark-card border border-dark-border rounded px-2 py-0.5 text-xs font-mono text-dark-text">{{ s.keys }}</kbd>
          </div>
        </div>
      </div>

      <!-- Actions -->
      <div class="flex gap-3">
        <button @click="reload" class="flex-1 py-2.5 bg-dark-panel border border-dark-border rounded-xl text-sm hover:bg-dark-hover transition-colors flex items-center justify-center gap-2 text-dark-muted hover:text-dark-text">
          <RefreshCw :size="14" /> 刷新页面
        </button>
        <a href="https://github.com" target="_blank" class="flex-1 py-2.5 bg-dark-panel border border-dark-border rounded-xl text-sm hover:bg-dark-hover transition-colors flex items-center justify-center gap-2 text-dark-muted hover:text-dark-text">
          <Globe :size="14" /> 项目主页
        </a>
      </div>

      <div class="text-center text-[10px] text-dark-muted/50 pt-2">Powered by MCP · FastMCP · Vue 3 · TailwindCSS</div>
    </div>
  </div>
</template>
