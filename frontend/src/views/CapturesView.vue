<template>
  <div class="p-6 space-y-5 animate-fade-in">
    <!-- Header -->
    <div class="page-header flex items-start justify-between">
      <div>
        <h2 class="page-title">Captures &amp; Logs</h2>
        <p class="page-subtitle">Browse, manage and delete files in <span class="font-mono text-slate-300">/tmp/airmongui</span></p>
      </div>
      <div class="flex items-center gap-2 mt-1">
        <button @click="load" :disabled="loading" class="btn-secondary btn-sm">
          <span v-if="loading" class="inline-block w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin mr-1"></span>
          ↻ Refresh
        </button>
      </div>
    </div>

    <!-- Toolbar -->
    <div class="card py-3 space-y-2">
      <div class="flex flex-wrap items-center gap-3">
        <select v-model="typeFilter" class="field-input text-xs w-32">
          <option value="">All types</option>
          <option value=".cap">CAP</option>
          <option value=".pcap">PCAP</option>
          <option value=".csv">CSV</option>
          <option value=".ivs">IVS</option>
          <option value=".log">LOG</option>
        </select>
        <input
          v-model="textFilter"
          class="field-input text-xs w-48"
          placeholder="Search filename…"
        />
        <button
          v-if="typeFilter || textFilter"
          @click="typeFilter = ''; textFilter = ''"
          class="text-xs text-slate-500 hover:text-slate-300 underline"
        >Clear</button>
        <span class="ml-auto text-xs text-slate-500">
          {{ filtered.length }}<span v-if="filtered.length !== captures.length"> / {{ captures.length }}</span> file{{ filtered.length !== 1 ? 's' : '' }}
          <span v-if="totalSize" class="ml-1">· {{ formatSize(totalSize) }} total</span>
        </span>
        <button
          v-if="captures.length"
          @click="deleteAllConfirm ? confirmDeleteAll() : (deleteAllConfirm = true)"
          :class="deleteAllConfirm ? 'btn-danger btn-sm' : 'btn-ghost btn-sm text-red-400 hover:text-red-300'"
        >
          {{ deleteAllConfirm ? '⚠ Confirm – Delete All' : '🗑 Delete All' }}
        </button>
        <button v-if="deleteAllConfirm" @click="deleteAllConfirm = false" class="btn-ghost btn-sm">Cancel</button>
      </div>

      <!-- Bulk action bar — visible only when rows are selected -->
      <div v-if="selectedFiles.length" class="flex items-center gap-3 pt-2 border-t border-slate-700/60">
        <span class="text-xs text-slate-400">
          <span class="font-semibold text-white">{{ selectedFiles.length }}</span> selected
        </span>
        <button
          @click="bulkDeleteConfirm ? deleteBulk() : (bulkDeleteConfirm = true)"
          :class="bulkDeleteConfirm ? 'btn-danger btn-sm' : 'btn-ghost btn-sm text-red-400 hover:text-red-300'"
        >
          {{ bulkDeleteConfirm ? `⚠ Confirm – Delete ${selectedFiles.length}` : `🗑 Delete Selected` }}
        </button>
        <button v-if="bulkDeleteConfirm" @click="bulkDeleteConfirm = false" class="btn-ghost btn-sm">Cancel</button>
        <button @click="selectedFiles = []" class="text-xs text-slate-500 hover:text-slate-300 underline ml-auto">
          Deselect all
        </button>
      </div>
    </div>

    <!-- Empty state -->
    <div v-if="!loading && !captures.length" class="card text-center py-14">
      <p class="text-slate-400 font-medium">No capture files found.</p>
      <p class="text-slate-500 text-sm mt-1">Run a scan or handshake capture to generate files.</p>
      <button @click="navigate('scan')" class="btn-secondary mt-5">Go to Network Scan</button>
    </div>

    <!-- File table -->
    <div v-else-if="filtered.length" class="card p-0 overflow-hidden">
      <table class="data-table">
        <thead>
          <tr>
            <th class="w-10 text-center">
              <input
                type="checkbox"
                :checked="allSelected"
                :indeterminate.prop="someSelected"
                @change="toggleSelectAll"
                class="w-3.5 h-3.5 rounded border-slate-600 bg-slate-800 cursor-pointer"
              />
            </th>
            <th class="w-8"></th>
            <th>Filename</th>
            <th>Type</th>
            <th>Size</th>
            <th>Modified</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="file in filtered"
            :key="file.filename"
            :class="selectedFiles.includes(file.filename) ? 'bg-slate-800/60' : ''"
          >
            <!-- Checkbox -->
            <td class="text-center">
              <input
                type="checkbox"
                :checked="selectedFiles.includes(file.filename)"
                @change="toggleSelect(file.filename)"
                class="w-3.5 h-3.5 rounded border-slate-600 bg-slate-800 cursor-pointer"
              />
            </td>
            <!-- Icon -->
            <td class="text-center">
              <span class="text-base" :title="file.filename">{{ fileIcon(file.ext) }}</span>
            </td>
            <!-- Name -->
            <td>
              <span class="font-mono text-sm text-slate-200 break-all">{{ file.filename }}</span>
            </td>
            <!-- Type badge -->
            <td>
              <span
                class="text-xs font-mono px-1.5 py-0.5 rounded border"
                :class="extBadgeClass(file.ext)"
              >{{ file.ext || '?' }}</span>
            </td>
            <!-- Size -->
            <td class="text-slate-400 font-mono text-xs whitespace-nowrap">{{ formatSize(file.size) }}</td>
            <!-- Modified -->
            <td class="text-slate-500 text-xs whitespace-nowrap">{{ formatDate(file.mtime) }}</td>
            <!-- Actions -->
            <td>
              <div class="flex items-center gap-1.5">
                <!-- Use for cracking (CAP/PCAP only) -->
                <button
                  v-if="file.ext === '.cap' || file.ext === '.pcap'"
                  @click="useToCrack(file)"
                  class="btn-ghost btn-sm text-cyber-400 hover:text-cyber-300 hover:bg-cyber-900/20 text-xs"
                  title="Load into Crack view"
                >
                  🔓 Crack
                </button>
                <!-- Delete with inline confirmation -->
                <button
                  v-if="pendingDelete !== file.filename"
                  @click="pendingDelete = file.filename"
                  class="btn-ghost btn-sm text-red-500 hover:text-red-300 hover:bg-red-900/20 text-xs"
                  title="Delete file"
                >
                  🗑
                </button>
                <template v-else>
                  <button @click="doDelete(file.filename)" class="btn-danger btn-sm text-xs">Confirm</button>
                  <button @click="pendingDelete = ''" class="btn-ghost btn-sm text-xs">Cancel</button>
                </template>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-else-if="!loading" class="card text-center py-8">
      <p class="text-slate-500 text-sm">No files match the current filter.</p>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { api } from '../api/index.js'
