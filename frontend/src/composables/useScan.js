import { reactive, ref } from 'vue'
import { api } from '../api/index.js'
import { useLogs } from './useLogs.js'
import { useToast } from './useToast.js'

// Singleton scan state
const form = reactive({
  interface: '',
  channel: '',
  band: '',
  bssid: '',
  outputPrefix: '',
})
const activeJobId = ref('')
const results = reactive({ networks: [], clients: [] })
const isRunning = ref(false)
const jobs = ref([])
const scanLoading = ref(false)
const logTail = ref('')

export function useScan() {
  const toast = useToast()
  const logs = useLogs()

  async function start() {
    if (!form.interface) {
      toast.warning('Select an interface first')
      return
    }
    scanLoading.value = true
    try {
      const data = await api.airodump.start({
        interface: form.interface,
        channel: form.channel || null,
        band: form.band || null,
        bssid: form.bssid || null,
        output_prefix: form.outputPrefix || null,
      })
      // Clear stale results before activating the new job
      results.networks = []
      results.clients = []
      logTail.value = ''
      activeJobId.value = data.job_id
      isRunning.value = true
      const channelStatus = data.channel_result?.current
        ? `Locked channel: ${data.channel_result.current}\n`
        : ''
      logs.add('airodump-ng start', { stdout: `${channelStatus}Command: ${data.command}`, success: true })
      toast.success('Scan started')
      await loadJobs()
    } catch (err) {
      toast.error(err.message)
    } finally {
      scanLoading.value = false
    }
  }

  async function stop() {
    if (!activeJobId.value) return
    scanLoading.value = true
    try {
      await api.airodump.stop(activeJobId.value)
      isRunning.value = false
      logs.add(`airodump-ng stop`, { stdout: `Job ${activeJobId.value} stopped`, success: true })
      toast.success('Scan stopped')
      await loadJobs()
    } catch (err) {
      toast.error(err.message)
    } finally {
      scanLoading.value = false
    }
  }

  async function fetchResults() {
    if (!activeJobId.value) return
    scanLoading.value = true
    try {
      const data = await api.airodump.results(activeJobId.value)
      results.networks = data.data?.networks || []
      results.clients = data.data?.clients || []
      logTail.value = data.log_tail || ''
      isRunning.value = data.running
    } catch (err) {
      toast.error(err.message)
    } finally {
      scanLoading.value = false
    }
  }

  async function loadJobs() {
    try {
      const data = await api.airodump.jobs()
      jobs.value = data.jobs || []
      const active = jobs.value.find((j) => j.running)
      if (active && !activeJobId.value) {
        activeJobId.value = active.job_id
        isRunning.value = true
      }
    } catch {
      // silent — not critical
    }
  }

  return { form, activeJobId, results, isRunning, jobs, scanLoading, logTail, start, stop, fetchResults, loadJobs }
}
