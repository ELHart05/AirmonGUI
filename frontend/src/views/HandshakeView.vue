<template>
  <div class="p-6 space-y-5 animate-fade-in">
    <!-- Header -->
    <div class="page-header">
      <h2 class="page-title">WPA Handshake Capture</h2>
      <p class="page-subtitle">
        airodump-ng targeted capture + aireplay-ng deauth — obtain a WPA 4-way handshake for cracking
      </p>
    </div>

    <!-- Legal disclaimer -->
    <div class="alert-warning">
      ⚠ Only use against networks you own or have explicit written authorisation to test.
      Capturing network traffic without permission is illegal in most jurisdictions.
    </div>

    <!-- Stage stepper -->
    <div class="flex items-center">
      <template v-for="(label, i) in ['Configure', 'Capture & Deauth', 'Complete']" :key="i">
        <div class="flex items-center shrink-0">
          <div
            :class="[
              'w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm',
              stage > i
                ? 'bg-cyber-500 text-slate-950 shadow-lg shadow-cyber-500/20'
                : stage === i
                ? 'bg-cyber-500/15 border border-cyber-500/45 text-cyber-200'
                : 'bg-slate-950 border border-cyber-500/15 text-slate-500',
            ]"
          >
            {{ stage > i ? '✓' : i + 1 }}
          </div>
          <span
            :class="[
              'ml-2 text-xs font-semibold',
              stage === i ? 'text-cyber-300' : stage > i ? 'text-cyber-400' : 'text-slate-500',
            ]"
          >{{ label }}</span>
        </div>
        <div v-if="i < 2" class="flex-1 h-px bg-cyber-500/20 mx-3"></div>
      </template>
    </div>

    <!-- ─── Stage 0: Configure ─── -->
    <div v-if="stage === 0" class="card">
      <div class="card-header">
        <h3 class="card-title">Target Configuration</h3>
        <span v-if="bssid" class="badge-info text-xs">Auto-filled from scan</span>
      </div>

      <!-- PMF warning -->
      <div v-if="targetPmf" class="mb-4 rounded-xl border px-4 py-3 text-xs flex items-start gap-3"
        :class="targetPmf === 'required'
          ? 'border-red-600/40 bg-red-950/30 text-red-300'
          : 'border-amber-600/40 bg-amber-950/30 text-amber-300'"
      >
        <span class="shrink-0 mt-0.5 text-base">🛡</span>
        <div>
          <p class="font-bold">PMF / 802.11w — {{ targetPmf === 'required' ? 'Required' : 'Capable' }}</p>
          <p class="mt-0.5 opacity-80">
            {{ targetPmf === 'required'
              ? 'This AP uses WPA3/SAE with mandatory PMF. Deauth frames in the Deauth Engine below may be ignored by compliant clients. The capture may still succeed if the AP downgrades or if a client reconnects naturally.'
              : 'This AP supports PMF (802.11w). PMF-enabled clients may reject deauth frames, but non-PMF clients on the same AP can still be deauthenticated.' }}
          </p>
        </div>
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-5">
        <div>
          <label class="field-label">Interface (monitor mode) *</label>
          <select v-model="form.interface" class="field-select">
            <option value="" disabled>Select interface…</option>
            <option
              v-for="iface in interfaces"
              :key="iface.interface"
              :value="iface.interface"
              :class="iface.monitor_mode ? 'text-green-400' : ''"
            >
              {{ iface.interface }}{{ iface.monitor_mode ? ' ✓ monitor' : ' (managed)' }}
            </option>
          </select>
        </div>

        <div>
          <label class="field-label">Target BSSID *</label>
          <input
            v-model="form.bssid"
            class="field-input"
            placeholder="AA:BB:CC:DD:EE:FF"
            spellcheck="false"
          />
        </div>

        <div>
          <label class="field-label">Channel *</label>
          <input
            v-model="form.channel"
            class="field-input mb-2"
            placeholder="e.g. 6"
            spellcheck="false"
          />
          <div class="flex flex-wrap gap-1">
            <button
              v-for="ch in ch24"
              :key="ch"
              @click="form.channel = String(ch)"
              :class="[
                'px-1.5 py-0.5 rounded text-xs font-mono border transition-colors',
                form.channel === String(ch)
                  ? 'bg-cyber-500/20 border-cyber-500/50 text-cyber-300'
                  : 'border-slate-700 text-slate-500 hover:border-slate-500 hover:text-slate-200',
              ]"
            >{{ ch }}</button>
            <span class="text-slate-700 text-xs self-center px-1">|</span>
            <button
              v-for="ch in ch5short"
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
        </div>

        <div>
          <label class="field-label">ESSID (optional — for display only)</label>
          <input
            v-model="form.essid"
            class="field-input"
            placeholder="Network name"
            spellcheck="false"
          />
        </div>

        <div>
          <label class="field-label">Output Prefix (optional)</label>
          <input
            v-model="form.outputPrefix"
            class="field-input"
            placeholder="auto-generated from BSSID"
            spellcheck="false"
          />
        </div>
      </div>

      <div class="flex flex-wrap gap-3 items-center">
        <button
          @click="startCapture"
          :disabled="!form.interface || !form.bssid || !form.channel || startingCapture"
          class="btn-primary"
        >
          <span v-if="startingCapture" class="inline-block w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin mr-1"></span>
          {{ startingCapture ? 'Starting…' : '▶ Start Targeted Capture' }}
        </button>
        <p class="text-xs text-slate-500">
          Launches airodump-ng locked to the target BSSID and channel.
          Keep this running while you send deauth packets in Step 2.
        </p>
      </div>
    </div>

    <!-- ─── Stage 1: Capturing + Deauth ─── -->
    <template v-if="stage === 1">

      <!-- Status bar -->
      <div class="card">
        <div class="flex flex-wrap items-center justify-between gap-4">
          <div class="flex items-center gap-3">
            <span
              :class="capturing ? 'bg-red-500 animate-pulse' : 'bg-slate-600'"
              class="w-3 h-3 rounded-full shrink-0"
            ></span>
            <div>
              <div class="font-mono text-cyber-400 font-bold text-sm">{{ captureJob?.bssid }}</div>
              <div class="text-xs text-slate-400">
                CH {{ captureJob?.channel }}
                <span v-if="form.essid" class="ml-2 text-slate-500">({{ form.essid }})</span>
                <span v-if="captureStatus" class="ml-2">· {{ captureStatus.elapsed }}s elapsed</span>
                <span v-if="targetPmf" class="ml-2 font-semibold" :class="targetPmf === 'required' ? 'text-red-400' : 'text-amber-400'">
                  🛡 PMF {{ targetPmf }}
                </span>
              </div>
            </div>
          </div>

          <!-- Handshake badge -->
          <div
            :class="
              handshakeDetected
                ? 'border-green-600/50 bg-green-950/40'
                : 'border-slate-700 bg-slate-800/50'
            "
            class="flex items-center gap-2.5 px-3 py-2 rounded-xl border"
          >
            <span
              :class="handshakeDetected ? 'bg-green-500' : 'bg-amber-500 animate-pulse'"
              class="w-2.5 h-2.5 rounded-full shrink-0"
            ></span>
            <span :class="handshakeDetected ? 'text-green-300 font-bold' : 'text-slate-400'" class="text-sm">
              {{ handshakeDetected ? '🎉 Handshake captured!' : 'Waiting for handshake…' }}
            </span>
          </div>
        </div>

        <div v-if="captureStatus?.cap_path" class="mt-3 pt-3 border-t border-slate-700/50">
          <span class="text-xs text-slate-500">Cap file: </span>
          <span class="font-mono text-xs text-slate-300">{{ captureStatus.cap_path }}</span>
          <span v-if="captureStatus.cap_size" class="text-xs text-slate-500 ml-2">
            ({{ formatSize(captureStatus.cap_size) }})
          </span>
        </div>
      </div>

      <!-- Handshake detected → big CTA -->
      <div
        v-if="handshakeDetected"
        class="card border-green-600/40 bg-green-950/20"
      >
        <div class="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h3 class="text-green-300 font-bold text-lg">🎉 WPA Handshake Captured!</h3>
            <p class="text-green-400/80 text-sm mt-1 font-mono">
              {{ captureStatus?.cap_path }}
            </p>
            <p class="text-slate-400 text-xs mt-1">
              You can stop the capture now and proceed to crack the passphrase.
            </p>
          </div>
          <div class="flex gap-2">
            <button
              @click="doStop"
              :disabled="doStopping"
              class="btn-secondary"
            >
              <span v-if="doStopping" class="inline-block w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin mr-1"></span>
              {{ doStopping ? 'Stopping…' : '⏹ Stop' }}
            </button>
            <button @click="proceedToCrack" class="btn-primary">🔓 Crack Now →</button>
          </div>
        </div>
      </div>

      <!-- Live capture log -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">Live Capture Log</h3>
          <span class="text-xs text-slate-500 font-mono truncate max-w-xs">
            {{ captureJob?.command }}
          </span>
        </div>
        <div class="terminal max-h-52 overflow-y-auto">
          <div
            v-if="captureStatus?.log_tail"
            class="whitespace-pre-wrap"
            :class="handshakeDetected && 'text-green-300'"
          >{{ captureStatus.log_tail }}</div>
          <div v-else class="text-slate-500 italic">Waiting for airodump-ng output…</div>
        </div>
      </div>

      <!-- ─── Deauth Engine ─── -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">⚡ Deauth Engine</h3>
          <p class="text-xs text-slate-400">
            Force connected clients to re-authenticate, triggering the 4-way handshake
          </p>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-4">
          <div>
            <label class="field-label">Interface</label>
            <select v-model="deauthForm.interface" class="field-select">
              <option value="" disabled>Select interface…</option>
              <option v-for="iface in interfaces" :key="iface.interface" :value="iface.interface">
                {{ iface.interface }}{{ iface.monitor_mode ? ' ✓' : '' }}
              </option>
            </select>
          </div>

          <div>
            <label class="field-label">Target Client MAC (optional)</label>
            <input
              v-model="deauthForm.client"
              class="field-input"
              placeholder="broadcast all clients"
              spellcheck="false"
            />
          </div>

          <div>
            <label class="field-label">Deauth Count</label>
            <div class="flex gap-1 mt-1.5">
              <button
                v-for="n in [0, 10, 30, 50, 100]"
                :key="n"
                @click="deauthForm.count = n"
                :class="[
                  'px-2 py-1 rounded text-xs font-mono border transition-colors',
                  deauthForm.count === n
                    ? 'bg-amber-500/20 border-amber-500/50 text-amber-300'
                    : 'border-slate-700 text-slate-400 hover:border-slate-500',
                ]"
              >{{ n === 0 ? '∞' : n }}</button>
            </div>
          </div>
        </div>

        <div class="flex flex-wrap items-center gap-3 mb-3">
          <button
            @click="sendDeauth"
            :disabled="deauthing || !deauthForm.interface || autoDeauth"
            class="btn-danger"
          >
            {{ deauthing ? '⏳ Sending…' : '⚡ Send Deauth Burst' }}
          </button>

          <button
            v-if="deauthing"
            @click="cancelDeauth"
            class="btn-secondary"
          >
            ⏹ Cancel Deauth
          </button>

          <!-- Stop button — only shown while auto-deauth is running -->
          <button
            v-if="autoDeauth"
            @click="stopAutoDeauth"
            class="btn-secondary flex items-center gap-1.5"
          >
            ⏹ Stop Sending
          </button>

          <label class="flex items-center gap-2 cursor-pointer select-none">
            <input
              type="checkbox"
              v-model="autoDeauth"
              class="w-4 h-4 rounded border-slate-600 bg-slate-800 text-red-500 focus:ring-red-500"
            />
            <span class="text-sm text-slate-300">Auto every {{ autoInterval }}s</span>
          </label>
          <input
            v-if="autoDeauth"
            type="range"
            v-model.number="autoInterval"
            min="3"
            max="30"
            step="1"
            class="w-24 accent-red-500"
          />

          <span v-if="lastDeauthTime" class="text-xs text-slate-500">
            Last burst {{ lastDeauthTime }}
          </span>
        </div>

        <div v-if="deauthResult?.stdout || deauthResult?.stderr" class="terminal text-xs mt-3">
          <div v-if="deauthResult.stdout" class="whitespace-pre-wrap">{{ deauthResult.stdout }}</div>
          <div v-if="deauthResult.stderr" class="text-red-400 mt-2 whitespace-pre-wrap">
            {{ deauthResult.stderr }}
          </div>
        </div>

        <p class="text-xs text-slate-500 mt-2">
          Broadcast deauth (no client) works on most APs. If clients are using Protected Management
          Frames (802.11w), targeted deauth may fail — try a specific client MAC instead.
        </p>
      </div>

      <!-- Stop button -->
      <div>
        <button
          @click="doStop"
          :disabled="doStopping"
          class="btn-danger"
        >
          <span v-if="doStopping" class="inline-block w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin mr-1"></span>
          {{ doStopping ? 'Stopping…' : '⏹ Stop Capture' }}
        </button>
      </div>
    </template>

    <!-- ─── Stage 2: Complete ─── -->
    <div v-if="stage === 2" class="card">
      <div class="flex items-start gap-4">
        <div
          :class="handshakeDetected ? 'text-green-400' : 'text-amber-400'"
          class="text-4xl shrink-0 mt-1"
        >
          {{ handshakeDetected ? '✅' : '⚠️' }}
        </div>
        <div class="flex-1">
          <h3
            :class="handshakeDetected ? 'text-green-300' : 'text-amber-300'"
            class="font-bold text-lg mb-1"
          >
            {{
              handshakeDetected
                ? 'Handshake captured successfully'
                : 'Capture stopped — handshake not confirmed'
            }}
          </h3>
          <div class="space-y-1 text-sm">
            <p class="text-slate-400">
              Cap file:
              <span class="font-mono text-slate-200">{{ captureStatus?.cap_path || '—' }}</span>
            </p>
            <p v-if="captureStatus?.cap_size" class="text-slate-400">
              File size: <span class="text-slate-200">{{ formatSize(captureStatus.cap_size) }}</span>
            </p>
            <p class="text-slate-400">
              Target BSSID: <span class="font-mono text-cyber-400">{{ captureJob?.bssid }}</span>
              · Channel {{ captureJob?.channel }}
            </p>
          </div>
          <p v-if="!handshakeDetected" class="mt-3 text-xs text-slate-500">
            No handshake was detected. The cap file still exists — try opening it with Wireshark,
            or start a new capture and use the deauth engine to force client reconnection.
          </p>
        </div>
      </div>

      <div class="flex flex-wrap gap-3 mt-5">
        <button @click="newCapture" class="btn-secondary">↩ New Capture</button>
        <button
          v-if="captureStatus?.cap_path"
          @click="proceedToCrack"
          class="btn-primary"
        >
          🔓 Crack with Wordlist →
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { api } from '../api/index.js'
import { useHandshake } from '../composables/useHandshake.js'
import { useInterfaces } from '../composables/useInterfaces.js'
import { useNav } from '../composables/useNav.js'
import { useTarget } from '../composables/useTarget.js'
import { useToast } from '../composables/useToast.js'
import { useLogs } from '../composables/useLogs.js'

