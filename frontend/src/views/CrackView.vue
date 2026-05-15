<template>
  <div class="p-4 sm:p-6 space-y-5 animate-fade-in">
    <!-- Header -->
    <div class="page-header">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 class="page-title">Crack WPA / WEP</h2>
          <p class="page-subtitle">aircrack-ng · dictionary attack against a CAP file</p>
        </div>
        <!-- Live status pill -->
        <div
          v-if="cracking"
          class="flex items-center gap-2 px-3 py-1.5 bg-red-950/40 border border-red-600/40 rounded-xl"
        >
          <span class="w-2.5 h-2.5 rounded-full bg-red-500 animate-pulse shrink-0"></span>
          <span class="text-sm text-red-300 font-semibold">
            Cracking… {{ crackStatus?.elapsed ?? 0 }}s
          </span>
        </div>
        <div
          v-else-if="crackStatus && !cracking"
          :class="[
            'flex items-center gap-2 px-3 py-1.5 rounded-xl border',
            keyFound
              ? 'bg-green-950/40 border-green-600/40'
              : 'bg-slate-800 border-slate-600/40',
          ]"
        >
          <span
            :class="keyFound ? 'bg-green-500' : 'bg-slate-500'"
            class="w-2.5 h-2.5 rounded-full shrink-0"
          ></span>
          <span :class="keyFound ? 'text-green-300' : 'text-slate-400'" class="text-sm font-semibold">
            {{ keyFound ? 'Key found' : 'Finished — not found' }}
          </span>
        </div>
      </div>
    </div>

    <!-- ─── Live Log Card (shown while cracking or after) ─── -->
    <div v-if="job" class="card">
      <div class="card-header">
        <div class="flex items-center gap-2.5">
          <span
            :class="cracking ? 'bg-red-500 animate-pulse' : (keyFound ? 'bg-green-500' : 'bg-slate-500')"
            class="w-2.5 h-2.5 rounded-full shrink-0"
          ></span>
          <h3 class="card-title">{{ cracking ? 'Live Output' : 'Session Output' }}</h3>
          <span v-if="crackStatus?.elapsed" class="text-xs text-slate-500">
            {{ crackStatus.elapsed }}s
          </span>
        </div>
        <div class="flex items-center gap-2">
          <button
            v-if="cracking"
            @click="stopCrack"
            :disabled="stopping"
            class="btn-danger btn-sm"
          >
            <span v-if="stopping" class="inline-block w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin mr-1"></span>
            {{ stopping ? 'Stopping…' : '⏹ Stop' }}
          </button>
          <button v-else @click="resetResult" class="btn-secondary btn-sm">↩ New Session</button>
        </div>
      </div>

      <!-- Key found highlight -->
      <div
        v-if="keyFound"
        class="flex items-center gap-3 px-4 py-3 mb-3 bg-green-950/60 border border-green-600/50 rounded-xl"
      >
        <span class="text-2xl">🎉</span>
        <div>
          <p class="font-bold text-green-300">KEY FOUND!</p>
          <p class="font-mono text-green-200 text-sm mt-0.5 select-all">{{ keyFound }}</p>
        </div>
      </div>

      <!-- Log terminal with auto-scroll -->
      <div ref="logEl" class="terminal max-h-72 overflow-y-auto">
        <div
          v-if="crackStatus?.log_tail"
          class="whitespace-pre-wrap"
          :class="keyFound ? 'text-green-300' : ''"
        >{{ crackStatus.log_tail }}</div>
        <div v-else class="text-slate-500 italic">Waiting for aircrack-ng output…</div>
      </div>

      <p class="text-xs text-slate-500 mt-2 font-mono truncate hidden sm:block">
        {{ job.command }}
      </p>
    </div>

    <!-- ─── Config Card ─── -->
    <div class="card">
      <div class="card-header">
        <h3 class="card-title">Session Parameters</h3>
        <button @click="loadCaptures" class="btn-ghost btn-sm">↻ Refresh</button>
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-5">
        <!-- Capture file -->
        <div class="sm:col-span-2">
          <label class="field-label">Capture File *</label>
          <div class="flex flex-wrap gap-2 items-center">
            <select
              v-model="form.captureFile"
              @change="validateCap"
              class="field-select flex-1 min-w-0"
            >
              <option value="" disabled>Select a capture file…</option>
              <option v-for="cap in captures" :key="cap.path" :value="cap.path">
                {{ cap.name }} ({{ formatSize(cap.size) }})
              </option>
            </select>
            <span v-if="validating" class="text-xs text-slate-400 whitespace-nowrap">⏳ checking…</span>
            <span
              v-else-if="capValidation"
              :class="[
                'text-xs font-semibold rounded-full px-2.5 py-1 whitespace-nowrap border shrink-0',
                capValidation.has_handshake
                  ? 'text-green-300 bg-green-950/50 border-green-600/40'
                  : 'text-red-300 bg-red-950/50 border-red-600/40',
              ]"
            >
              {{ capValidation.has_handshake
                ? `✓ ${capValidation.handshake_count} handshake${capValidation.handshake_count !== 1 ? 's' : ''}`
                : '✗ 0 handshakes' }}
            </span>
          </div>

          <!-- Warning banner: no handshake -->
          <div
            v-if="capValidation && !capValidation.has_handshake"
            class="mt-2 px-3 py-2.5 bg-red-950/40 border border-red-600/40 rounded-xl text-sm"
          >
            <p class="text-red-300 font-semibold mb-1">⚠ No WPA handshake in capture file</p>
            <p class="text-red-400/80 text-xs">
              {{ capValidation.no_eapol
                ? 'No EAPOL data — use the Handshake Capture workflow, send deauth bursts, and wait for the detection indicator.'
                : 'aircrack-ng found 0 handshakes. Re-run the capture workflow.'
              }}
            </p>
          </div>

          <p v-if="captures.length === 0" class="text-xs text-slate-500 mt-1.5">
            No .cap files found in <span class="font-mono">{{ captureDir }}</span>.
            Use the Handshake Capture workflow first.
          </p>
        </div>

        <!-- Wordlist -->
        <div class="sm:col-span-2">
          <label class="field-label">Wordlist Path *</label>
          <input
            v-model="form.wordlist"
            class="field-input"
            placeholder="/usr/share/wordlists/rockyou.txt"
            spellcheck="false"
          />
          <div class="flex flex-wrap gap-2 mt-2">
            <button
              v-for="preset in wordlistPresets"
              :key="preset"
              @click="form.wordlist = preset"
              :class="['btn-ghost btn-sm text-xs font-mono', form.wordlist === preset && 'bg-slate-700 text-white']"
            >
              {{ preset.split('/').pop() }}
            </button>
          </div>
        </div>

        <!-- BSSID filter -->
        <div>
          <label class="field-label">Filter BSSID (optional)</label>
          <input
            v-model="form.bssid"
            class="field-input"
            placeholder="00:11:22:33:44:55"
            spellcheck="false"
          />
        </div>

        <!-- Channel -->
        <div>
          <label class="field-label">Channel (optional)</label>
          <input v-model="form.channel" class="field-input" placeholder="6" />
        </div>
      </div>

      <div class="flex flex-wrap gap-3">
        <button
          @click="startCrack"
          :disabled="cracking || !form.captureFile || !form.wordlist"
          class="btn-primary"
        >
          {{ cracking ? '⏳ Cracking…' : '🔓 Run aircrack-ng' }}
        </button>
        <button
          v-if="cracking"
          @click="stopCrack"
          :disabled="stopping"
          class="btn-danger"
        >
          <span v-if="stopping" class="inline-block w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin mr-1"></span>
          {{ stopping ? 'Stopping…' : '⏹ Stop' }}
        </button>
        <button @click="resetAll" :disabled="cracking" class="btn-ghost btn-sm">Reset</button>
      </div>

      <p class="text-xs text-slate-500 mt-3">
        aircrack-ng will attempt to recover the WPA/WEP key using the wordlist.
        For large wordlists, consider hashcat instead.
      </p>
    </div>

    <!-- ─── Capture Files Table ─── -->
    <div v-if="captures.length" class="card">
      <div class="card-header">
        <h3 class="card-title">Capture Files</h3>
        <span class="badge-neutral">{{ captures.length }} file{{ captures.length !== 1 ? 's' : '' }}</span>
      </div>
      <div class="overflow-x-auto -mx-5 px-5">
        <table class="data-table">
          <thead>
            <tr>
              <th>Filename</th>
              <th>Size</th>
              <th class="hidden sm:table-cell">Modified</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="cap in captures"
              :key="cap.path"
              :class="form.captureFile === cap.path && 'row-selected'"
              @click="form.captureFile = cap.path"
            >
              <td class="text-cyber-400 font-semibold">{{ cap.name }}</td>
              <td>{{ formatSize(cap.size) }}</td>
              <td class="hidden sm:table-cell">{{ formatDate(cap.modified) }}</td>
              <td>
                <button
                  @click.stop="deleteCapture(cap.name)"
                  class="btn-ghost btn-sm text-red-400 hover:text-red-300 hover:bg-red-900/20"
                >
                  🗑 Delete
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { nextTick, onMounted, ref, watch } from 'vue'
import { api } from '../api/index.js'
import { useCrack } from '../composables/useCrack.js'
import { useToast } from '../composables/useToast.js'
import { useTarget } from '../composables/useTarget.js'

