import { reactive, watch } from 'vue'

export interface Settings {
  username: string
  notifySound: boolean
  markdown: boolean
  fontSize: number
  volume: number
  quickPrompts: string[]
  theme: 'dark' | 'light'
  vaultPath: string
}

const STORAGE_KEY = 'mcp-chat-settings'

const defaults: Settings = {
  username: '',
  notifySound: true,
  markdown: true,
  fontSize: 14,
  volume: 50,
  quickPrompts: ['继续', '确认', '好的', '重试'],
  theme: 'dark',
  vaultPath: 'D:/工作笔记/work/MCP',
}

function load(): Settings {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) {
      const parsed = JSON.parse(saved)
      return { ...defaults, ...parsed, quickPrompts: parsed.quickPrompts || [...defaults.quickPrompts] }
    }
    return { ...defaults, quickPrompts: [...defaults.quickPrompts] }
  } catch {
    return { ...defaults, quickPrompts: [...defaults.quickPrompts] }
  }
}

export function useSettings() {
  const settings = reactive<Settings>(load())

  watch(settings, (v) => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(v))
  }, { deep: true })

  return { settings }
}
