<script setup lang="ts">
import { Menu, MessageCircle, Code2, BookOpen } from 'lucide-vue-next'

const props = defineProps<{ activeTab: string; connected: boolean; waitingCount: number; sessionCount: number; projectCount: number; currentTitle: string; sidebarOpen: boolean; appMode: 'chat' | 'code' | 'vault' }>()
const emit = defineEmits<{ 'update:activeTab': [tab: string]; 'toggleSidebar': []; 'update:appMode': [mode: 'chat' | 'code' | 'vault'] }>()
</script>

<template>
  <header class="flex items-center h-14 px-3 select-none shrink-0">
    <!-- Left: hamburger -->
    <button @click="emit('toggleSidebar')" class="w-10 h-10 flex items-center justify-center rounded-full hover:bg-white/[0.08] transition-colors shrink-0">
      <Menu :size="20" class="text-[#9aa0a6]" />
    </button>

    <!-- Center: mode toggle -->
    <div class="flex-1 flex items-center justify-center">
      <div class="flex items-center bg-[#131314] rounded-full p-1 gap-0.5">
        <button
          @click="emit('update:appMode', 'chat')"
          class="flex items-center gap-1.5 px-4 py-1.5 rounded-full text-sm transition-all duration-200"
          :class="appMode === 'chat' ? 'bg-[#2b2d31] text-[#e3e3e1] shadow-sm' : 'text-[#9aa0a6] hover:text-[#c4c7c5]'"
        >
          <MessageCircle :size="15" />
          <span>聊天</span>
        </button>
        <button
          @click="emit('update:appMode', 'code')"
          class="flex items-center gap-1.5 px-4 py-1.5 rounded-full text-sm transition-all duration-200"
          :class="appMode === 'code' ? 'bg-[#2b2d31] text-[#e3e3e1] shadow-sm' : 'text-[#9aa0a6] hover:text-[#c4c7c5]'"
        >
          <Code2 :size="15" />
          <span>工作</span>
        </button>
        <button
          @click="emit('update:appMode', 'vault')"
          class="flex items-center gap-1.5 px-4 py-1.5 rounded-full text-sm transition-all duration-200"
          :class="appMode === 'vault' ? 'bg-[#2b2d31] text-[#e3e3e1] shadow-sm' : 'text-[#9aa0a6] hover:text-[#c4c7c5]'"
        >
          <BookOpen :size="15" />
          <span>笔记</span>
        </button>
      </div>
    </div>

    <!-- Right: status -->
    <div class="flex items-center gap-3 pr-1 shrink-0">
      <span v-if="waitingCount > 0" class="text-xs text-blue-400 font-medium px-2.5 py-1 bg-blue-400/10 rounded-full">
        {{ waitingCount }} 待回复
      </span>
      <span class="w-2 h-2 rounded-full shrink-0" :class="connected ? 'bg-emerald-500' : 'bg-zinc-600'" :title="connected ? '已连接' : '离线'" />
    </div>
  </header>
</template>
