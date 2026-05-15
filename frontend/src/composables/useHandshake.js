import { ref } from 'vue'
import { api } from '../api/index.js'
import { useLogs } from './useLogs.js'
import { useToast } from './useToast.js'

// Singleton handshake state
const captureJob = ref(null)   // { job_id, cap_path, bssid, channel, command }
const captureStatus = ref(null) // latest poll result
const capturing = ref(false)
const handshakeDetected = ref(false)

export function useHandshake() {
  const toast = useToast()
  const logs = useLogs()

  async function startCapture(params) {
    capturing.value = false
    handshakeDetected.value = false
    captureStatus.value = null
    captureJob.value = null
    try {
      const data = await api.handshake.start(params)
      captureJob.value = data
      capturing.value = true
      const channelStatus = data.channel_result?.current
        ? `\nLocked channel: ${data.channel_result.current}`
        : ''
      logs.add('airodump-ng (handshake capture)', {
        stdout: `Started targeted capture on ${params.bssid} CH${params.channel}${channelStatus}\nCommand: ${data.command}`,
        success: true,
      })
      toast.success('Targeted capture started — watching for handshake')
      return data
    } catch (err) {
      toast.error(err.message)
      throw err
    }
  }

  async function pollStatus() {
    if (!captureJob.value) return null
    try {
      const data = await api.handshake.status(captureJob.value.job_id)
      captureStatus.value = data
      capturing.value = data.running
      if (data.handshake_detected && !handshakeDetected.value) {
        handshakeDetected.value = true
        toast.success('🎉 WPA Handshake captured!')
      }
      return data
    } catch {
      return null
    }
  }

  async function stopCapture() {
    if (!captureJob.value) return
    try {
      const data = await api.handshake.stop(captureJob.value.job_id)
      capturing.value = false
      logs.add('airodump-ng stop (handshake)', {
        stdout: `Capture stopped. Cap: ${data.cap_path}`,
        success: true,
      })
      toast.info('Capture stopped')
      return data
    } catch (err) {
      toast.error(err.message)
    }
  }

  function reset() {
    captureJob.value = null
    captureStatus.value = null
    capturing.value = false
    handshakeDetected.value = false
  }

  return {
    captureJob,
    captureStatus,
    capturing,
    handshakeDetected,
    startCapture,
    pollStatus,
    stopCapture,
    reset,
  }
}
