<template>
  <div class="p-6 space-y-5 animate-fade-in">
    <!-- Header -->
    <div class="page-header flex items-start justify-between">
      <div>
        <h2 class="page-title">Signal Analysis</h2>
        <p class="page-subtitle">Access points ranked by attack potential · sourced from last scan</p>
      </div>
      <div class="flex items-center gap-2 mt-1">
        <span v-if="networks.length" class="badge-info">{{ networks.length }} AP{{ networks.length !== 1 ? 's' : '' }}</span>
        <button @click="fetchResults" :disabled="!activeJobId || scanLoading" class="btn-ghost btn-sm">
          <span v-if="scanLoading" class="inline-block w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin mr-1" />
          Refresh
        </button>
      </div>
    </div>

    <!-- No data -->
    <div v-if="!networks.length" class="card text-center py-14">
      <p class="text-slate-400 font-medium">No scan data available.</p>
      <p class="text-slate-500 text-sm mt-1">Run a scan from the Network Scan view first, then return here.</p>
      <button @click="navigate('scan')" class="btn-secondary mt-5">Go to Network Scan</button>
    </div>

    <template v-else>
      <!-- Own-device warning -->
      <div v-if="ownMacSet.size" class="rounded-xl border border-blue-600/30 bg-blue-950/30 px-4 py-2.5 text-xs text-blue-300 flex items-start gap-2">
        <span class="shrink-0 mt-0.5">&#9432;</span>
        <span>
          Your adapter MAC{{ ownMacSet.size > 1 ? 's' : '' }}:
          <span v-for="(m, i) in [...ownMacSet]" :key="m" class="font-mono ml-1">{{ m }}<span v-if="i < ownMacSet.size - 1">,</span></span>
          — APs or clients matching these are flagged <span class="text-blue-200 font-semibold">Self</span>.
        </span>
      </div>

      <!-- Filters bar -->
      <div class="card py-3">
        <div class="flex flex-wrap items-center gap-3">
          <!-- Text search -->
          <input
            v-model="filterText"
            class="field-input w-44 text-xs"
            placeholder="Search SSID / BSSID…"
          />
          <!-- Privacy filter -->
          <select v-model="filterPrivacy" class="field-input text-xs w-32">
            <option value="">All security</option>
            <option value="WPA3">WPA3</option>
            <option value="WPA2">WPA2</option>
            <option value="WPA">WPA</option>
            <option value="WEP">WEP</option>
            <option value="OPN">Open</option>
          </select>
          <!-- Band filter -->
          <select v-model="filterBand" class="field-input text-xs w-28">
            <option value="">All bands</option>
            <option value="2.4">2.4 GHz</option>
            <option value="5">5 GHz</option>
          </select>
          <!-- Sort -->
          <select v-model="sortBy" class="field-input text-xs w-36">
            <option value="score">Sort: Best target</option>
            <option value="signal">Sort: Signal ↓</option>
            <option value="clients">Sort: Clients ↓</option>
            <option value="essid">Sort: SSID A-Z</option>
          </select>
          <!-- Clear filters -->
          <button
            v-if="filterText || filterPrivacy || filterBand"
            @click="clearFilters"
            class="text-xs text-slate-500 hover:text-slate-300 underline"
          >Clear</button>
          <span class="ml-auto text-xs text-slate-500">{{ filteredAPs.length }} / {{ enriched.length }} shown</span>
        </div>
      </div>

      <!-- AP list (ranked) -->
      <div class="card p-0 overflow-hidden">
        <div class="px-4 py-3 border-b border-slate-800 flex items-center justify-between">
          <h3 class="card-title">Access Points</h3>
          <div class="flex items-center gap-3 text-xs text-slate-500">
            <span class="flex items-center gap-1.5"><span class="w-2 h-2 rounded-full bg-green-500"></span> High potential</span>
            <span class="flex items-center gap-1.5"><span class="w-2 h-2 rounded-full bg-amber-500"></span> Medium</span>
            <span class="flex items-center gap-1.5"><span class="w-2 h-2 rounded-full bg-slate-500"></span> Low</span>
          </div>
        </div>

        <div v-if="!filteredAPs.length" class="px-4 py-8 text-center text-slate-500 text-sm">
          No APs match the current filters.
        </div>

        <div v-else class="divide-y divide-slate-800/60">
          <div
            v-for="(ap, idx) in filteredAPs"
            :key="ap.bssid"
            class="px-4 py-3 hover:bg-slate-800/40 transition-colors group"
          >
            <div class="flex items-center gap-3">
              <!-- Rank + score indicator -->
              <div class="shrink-0 flex flex-col items-center w-10 gap-1">
                <span class="text-xs font-bold text-slate-500">#{{ idx + 1 }}</span>
                <div
                  class="w-2 h-2 rounded-full"
                  :class="ap.score >= 60 ? 'bg-green-500' : ap.score >= 35 ? 'bg-amber-500' : 'bg-slate-500'"
                  :title="`Score: ${ap.score}`"
                />
              </div>

              <!-- Signal bars -->
              <div class="flex items-end gap-0.5 shrink-0" style="height:18px;width:18px">
                <div
                  v-for="i in 4"
                  :key="i"
                  class="w-1 rounded-sm"
                  :style="{ height: (i * 4 + 2) + 'px' }"
                  :class="i <= ap.bars ? signalBarColor(ap.dbm) : 'bg-slate-700'"
                />
              </div>

              <!-- Main info -->
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 flex-wrap">
                  <span class="font-semibold text-sm text-white truncate max-w-[180px]">
                    {{ ap.essid || '&lt;hidden&gt;' }}
                  </span>
                  <!-- Self badge -->
                  <span v-if="ap.isSelf" class="text-xs px-1.5 py-0.5 rounded border border-blue-500/50 bg-blue-900/30 text-blue-300 font-semibold shrink-0">Self</span>
                  <!-- Security badge -->
                  <span
                    class="text-xs px-1.5 py-0.5 rounded border font-mono shrink-0"
                    :class="privacyBadgeClass(ap.privacy)"
                  >{{ ap.privacy || 'OPN' }}</span>
                  <span class="text-xs text-amber-400 font-mono shrink-0">CH {{ ap.channel }}</span>
                  <span v-if="ap.clientCount > 0" class="text-xs text-green-400 font-mono shrink-0">
                    {{ ap.clientCount }} client{{ ap.clientCount !== 1 ? 's' : '' }}
                  </span>
                </div>
                <div class="flex items-center gap-3 mt-0.5">
                  <span class="text-xs text-slate-500 font-mono">{{ ap.bssid }}</span>
                  <!-- Associated clients that are ourselves -->
                  <span
                    v-if="ap.selfClients.length"
                    class="text-xs text-blue-400"
                    :title="ap.selfClients.join(', ')"
                  >&#9432; Your adapter connected</span>
                </div>
              </div>

              <!-- Score + signal -->
              <div class="shrink-0 text-right hidden sm:block">
                <div class="text-xs font-semibold mb-0.5" :class="signalTextColor(ap.dbm)">{{ ap.dbm }} dBm</div>
                <div class="w-24 h-1.5 bg-slate-700 rounded-full overflow-hidden">
                  <div
                    class="h-full rounded-full"
                    :class="signalBarColor(ap.dbm)"
                    :style="{ width: signalPct(ap.dbm) + '%' }"
                  />
                </div>
              </div>

              <!-- Score pill -->
              <div class="shrink-0 hidden md:flex flex-col items-center w-14">
                <span
                  class="text-xs font-bold px-2 py-0.5 rounded-full"
                  :class="ap.score >= 60 ? 'bg-green-900/40 text-green-300' : ap.score >= 35 ? 'bg-amber-900/40 text-amber-300' : 'bg-slate-800 text-slate-400'"
                >{{ ap.score }}</span>
                <span class="text-[10px] text-slate-600 mt-0.5">score</span>
              </div>

              <!-- Actions (always visible on small, opacity on large) -->
              <div class="shrink-0 flex items-center gap-1.5 opacity-100 sm:opacity-0 group-hover:opacity-100 transition-opacity">
                <button
                  @click="targetHandshake(ap)"
                  class="px-2.5 py-1 rounded-lg text-xs font-semibold bg-cyber-500/15 border border-cyber-500/40 text-cyber-300 hover:bg-cyber-500/30 transition-colors"
                  title="Capture handshake"
                >Handshake</button>
                <button
                  @click="targetDeauth(ap)"
                  class="px-2.5 py-1 rounded-lg text-xs font-semibold bg-red-500/15 border border-red-500/40 text-red-300 hover:bg-red-500/30 transition-colors"
                  title="Deauth attack"
                >Deauth</button>
              </div>
            </div>

            <!-- Clients sub-row -->
            <div v-if="ap.associatedClients.length" class="mt-2 ml-11 flex flex-wrap gap-2">
              <div
                v-for="client in ap.associatedClients"
                :key="client.mac"
                class="flex items-center gap-1.5 text-xs px-2 py-0.5 rounded-lg border"
                :class="client.isSelf ? 'border-blue-600/40 bg-blue-900/20 text-blue-300' : 'border-slate-700 bg-slate-800/50 text-slate-400'"
              >
                <span class="font-mono">{{ client.mac }}</span>
                <span v-if="client.isSelf" class="text-[10px] text-blue-400 font-semibold">Your device</span>
                <span v-if="client.power && client.power !== '-1'" class="text-slate-500">{{ client.power }} dBm</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Channel utilization + stats row -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <!-- Channel utilization -->
        <div class="card">
          <div class="card-header mb-3">
            <h3 class="card-title">Channel Utilization</h3>
          </div>
          <div class="space-y-2">
            <div
              v-for="ch in channelStats"
              :key="ch.channel"
              class="flex items-center gap-3 text-xs"
            >
              <span class="w-10 text-right font-mono text-slate-400 shrink-0">CH {{ ch.channel }}</span>
              <div class="flex-1 h-5 bg-slate-800 rounded-lg overflow-hidden">
                <div
                  class="h-full rounded-lg flex items-center px-2 font-semibold text-white text-xs transition-all duration-500"
                  :style="{ width: ch.pct + '%', minWidth: ch.count > 0 ? '1.8rem' : '0' }"
                  :class="channelBarColor(ch.channel)"
                >{{ ch.count > 0 ? ch.count : '' }}</div>
              </div>
            </div>
          </div>
        </div>

        <!-- Security + band stats -->
        <div class="space-y-4">
          <div class="card">
            <h3 class="card-title mb-3">Security Profile</h3>
            <div class="space-y-2">
              <div v-for="s in securityStats" :key="s.label" class="flex items-center gap-2 text-xs">
                <span class="w-16 font-mono shrink-0" :class="s.color">{{ s.label }}</span>
                <div class="flex-1 h-2.5 bg-slate-800 rounded-full overflow-hidden">
                  <div class="h-full rounded-full" :class="s.barColor" :style="{ width: s.pct + '%' }" />
                </div>
                <span class="w-5 text-right text-slate-500 shrink-0">{{ s.count }}</span>
              </div>
            </div>
          </div>
          <div class="card">
            <h3 class="card-title mb-3">Band Distribution</h3>
            <div class="flex items-end gap-6 justify-center" style="height:60px">
              <div class="flex flex-col items-center gap-1">
                <span class="text-xl font-bold text-cyber-400">{{ band24Count }}</span>
                <div class="h-8 w-16 bg-cyber-500/20 border border-cyber-500/40 rounded-lg flex items-center justify-center text-xs text-cyber-300">2.4 GHz</div>
              </div>
              <div class="flex flex-col items-center gap-1">
                <span class="text-xl font-bold text-amber-400">{{ band5Count }}</span>
                <div class="h-8 w-16 bg-amber-500/20 border border-amber-500/40 rounded-lg flex items-center justify-center text-xs text-amber-300">5 GHz</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useNav } from '../composables/useNav.js'
