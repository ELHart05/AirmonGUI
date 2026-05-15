<template>
  <div class="p-6 space-y-5 animate-fade-in">
    <div class="page-header">
      <h2 class="page-title">Command Logs</h2>
      <p class="page-subtitle">History of all commands executed this session</p>
    </div>

    <!-- Toolbar -->
    <div class="card">
      <div class="flex flex-wrap items-center gap-3">
        <input
          v-model="filter"
          class="field-input flex-1 min-w-[200px]"
          placeholder="Filter by command or keyword…"
        />
        <span class="badge-neutral">{{ filtered.length }} / {{ entries.length }}</span>
        <button @click="clear" :disabled="!entries.length" class="btn-danger btn-sm">
          🗑 Clear All
        </button>
      </div>
    </div>

    <!-- Empty state -->
    <div v-if="!entries.length" class="card text-center py-12">
      <p class="text-3xl mb-3">📭</p>
      <p class="text-slate-400 font-medium">No commands logged yet.</p>
      <p class="text-slate-500 text-sm mt-1">Use the other views to run tools and they'll appear here.</p>
    </div>

    <!-- Log entries (newest first) -->
    <div v-else-if="filtered.length === 0" class="card text-center py-8 text-slate-400">
      No entries match <span class="font-mono text-slate-300">"{{ filter }}"</span>.
    </div>

    <div v-for="entry in filtered" :key="entry.id" class="card">
      <div class="card-header">
        <div class="flex items-center gap-2 min-w-0">
          <span :class="entry.success ? 'badge-success' : 'badge-error'" class="shrink-0">
            {{ entry.success ? 'ok' : 'err' }}
          </span>
          <span class="font-mono text-sm text-cyber-400 truncate font-semibold">{{ entry.command }}</span>
        </div>
        <div class="flex items-center gap-2 shrink-0">
          <span class="text-xs text-slate-500">{{ entry.time }}</span>
          <button
            @click="copyEntry(entry)"
            class="btn-ghost btn-sm text-xs"
            title="Copy to clipboard"
          >
            {{ copied === entry.id ? '✓ Copied' : '⎘ Copy' }}
          </button>
        </div>
      </div>

      <div v-if="entry.stdout" class="terminal mb-2">
        <div
          v-for="(line, idx) in entry.stdout.split('\n')"
          :key="idx"
          :class="[
            'whitespace-pre-wrap',
            line.includes('KEY FOUND') && 'text-green-400 font-bold',
            line.includes('error') && 'text-red-400',
            line.includes('warning') && 'text-amber-300',
          ]"
        >{{ line }}</div>
      </div>
      <div v-if="entry.stderr" class="terminal text-red-400 whitespace-pre-wrap">{{ entry.stderr }}</div>
      <div v-if="!entry.stdout && !entry.stderr" class="text-xs text-slate-500 italic">— no output —</div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useLogs } from '../composables/useLogs.js'
import { useToast } from '../composables/useToast.js'

const logs = useLogs()
const toast = useToast()

const filter = ref('')
const copied = ref(null)

const entries = computed(() => [...logs.entries.value].reverse())

const filtered = computed(() => {
  const q = filter.value.toLowerCase()
  if (!q) return entries.value
  return entries.value.filter(
    (e) =>
      e.command.toLowerCase().includes(q) ||
      (e.stdout || '').toLowerCase().includes(q) ||
      (e.stderr || '').toLowerCase().includes(q),
  )
})

function clear() {
  if (!confirm('Clear all command logs?')) return
  logs.clear()
  toast.info('Logs cleared')
}

async function copyEntry(entry) {
  const text = [
    `[${entry.time}] ${entry.command}`,
    entry.stdout,
    entry.stderr,
  ]
    .filter(Boolean)
    .join('\n')
  try {
    await navigator.clipboard.writeText(text)
    copied.value = entry.id
    setTimeout(() => { copied.value = null }, 2000)
  } catch {
    toast.error('Clipboard copy failed')
  }
}
</script>
