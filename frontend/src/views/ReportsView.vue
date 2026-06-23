<template>
  <div class="p-6 space-y-5 animate-fade-in">
    <div class="page-header flex items-start justify-between">
      <div>
        <h2 class="page-title">Audit Reports</h2>
        <p class="page-subtitle">Generate and export a session report — HTML download or browser PDF</p>
      </div>
      <div class="flex items-center gap-2 mt-1">
        <button @click="refresh" :disabled="loading" class="btn-ghost btn-sm">
          <span v-if="loading" class="inline-block w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin mr-1"></span>
          Refresh Data
        </button>
      </div>
    </div>

    <!-- Report configuration -->
    <div class="card">
      <div class="card-header">
        <h3 class="card-title">Report Settings</h3>
      </div>
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <div>
          <label class="field-label">Title</label>
          <input v-model="config.title" class="field-input" placeholder="Wireless Security Audit" />
        </div>
        <div>
          <label class="field-label">Author / Tester</label>
          <input v-model="config.author" class="field-input" placeholder="Your name or organisation" />
        </div>
        <div>
          <label class="field-label">Target Scope</label>
          <input v-model="config.scope" class="field-input" placeholder="e.g. Lab SSID / Building A" />
        </div>
      </div>
      <div class="mt-4">
        <label class="field-label">Notes / Executive Summary</label>
        <textarea v-model="config.notes" class="field-input h-24 resize-none" placeholder="Brief description of the test, findings, or any extra context…" />
      </div>
    </div>

    <!-- Summary tiles -->
    <div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
      <div class="card text-center">
        <p class="text-3xl font-bold text-white">{{ summary.interfaces }}</p>
        <p class="text-xs text-slate-500 mt-1 uppercase tracking-wider">Interfaces</p>
      </div>
      <div class="card text-center">
        <p class="text-3xl font-bold" :class="summary.networks > 0 ? 'text-cyber-400' : 'text-white'">{{ summary.networks }}</p>
        <p class="text-xs text-slate-500 mt-1 uppercase tracking-wider">Networks Found</p>
      </div>
      <div class="card text-center">
        <p class="text-3xl font-bold" :class="summary.clients > 0 ? 'text-amber-400' : 'text-white'">{{ summary.clients }}</p>
        <p class="text-xs text-slate-500 mt-1 uppercase tracking-wider">Clients Found</p>
      </div>
      <div class="card text-center">
        <p class="text-3xl font-bold" :class="summary.captures > 0 ? 'text-green-400' : 'text-white'">{{ summary.captures }}</p>
        <p class="text-xs text-slate-500 mt-1 uppercase tracking-wider">Capture Files</p>
      </div>
    </div>

    <!-- Data preview sections -->
    <div v-if="networks.length" class="card">
      <div class="card-header">
        <h3 class="card-title">Discovered Networks ({{ networks.length }})</h3>
      </div>
      <div class="overflow-x-auto">
        <table class="data-table text-xs">
          <thead>
            <tr>
              <th>BSSID</th>
              <th>ESSID</th>
              <th>CH</th>
              <th>Signal</th>
              <th>Privacy</th>
              <th>Clients</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="ap in networks" :key="ap.bssid">
              <td class="font-mono text-cyber-400">{{ ap.bssid }}</td>
              <td class="text-white">{{ ap.essid || '&lt;hidden&gt;' }}</td>
              <td class="text-amber-400">{{ ap.channel }}</td>
              <td :class="signalClass(ap.dbm)">{{ ap.dbm }} dBm</td>
              <td>{{ ap.privacy }}</td>
              <td>{{ ap.clientCount }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="captureFiles.length" class="card">
      <div class="card-header">
        <h3 class="card-title">Capture Files ({{ captureFiles.length }})</h3>
      </div>
      <div class="space-y-1">
        <div
          v-for="f in captureFiles"
          :key="f.filename"
          class="flex items-center gap-3 px-3 py-2 rounded-lg bg-slate-800/50 text-xs font-mono"
        >
          <span class="text-cyber-400 flex-1 truncate">{{ f.filename }}</span>
          <span class="text-slate-500">{{ f.size_human }}</span>
        </div>
      </div>
    </div>

    <!-- Export actions -->
    <div class="card">
      <div class="card-header">
        <h3 class="card-title">Export</h3>
      </div>
      <div class="flex flex-wrap gap-3">
        <button @click="downloadHtml" class="btn-primary">
          Download HTML Report
        </button>
        <button @click="printReport" class="btn-secondary">
          Print / Save as PDF
        </button>
      </div>
      <p class="text-xs text-slate-500 mt-3">
        "Print / Save as PDF" uses your browser's print dialog. Select "Save as PDF" as the destination for a PDF file.
      </p>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { api } from '../api/index.js'
import { useInterfaces } from '../composables/useInterfaces.js'
import { useScan } from '../composables/useScan.js'
import { buildHtmlReport } from '../utils/report.js'

const { interfaces } = useInterfaces()
const { results } = useScan()

const loading = ref(false)
const captureFiles = ref([])
const now = ref(new Date())

const config = reactive({
  title: 'Wireless Security Audit',
  author: '',
  scope: '',
  notes: '',
})

// ── helpers ──────────────────────────────────────────────────────────────────

function pick(obj, keys) {
  for (const k of keys) {
    const v = obj[k]
    if (v !== undefined && String(v).trim() !== '') return String(v).trim()
  }
  return ''
}

function parseDbm(obj) {
  const n = parseInt(pick(obj, ['Power', 'PWR', 'power']))
  return isNaN(n) ? -100 : n
}

function formatSize(bytes) {
  if (!bytes) return '0 B'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`
}

// ── enriched data ─────────────────────────────────────────────────────────────

const networks = computed(() => {
  const clientsByBssid = {}
  for (const c of results.clients) {
    const bssid = pick(c, ['BSSID'])
    if (bssid && bssid !== '(not associated)') {
      clientsByBssid[bssid] = (clientsByBssid[bssid] || 0) + 1
    }
  }
  return results.networks.map((row) => ({
    bssid: pick(row, ['BSSID']),
    essid: pick(row, ['ESSID', 'essid']),
    channel: pick(row, ['channel', 'Channel', ' channel']),
    dbm: parseDbm(row),
    privacy: pick(row, ['Privacy', 'privacy']),
    clientCount: clientsByBssid[pick(row, ['BSSID'])] || 0,
  }))
})

const summary = computed(() => ({
  interfaces: interfaces.value.length,
  networks: networks.value.length,
  clients: results.clients.length,
  captures: captureFiles.value.length,
}))

function signalClass(dbm) {
  if (dbm >= -50) return 'text-green-400'
  if (dbm >= -70) return 'text-amber-400'
  return 'text-red-400'
}

// ── data loading ──────────────────────────────────────────────────────────────

async function refresh() {
  loading.value = true
  now.value = new Date()
  try {
    const data = await api.captures.list()
    // Backend returns { name, path, size, modified }; map to the fields this view renders.
    captureFiles.value = (data.captures || []).map((f) => ({
      ...f,
      filename: f.name,
      size_human: formatSize(f.size),
    }))
  } catch {
    captureFiles.value = []
  } finally {
    loading.value = false
  }
}

onMounted(refresh)

// ── HTML report generation ────────────────────────────────────────────────────

// Snapshot the current state into the plain object the report builder escapes.
function reportData() {
  return {
    config: { ...config },
    generatedAt: now.value.toLocaleString(),
    networks: networks.value,
    summary: summary.value,
    captureFiles: captureFiles.value,
    interfaces: interfaces.value,
  }
}

function downloadHtml() {
  const html = buildHtmlReport(reportData())
  const blob = new Blob([html], { type: 'text/html' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  const safe = config.title.replace(/[^a-z0-9]/gi, '_').toLowerCase()
  a.href = url
  a.download = `${safe}_${Date.now()}.html`
  a.click()
  setTimeout(() => URL.revokeObjectURL(url), 5000)
}

function printReport() {
  const html = buildHtmlReport(reportData())
  const win = window.open('', '_blank', 'width=900,height=700')
  if (!win) return
  // Sever the link back to this app so the report window cannot reach window.opener.
  win.opener = null
  win.document.write(html)
  win.document.close()
  win.focus()
  // Print after close(); the load event is unreliable for document.write windows.
  win.print()
}
</script>
