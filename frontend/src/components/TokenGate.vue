<template>
  <div class="h-screen w-screen flex items-center justify-center bg-slate-950 px-4">
    <div class="w-full max-w-md card">
      <div class="card-header">
        <h2 class="card-title">Unlock AirmonGUI</h2>
      </div>
      <p class="text-sm text-slate-400 mb-4">
        The backend prints an API token to its console on startup. Paste it here to connect.
        If you set <code class="text-cyber-300">AIRMON_GUI_AUTH_TOKEN</code>, use that value.
      </p>

      <form @submit.prevent="submit" class="space-y-3">
        <div>
          <label class="field-label">API token</label>
          <input
            v-model="value"
            type="password"
            autocomplete="off"
            autofocus
            class="field-input font-mono"
            placeholder="paste token"
          />
        </div>

        <p v-if="error" class="text-xs text-red-400">{{ error }}</p>

        <button type="submit" :disabled="busy || !value.trim()" class="btn-primary w-full">
          <span v-if="busy" class="inline-block w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin mr-1"></span>
          {{ busy ? 'Checking…' : 'Connect' }}
        </button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { api } from '../api/index.js'
import { setToken } from '../composables/useAuth.js'

const value = ref('')
const busy = ref(false)
const error = ref('')

async function submit() {
  if (busy.value || !value.value.trim()) return
  busy.value = true
  error.value = ''
  // Store the token first so the verify call carries it, then check it.
  setToken(value.value)
  try {
    await api.verify()
    // Token is valid; useAuth.token is now set and App swaps in the app shell.
  } catch (err) {
    // request() already cleared the bad token on a 401.
    error.value = err.message === 'HTTP 401' || /token/i.test(err.message)
      ? 'That token was rejected. Check the backend console and try again.'
      : `Could not reach the backend: ${err.message}`
  } finally {
    busy.value = false
  }
}
</script>