import { useScan } from '../composables/useScan.js'
import { useInterfaces } from '../composables/useInterfaces.js'
import { useTarget } from '../composables/useTarget.js'
import { useToast } from '../composables/useToast.js'

const { results, activeJobId, scanLoading, fetchResults } = useScan()
const { interfaces } = useInterfaces()
const { setTarget } = useTarget()
const { navigate } = useNav()
const { info } = useToast()

// Filters
const filterText = ref('')
const filterPrivacy = ref('')
const filterBand = ref('')
const sortBy = ref('score')

function clearFilters() {
  filterText.value = ''
  filterPrivacy.value = ''
  filterBand.value = ''
}

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

function parseChannel(obj) {
  const n = parseInt(pick(obj, ['channel', 'Channel', ' channel']))
  return isNaN(n) ? 0 : n
}

// ── own MAC detection ─────────────────────────────────────────────────────────

const ownMacSet = computed(() => {
  const set = new Set()
  for (const iface of interfaces.value) {
    if (iface.mac) set.add(iface.mac.toUpperCase())
  }
  return set
})

// ── scoring formula ───────────────────────────────────────────────────────────
// 0–100 score: higher = better attack candidate
// Components: signal (0-40) + security weakness (0-35) + has clients bonus (0-15) + channel overlap penalty (-5)
function calcScore(dbm, privacy, clientCount, channel) {
  // Signal: map [-100, -30] → [0, 40]
  const sigScore = Math.round(Math.min(40, Math.max(0, ((dbm + 100) / 70) * 40)))

  // Security weakness: WEP easiest, WPA3 hardest
  const secMap = { WEP: 35, OPN: 20, WPA: 25, WPA2: 15, WPA3: 0 }
  const p = (privacy || '').toUpperCase()
  let secScore = 15
  for (const [k, v] of Object.entries(secMap)) {
    if (p.includes(k)) { secScore = v; break }
  }

  // Clients: having active clients means we can capture handshake faster
  const clientScore = Math.min(15, clientCount * 5)

  return Math.min(100, sigScore + secScore + clientScore)
}