const { interfaces } = useInterfaces()
const { bssid, essid, channel, setCrackFile, pmf: targetPmf } = useTarget()
const { navigate } = useNav()
const toast = useToast()
const logs = useLogs()

const {
  captureJob,
  captureStatus,
  capturing,
  handshakeDetected,
  startCapture: hsStart,
  pollStatus,
  stopCapture: hsStop,
  resume: resumeCapture,
  reset: hsReset,
} = useHandshake()

// ─── Form ──────────────────────────────────────────────────────────────
const form = reactive({
  interface: '',
  bssid: bssid.value || '',
  channel: channel.value || '',
  essid: essid.value || '',
  outputPrefix: '',
})

const stage = ref(0)  // 0 = configure, 1 = capturing, 2 = complete
const startingCapture = ref(false)
const doStopping = ref(false)

// ─── Channel presets ────────────────────────────────────────────────────
const ch24 = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]
const ch5short = [36, 40, 44, 48, 52, 56, 60, 64, 100, 149, 153, 157, 161, 165]

// ─── Deauth form ────────────────────────────────────────────────────────
const deauthForm = reactive({
  interface: '',
  client: '',
  count: 10,
})
const deauthing = ref(false)
const deauthResult = ref(null)
const lastDeauthTime = ref('')
const autoDeauth = ref(false)
const autoInterval = ref(5)
const deauthJobId = ref('')
let autoTimer = null
let pollTimer = null
let deauthPollTimer = null

