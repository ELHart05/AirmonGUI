import { ref } from 'vue'

// Singleton — state lives outside function scope so all callers share it
const toasts = ref([])
let _nextId = 0

export function useToast() {
  function show(message, type = 'info', duration = 4500) {
    const id = ++_nextId
    toasts.value.push({ id, message, type })
    if (duration > 0) {
      setTimeout(() => dismiss(id), duration)
    }
    return id
  }

  function dismiss(id) {
    const idx = toasts.value.findIndex((t) => t.id === id)
    if (idx !== -1) toasts.value.splice(idx, 1)
  }

  return {
    toasts,
    success: (msg, dur) => show(msg, 'success', dur),
    error: (msg, dur) => show(msg, 'error', dur),
    warning: (msg, dur) => show(msg, 'warning', dur),
    info: (msg, dur) => show(msg, 'info', dur),
    dismiss,
  }
}
