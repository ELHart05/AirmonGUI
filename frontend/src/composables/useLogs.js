import { ref } from 'vue'

// Singleton log store
const entries = ref([])

export function useLogs() {
  function add(command, result) {
    entries.value.unshift({
      id: Date.now() + Math.random(),
      command,
      stdout: result?.stdout || '',
      stderr: result?.stderr || '',
      success: result?.success !== false,
      returncode: result?.returncode ?? null,
      time: new Date().toISOString(),
    })
    // Keep last 200 entries
    if (entries.value.length > 200) entries.value.splice(200)
  }

  function clear() {
    entries.value = []
  }

  return { entries, add, clear }
}