// ─── Capture workflow ────────────────────────────────────────────────────
async function startCapture() {
  startingCapture.value = true
  try {
    const started = await hsStart({
      interface: form.interface,
      bssid: form.bssid,
      channel: form.channel,
      output_prefix: form.outputPrefix || null,
    })
    if (started?.channel) form.channel = String(started.channel)
    stage.value = 1
    deauthForm.interface = form.interface
    // Start polling status every 2s
    pollTimer = setInterval(pollStatus, 2000)
  } finally {
    startingCapture.value = false
  }
}

async function doStop() {
  doStopping.value = true
  try {
    clearInterval(pollTimer)
    await stopAutoDeauth()
    await pollStatus()  // final status update
    await hsStop()
    stage.value = 2
  } finally {
    doStopping.value = false
  }
}

async function newCapture() {
  clearInterval(pollTimer)
  await stopAutoDeauth()
  hsReset()
  stage.value = 0
}

// ─── Deauth ─────────────────────────────────────────────────────────────
async function sendDeauth() {
  if (deauthing.value) return
  if (!deauthForm.interface) {
    toast.warning('Select an interface for deauth')
    return
  }
  deauthing.value = true
  deauthResult.value = null
  try {
    const started = await api.aireplay.startDeauth({
      interface: deauthForm.interface,
      bssid: form.bssid,
      client: deauthForm.client || null,
      count: deauthForm.count,
      channel: deauthChannel.value ? parseInt(deauthChannel.value) : null,
    })
    deauthJobId.value = started.job_id
    deauthResult.value = { ...started, success: true, returncode: null, stdout: '', stderr: '' }
    lastDeauthTime.value = new Date().toLocaleTimeString()
    await pollDeauthJob()
  } catch (err) {
    toast.error(err.message)
  } finally {
    deauthing.value = false
  }
}

