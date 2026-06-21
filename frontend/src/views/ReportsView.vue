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

function buildHtmlReport() {
  const ts = now.value.toLocaleString()
  const aps = networks.value

  const secBreakdown = (() => {
    const g = {}
    for (const ap of aps) {
      const k = ap.privacy || 'OPN'
      g[k] = (g[k] || 0) + 1
    }
    return Object.entries(g)
      .sort((a, b) => b[1] - a[1])
      .map(([p, c]) => `<tr><td>${p}</td><td>${c}</td><td>${Math.round((c / aps.length) * 100)}%</td></tr>`)
      .join('')
  })()

  const networksRows = aps
    .sort((a, b) => b.dbm - a.dbm)
    .map(
      (ap) =>
        `<tr>
          <td style="font-family:monospace">${ap.bssid}</td>
          <td>${ap.essid || '<i>hidden</i>'}</td>
          <td>${ap.channel}</td>
          <td>${ap.dbm} dBm</td>
          <td>${ap.privacy}</td>
          <td>${ap.clientCount}</td>
        </tr>`,
    )
    .join('')

  const captureRows = captureFiles.value
    .map((f) => `<tr><td style="font-family:monospace">${f.filename}</td><td>${f.size_human}</td></tr>`)
    .join('')

  const ifaceRows = interfaces.value
    .map(
      (i) =>
        `<tr>
          <td style="font-family:monospace">${i.interface}</td>
          <td>${i.driver || ''}</td>
          <td>${i.monitor_mode ? 'Monitor' : 'Managed'}</td>
        </tr>`,
    )
    .join('')

  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>${config.title}</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; color: #1e293b; line-height: 1.6; padding: 40px; }
  h1 { font-size: 2rem; color: #0f172a; margin-bottom: 4px; }
  h2 { font-size: 1.1rem; color: #334155; margin: 32px 0 12px; border-bottom: 2px solid #e2e8f0; padding-bottom: 6px; }
  .meta { color: #64748b; font-size: 0.85rem; margin-bottom: 32px; }
  .meta span { margin-right: 24px; }
  .tiles { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 32px; }
  .tile { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 20px; text-align: center; }
  .tile .num { font-size: 2.5rem; font-weight: 700; color: #0f172a; }
  .tile .lbl { font-size: 0.75rem; color: #94a3b8; text-transform: uppercase; letter-spacing: .05em; margin-top: 4px; }
  table { width: 100%; border-collapse: collapse; font-size: 0.85rem; margin-bottom: 24px; }
  th { background: #f1f5f9; padding: 8px 12px; text-align: left; color: #475569; font-weight: 600; border-bottom: 1px solid #e2e8f0; }
  td { padding: 7px 12px; border-bottom: 1px solid #f1f5f9; vertical-align: middle; }
  tr:last-child td { border-bottom: none; }
  .notes { background: #f8fafc; border-left: 4px solid #3b82f6; padding: 16px 20px; border-radius: 0 8px 8px 0; white-space: pre-wrap; font-size: 0.9rem; color: #334155; margin-bottom: 16px; }
  .footer { margin-top: 48px; font-size: 0.75rem; color: #94a3b8; text-align: center; border-top: 1px solid #e2e8f0; padding-top: 16px; }
  @media print { body { padding: 20px; } .tiles { grid-template-columns: repeat(4, 1fr); } }
</style>
</head>
<body>
<h1>${config.title}</h1>
<div class="meta">
  ${config.author ? `<span>Author: <strong>${config.author}</strong></span>` : ''}
  ${config.scope ? `<span>Scope: <strong>${config.scope}</strong></span>` : ''}
  <span>Generated: <strong>${ts}</strong></span>
  <span>Generated by: <strong>AirmonGUI v0.2</strong></span>
</div>

${config.notes ? `<div class="notes">${config.notes}</div>` : ''}

<div class="tiles">
  <div class="tile"><div class="num">${summary.value.interfaces}</div><div class="lbl">Interfaces</div></div>
  <div class="tile"><div class="num">${summary.value.networks}</div><div class="lbl">Networks Found</div></div>
  <div class="tile"><div class="num">${summary.value.clients}</div><div class="lbl">Clients Found</div></div>
  <div class="tile"><div class="num">${summary.value.captures}</div><div class="lbl">Capture Files</div></div>
</div>

${
  ifaceRows
    ? `<h2>Wireless Interfaces</h2>
<table><thead><tr><th>Interface</th><th>Driver</th><th>Mode</th></tr></thead>
<tbody>${ifaceRows}</tbody></table>`
    : ''
}

${
  networksRows
    ? `<h2>Discovered Access Points (${aps.length})</h2>
<table><thead><tr><th>BSSID</th><th>ESSID</th><th>Channel</th><th>Signal</th><th>Security</th><th>Clients</th></tr></thead>
<tbody>${networksRows}</tbody></table>

<h2>Security Profile</h2>
<table><thead><tr><th>Protocol</th><th>Count</th><th>Share</th></tr></thead>
<tbody>${secBreakdown}</tbody></table>`
    : '<p style="color:#94a3b8;margin:16px 0">No scan data included in this report. Run a scan first.</p>'
}

${
  captureRows
    ? `<h2>Capture Files</h2>
<table><thead><tr><th>Filename</th><th>Size</th></tr></thead>
<tbody>${captureRows}</tbody></table>`
    : ''
}

<div class="footer">AirmonGUI &mdash; for authorised testing only &mdash; ${ts}</div>
</body>
</html>`
}

function downloadHtml() {
  const html = buildHtmlReport()
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
  const html = buildHtmlReport()
  const win = window.open('', '_blank', 'width=900,height=700')
  win.document.write(html)
  win.document.close()
  win.addEventListener('load', () => {
    win.print()
  })
}
</script>
