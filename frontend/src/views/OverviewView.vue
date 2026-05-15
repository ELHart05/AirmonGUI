<template>
  <div class="p-6 space-y-5 animate-fade-in">
    <!-- Header -->
    <div class="page-header">
      <h2 class="page-title">Overview</h2>
      <p class="page-subtitle">System dashboard and quick actions</p>
    </div>

    <!-- Stats row -->
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
      <div class="card cursor-pointer hover:border-cyber-500/40 hover:bg-slate-800/60 transition-all" @click="navigate('monitor')">
        <p class="text-xs font-semibold text-slate-500 uppercase tracking-wider">Interfaces</p>
        <p class="text-4xl font-bold text-white mt-2">{{ interfaces.length }}</p>
        <p class="text-xs text-slate-500 mt-1">Wireless devices detected</p>
      </div>
      <div class="card cursor-pointer hover:border-cyber-500/40 hover:bg-slate-800/60 transition-all" @click="navigate('scan')">
        <p class="text-xs font-semibold text-slate-500 uppercase tracking-wider">Active Scans</p>
        <p class="text-4xl font-bold mt-2" :class="activeJobCount > 0 ? 'text-green-400' : 'text-white'">
          {{ activeJobCount }}
        </p>
        <p class="text-xs text-slate-500 mt-1">Running capture jobs</p>
      </div>
      <div class="card cursor-pointer hover:border-cyber-500/40 hover:bg-slate-800/60 transition-all" @click="navigate('captures')">
        <p class="text-xs font-semibold text-slate-500 uppercase tracking-wider">Captures</p>
        <p class="text-4xl font-bold text-white mt-2">{{ captureCount }}</p>
        <p class="text-xs text-slate-500 mt-1">CAP / CSV files on disk</p>
      </div>
    </div>

    <!-- Tool status -->
    <div class="card">
      <div class="card-header">
        <h3 class="card-title">Tool Status</h3>
        <button @click="checkTools" class="btn-ghost btn-sm">Refresh</button>
      </div>
      <div v-if="Object.keys(tools).length" class="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div
          v-for="(info, name) in tools"
          :key="name"
          :class="[
            'flex items-center gap-2.5 px-3 py-2.5 rounded-xl border text-xs font-mono transition-all',
            info.installed
              ? 'bg-green-950/40 border-green-700/30 text-green-400'
              : 'bg-red-950/40 border-red-700/30 text-red-400',
          ]"
        >
          <span :class="info.installed ? 'text-green-500' : 'text-red-500'" class="text-base leading-none">
            {{ info.installed ? '●' : '○' }}
          </span>
          <div>
            <div class="font-semibold">{{ name }}</div>
            <div v-if="info.path" class="opacity-60 truncate max-w-[110px]">{{ info.path }}</div>
            <div v-else class="opacity-60">not found</div>
          </div>
        </div>
      </div>
      <div v-else class="text-sm text-slate-500">Loading tool status…</div>
    </div>

    <!-- Quick actions -->
    <div class="card">
      <div class="card-header">
        <h3 class="card-title">Quick Actions</h3>
      </div>
      <div class="flex flex-wrap gap-3">
        <button @click="navigate('monitor')" class="btn-primary">📡 Start Monitor Mode</button>
        <button @click="navigate('scan')" class="btn-secondary">🔍 Launch Scan</button>
        <button @click="navigate('crack')" class="btn-secondary">🔓 Crack a Capture</button>
        <button @click="handleRefresh" :disabled="loading" class="btn-ghost">
          {{ loading ? '…' : '↻ Refresh Interfaces' }}
        </button>
        <button @click="handleCheckKill" :disabled="!selectedInterface || loading" class="btn-ghost">
          {{ selectedInterface ? `⚡ Release ${selectedInterface}` : '⚡ Select Interface' }}
        </button>
      </div>
    </div>

    <!-- Interface snapshot -->
    <div class="card">
      <div class="card-header">
        <h3 class="card-title">Detected Interfaces</h3>
        <button @click="navigate('monitor')" class="btn-ghost btn-sm">Manage →</button>
      </div>
      <div v-if="interfaces.length" class="overflow-x-auto">
        <table class="data-table">
          <thead>
            <tr>
              <th>Interface</th>
              <th>Driver</th>
              <th>Chipset</th>
              <th>Mode</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="iface in interfaces" :key="iface.interface" @click="navigate('monitor')">
              <td class="text-cyber-400 font-semibold">{{ iface.interface }}</td>
              <td>{{ iface.driver || '-' }}</td>
              <td class="max-w-xs truncate">{{ iface.chipset || '-' }}</td>
              <td>
                <span :class="iface.monitor_mode ? 'badge-success' : 'badge-neutral'">
                  {{ iface.monitor_mode ? 'monitor' : 'managed' }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else class="flex items-center gap-4 py-4 text-slate-400">
        <span class="text-3xl">📡</span>
        <div>
          <p class="font-semibold text-slate-300">No interfaces detected</p>
          <p class="text-sm mt-0.5">
            Ensure your wireless adapter is connected and airmon-ng is installed.
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { api } from '../api/index.js'
import { useInterfaces } from '../composables/useInterfaces.js'
import { useNav } from '../composables/useNav.js'
import { useScan } from '../composables/useScan.js'

const { navigate } = useNav()
const { interfaces, selectedInterface, loading, refresh, checkKill } = useInterfaces()
const { jobs } = useScan()

const tools = ref({})
const captureCount = ref(0)
const activeJobCount = computed(() => jobs.value.filter((j) => j.running).length)

async function checkTools() {
  try {
    const data = await api.toolCheck()
    tools.value = data.tools
  } catch {
    // ignore
  }
}

async function handleRefresh() {
  await refresh()
}

async function handleCheckKill() {
  if (!selectedInterface.value) return
  await checkKill(selectedInterface.value)
}

onMounted(async () => {
  await checkTools()
  try {
    const caps = await api.captures.list()
    captureCount.value = caps.captures.length
  } catch {
    // ignore
  }
})
</script>