import { useNav } from '../composables/useNav.js'
import { useTarget } from '../composables/useTarget.js'
import { useToast } from '../composables/useToast.js'

const { navigate } = useNav()
const { setCrackFile } = useTarget()
const toast = useToast()

const captures = ref([])
const loading = ref(false)
const typeFilter = ref('')
const textFilter = ref('')
const pendingDelete = ref('')
const deleteAllConfirm = ref(false)
const selectedFiles = ref([])
const bulkDeleteConfirm = ref(false)

// ── data loading ──────────────────────────────────────────────────────────────

async function load() {
  loading.value = true
  try {
    const data = await api.captures.list()
    // Enrich each file with a parsed extension
    captures.value = (data.captures || [])
      .map((f) => ({
        ...f,
        filename: f.name || f.filename,
        mtime: f.modified || f.mtime,
        ext: extOf(f.name || f.filename || ''),
      }))
      .sort((a, b) => (b.mtime || 0) - (a.mtime || 0))
  } catch (err) {
    toast.error(err.message || 'Failed to load captures')
  } finally {
    loading.value = false
  }
}

// ── filters ───────────────────────────────────────────────────────────────────

const filtered = computed(() => {
  const q = textFilter.value.toLowerCase()
  const ext = typeFilter.value.toLowerCase()
  return captures.value.filter((f) => {
    if (ext && f.ext !== ext) return false
    if (q && !f.filename.toLowerCase().includes(q)) return false
    return true
  })
})