// ── derived data ──────────────────────────────────────────────────────────────

const networks = computed(() => results.networks)
const clients = computed(() => results.clients)

// Map: bssid → list of clients associated with that AP
const clientsByBssid = computed(() => {
  const map = {}
  for (const c of clients.value) {
    const stationBssid = (c['BSSID'] || c['bssid'] || '').trim().toUpperCase()
    if (!stationBssid || stationBssid === '(NOT ASSOCIATED)') continue
    if (!map[stationBssid]) map[stationBssid] = []
    map[stationBssid].push({
      mac: (c['Station MAC'] || c['station mac'] || '').trim().toUpperCase(),
      power: (c['Power'] || c['power'] || '').trim(),
      isSelf: ownMacSet.value.has((c['Station MAC'] || c['station mac'] || '').trim().toUpperCase()),
    })
  }
  return map
})

const enriched = computed(() =>
  networks.value.map((row) => {
    const dbm = parseDbm(row)
    const bars = dbm >= -50 ? 4 : dbm >= -65 ? 3 : dbm >= -75 ? 2 : 1
    const bssid = pick(row, ['BSSID']).toUpperCase()
    const privacy = pick(row, ['Privacy', 'privacy'])
    const channel = parseChannel(row)
    const associated = clientsByBssid.value[bssid] || []
    const clientCount = associated.length
    const score = calcScore(dbm, privacy, clientCount, channel)
    return {
      bssid,
      essid: pick(row, ['ESSID', 'essid']),
      channel,
      dbm,
      bars,
      privacy,
      score,
      clientCount,
      associatedClients: associated,
      selfClients: associated.filter((c) => c.isSelf).map((c) => c.mac),
      isSelf: ownMacSet.value.has(bssid),
      _raw: row,
    }
  }),
)

