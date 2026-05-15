import { computed, reactive, ref } from 'vue'
import { api } from '../api/index.js'
import { useLogs } from './useLogs.js'
import { useToast } from './useToast.js'

// ─── Singleton state — persists across tab switches ────────────────────────
const form = reactive({
  captureFile: '',
  wordlist: '',
  bssid: '',
  channel: '',
})

const job = ref(null)          // { job_id, command } from POST /crack
const crackStatus = ref(null)  // latest poll result
const cracking = ref(false)
const captures = ref([])
const captureDir = ref('/tmp/airmongui')
const capValidation = ref(null)
const validating = ref(false)

let pollTimer = null
const stopping = ref(false)
const crackJobs = ref([])

// ────────────────────────────────────────────────────────────────────────────

export function useCrack() {
  const toast = useToast()
  const logs = useLogs()

  const keyFound = computed(() =>
    crackStatus.value?.key_found ? crackStatus.value.key : null,
  )

  // ── Captures ──────────────────────────────────────────────────────────────
  async function loadCaptures() {
    try {
      const data = await api.captures.capFiles()
      captures.value = data.captures
      captureDir.value = data.capture_dir
    } catch (err) {
      toast.error(`Failed to load captures: ${err.message}`)
    }
  }

  async function validateCap() {
    if (!form.captureFile) { capValidation.value = null; return }
    validating.value = true
    capValidation.value = null
    try {
      capValidation.value = await api.aircrack.validate(form.captureFile)
    } catch {
      // non-fatal — advisory only
    } finally {
      validating.value = false
    }
  }

  // ── Crack workflow ────────────────────────────────────────────────────────
  async function startCrack() {
    if (!form.captureFile || !form.wordlist) return
    cracking.value = true
    crackStatus.value = null
    job.value = null
    try {
      const data = await api.aircrack.crack({
        capture_file: form.captureFile,
        wordlist: form.wordlist,
        bssid: form.bssid || null,
        channel: form.channel || null,
      })
      job.value = data
      logs.add('aircrack-ng', { stdout: `Started: ${data.command}`, success: true })
      toast.success('Aircrack-ng started — watching for results…')
      pollTimer = setInterval(pollStatus, 2000)
      await loadJobs()
    } catch (err) {
      cracking.value = false
      toast.error(err.message)
    }
  }

  async function pollStatus() {
    if (!job.value) return
    try {
      const data = await api.aircrack.status(job.value.job_id)
      crackStatus.value = data
      if (!data.running) {
        clearInterval(pollTimer)
        pollTimer = null
        cracking.value = false
        logs.add('aircrack-ng result', {
          stdout: data.log_tail,
          success: data.key_found,
        })
        if (data.key_found) {
          toast.success(`🔑 KEY FOUND: ${data.key}`)
        } else if (data.returncode !== null) {
          toast.info('Aircrack finished — key not in wordlist')
        }
      }
    } catch {
      // ignore transient poll errors
    }
  }

  async function loadJobs() {
    try {
      const data = await api.aircrack.jobs()
      crackJobs.value = data.jobs || []
      return crackJobs.value
    } catch {
      return []
    }
  }

  async function resume() {
    const jobs = await loadJobs()
    const active = jobs.find((item) => item.running)
    if (!active) return null

    job.value = {
      job_id: active.job_id,
      command: active.command,
    }
    form.captureFile = active.capture_file || form.captureFile
    form.wordlist = active.wordlist || form.wordlist
    cracking.value = true
    await pollStatus()
    if (!pollTimer && cracking.value) {
      pollTimer = setInterval(pollStatus, 2000)
    }
    return active
  }

  async function stopCrack() {
    if (!job.value) return
    clearInterval(pollTimer)
    pollTimer = null
    stopping.value = true
    try {
      await api.aircrack.stop(job.value.job_id)
      // one final poll to get last log snapshot
      const data = await api.aircrack.status(job.value.job_id)
      crackStatus.value = data
    } catch { /* ignore */ } finally {
      stopping.value = false
    }
    cracking.value = false
    toast.info('Crack session stopped')
  }

  function resetResult() {
    clearInterval(pollTimer)
    pollTimer = null
    job.value = null
    crackStatus.value = null
    cracking.value = false
    capValidation.value = null
  }

  function resetAll() {
    resetResult()
    form.captureFile = ''
    form.wordlist = ''
    form.bssid = ''
    form.channel = ''
  }

  return {
    form,
    job,
    crackStatus,
    cracking,
    stopping,
    keyFound,
    captures,
    crackJobs,
    captureDir,
    capValidation,
    validating,
    loadCaptures,
    loadJobs,
    resume,
    validateCap,
    startCrack,
    pollStatus,
    stopCrack,
    resetResult,
    resetAll,
  }
}