const toast = useToast()
const { capFile } = useTarget()

const {
  form,
  job,
  crackStatus,
  cracking,
  stopping,
  keyFound,
  captures,
  captureDir,
  capValidation,
  validating,
  loadCaptures,
  validateCap,
  startCrack,
  stopCrack,
  resetResult,
  resetAll,
} = useCrack()

const logEl = ref(null)

const wordlistPresets = [
  '/usr/share/wordlists/rockyou.txt',
  '/usr/share/wordlists/fasttrack.txt',
  '/usr/share/wordlists/nmap.lst',
]

// Auto-scroll log terminal on new content
watch(
  () => crackStatus.value?.log_tail,
  () => nextTick(() => {
    if (logEl.value) logEl.value.scrollTop = logEl.value.scrollHeight
  }),
)

// Trigger validation whenever captureFile changes
watch(() => form.captureFile, validateCap)

async function deleteCapture(filename) {
  if (!confirm(`Delete ${filename}?`)) return
  try {
    await api.captures.delete(filename)
    toast.success(`Deleted ${filename}`)
    if (form.captureFile.endsWith(filename)) form.captureFile = ''
    await loadCaptures()
  } catch (err) {
    toast.error(err.message)
  }
}

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`
}

function formatDate(ts) {
  return new Date(ts * 1000).toLocaleString()
}

onMounted(async () => {
  await loadCaptures()
  // Pre-fill from handshake workflow if not already set
  if (!form.captureFile && capFile.value && captures.value.some((c) => c.path === capFile.value)) {
    form.captureFile = capFile.value
  }
})
</script>
