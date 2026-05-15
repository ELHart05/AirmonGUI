import { ref } from 'vue'
import { api } from '../api/index.js'
import { useLogs } from './useLogs.js'
import { useToast } from './useToast.js'

// Singleton interface state
const interfaces = ref([])
const selectedInterface = ref('')
const loading = ref(false)

export function useInterfaces() {
  const toast = useToast()
  const logs = useLogs()

  async function refresh() {
    loading.value = true
    try {
      const data = await api.interfaces.list()
      interfaces.value = data.interfaces || []
      if (!selectedInterface.value && interfaces.value.length) {
        selectedInterface.value = interfaces.value[0].interface
      }
      logs.add('airmon-ng', { stdout: data.raw, success: true })
      toast.success('Interfaces refreshed')
    } catch (err) {
      toast.error(`Failed to load interfaces: ${err.message}`)
    } finally {
      loading.value = false
    }
  }

  async function startMonitor(iface) {
    loading.value = true
    try {
      const data = await api.interfaces.monitor(iface, 'start')
      if (data.interfaces) interfaces.value = data.interfaces
      logs.add(`airmon-ng start ${iface}`, data)
      toast.success(`Monitor mode started on ${iface}`)
      return data
    } catch (err) {
      toast.error(err.message)
      throw err
    } finally {
      loading.value = false
    }
  }

  async function stopMonitor(iface) {
    loading.value = true
    try {
      const data = await api.interfaces.monitor(iface, 'stop')
      if (data.interfaces) interfaces.value = data.interfaces
      logs.add(`airmon-ng stop ${iface}`, data)
      toast.success(`Monitor mode stopped on ${iface}`)
      return data
    } catch (err) {
      toast.error(err.message)
      throw err
    } finally {
      loading.value = false
    }
  }

  async function checkKill() {
    loading.value = true
    try {
      const data = await api.interfaces.checkKill()
      logs.add('airmon-ng check kill', data)
      toast.success('Check-kill process completed')
      return data
    } catch (err) {
      toast.error(err.message)
      throw err
    } finally {
      loading.value = false
    }
  }

  function select(iface) {
    selectedInterface.value = iface
  }

  return {
    interfaces,
    selectedInterface,
    loading,
    refresh,
    startMonitor,
    stopMonitor,
    checkKill,
    select,
  }
}
