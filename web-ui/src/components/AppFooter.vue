<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { MessageSquare, Wifi, WifiOff, Clock } from 'lucide-vue-next'

defineProps<{ connected: boolean; sessionCount: number; waitingCount: number; wsLatency: number }>()

const time = ref('')
let timer: number

onMounted(() => {
  const tick = () => { time.value = new Date().toLocaleString('zh-CN', { hour12: false }) }
  tick()
  timer = window.setInterval(tick, 1000)
})
onUnmounted(() => clearInterval(timer))
</script>

<template>
  <footer class="flex items-center justify-between px-5 py-1.5 border-t border-dark-border bg-dark-panel text-[11px] text-dark-muted select-none">
    <div class="flex items-center gap-4">
      <span class="flex items-center gap-1" :class="connected ? 'text-green-400' : 'text-yellow-400'">
        <component :is="connected ? Wifi : WifiOff" :size="10" />
        {{ connected ? 'WebSocket' : 'HTTP' }}
        <span v-if="connected && wsLatency >= 0" class="text-dark-muted/60">{{ wsLatency }}ms</span>
      </span>
      <span v-if="sessionCount > 0" class="flex items-center gap-1">
        <MessageSquare :size="10" />
        {{ sessionCount }} 会话
        <template v-if="waitingCount > 0"> · <span class="text-green-400">{{ waitingCount }} 待回复</span></template>
      </span>
    </div>
    <div class="flex items-center gap-1">
      <Clock :size="10" />
      <span>{{ time }}</span>
      <span class="ml-2 text-dark-muted/40">MCP Chat v1.0</span>
    </div>
  </footer>
</template>