const filteredAPs = computed(() => {
  const q = filterText.value.toLowerCase()
  const priv = filterPrivacy.value.toUpperCase()
  const band = filterBand.value

  return [...enriched.value]
    .filter((ap) => {
      if (q && !ap.essid.toLowerCase().includes(q) && !ap.bssid.toLowerCase().includes(q)) return false
      if (priv && !(ap.privacy || 'OPN').toUpperCase().includes(priv)) return false
      if (band === '2.4' && !(ap.channel >= 1 && ap.channel <= 14)) return false
      if (band === '5' && !(ap.channel >= 36)) return false
      return true
    })
    .sort((a, b) => {
      if (sortBy.value === 'score') return b.score - a.score
      if (sortBy.value === 'signal') return b.dbm - a.dbm
      if (sortBy.value === 'clients') return b.clientCount - a.clientCount
      if (sortBy.value === 'essid') return a.essid.localeCompare(b.essid)
      return 0
    })
})

// Channel utilization
const channelStats = computed(() => {
  const counts = {}
  for (const ap of enriched.value) {
    if (ap.channel > 0) counts[ap.channel] = (counts[ap.channel] || 0) + 1
  }
  const usedChannels = Object.keys(counts).map(Number).sort((a, b) => a - b)
  if (!usedChannels.length) return []
  const maxCount = Math.max(...Object.values(counts))
  return usedChannels.map((ch) => ({
    channel: ch,
    count: counts[ch],
    pct: maxCount > 0 ? Math.max(4, Math.round((counts[ch] / maxCount) * 100)) : 0,
  }))
})