async function pollDeauthJob() {
  clearTimeout(deauthPollTimer)
  if (!deauthJobId.value) return
  const data = await api.aireplay.deauthStatus(deauthJobId.value)
  deauthResult.value = data
  if (data.running) {
    await new Promise((resolve) => {
      deauthPollTimer = setTimeout(resolve, 500)
    })
    return pollDeauthJob()
  }
  logs.add(data.stopped ? 'aireplay-ng --deauth cancelled' : 'aireplay-ng --deauth', data)
  if (data.stopped) toast.info('Deauth cancelled')
  else if (!data.success) toast.warning('Deauth returned non-zero exit code')
  deauthJobId.value = ''
}

async function cancelDeauth() {
  autoDeauth.value = false
  clearAutoDeauth()
  clearTimeout(deauthPollTimer)
  if (deauthJobId.value) {
    try {
      deauthResult.value = await api.aireplay.stopDeauth(deauthJobId.value)
      logs.add('aireplay-ng --deauth cancelled', deauthResult.value)
      toast.info('Deauth cancelled')
    } catch (err) {
      toast.error(err.message)
    }
  }
  deauthJobId.value = ''
  deauthing.value = false
}

async function stopAutoDeauth() {
  autoDeauth.value = false
  clearAutoDeauth()
  if (deauthing.value || deauthJobId.value) {
    await cancelDeauth()
  }
}

