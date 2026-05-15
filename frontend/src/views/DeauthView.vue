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
      </div>
    </div>

    <!-- Output -->
    <div v-if="output" class="card">
      <div class="card-header">
        <h3 class="card-title">Command Output</h3>
        <span :class="output.success ? 'badge-success' : 'badge-error'">
          {{ output.success ? 'Success' : `Exited (rc=${output.returncode})` }}
        </span>
      </div>
      <div class="terminal">
        <div v-if="output.stdout" class="whitespace-pre-wrap">{{ output.stdout }}</div>
        <div v-if="output.stderr" class="text-red-400 mt-2 whitespace-pre-wrap">
          {{ output.stderr }}
        </div>
      </div>
    </div>

    <!-- Live log history — updates every time a new deauth runs -->
    <div v-if="deauthLogs.length" class="card">
      <div class="card-header">
        <h3 class="card-title">Deauth Log History</h3>
        <div class="flex items-center gap-2">
          <span class="text-xs text-slate-500">{{ deauthLogs.length }} entr{{ deauthLogs.length === 1 ? 'y' : 'ies' }}</span>
          <button @click="logs.clear()" class="btn-ghost btn-sm text-xs text-red-400 hover:text-red-300">Clear</button>
        </div>
      </div>
      <div class="space-y-2 max-h-72 overflow-y-auto">
        <div
          v-for="entry in deauthLogs"
          :key="entry.id"
          class="rounded-lg border px-3 py-2 text-xs"
          :class="entry.success ? 'border-slate-700 bg-slate-800/40' : 'border-red-800/40 bg-red-950/20'"
        >
          <div class="flex items-center justify-between mb-1">
            <span class="font-mono text-slate-400">{{ entry.command }}</span>
            <div class="flex items-center gap-2 shrink-0 ml-2">
              <span :class="entry.success ? 'badge-success' : 'badge-error'" class="text-xs">
                {{ entry.success ? 'ok' : `rc=${entry.returncode}` }}
              </span>
              <span class="text-slate-600 text-xs">{{ formatLogTime(entry.time) }}</span>
            </div>
          </div>
          <div v-if="entry.stdout" class="font-mono text-slate-300 whitespace-pre-wrap leading-relaxed">{{ entry.stdout.trim() }}</div>
          <div v-if="entry.stderr" class="font-mono text-red-400 mt-1 whitespace-pre-wrap leading-relaxed">{{ entry.stderr.trim() }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { api } from '../api/index.js'
import { useInterfaces } from '../composables/useInterfaces.js'
import { useLogs } from '../composables/useLogs.js'
import { useTarget } from '../composables/useTarget.js'
import { useToast } from '../composables/useToast.js'

const { interfaces, selectedInterface } = useInterfaces()
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
  try {
    const data = await api.aireplay.deauth({
      interface: form.interface,
      bssid: form.bssid,
      client: form.client || null,
      count: form.count,
      channel: form.channel ? parseInt(form.channel) : null,
    })
    output.value = data
    logs.add('aireplay-ng --deauth', data)
    if (data.success) {
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

onMounted(() => {
  if (selectedInterface.value) form.interface = selectedInterface.value
  if (targetBssid.value) form.bssid = targetBssid.value
  if (targetChannel.value) form.channel = String(targetChannel.value)
})

function formatLogTime(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}
</script>
