<script setup lang="ts">
import { ref } from 'vue'
import { Copy, Check, ChevronDown, ChevronRight, Terminal, Settings, Zap, BookOpen, AlertTriangle, HelpCircle, FolderOpen } from 'lucide-vue-next'

defineOptions({ name: 'GuideTab' })
type IDE = 'windsurf' | 'cursor' | 'copilot'
const activeIDE = ref<IDE>('windsurf')
const openSections = ref<Record<string, boolean>>({ quick: true })

function toggle(key: string) {
  openSections.value[key] = !openSections.value[key]
}
function isOpen(key: string, defaultOpen = false) {
  return openSections.value[key] ?? defaultOpen
}

const copiedKey = ref('')
function copyCode(text: string, key: string) {
  navigator.clipboard.writeText(text).then(() => {
    copiedKey.value = key
    setTimeout(() => { copiedKey.value = '' }, 2000)
  }).catch(() => {})
}

const ides = [
  { id: 'windsurf' as IDE, name: 'Windsurf', icon: '🏄', color: 'from-cyan-500/20 to-blue-500/20', desc: 'Cascade AI' },
  { id: 'cursor' as IDE, name: 'Cursor', icon: '⚡', color: 'from-purple-500/20 to-pink-500/20', desc: 'Agent 模式' },
  { id: 'copilot' as IDE, name: 'VS Code + Copilot', icon: '🤖', color: 'from-green-500/20 to-emerald-500/20', desc: 'Agent 模式' },
]

const codes: Record<string, string> = {
  pip: `pip install mcp`,
  startPrompt: `调用 get_prompt 获取工作流程，然后调用 chat 工具与我对话`,
  // ---- Windsurf ----
  windsurfGlobal: `{
  "mcpServers": {
    "mcp-chat": {
      "command": "python",
      "args": ["E:/MCP/server.py"],
      "env": {
        "MCP_CHAT_SOURCE": "Windsurf",
        "MCP_CHAT_PROJECT": "MyProject"
      }
    }
  }
}`,
  // ---- Cursor ----
  cursorGlobal: `{
  "mcpServers": {
    "mcp-chat": {
      "command": "python",
      "args": ["E:/MCP/server.py"],
      "env": {
        "MCP_CHAT_SOURCE": "Cursor",
        "MCP_CHAT_PROJECT": "MyProject"
      }
    }
  }
}`,
  // ---- Copilot ----
  copilotMcp: `{
  "servers": {
    "mcp-chat": {
      "type": "stdio",
      "command": "python",
      "args": ["E:/MCP/server.py"],
      "env": {
        "MCP_CHAT_SOURCE": "Copilot",
        "MCP_CHAT_PROJECT": "MyProject"
      }
    }
  }
}`,
}
</script>