const band24Count = computed(() => enriched.value.filter((a) => a.channel >= 1 && a.channel <= 14).length)
const band5Count = computed(() => enriched.value.filter((a) => a.channel >= 36).length)

const securityStats = computed(() => {
  const total = enriched.value.length || 1
  const groups = {}
  for (const ap of enriched.value) {
    const key = ap.privacy || 'OPN'
    groups[key] = (groups[key] || 0) + 1
  }
  const colorMap = {
    WPA3: { color: 'text-green-400', bar: 'bg-green-500' },
    WPA2: { color: 'text-cyber-400', bar: 'bg-cyber-500' },
    WPA: { color: 'text-amber-400', bar: 'bg-amber-500' },
    WEP: { color: 'text-red-400', bar: 'bg-red-500' },
    OPN: { color: 'text-slate-400', bar: 'bg-slate-500' },
  }
  return Object.entries(groups)
    .sort((a, b) => b[1] - a[1])
    .map(([label, count]) => ({
      label,
      count,
      pct: Math.round((count / total) * 100),
      color: (colorMap[label] || colorMap.OPN).color,
      barColor: (colorMap[label] || colorMap.OPN).bar,
    }))
})

// ── visual helpers ────────────────────────────────────────────────────────────

function signalPct(dbm) {
  return Math.min(100, Math.max(0, Math.round(((dbm + 100) / 70) * 100)))
}

function signalBarColor(dbm) {
  if (dbm >= -50) return 'bg-green-500'
  if (dbm >= -65) return 'bg-cyber-500'
  if (dbm >= -75) return 'bg-amber-500'
  return 'bg-red-500'
}

function signalTextColor(dbm) {
  if (dbm >= -50) return 'text-green-400'
  if (dbm >= -65) return 'text-cyber-400'
  if (dbm >= -75) return 'text-amber-400'
  return 'text-red-400'
}

function channelBarColor(ch) {
  if ([1, 6, 11].includes(ch)) return 'bg-cyber-500'
  if (ch >= 36) return 'bg-amber-500'
  return 'bg-slate-500'
}

function privacyBadgeClass(privacy) {
  const p = (privacy || 'OPN').toUpperCase()
  if (p.includes('WPA3')) return 'border-green-600/50 text-green-300'
  if (p.includes('WPA2')) return 'border-cyber-600/50 text-cyber-300'
  if (p.includes('WPA')) return 'border-amber-600/50 text-amber-300'
  if (p.includes('WEP')) return 'border-red-600/50 text-red-300'
  return 'border-slate-600 text-slate-400'
}

// ── actions ───────────────────────────────────────────────────────────────────

function targetDeauth(ap) {
  if (ap._raw) {
    setTarget(ap._raw)
    info(`Deauth target set: ${ap.essid || ap.bssid}`)
    navigate('deauth')
  }
}

function targetHandshake(ap) {
  if (ap._raw) {
    setTarget(ap._raw)
    info(`Handshake target set: ${ap.essid || ap.bssid}`)
    navigate('handshake')
  }
}
</script>
