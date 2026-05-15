<template>
  <div class="p-6 space-y-5 animate-fade-in">
    <div class="page-header flex items-start justify-between">
      <div>
        <h2 class="page-title">Network Scan</h2>
        <p class="page-subtitle">airodump-ng · discover networks and clients</p>
      </div>
      <div class="flex items-center gap-2 mt-1">
        <span v-if="isRunning" class="flex items-center gap-1.5 badge-success">
          <span class="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse"></span>
          Running
        </span>
        <span v-else class="badge-neutral">Idle</span>
      </div>
    </div>

    <!-- Scan configuration -->
    <div class="card">
      <div class="card-header">
        <h3 class="card-title">Scan Configuration</h3>
      </div>
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-4">
        <div>
          <label class="field-label">Interface *</label>
          <select v-model="form.interface" class="field-select">
            <option value="" disabled>Select interface…</option>
            <option v-for="iface in interfaces" :key="iface.interface" :value="iface.interface">
              {{ iface.interface }}
              {{ iface.monitor_mode ? '(monitor)' : '' }}
            </option>
          </select>
        </div>
        <div>
          <label class="field-label">Channel (optional)</label>
          <input
            v-model="form.channel"
            class="field-input mb-2"
            placeholder="leave empty to hop all channels"
          />
          <div class="space-y-1.5">
            <div class="flex flex-wrap items-center gap-1">
              <span class="text-xs text-slate-500 w-14 shrink-0">2.4 GHz</span>
              <button
                v-for="ch in ch24"
                :key="ch"
                @click="form.channel = String(ch)"
                :class="['px-1.5 py-0.5 rounded text-xs font-mono border transition-colors',
                  form.channel === String(ch)
                    ? 'bg-cyber-500/20 border-cyber-500/50 text-cyber-300'
                    : 'border-slate-700 text-slate-500 hover:border-slate-500 hover:text-slate-200']"
              >{{ ch }}</button>
              <button
                @click="form.channel = '1,6,11'"
                :class="['px-1.5 py-0.5 rounded text-xs font-mono border transition-colors',
                  form.channel === '1,6,11'
                    ? 'bg-amber-500/20 border-amber-500/50 text-amber-300'
                    : 'border-slate-700 text-slate-500 hover:border-slate-500 hover:text-amber-300']"
              >1,6,11</button>
            </div>
            <div class="flex flex-wrap items-center gap-1">
              <span class="text-xs text-slate-500 w-14 shrink-0">5 GHz</span>
              <button
                v-for="ch in ch5"
                :key="ch"
                @click="form.channel = String(ch)"
                :class="['px-1.5 py-0.5 rounded text-xs font-mono border transition-colors',
                  form.channel === String(ch)
                    ? 'bg-cyber-500/20 border-cyber-500/50 text-cyber-300'
                    : 'border-slate-700 text-slate-500 hover:border-slate-500 hover:text-slate-200']"
              >{{ ch }}</button>
            </div>
            <button
              v-if="form.channel"
              @click="form.channel = ''"
              class="text-xs text-slate-600 hover:text-slate-300 transition-colors"
            >✕ clear (hop all)</button>
          </div>
        </div>
        <div>
          <label class="field-label">Band</label>
          <select v-model="form.band" class="field-select">
            <option value="">Any</option>
            <option value="a">5 GHz (a)</option>
            <option value="g">2.4 GHz (g)</option>
            <option value="bg">2.4 GHz (bg)</option>
            <option value="ag">Dual (ag)</option>
          </select>
        </div>
        <div>
          <label class="field-label">Filter BSSID (optional)</label>
          <input
            v-model="form.bssid"
            class="field-input"
            placeholder="00:11:22:33:44:55"
          />
        </div>
        <div>
          <label class="field-label">Output Prefix</label>
          <input
            v-model="form.outputPrefix"
            class="field-input"
            placeholder="campus_scan"
          />
        </div>
        <div>
          <label class="field-label">Auto-refresh</label>
          <div class="flex items-center gap-3 mt-2">
            <label class="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                v-model="autoRefresh"
                class="w-4 h-4 rounded border-slate-600 bg-slate-800 text-cyber-500 focus:ring-cyber-500"
              />
              <span class="text-sm text-slate-300">Every {{ refreshInterval }}s</span>
            </label>
            <input
              type="range"
              v-model.number="refreshInterval"
              min="2"
              max="30"
              step="1"
              class="flex-1 accent-cyber-500"
            />
          </div>
        </div>
      </div>

      <div class="flex flex-wrap gap-3">
        <button @click="start" :disabled="isRunning || !form.interface || scanLoading" class="btn-primary">
          <span v-if="scanLoading && !isRunning" class="inline-block w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin mr-1"></span>
          ▶ Start Scan
        </button>
        <button @click="stop" :disabled="!isRunning || scanLoading" class="btn-danger">
          <span v-if="scanLoading && isRunning" class="inline-block w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin mr-1"></span>
          {{ scanLoading && isRunning ? 'Stopping…' : '⏹ Stop Scan' }}
        </button>
        <button @click="fetchResults" :disabled="!activeJobId || scanLoading" class="btn-secondary">
          {{ scanLoading && !isRunning ? 'Refreshing…' : '↻ Refresh Results' }}
        </button>
        <button v-if="activeJobId" @click="clearResults" class="btn-ghost btn-sm">
          Clear Results
        </button>
      </div>
    </div>

    <!-- Live scan log -->
    <!--<div v-if="logTail" class="card">
      <div class="card-header">
        <h3 class="card-title">Live Capture Log</h3>
        <span class="text-xs text-slate-500 font-mono truncate max-w-xs">
          {{ jobs.find((job) => job.job_id === activeJobId)?.command }}
        </span>
      </div>
      <div class="terminal max-h-52 overflow-y-auto whitespace-pre">
        {{ logTail }}
      </div>
    </div>-->

    <!-- Networks table -->
    <div class="card">
      <div class="card-header">
        <h3 class="card-title">
          Discovered Networks
          <span v-if="results.networks.length" class="badge-info ml-2">
            {{ filteredNetworks.length }}<span v-if="filteredNetworks.length !== results.networks.length"> / {{ results.networks.length }}</span>
          </span>
        </h3>
        <div class="flex flex-wrap items-center gap-2">
          <input
            v-model="networkFilter"
            class="field-input w-40 text-xs"
            placeholder="Filter ESSID / BSSID…"
          />
          <select v-model="privacyFilter" class="field-input text-xs w-28">
            <option value="">All security</option>
            <option value="WPA3">WPA3</option>
            <option value="WPA2">WPA2</option>
            <option value="WPA">WPA</option>
            <option value="WEP">WEP</option>
            <option value="OPN">Open</option>
          </select>
          <select v-model="bandFilter" class="field-input text-xs w-24">
            <option value="">All bands</option>
            <option value="2.4">2.4 GHz</option>
            <option value="5">5 GHz</option>
          </select>
          <button
            v-if="networkFilter || privacyFilter || bandFilter"
            @click="networkFilter = ''; privacyFilter = ''; bandFilter = ''"
            class="text-xs text-slate-500 hover:text-slate-300 underline"
          >Clear</button>
        </div>
      </div>
      <div v-if="filteredNetworks.length" class="overflow-x-auto">
        <table class="data-table">
          <thead>
            <tr>
              <th>BSSID</th>
              <th>ESSID</th>
              <th>CH</th>
              <th>Signal</th>
              <th>Privacy</th>
              <th>Beacons</th>
              <th>#Data</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="row in filteredNetworks"
              :key="pick(row, ['BSSID'])"
              :class="selectedNetwork?.BSSID === row.BSSID && 'row-selected'"
              @click="selectedNetwork = row"
            >
              <td class="text-cyber-400 font-bold">{{ pick(row, ['BSSID']) }}</td>
              <td class="text-white font-semibold">{{ pick(row, ['ESSID', 'essid']) || '&lt;hidden&gt;' }}</td>
              <td class="text-amber-400">{{ pick(row, ['channel', 'Channel', ' channel']) }}</td>
              <td>
                <span :class="signalClass(pick(row, ['Power', 'PWR', 'power']))">
                  {{ pick(row, ['Power', 'PWR', 'power']) }} dBm
                </span>
              </td>
              <td>{{ pick(row, ['Privacy', 'privacy']) }}</td>
              <td>{{ pick(row, ['Beacons', 'beacons']) }}</td>
              <td>{{ pick(row, ['# Data', '#Data', 'data']) }}</td>
              <td>
                <div class="flex gap-1">
                  <button
                    @click.stop="targetNetwork(row)"
                    class="btn-ghost btn-sm text-amber-400 hover:text-amber-300 hover:bg-amber-900/20"
                    title="Set as deauth target"
                  >
                    ⚡ Deauth
                  </button>
                  <button
                    @click.stop="targetHandshake(row)"
                    class="btn-ghost btn-sm text-cyber-400 hover:text-cyber-300 hover:bg-cyber-900/20"
                    title="Capture WPA handshake from this AP"
                  >
                    🤝 H/S
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else class="py-6 text-center text-slate-500 text-sm">
        {{ results.networks.length ? 'No networks match the filter.' : 'No networks discovered yet. Start a scan.' }}
      </div>
    </div>

    <!-- Clients table -->
    <div class="card">
      <div class="card-header">
        <h3 class="card-title">
          Detected Clients
          <span v-if="results.clients.length" class="badge-info ml-2">
            {{ results.clients.length }}
          </span>
        </h3>
      </div>
      <div v-if="results.clients.length" class="overflow-x-auto">
        <table class="data-table">
          <thead>
            <tr>
              <th>Station MAC</th>
              <th>BSSID (AP)</th>
              <th>Signal</th>
              <th>Packets</th>
              <th>Probes</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in results.clients" :key="pick(row, ['Station MAC'])">
              <td class="text-purple-400 font-bold">{{ pick(row, ['Station MAC']) }}</td>
              <td class="text-cyber-400">{{ pick(row, ['BSSID']) }}</td>
              <td>{{ pick(row, ['Power', 'PWR', 'power']) }}</td>
              <td>{{ pick(row, ['# packets', 'Packets', 'Frames']) }}</td>
              <td class="text-slate-400">{{ pick(row, ['Probed ESSIDs', 'probed']) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else class="py-4 text-center text-slate-500 text-sm">
        No clients captured yet.
      </div>
    </div>

    <!-- Job list -->
    <div v-if="jobs.length" class="card">
      <div class="card-header">
        <h3 class="card-title">Job History</h3>
      </div>
      <div class="space-y-2">
        <div
          v-for="job in jobs"
          :key="job.job_id"
          class="flex items-center gap-3 px-3 py-2 bg-slate-800/50 rounded-xl text-xs font-mono"
        >
          <span :class="job.running ? 'text-green-400 animate-pulse' : 'text-slate-500'">●</span>
          <span class="text-slate-400">{{ job.job_id.slice(0, 8) }}</span>
          <span class="text-cyber-400">{{ job.interface }}</span>
          <span class="text-slate-500 flex-1 truncate">{{ job.command }}</span>
          <span :class="job.running ? 'badge-success' : 'badge-neutral'">
            {{ job.running ? 'running' : 'stopped' }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useInterfaces } from '../composables/useInterfaces.js'
import { useNav } from '../composables/useNav.js'
import { useScan } from '../composables/useScan.js'
import { useTarget } from '../composables/useTarget.js'
import { useToast } from '../composables/useToast.js'

const { interfaces } = useInterfaces()
const { form, activeJobId, results, isRunning, jobs, scanLoading, logTail, start, stop, fetchResults, loadJobs } = useScan()
const { setTarget } = useTarget()
const { navigate } = useNav()
const { info } = useToast()

const ch24 = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]
const ch5 = [36, 40, 44, 48, 52, 56, 60, 64, 100, 104, 108, 112, 116, 120, 124, 128, 132, 136, 140, 149, 153, 157, 161, 165]

const networkFilter = ref('')
const privacyFilter = ref('')
const bandFilter = ref('')
const selectedNetwork = ref(null)
const autoRefresh = ref(false)
const refreshInterval = ref(5)
let timer = null

const filteredNetworks = computed(() => {
  const q = networkFilter.value.toLowerCase()
  const priv = privacyFilter.value.toUpperCase()
  const band = bandFilter.value
  return results.networks.filter((r) => {
    const bssid = (r['BSSID'] || '').toLowerCase()
    const essid = (r['ESSID'] || r['essid'] || '').toLowerCase()
    if (q && !bssid.includes(q) && !essid.includes(q)) return false
    if (priv) {
      const privacy = (r['Privacy'] || r['privacy'] || 'OPN').toUpperCase()
      if (!privacy.includes(priv)) return false
    }
    if (band) {
      const ch = parseInt(r['channel'] || r['Channel'] || r[' channel'] || '0')
      if (band === '2.4' && !(ch >= 1 && ch <= 14)) return false
      if (band === '5' && !(ch >= 36)) return false
    }
    return true
  })
})

function pick(obj, keys) {
  for (const key of keys) {
    const v = obj[key]
    if (v && String(v).trim() !== '') return String(v).trim()
  }
  return '-'
}

function signalClass(val) {
  const n = parseInt(val)
  if (isNaN(n)) return 'text-slate-400'
  if (n >= -50) return 'text-green-400 font-semibold'
  if (n >= -70) return 'text-amber-400'
  return 'text-red-400'
}

function targetNetwork(row) {
  setTarget(row)
  info(`Targeting ${pick(row, ['ESSID', 'essid']) || pick(row, ['BSSID'])} — switching to Deauth`)
  navigate('deauth')
}

function targetHandshake(row) {
  setTarget(row)
  info(`Targeting ${pick(row, ['ESSID', 'essid']) || pick(row, ['BSSID'])} for handshake capture`)
  navigate('handshake')
}

function clearResults() {
  results.networks = []
  results.clients = []
}

function startTimer() {
  clearInterval(timer)
  if (autoRefresh.value && activeJobId.value && isRunning.value) {
    timer = setInterval(fetchResults, refreshInterval.value * 1000)
  }
}

watch(autoRefresh, startTimer)
watch(refreshInterval, startTimer)

// Stop timer automatically when scan stops; restart when new scan begins
watch(isRunning, (running) => {
  if (!running) clearInterval(timer)
  else startTimer()
})

// When a new job starts, reset old results then kick off the timer
watch(activeJobId, (id, oldId) => {
  if (id && id !== oldId) {
    clearResults()
    startTimer()
  }
})

onMounted(async () => {
  await loadJobs()
  if (activeJobId.value) await fetchResults()
})

onUnmounted(() => clearInterval(timer))
</script>
