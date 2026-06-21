<template>
  <div class="p-6 space-y-5 animate-fade-in">
    <div class="page-header">
      <h2 class="page-title">Deauth Attack</h2>
      <p class="page-subtitle">aireplay-ng · send deauthentication frames</p>
    </div>

    <!-- Legal disclaimer -->
    <div class="alert-warning">
      <span class="text-xl shrink-0">⚠</span>
      <div>
        <p class="font-bold">Authorized Use Only</p>
        <p class="mt-1 text-amber-400/80">
          Sending deauthentication frames against networks you do not own or have explicit written
          permission to test is illegal in most jurisdictions. Use this feature solely on your own
          networks or in controlled lab environments.
        </p>
      </div>
    </div>

    <!-- Target pre-fill banner -->
    <div v-if="targetBssid" class="alert-info">
      <span class="text-xl shrink-0">🎯</span>
      <div class="flex items-center justify-between flex-1">
        <div>
          <p class="font-bold">Target imported from Scan</p>
          <p class="mt-0.5 text-cyber-400/80 font-mono text-xs">
            {{ targetBssid }}{{ targetEssid ? ` · ${targetEssid}` : '' }}
            {{ targetChannel ? ` · CH ${targetChannel}` : '' }}
          </p>
        </div>
        <button @click="applyTarget" class="btn-primary btn-sm shrink-0">Apply</button>
      </div>
    </div>

    <!-- PMF warning -->
    <div v-if="targetPmf" class="rounded-xl border px-4 py-3 text-xs flex items-start gap-3"
      :class="targetPmf === 'required'
        ? 'border-red-600/40 bg-red-950/30 text-red-300'
        : 'border-amber-600/40 bg-amber-950/30 text-amber-300'"
    >
      <span class="shrink-0 mt-0.5 text-base">🛡</span>
      <div>
        <p class="font-bold">
          PMF / 802.11w detected —
          {{ targetPmf === 'required' ? 'Protection Required' : 'Protection Capable' }}
        </p>
        <p class="mt-0.5 opacity-80">
          This AP enforces Management Frame Protection (802.11w).
          {{ targetPmf === 'required'
            ? 'Deauthentication frames are cryptographically protected — broadcast deauth attacks will be silently dropped by compliant clients (WPA3/SAE).'
            : 'Some clients may accept deauth frames; however, PMF-enabled clients will ignore them.' }}
        </p>
      </div>
    </div>

    <!-- Deauth form -->
    <div class="card">
      <div class="card-header">
        <h3 class="card-title">Attack Parameters</h3>
        <button @click="resetForm" class="btn-ghost btn-sm text-red-400 hover:text-red-300">
          Reset
        </button>
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-5">
        <div>
          <label class="field-label">Interface *</label>
          <select v-model="form.interface" class="field-select">
            <option value="" disabled>Select interface…</option>
            <option v-for="iface in interfaces" :key="iface.interface" :value="iface.interface">
              {{ iface.interface }} {{ iface.monitor_mode ? '(monitor ✓)' : '' }}
            </option>
          </select>
        </div>
        <div>
          <label class="field-label">Target BSSID *</label>
          <input
            v-model="form.bssid"
            class="field-input"
            placeholder="00:11:22:33:44:55"
            spellcheck="false"
          />
        </div>
        <div>
          <label class="field-label">Client MAC (optional — blank = broadcast)</label>
          <input
            v-model="form.client"
            class="field-input"
            placeholder="AA:BB:CC:DD:EE:FF"
            spellcheck="false"
          />
        </div>
        <div>
          <label class="field-label">AP Channel *</label>
          <input
            v-model="form.channel"
            class="field-input mb-2"
            placeholder="e.g. 6"
            spellcheck="false"
          />
          <div class="flex flex-wrap gap-1">
            <button
              v-for="ch in [1,2,3,4,5,6,7,8,9,10,11,36,40,44,48,100,149,153,157,161]"
              :key="ch"
              @click="form.channel = String(ch)"
              :class="[
                'px-1.5 py-0.5 rounded text-xs font-mono border transition-colors',
                form.channel === String(ch)
                  ? 'bg-cyber-500/20 border-cyber-500/50 text-cyber-300'
                  : 'border-slate-700 text-slate-500 hover:border-slate-500 hover:text-slate-200',
              ]"
            >{{ ch }}</button>
          </div>
          <p class="text-xs text-slate-500 mt-1">
            Sets the interface to this channel before attacking. Must match the AP's channel.
          </p>
        </div>
        <div>
          <label class="field-label">Packet Count (0 = continuous)</label>
          <div class="flex gap-2">
            <input
              type="number"
              v-model.number="form.count"
              min="0"
              max="65535"
              class="field-input flex-1"
            />
            <div class="flex flex-col gap-1">
              <button
                v-for="preset in [10, 50, 100, 0]"
                :key="preset"
                @click="form.count = preset"
                :class="['btn-ghost btn-sm px-2 py-0.5 text-xs', form.count === preset && 'bg-slate-700 text-white']"
              >
                {{ preset === 0 ? '∞' : preset }}
              </button>
            </div>
          </div>
        </div>
      </div>

      <div class="flex flex-wrap gap-3">
        <button
          @click="execute"
          :disabled="running || !form.interface || !form.bssid"
          class="btn-danger"
        >
          {{ running ? '⏳ Sending…' : '⚡ Execute Deauth' }}
        </button>
        <button
          v-if="running"
          @click="cancelDeauth"
          class="btn-secondary"
        >
          ⏹ Cancel Deauth
        </button>
      </div>
    </div>

    <!-- Output -->
    <div v-if="output" class="card">
      <div class="card-header">
        <h3 class="card-title">Last Deauth Result</h3>
        <span :class="output.success ? 'badge-success' : 'badge-error'">
          {{ output.success ? 'Success' : `Exited (rc=${output.returncode})` }}
        </span>
      </div>
      <div class="overflow-x-auto">
        <table class="data-table">
          <thead>
            <tr>
              <th>Interface</th>
              <th>BSSID</th>
              <th>Client</th>
              <th>Channel</th>
              <th>Count</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td class="text-cyber-400">{{ lastRun?.interface || form.interface }}</td>
              <td>{{ lastRun?.bssid || form.bssid }}</td>
              <td>{{ lastRun?.client || 'broadcast' }}</td>
              <td class="text-amber-400">{{ output.channel?.current || lastRun?.channel || 'auto' }}</td>
              <td>{{ lastRun?.count ?? form.count }}</td>
              <td>
                <span :class="output.success ? 'badge-success' : 'badge-error'">
                  {{ output.success ? 'ok' : `rc=${output.returncode}` }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <p v-if="output.stderr" class="mt-3 text-xs text-red-300">
        {{ output.stderr.trim() }}
      </p>
      <p v-else-if="output.channel?.method" class="mt-3 text-xs text-slate-500">
        Channel lock method: <span class="font-mono text-slate-300">{{ output.channel.method }}</span>
      </p>
      <p v-if="output.stdout" class="mt-2 text-xs text-slate-500">
        Raw aireplay-ng output is still available in the Logs view.
      </p>
      <div v-if="output.stdout || output.stderr" class="terminal mt-3">
        <div v-if="output.stdout" class="whitespace-pre-wrap">{{ output.stdout }}</div>
        <div v-if="output.stderr" class="text-red-400 mt-2 whitespace-pre-wrap">
          {{ output.stderr }}
        </div>
      </div>
    </div>

    <!-- Parsed aireplay output -->
    <div v-if="deauthEvents.length" class="card">
      <div class="card-header">
        <h3 class="card-title">Deauth Events</h3>
        <span class="badge-info">{{ deauthEvents.length }}</span>
      </div>
      <div class="overflow-x-auto">
        <table class="data-table">
          <thead>
            <tr>
              <th>Type</th>
              <th>Message</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="event in deauthEvents" :key="event.id">
              <td class="text-cyber-400">{{ event.type }}</td>
              <td>{{ event.message }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Structured run history -->
    <div v-if="deauthRuns.length" class="card">
      <div class="card-header">
        <h3 class="card-title">Deauth Run History</h3>
        <span class="badge-info">{{ deauthRuns.length }}</span>
      </div>
      <div class="overflow-x-auto">
        <table class="data-table">
          <thead>
            <tr>
              <th>Time</th>
              <th>Interface</th>
              <th>BSSID</th>
              <th>Client</th>
              <th>CH</th>
              <th>Count</th>
              <th>Result</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="run in deauthRuns" :key="run.id">
              <td class="text-slate-500">{{ run.time }}</td>
              <td class="text-cyber-400">{{ run.interface }}</td>
              <td>{{ run.bssid }}</td>
              <td>{{ run.client || 'broadcast' }}</td>
              <td class="text-amber-400">{{ run.lockedChannel || run.channel || 'auto' }}</td>
              <td>{{ run.count }}</td>
              <td>
                <span :class="run.success ? 'badge-success' : 'badge-error'">
                  {{ run.success ? 'ok' : `rc=${run.returncode}` }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Shared command history summary -->
    <div v-if="deauthLogs.length" class="card">
      <div class="card-header">
        <h3 class="card-title">Command History</h3>
        <div class="flex items-center gap-2">
          <span class="text-xs text-slate-500">{{ deauthLogs.length }} entr{{ deauthLogs.length === 1 ? 'y' : 'ies' }}</span>
          <button @click="logs.clear()" class="btn-ghost btn-sm text-xs text-red-400 hover:text-red-300">Clear</button>
        </div>
      </div>
      <div class="overflow-x-auto">
        <table class="data-table">
          <thead>
            <tr>
              <th>Time</th>
              <th>Command</th>
              <th>Status</th>
              <th>Output</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="entry in deauthLogs" :key="entry.id">
              <td class="text-slate-500">{{ formatLogTime(entry.time) }}</td>
              <td class="font-mono text-slate-400">{{ entry.command }}</td>
              <td>
                <span :class="entry.success ? 'badge-success' : 'badge-error'">
                  {{ entry.success ? 'ok' : `rc=${entry.returncode}` }}
                </span>
              </td>
              <td class="text-slate-500">
                {{ summarizeOutput(entry) }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { api } from '../api/index.js'
import { useInterfaces } from '../composables/useInterfaces.js'
import { useLogs } from '../composables/useLogs.js'
import { useScan } from '../composables/useScan.js'
import { useTarget } from '../composables/useTarget.js'
import { useToast } from '../composables/useToast.js'

const { interfaces, selectedInterface } = useInterfaces()
const { loadJobs: loadScanJobs } = useScan()
const { bssid: targetBssid, essid: targetEssid, channel: targetChannel, pmf: targetPmf } = useTarget()
const toast = useToast()
const logs = useLogs()

// Filter only deauth entries from the shared log store
const deauthLogs = computed(() =>
  logs.entries.value.filter((e) => e.command && e.command.includes('deauth'))
)

const form = reactive({
  interface: '',
  bssid: '',
  client: '',
  count: 10,
  channel: '',
})

const running = ref(false)
const output = ref(null)
const deauthRuns = ref([])
const lastRun = ref(null)
const deauthJobId = ref('')
let deauthPollTimer = null
const deauthEvents = computed(() => parseDeauthEvents(output.value))

function applyTarget() {
  form.bssid = targetBssid.value
  if (targetChannel.value) form.channel = targetChannel.value
  if (!form.interface && selectedInterface.value) form.interface = selectedInterface.value
}

function resetForm() {
  form.interface = ''
  form.bssid = ''
  form.client = ''
  form.count = 10
  form.channel = ''
  output.value = null
}

async function execute() {
  if (running.value) return
  if (!form.interface) {
    toast.warning('Select an interface')
    return
  }
  if (!form.bssid) {
    toast.warning('Enter a target BSSID')
    return
  }

  running.value = true
  output.value = null
  const run = {
    id: crypto.randomUUID?.() || `${Date.now()}-${Math.random()}`,
    time: new Date().toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
    interface: form.interface,
    bssid: form.bssid,
    client: form.client || '',
    count: form.count,
    channel: form.channel || '',
    lockedChannel: '',
    success: false,
    returncode: '',
  }
  try {
    const started = await api.aireplay.startDeauth({
      interface: form.interface,
      bssid: form.bssid,
      client: form.client || null,
      count: form.count,
      channel: form.channel ? parseInt(form.channel) : null,
    })
    if (started.stopped_scan_jobs?.length) {
      await loadScanJobs()
      logs.add('airodump-ng stop (auto)', {
        stdout: `Stopped active scan job${started.stopped_scan_jobs.length > 1 ? 's' : ''} ${started.stopped_scan_jobs.join(', ')} before deauth channel lock.`,
        success: true,
      })
      toast.info('Active network scan stopped so the interface could switch channels')
    }
    deauthJobId.value = started.job_id
    output.value = { ...started, success: true, returncode: null, stdout: '', stderr: '' }
    await pollDeauthJob(run)
    if (output.value?.success) {
      toast.success('Deauth command finished')
    } else {
      toast.warning('Command finished with errors — check output')
    }
  } catch (err) {
    toast.error(err.message)
  } finally {
    running.value = false
  }
}

async function pollDeauthJob(run) {
  clearTimeout(deauthPollTimer)
  if (!deauthJobId.value) return
  const data = await api.aireplay.deauthStatus(deauthJobId.value)
  output.value = data
  if (data.running) {
    await new Promise((resolve) => {
      deauthPollTimer = setTimeout(resolve, 500)
    })
    return pollDeauthJob(run)
  }
  run.success = Boolean(data.success)
  run.returncode = data.returncode
  run.lockedChannel = data.channel?.current || ''
  lastRun.value = run
  deauthRuns.value = [run, ...deauthRuns.value].slice(0, 12)
  logs.add(data.stopped ? 'aireplay-ng --deauth cancelled' : 'aireplay-ng --deauth', data)
  deauthJobId.value = ''
}

async function cancelDeauth() {
  clearTimeout(deauthPollTimer)
  if (deauthJobId.value) {
    try {
      output.value = await api.aireplay.stopDeauth(deauthJobId.value)
      logs.add('aireplay-ng --deauth cancelled', output.value)
      toast.info('Deauth cancelled')
    } catch (err) {
      toast.error(err.message)
    }
  }
  deauthJobId.value = ''
  running.value = false
}

async function resumeDeauth() {
  try {
    const data = await api.aireplay.deauthJobs()
    const active = (data.jobs || []).find((job) => job.running)
    if (!active) return
    deauthJobId.value = active.job_id
    form.interface = active.interface || form.interface
    form.bssid = active.bssid || form.bssid
    form.client = active.client || form.client
    form.count = active.count ?? form.count
    form.channel = active.channel || form.channel
    running.value = true
    output.value = active
    const run = {
      id: active.job_id,
      time: new Date((active.start_time || Date.now() / 1000) * 1000).toLocaleTimeString(undefined, {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      }),
      interface: active.interface || '',
      bssid: active.bssid || '',
      client: active.client || '',
      count: active.count ?? '',
      channel: active.channel || '',
      lockedChannel: '',
      success: false,
      returncode: '',
    }
    await pollDeauthJob(run)
  } catch {
    // non-critical resume path
  }
}

onMounted(async () => {
  if (selectedInterface.value) form.interface = selectedInterface.value
  if (targetBssid.value) form.bssid = targetBssid.value
  if (targetChannel.value) form.channel = String(targetChannel.value)
  await resumeDeauth()
})

onUnmounted(() => {
  // Stop the backend deauth job and the recursive poll loop on navigation away.
  if (deauthJobId.value) cancelDeauth()
  else clearTimeout(deauthPollTimer)
})

function formatLogTime(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

function summarizeOutput(entry) {
  const text = `${entry.stdout || ''} ${entry.stderr || ''}`.trim()
  if (!text) return 'no output'
  const firstLine = text.split(/\r?\n/).find((line) => line.trim())
  return firstLine ? firstLine.slice(0, 120) : 'output available'
}

function parseDeauthEvents(result) {
  if (!result) return []
  const text = `${result.stdout || ''}\n${result.stderr || ''}`.trim()
  if (!text) {
    return [{
      id: 'empty',
      type: result.success ? 'complete' : 'error',
      message: result.success ? 'Command completed without text output.' : 'Command failed without text output.',
    }]
  }
  return text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .slice(-12)
    .map((line, index) => ({
      id: `${index}-${line}`,
      type: classifyDeauthLine(line),
      message: line,
    }))
}

function classifyDeauthLine(line) {
  const lower = line.toLowerCase()
  if (lower.includes('channel')) return 'channel'
  if (lower.includes('error') || lower.includes('fail')) return 'error'
  if (lower.includes('waiting') || lower.includes('send')) return 'transmit'
  if (lower.includes('ack') || lower.includes('deauth')) return 'frame'
  return 'output'
}
</script>