<template>
  <div class="flex-1 overflow-y-auto p-6">
    <div class="max-w-3xl mx-auto">
      <!-- Header -->
      <div class="text-center mb-8">
        <h1 class="text-2xl font-bold text-white mb-2">MCP Chat 使用指南</h1>
        <p class="text-dark-muted text-sm">3 步上手，让 AI 通过浏览器与你实时对话</p>
      </div>

      <!-- ======================== QUICK START ======================== -->
      <div class="border-2 border-blue-500/30 rounded-xl overflow-hidden mb-8 bg-gradient-to-b from-blue-500/5 to-transparent">
        <button @click="toggle('quick')" class="w-full flex items-center gap-3 px-5 py-4 text-left">
          <Zap :size="20" class="text-blue-400 flex-shrink-0" />
          <span class="flex-1 font-bold text-base text-white">快速开始（3 步）</span>
          <component :is="isOpen('quick', true) ? ChevronDown : ChevronRight" :size="16" class="text-dark-muted" />
        </button>
        <div v-if="isOpen('quick', true)" class="px-5 pb-5 space-y-5">
          <!-- Step 1 -->
          <div class="flex gap-4">
            <div class="flex-shrink-0 w-8 h-8 rounded-full bg-blue-500 text-white flex items-center justify-center text-sm font-bold">1</div>
            <div class="flex-1 min-w-0 pt-1">
              <h4 class="text-sm font-semibold text-white mb-1">安装依赖</h4>
              <p class="text-xs text-dark-muted mb-2">确保 Python 环境中已安装 MCP 库</p>
              <div class="relative">
                <button @click="copyCode(codes.pip, 'pip')" class="absolute top-2 right-2 px-2 py-0.5 text-[10px] rounded flex items-center gap-1 z-10 bg-blue-500/20 text-blue-400 hover:bg-blue-500/30 transition-colors">
                  <component :is="copiedKey === 'pip' ? Check : Copy" :size="10" /> {{ copiedKey === 'pip' ? '已复制' : '复制' }}
                </button>
                <pre class="bg-[#161618] border border-dark-border rounded-lg px-4 py-3 text-sm text-green-400 font-mono">pip install mcp</pre>
              </div>
            </div>
          </div>
          <!-- Step 2 -->
          <div class="flex gap-4">
            <div class="flex-shrink-0 w-8 h-8 rounded-full bg-blue-500 text-white flex items-center justify-center text-sm font-bold">2</div>
            <div class="flex-1 min-w-0 pt-1">
              <h4 class="text-sm font-semibold text-white mb-1">配置 MCP 服务器</h4>
              <p class="text-xs text-dark-muted">在下方选择你的 IDE，复制配置到对应的配置文件</p>
            </div>
          </div>
          <!-- Step 3 -->
          <div class="flex gap-4">
            <div class="flex-shrink-0 w-8 h-8 rounded-full bg-blue-500 text-white flex items-center justify-center text-sm font-bold">3</div>
            <div class="flex-1 min-w-0 pt-1">
              <h4 class="text-sm font-semibold text-white mb-1">发送提示词</h4>
              <p class="text-xs text-dark-muted mb-2">在 IDE 的 AI 聊天中输入以下内容：</p>
              <div class="relative">
                <button @click="copyCode(codes.startPrompt, 'sp')" class="absolute top-2 right-2 px-2 py-0.5 text-[10px] rounded flex items-center gap-1 z-10 bg-blue-500/20 text-blue-400 hover:bg-blue-500/30 transition-colors">
                  <component :is="copiedKey === 'sp' ? Check : Copy" :size="10" /> {{ copiedKey === 'sp' ? '已复制' : '复制' }}
                </button>
                <pre class="bg-[#161618] border border-blue-500/30 rounded-lg px-4 py-3 text-sm text-blue-300 font-mono">{{ codes.startPrompt }}</pre>
              </div>
              <p class="text-xs text-dark-muted mt-2">浏览器会自动打开 <code class="bg-dark-hover px-1 py-0.5 rounded text-blue-300 text-[11px]">http://127.0.0.1:8080</code>，在网页中与 AI 交互</p>
            </div>
          </div>
        </div>
      </div>

      <!-- IDE selector -->
      <h2 class="text-sm font-semibold text-dark-muted mb-3 uppercase tracking-wider">选择 IDE 查看配置</h2>
      <div class="flex gap-3 mb-6">
        <button
          v-for="ide in ides" :key="ide.id"
          @click="activeIDE = ide.id"
          class="flex-1 py-3 px-4 rounded-xl border transition-all text-center"
          :class="activeIDE === ide.id ? `bg-gradient-to-r ${ide.color} border-blue-500/40 shadow-lg` : 'bg-dark-card border-dark-border hover:bg-dark-hover'"
        >
          <div class="text-2xl mb-1">{{ ide.icon }}</div>
          <div class="text-sm font-medium" :class="activeIDE === ide.id ? 'text-white' : 'text-dark-muted'">{{ ide.name }}</div>
          <div class="text-[10px] mt-0.5" :class="activeIDE === ide.id ? 'text-white/60' : 'text-dark-muted/50'">{{ ide.desc }}</div>
        </button>
      </div>

      <!-- ======================== WINDSURF ======================== -->
      <template v-if="activeIDE === 'windsurf'">
        <div class="border border-dark-border rounded-xl overflow-hidden mb-4">
          <div class="px-5 py-4 bg-dark-card border-b border-dark-border flex items-center gap-3">
            <Settings :size="18" class="text-cyan-400 flex-shrink-0" />
            <span class="font-semibold text-sm">Windsurf 配置</span>
          </div>
          <div class="px-5 py-4 bg-dark-panel space-y-4">
            <div>
              <p class="text-sm text-dark-muted mb-1">配置文件路径：</p>
              <code class="block bg-dark-card px-3 py-2 rounded-lg text-xs text-cyan-300 border border-dark-border font-mono">~/.codeium/windsurf/mcp_config.json</code>
              <p class="text-[11px] text-dark-muted/60 mt-1">Windows: <code class="text-dark-muted">%USERPROFILE%\.codeium\windsurf\mcp_config.json</code></p>
            </div>
            <div>
              <p class="text-sm text-dark-muted mb-2">将以下内容写入配置文件（修改 <code class="text-orange-300 text-xs">args</code> 中的路径为你的 server.py 路径）：</p>
              <div class="relative">
                <button @click="copyCode(codes.windsurfGlobal, 'wg')" class="absolute top-2 right-2 px-2 py-0.5 text-[10px] rounded flex items-center gap-1 z-10 bg-blue-500/20 text-blue-400 hover:bg-blue-500/30 transition-colors">
                  <component :is="copiedKey === 'wg' ? Check : Copy" :size="10" /> {{ copiedKey === 'wg' ? '已复制' : '复制' }}
                </button>
                <pre class="bg-[#161618] border border-dark-border rounded-lg p-4 pr-16 text-[13px] text-dark-text overflow-x-auto leading-relaxed"><code>{{ codes.windsurfGlobal }}</code></pre>
              </div>
            </div>
            <div class="bg-cyan-500/5 border border-cyan-500/20 rounded-lg p-3 space-y-1.5">
              <p class="text-xs text-cyan-400 font-medium">验证连接</p>
              <p class="text-xs text-dark-muted">1. 保存配置文件后，Windsurf 会自动检测到变化</p>
              <p class="text-xs text-dark-muted">2. 按 <code class="bg-dark-hover px-1 py-0.5 rounded text-cyan-300 text-[11px]">Ctrl+Shift+P</code> → 输入 <code class="bg-dark-hover px-1 py-0.5 rounded text-cyan-300 text-[11px]">Manage MCP</code></p>
              <p class="text-xs text-dark-muted">3. 确认 <code class="text-cyan-300 text-[11px]">mcp-chat</code> 旁边显示绿色圆点</p>
              <p class="text-xs text-dark-muted">4. 开新对话，发送提示词即可</p>
            </div>
          </div>
        </div>
      </template>

      <!-- ======================== CURSOR ======================== -->
      <template v-if="activeIDE === 'cursor'">
        <div class="border border-dark-border rounded-xl overflow-hidden mb-4">
          <div class="px-5 py-4 bg-dark-card border-b border-dark-border flex items-center gap-3">
            <Settings :size="18" class="text-purple-400 flex-shrink-0" />
            <span class="font-semibold text-sm">Cursor 配置</span>
          </div>
          <div class="px-5 py-4 bg-dark-panel space-y-4">
            <div>
              <p class="text-sm text-dark-muted mb-1">配置文件路径（二选一）：</p>
              <code class="block bg-dark-card px-3 py-2 rounded-lg text-xs text-purple-300 border border-dark-border font-mono mb-1">~/.cursor/mcp.json</code>
              <p class="text-[11px] text-dark-muted/60">或项目根目录下 <code class="text-dark-muted">.cursor/mcp.json</code></p>
            </div>
            <div>
              <p class="text-sm text-dark-muted mb-2">将以下内容写入配置文件：</p>
              <div class="relative">
                <button @click="copyCode(codes.cursorGlobal, 'cg')" class="absolute top-2 right-2 px-2 py-0.5 text-[10px] rounded flex items-center gap-1 z-10 bg-blue-500/20 text-blue-400 hover:bg-blue-500/30 transition-colors">
                  <component :is="copiedKey === 'cg' ? Check : Copy" :size="10" /> {{ copiedKey === 'cg' ? '已复制' : '复制' }}
                </button>
                <pre class="bg-[#161618] border border-dark-border rounded-lg p-4 pr-16 text-[13px] text-dark-text overflow-x-auto leading-relaxed"><code>{{ codes.cursorGlobal }}</code></pre>
              </div>
            </div>
            <div class="bg-purple-500/5 border border-purple-500/20 rounded-lg p-3 space-y-1.5">
              <p class="text-xs text-purple-400 font-medium">验证连接</p>
              <p class="text-xs text-dark-muted">1. 打开 <code class="bg-dark-hover px-1 py-0.5 rounded text-purple-300 text-[11px]">Settings → MCP</code>，确认 mcp-chat 状态为绿色</p>
              <p class="text-xs text-dark-muted">2. 聊天模式切换为 <strong class="text-white">Agent</strong>（非 Ask 模式）</p>
              <p class="text-xs text-dark-muted">3. 建议开启 <code class="bg-dark-hover px-1 py-0.5 rounded text-purple-300 text-[11px]">Auto-approve</code> 以获更流畅体验</p>
            </div>
          </div>
        </div>
      </template>

      <!-- ======================== COPILOT ======================== -->
      <template v-if="activeIDE === 'copilot'">
        <div class="border border-dark-border rounded-xl overflow-hidden mb-4">
          <div class="px-5 py-4 bg-dark-card border-b border-dark-border flex items-center gap-3">
            <Settings :size="18" class="text-green-400 flex-shrink-0" />
            <span class="font-semibold text-sm">VS Code + GitHub Copilot 配置</span>
          </div>
          <div class="px-5 py-4 bg-dark-panel space-y-4">
            <div>
              <p class="text-sm text-dark-muted mb-1">配置文件路径：</p>
              <code class="block bg-dark-card px-3 py-2 rounded-lg text-xs text-green-300 border border-dark-border font-mono">.vscode/mcp.json（项目根目录）</code>
            </div>
            <div>
              <p class="text-sm text-dark-muted mb-2">将以下内容写入配置文件：</p>
              <div class="relative">
                <button @click="copyCode(codes.copilotMcp, 'cm')" class="absolute top-2 right-2 px-2 py-0.5 text-[10px] rounded flex items-center gap-1 z-10 bg-blue-500/20 text-blue-400 hover:bg-blue-500/30 transition-colors">
                  <component :is="copiedKey === 'cm' ? Check : Copy" :size="10" /> {{ copiedKey === 'cm' ? '已复制' : '复制' }}
                </button>
                <pre class="bg-[#161618] border border-dark-border rounded-lg p-4 pr-16 text-[13px] text-dark-text overflow-x-auto leading-relaxed"><code>{{ codes.copilotMcp }}</code></pre>
              </div>
            </div>
            <div class="bg-green-500/5 border border-green-500/20 rounded-lg p-3 space-y-1.5">
              <p class="text-xs text-green-400 font-medium">验证连接</p>
              <p class="text-xs text-dark-muted">1. 安装 <strong class="text-white">GitHub Copilot</strong> + <strong class="text-white">GitHub Copilot Chat</strong> 扩展</p>
              <p class="text-xs text-dark-muted">2. Copilot Chat 模式切换为 <strong class="text-white">Agent</strong></p>
              <p class="text-xs text-dark-muted">3. 点击工具图标确认 <code class="text-green-300 text-[11px]">mcp-chat</code> 已加载</p>
              <p class="text-xs text-dark-muted">4. VS Code 版本需 1.99+</p>
            </div>
          </div>
        </div>
      </template>

      <!-- ======================== MULTI-IDE ======================== -->
      <div class="border border-dark-border rounded-xl overflow-hidden mb-4">
        <button @click="toggle('multi')" class="w-full flex items-center gap-3 px-5 py-4 bg-dark-card hover:bg-dark-hover transition-colors text-left">
          <FolderOpen :size="18" class="text-orange-400 flex-shrink-0" />
          <span class="flex-1 font-semibold text-sm">多 IDE / 多项目管理</span>
          <component :is="isOpen('multi') ? ChevronDown : ChevronRight" :size="16" class="text-dark-muted" />
        </button>
        <div v-if="isOpen('multi')" class="px-5 py-4 bg-dark-panel border-t border-dark-border space-y-4">
          <p class="text-sm text-dark-muted">通过环境变量标识不同的 IDE 和项目，所有会话统一在浏览器中管理：</p>
          <div class="grid grid-cols-2 gap-3">
            <div class="bg-dark-card border border-dark-border rounded-lg p-3">
              <code class="text-xs text-cyan-300 font-mono">MCP_CHAT_SOURCE</code>
              <p class="text-[11px] text-dark-muted mt-1">IDE 名称，如 Windsurf、Cursor</p>
            </div>
            <div class="bg-dark-card border border-dark-border rounded-lg p-3">
              <code class="text-xs text-orange-300 font-mono">MCP_CHAT_PROJECT</code>
              <p class="text-[11px] text-dark-muted mt-1">项目名称，用于分组管理</p>
            </div>
          </div>
          <div class="bg-dark-card border border-dark-border rounded-lg p-3 space-y-1">
            <p class="text-xs text-dark-muted"><span class="text-green-400">✓</span> 多个 IDE 可同时连接同一个 MCP Chat 实例</p>
            <p class="text-xs text-dark-muted"><span class="text-green-400">✓</span> 先启动的 IDE 成为主实例，后续 IDE 自动连接</p>
            <p class="text-xs text-dark-muted"><span class="text-green-400">✓</span> 侧栏按项目分组，支持按来源和项目双重筛选</p>
          </div>
        </div>
      </div>

      <!-- ======================== TROUBLESHOOTING ======================== -->
      <div class="border border-dark-border rounded-xl overflow-hidden mb-4">
        <button @click="toggle('faq')" class="w-full flex items-center gap-3 px-5 py-4 bg-dark-card hover:bg-dark-hover transition-colors text-left">
          <HelpCircle :size="18" class="text-yellow-400 flex-shrink-0" />
          <span class="flex-1 font-semibold text-sm">常见问题</span>
          <component :is="isOpen('faq') ? ChevronDown : ChevronRight" :size="16" class="text-dark-muted" />
        </button>
        <div v-if="isOpen('faq')" class="px-5 py-4 bg-dark-panel border-t border-dark-border space-y-4">
          <div>
            <p class="text-sm font-medium text-white mb-1">MCP 工具没有出现？</p>
            <div class="text-xs text-dark-muted space-y-1 pl-3">
              <p>1. 确认配置文件的 JSON 格式正确（注意 <code class="text-red-300">mcpServers</code> 而非 <code class="text-red-300 line-through">mcp.servers</code>）</p>
              <p>2. 确认 <code class="text-blue-300">python</code> 命令可用，或改用完整路径如 <code class="text-blue-300">D:/env/python.exe</code></p>
              <p>3. 重启 IDE 或刷新 MCP 连接</p>
            </div>
          </div>
          <div>
            <p class="text-sm font-medium text-white mb-1">transport closed 错误？</p>
            <p class="text-xs text-dark-muted pl-3">chat 工具会长时间等待用户回复，这是正常的。部分 IDE 默认超时较短，已在配置中处理。</p>
          </div>
          <div>
            <p class="text-sm font-medium text-white mb-1">浏览器没有自动打开？</p>
            <p class="text-xs text-dark-muted pl-3">手动访问 <code class="text-blue-300">http://127.0.0.1:8080</code> 即可。</p>
          </div>
          <div>
            <p class="text-sm font-medium text-white mb-1">端口 8080 被占用？</p>
            <p class="text-xs text-dark-muted pl-3">修改 server.py 顶部的 <code class="text-blue-300">PORT = 8080</code> 和 <code class="text-blue-300">WS_PORT = 8081</code>。</p>
          </div>
        </div>
      </div>

      <!-- ======================== REQUIREMENTS ======================== -->
      <div class="border border-dark-border rounded-xl overflow-hidden mb-4">
        <button @click="toggle('req')" class="w-full flex items-center gap-3 px-5 py-4 bg-dark-card hover:bg-dark-hover transition-colors text-left">
          <Terminal :size="18" class="text-dark-muted flex-shrink-0" />
          <span class="flex-1 font-semibold text-sm">环境要求</span>
          <component :is="isOpen('req') ? ChevronDown : ChevronRight" :size="16" class="text-dark-muted" />
        </button>
        <div v-if="isOpen('req')" class="px-5 py-4 bg-dark-panel border-t border-dark-border">
          <div class="grid grid-cols-3 gap-3 text-center">
            <div class="bg-dark-card border border-dark-border rounded-lg p-3">
              <div class="text-lg mb-1">🐍</div>
              <div class="text-xs font-medium text-white">Python 3.10+</div>
            </div>
            <div class="bg-dark-card border border-dark-border rounded-lg p-3">
              <div class="text-lg mb-1">📦</div>
              <div class="text-xs font-medium text-white">mcp (pip)</div>
            </div>
            <div class="bg-dark-card border border-dark-border rounded-lg p-3">
              <div class="text-lg mb-1">🔌</div>
              <div class="text-xs font-medium text-white">websockets (可选)</div>
              <div class="text-[10px] text-dark-muted mt-0.5">实时通信</div>
            </div>
          </div>
        </div>
      </div>

    </div>
  </div>
</template>