const deauthChannel = computed(() =>
  captureStatus.value?.channel || captureJob.value?.channel || form.channel
)

function startAutoDeauth() {
  clearAutoDeauth()
  if (autoDeauth.value && deauthForm.interface) {
    autoTimer = setInterval(sendDeauth, autoInterval.value * 1000)
  }
}

function clearAutoDeauth() {
  clearInterval(autoTimer)
  autoTimer = null
}

// ─── Crack navigation ───────────────────────────────────────────────────
function proceedToCrack() {
  const path = captureStatus.value?.cap_path || captureJob.value?.cap_path
  if (path) setCrackFile(path)
  navigate('crack')
}

// ─── Helpers ────────────────────────────────────────────────────────────
function formatSize(bytes) {
  if (!bytes) return '0 B'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`
}

// Watch autoDeauth toggle
import { watch } from 'vue'
watch(autoDeauth, (val) => {
  if (val) startAutoDeauth()
  else clearAutoDeauth()
})
watch(autoInterval, () => {
  if (autoDeauth.value) startAutoDeauth()
})
watch(capturing, (running) => {
  if (running && captureJob.value) {
    stage.value = 1
    deauthForm.interface = form.interface || captureJob.value?.interface || ''
    clearInterval(pollTimer)
    pollTimer = setInterval(pollStatus, 2000)
  }
})

onMounted(async () => {
  await resumeCapture()
  // If navigated here with a target pre-set, fill the form
  if (bssid.value) form.bssid = bssid.value
  if (channel.value) form.channel = channel.value
  if (essid.value) form.essid = essid.value

  // Resume if a capture is already running
  if (capturing.value && captureJob.value) {
    stage.value = 1
    deauthForm.interface = form.interface || captureJob.value?.interface || ''
    clearInterval(pollTimer)
    pollTimer = setInterval(pollStatus, 2000)
  }
})

onUnmounted(() => {
  clearInterval(pollTimer)
  if (deauthJobId.value) cancelDeauth()
  else {
    clearTimeout(deauthPollTimer)
    clearAutoDeauth()
  }
})
</script>
