import { ref } from 'vue'

// The backend prints an API token on startup. The user pastes it once; we keep
// it in sessionStorage so it survives reloads but not a closed tab. Every API
// call sends it as the X-Auth-Token header.
const STORAGE_KEY = 'airmon_token'
const token = ref(sessionStorage.getItem(STORAGE_KEY) || '')

export function getToken() {
  return token.value
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
  return { token, setToken, clearToken }
}