const allSelected = computed(() =>
  filtered.value.length > 0 && filtered.value.every((f) => selectedFiles.value.includes(f.filename))
)
const someSelected = computed(() =>
  selectedFiles.value.length > 0 && !allSelected.value
)

function toggleSelectAll() {
  if (allSelected.value) {
    selectedFiles.value = []
  } else {
    selectedFiles.value = filtered.value.map((f) => f.filename)
  }
}

function toggleSelect(filename) {
  const idx = selectedFiles.value.indexOf(filename)
  if (idx >= 0) selectedFiles.value.splice(idx, 1)
  else selectedFiles.value.push(filename)
}

const totalSize = computed(() => captures.value.reduce((s, f) => s + (f.size || 0), 0))

// ── actions ───────────────────────────────────────────────────────────────────

async function doDelete(filename) {
  pendingDelete.value = ''
  try {
    await api.captures.delete(filename)
    captures.value = captures.value.filter((f) => f.filename !== filename)
    selectedFiles.value = selectedFiles.value.filter((n) => n !== filename)
    toast.success(`Deleted ${filename}`)
  } catch (err) {
    toast.error(err.message || 'Delete failed')
  }
}

async function deleteBulk() {
  bulkDeleteConfirm.value = false
  const toDelete = [...selectedFiles.value]
  let failed = 0
  for (const filename of toDelete) {
    try {
      await api.captures.delete(filename)
    } catch {
      failed++
    }
  }
  selectedFiles.value = []
  await load()
  if (failed) toast.warning(`${failed} file(s) could not be deleted`)
  else toast.success(`${toDelete.length} file(s) deleted`)
}

async function confirmDeleteAll() {
  deleteAllConfirm.value = false
  const toDelete = [...captures.value]
  let failed = 0
  for (const f of toDelete) {
    try {
      await api.captures.delete(f.filename)
    } catch {
      failed++
    }
  }
  selectedFiles.value = []
  await load()
  if (failed) toast.warning(`${failed} file(s) could not be deleted`)
  else toast.success('All files deleted')
}

function useToCrack(file) {
  setCrackFile(file.path || `/tmp/airmongui/${file.filename}`)
  navigate('crack')
}

// ── helpers ───────────────────────────────────────────────────────────────────

function extOf(name) {
  const m = name.match(/(\.[^./\\]+)$/)
  return m ? m[1].toLowerCase() : ''
}

function formatSize(bytes) {
  if (!bytes) return '0 B'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(2) + ' MB'
}

function formatDate(ts) {
  if (!ts) return '—'
  return new Date(ts * 1000).toLocaleString(undefined, {
    year: 'numeric', month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

function fileIcon(ext) {
  const map = { '.cap': '📦', '.pcap': '📦', '.csv': '📊', '.ivs': '🔑', '.log': '📄' }
  return map[ext] || '📁'
}

function extBadgeClass(ext) {
  const map = {
    '.cap': 'border-cyber-500/50 bg-cyber-900/30 text-cyber-300',
    '.pcap': 'border-cyber-500/50 bg-cyber-900/30 text-cyber-300',
    '.csv': 'border-green-500/50 bg-green-900/30 text-green-300',
    '.ivs': 'border-red-500/50 bg-red-900/30 text-red-300',
    '.log': 'border-slate-600 bg-slate-800/60 text-slate-400',
  }
  return map[ext] || 'border-slate-700 text-slate-500'
}

onMounted(load)
</script>
