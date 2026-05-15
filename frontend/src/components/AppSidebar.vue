<template>
  <aside class="h-full w-64 shrink-0 bg-black/80 backdrop-blur border-r border-cyber-500/20 flex flex-col overflow-hidden shadow-2xl shadow-cyber-950/40">
    <!-- Brand -->
    <div class="px-5 py-4 border-b border-cyber-500/20">
      <div class="flex items-center gap-3">
        <div
          class="p-2 rounded-lg bg-cyber-500/10 flex items-center justify-center text-cyber-300 shrink-0 transition-colors"
        >
          <Wifi class="w-5 h-5" />
        </div>
        <div class="flex-1 min-w-0">
          <h1 class="text-sm font-mono font-bold text-cyber-100 tracking-wide">
            AirMon<span class="text-cyber-400 text-glow">GUI</span>
          </h1>
          <p class="text-xs text-slate-400 mt-0.5">Local Aircrack-ng Console</p>
        </div>
        <!-- Mobile close button -->
        <button
          @click="sidebarOpen = false"
          class="lg:hidden p-1 rounded-lg text-slate-400 hover:text-cyber-100 hover:bg-cyber-500/10 transition-colors"
        >
          <X class="w-4 h-4" />
        </button>
      </div>
    </div>

    <!-- Tool health -->
    <div class="px-4 py-2.5 border-b border-cyber-500/20">
      <div class="flex items-center gap-2">
        <span
          :class="toolsOk ? 'bg-success-500 shadow-success-500/50' : 'bg-red-500 shadow-red-500/50'"
          class="w-2 h-2 rounded-full shadow-sm"
        ></span>
        <span class="text-xs font-mono text-slate-400">
          {{ toolsOk ? 'All tools ready' : 'Some tools missing' }}
        </span>
      </div>
    </div>

    <!-- Navigation -->
    <nav class="flex-1 py-3 px-2 space-y-0.5 overflow-y-auto">
      <button
        v-for="item in navItems"
        :key="item.id"
        @click="navigate(item.id)"
        :class="[
          'w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-left transition-all duration-150 group',
          currentView === item.id
            ? 'bg-cyber-500/10 border border-cyber-500/35 text-cyber-200 shadow-lg shadow-cyber-950/20'
            : 'text-slate-400 hover:bg-cyber-500/5 hover:text-cyber-100 border border-transparent hover:border-cyber-500/15',
        ]"
      >
        <component :is="item.icon" class="w-4 h-4 shrink-0" />
        <div class="min-w-0 flex-1">
          <div class="text-sm font-mono font-semibold leading-tight">{{ item.label }}</div>
          <div class="text-xs opacity-60 mt-0.5 leading-tight truncate">
            {{ item.description }}
          </div>
        </div>
        <!-- Scan in-progress indicator -->
        <span
          v-if="item.id === 'scan' && isScanning"
          class="w-2 h-2 rounded-full bg-green-500 shrink-0 animate-pulse"
        ></span>
        <!-- Crack in-progress indicator -->
        <span
          v-if="item.id === 'crack' && isCracking"
          class="w-2 h-2 rounded-full bg-red-500 shrink-0 animate-pulse"
        ></span>
      </button>
    </nav>

    <!-- Footer quick-actions -->
    <div class="px-2 py-3 border-t border-cyber-500/20 space-y-1">
      <button
        @click="handleRefresh"
        :disabled="loading"
        class="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-mono font-medium text-slate-400 hover:text-cyber-100 hover:bg-cyber-500/10 transition-all disabled:opacity-50"
      >
        <RefreshCw :class="loading && 'animate-spin'" class="w-3.5 h-3.5 shrink-0" />
        <span>{{ loading ? 'Refreshing…' : 'Refresh interfaces' }}</span>
      </button>
      <button
        @click="handleCheckKill"
        :disabled="!selectedInterface || loading"
        class="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-mono font-medium text-slate-400 hover:text-cyber-100 hover:bg-cyber-500/10 transition-all disabled:opacity-50"
      >
        <AlertTriangle :class="killing && 'animate-pulse'" class="w-3.5 h-3.5 shrink-0" />
        <span>{{ killing ? 'Releasing…' : selectedInterface ? `Release ${selectedInterface}` : 'Select interface' }}</span>
      </button>
    </div>
  </aside>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import {
  AlertTriangle,
  BarChart2,
  FolderOpen,
  KeyRound,
  LayoutDashboard,
  Radio,
  RefreshCw,
  ScanSearch,
  ScrollText,
  ShieldCheck,
  Terminal,
  Wifi,
  X,
  Zap,
} from 'lucide-vue-next'
import { api } from '../api/index.js'
import { useCrack } from '../composables/useCrack.js'
import { useInterfaces } from '../composables/useInterfaces.js'
import { useNav } from '../composables/useNav.js'
import { useScan } from '../composables/useScan.js'

const { currentView, navigate, sidebarOpen } = useNav()
const { loading, refresh, checkKill, selectedInterface } = useInterfaces()
const { isRunning: isScanning } = useScan()
const { cracking: isCracking } = useCrack()

const toolsOk = ref(false)
const killing = ref(false)

const navItems = [
  { id: 'overview', icon: LayoutDashboard, label: 'Overview', description: 'Dashboard & quick actions' },
  { id: 'monitor', icon: Radio, label: 'Monitor Mode', description: 'airmon-ng · enable/disable' },
  { id: 'scan', icon: ScanSearch, label: 'Network Scan', description: 'airodump-ng · live capture' },
  { id: 'signal', icon: BarChart2, label: 'Signal Analysis', description: 'Channel utilization & RSSI' },
  { id: 'deauth', icon: Zap, label: 'Deauth Attack', description: 'aireplay-ng · disconnect' },
  { id: 'handshake', icon: ShieldCheck, label: 'Handshake Capture', description: 'WPA 4-way · deauth + capture' },
  { id: 'crack', icon: KeyRound, label: 'Crack WPA/WEP', description: 'aircrack-ng · wordlist' },
  { id: 'captures', icon: FolderOpen, label: 'Captures & Logs', description: 'Manage dump files' },
  { id: 'terminal', icon: Terminal, label: 'Terminal', description: 'Integrated PTY shell' },
  { id: 'logs', icon: ScrollText, label: 'Logs', description: 'Command output history' },
]

async function handleRefresh() {
  await refresh()
}

async function handleCheckKill() {
  if (!selectedInterface.value) return
  killing.value = true
  try {
    await checkKill(selectedInterface.value)
  } finally {
    killing.value = false
  }
}

onMounted(async () => {
  try {
    const data = await api.toolCheck()
    toolsOk.value = Object.values(data.tools).every((t) => t.installed)
  } catch {
    // Backend not yet reachable
  }
})
</script>
