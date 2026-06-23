import { ref } from 'vue'

// The backend prints an API token on startup. The user pastes it once; we keep
// it in sessionStorage so it survives reloads but not a closed tab. Every API
// call sends it as the X-Auth-Token header.
const STORAGE_KEY = 'airmon_token'
const token = ref(sessionStorage.getItem(STORAGE_KEY) || '')

// UI bootstrap flags from /api/auth/status. Assume auth is required until we hear
// otherwise, so we never flash an open app. Terminal stays hidden until the
// backend confirms it is on.
const authRequired = ref(true)
const authChecked = ref(false)
const terminalEnabled = ref(false)

export function getToken() {
  return token.value
}

export function setUiStatus(status = {}) {
  authRequired.value = status.auth_required !== false
  terminalEnabled.value = status.terminal_enabled === true
  authChecked.value = true
}

export function setToken(value) {
  token.value = String(value ?? '').trim()
  if (token.value) {
    sessionStorage.setItem(STORAGE_KEY, token.value)
  } else {
    sessionStorage.removeItem(STORAGE_KEY)
  }
}

export function clearToken() {
  setToken('')
}

export function useAuth() {
  return { token, authRequired, authChecked, terminalEnabled, setToken, clearToken }
}
