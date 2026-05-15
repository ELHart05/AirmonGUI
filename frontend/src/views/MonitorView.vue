<template>
  <div class="p-6 space-y-5 animate-fade-in">
    <div class="page-header">
      <h2 class="page-title">Monitor Mode</h2>
      <p class="page-subtitle">Control airmon-ng — enable or disable monitor mode per interface</p>
    </div>

    <!-- Interface table -->
    <div class="card">
      <div class="card-header">
        <h3 class="card-title">Wireless Interfaces</h3>
        <div class="flex items-center gap-2">
          <span v-if="selectedInterface" class="badge-info">Selected: {{ selectedInterface }}</span>
          <button @click="refresh" :disabled="loading" class="btn-ghost btn-sm">
            {{ loading ? '…' : '↻ Refresh' }}
          </button>
        </div>
      </div>

      <div v-if="interfaces.length" class="overflow-x-auto">
        <table class="data-table">
          <thead>
            <tr>
              <th>PHY</th>
              <th>Interface</th>
              <th>Driver</th>
              <th>Chipset</th>
              <th>Mode</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="iface in interfaces"
              :key="iface.interface"
              :class="selectedInterface === iface.interface && 'row-selected'"
              @click="select(iface.interface)"
            >
              <td class="text-slate-500">{{ iface.phy || '-' }}</td>
              <td class="text-cyber-400 font-bold">{{ iface.interface }}</td>
              <td>{{ iface.driver || '-' }}</td>
              <td class="max-w-xs truncate text-slate-400">{{ iface.chipset || '-' }}</td>
              <td>
                <span :class="iface.monitor_mode ? 'badge-success' : 'badge-neutral'">
                  {{ iface.monitor_mode ? '● monitor' : '○ managed' }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else class="py-6 text-center text-slate-500 text-sm">
        No interfaces found. Click Refresh to scan again.
      </div>
    </div>

    <!-- Controls -->
    <div class="card">
      <div class="card-header">
        <h3 class="card-title">Monitor Mode Controls</h3>
      </div>
      <div class="flex flex-wrap gap-3 items-center">
        <button
          @click="handleStart"
          :disabled="!selectedInterface || loading"
          class="btn-primary"
        >
          <span v-if="startingMonitor" class="inline-block w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin mr-1"></span>
          {{ startingMonitor ? 'Starting…' : '📡 Start Monitor Mode' }}
        </button>
        <button
          @click="handleStop"
          :disabled="!selectedInterface || loading"
          class="btn-secondary"
        >
          <span v-if="stoppingMonitor" class="inline-block w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin mr-1"></span>
          {{ stoppingMonitor ? 'Stopping…' : '⏹ Stop Monitor Mode' }}
        </button>
        <button @click="handleCheckKill" :disabled="!selectedInterface || loading" class="btn-danger">
          <span v-if="killingProcesses" class="inline-block w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin mr-1"></span>
          {{ killingProcesses ? 'Releasing…' : selectedInterface ? `⚡ Release ${selectedInterface}` : '⚡ Select interface' }}
        </button>
      </div>
      <p class="text-xs text-slate-500 mt-3">
        Select an interface in the table above, then click Start or Stop. Monitor mode allows
        packet injection and capture. <strong class="text-slate-400">Release</strong> tells NetworkManager
        and wpa_supplicant to stop managing only the selected interface — other interfaces stay connected.
      </p>
    </div>

    <!-- Command output -->
    <div v-if="lastOutput" class="card">
      <div class="card-header">
        <h3 class="card-title">Last Command Output</h3>
        <span :class="lastOutput.success ? 'badge-success' : 'badge-error'">
          {{ lastOutput.success ? 'OK' : `rc=${lastOutput.returncode}` }}
        </span>
      </div>
      <div class="terminal">
        <div v-if="lastOutput.stdout" class="whitespace-pre-wrap">{{ lastOutput.stdout }}</div>
        <div v-if="lastOutput.stderr" class="text-red-400 mt-2 whitespace-pre-wrap">
          {{ lastOutput.stderr }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useInterfaces } from '../composables/useInterfaces.js'

const { interfaces, selectedInterface, loading, refresh, startMonitor, stopMonitor, checkKill, select } =
  useInterfaces()

const lastOutput = ref(null)
const startingMonitor = ref(false)
const stoppingMonitor = ref(false)
const killingProcesses = ref(false)

async function handleStart() {
  startingMonitor.value = true
  try {
    const data = await startMonitor(selectedInterface.value)
    lastOutput.value = data
  } catch {
    // toast already shown by composable
  } finally {
    startingMonitor.value = false
  }
}

async function handleStop() {
  stoppingMonitor.value = true
  try {
    const data = await stopMonitor(selectedInterface.value)
    lastOutput.value = data
  } catch {
    // toast already shown
  } finally {
    stoppingMonitor.value = false
  }
}

async function handleCheckKill() {
  if (!selectedInterface.value) return
  killingProcesses.value = true
  try {
    const data = await checkKill(selectedInterface.value)
    lastOutput.value = data
  } catch {
    // toast already shown
  } finally {
    killingProcesses.value = false
  }
}
</script>
