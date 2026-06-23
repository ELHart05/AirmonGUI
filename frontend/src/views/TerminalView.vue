<template>
  <div class="h-full flex flex-col overflow-hidden animate-fade-in">
    <!-- Header bar -->
    <div class="shrink-0 flex items-center justify-between px-6 pt-5 pb-3 border-b border-cyber-500/20 bg-black/35">
      <div>
        <h2 class="page-title">Terminal</h2>
        <p class="page-subtitle">Integrated shell · full PTY · runs as the same user as the backend</p>
      </div>
      <div class="flex items-center gap-2">
        <span v-if="connected" class="flex items-center gap-1.5 badge-success">
          <span class="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse"></span>
          Connected
        </span>
        <span v-else-if="connecting" class="badge-neutral">Connecting…</span>
        <span v-else class="flex items-center gap-1.5 badge-error">Disconnected</span>
        <button v-if="!connected && !connecting" @click="connect" class="btn-primary btn-sm">
          Reconnect
        </button>
        <button v-if="connected" @click="disconnect" class="btn-ghost btn-sm">
          Disconnect
        </button>
      </div>
    </div>

    <!-- Terminal — fills remaining space -->
    <div class="flex-1 min-h-0 relative mx-4 my-3 rounded-lg overflow-hidden border border-cyber-500/25 shadow-2xl shadow-cyber-950/30">
      <div
        ref="terminalEl"
        class="absolute inset-0"
        style="background: #020807; padding: 8px;"
      />
    </div>

    <!-- Quick-command toolbar -->
    <div class="shrink-0 px-6 py-3 border-t border-cyber-500/20 bg-black/35 flex flex-wrap items-center gap-3">
      <span class="text-xs font-mono text-slate-500">Quick commands:</span>
      <button
        v-for="cmd in quickCmds"
        :key="cmd.label"
        @click="sendText(cmd.cmd)"
        :disabled="!connected"
        class="px-2 py-1 rounded text-xs font-mono border border-cyber-500/20 text-slate-400 hover:border-cyber-500/50 hover:text-cyber-100 hover:bg-cyber-500/10 transition-colors disabled:opacity-40"
      >{{ cmd.label }}</button>
    </div>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import { Terminal } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import '@xterm/xterm/css/xterm.css'
import { getToken } from '../composables/useAuth.js'

const terminalEl = ref(null)
const connected = ref(false)
const connecting = ref(false)

let term = null
let fitAddon = null
let socket = null
let resizeObserver = null

const quickCmds = [
  { label: 'airmon-ng', cmd: 'airmon-ng\n' },
  { label: 'iwconfig', cmd: 'iwconfig\n' },
  { label: 'iw dev', cmd: 'iw dev\n' },
  { label: 'ip link', cmd: 'ip link\n' },
  { label: 'ls captures', cmd: 'ls -lh /var/lib/airmongui/captures/\n' },
  { label: 'clear', cmd: 'clear\n' },
]

function buildTerm() {
  if (term) {
    term.dispose()
  }
  term = new Terminal({
    cursorBlink: true,
    fontSize: 13,
    fontFamily: '"JetBrains Mono", "Fira Code", "Cascadia Code", "Consolas", monospace',
    theme: {
      background: '#020807',
      foreground: '#d9ffe8',
      cursor: '#22d3ee',
      cursorAccent: '#020807',
      selectionBackground: '#0f3f2a',
      black: '#020807',
      red: '#ff7b72',
      green: '#00ff66',
      yellow: '#d29922',
      blue: '#22d3ee',
      magenta: '#bc8cff',
      cyan: '#22f3ff',
      white: '#b6ffd2',
      brightBlack: '#6e7681',
      brightRed: '#ffa198',
      brightGreen: '#7dffad',
      brightYellow: '#e3b341',
      brightBlue: '#67e8f9',
      brightMagenta: '#d2a8ff',
      brightCyan: '#9afaff',
      brightWhite: '#effff5',
    },
    scrollback: 5000,
    allowTransparency: false,
  })

  fitAddon = new FitAddon()
  term.loadAddon(fitAddon)
  term.open(terminalEl.value)
  // Fit only once the panel has its real width. A single tick can run before the
  // flex layout settles, leaving xterm sized to a fraction of the width (the
  // half-width bug); a double rAF waits for an actual paint. The ResizeObserver
  // re-fits on any later size change.
  requestAnimationFrame(() => requestAnimationFrame(fitTerm))

  term.onData((data) => {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(new TextEncoder().encode(data))
    }
  })
}

function fitTerm() {
  if (!fitAddon || !term || !terminalEl.value) return
  try {
    fitAddon.fit()
  } catch {
    /* element not measurable yet; the ResizeObserver will retry */
  }
  sendResize()
}

function sendResize() {
  if (socket && socket.readyState === WebSocket.OPEN && term) {
    socket.send(JSON.stringify({ type: 'resize', cols: term.cols, rows: term.rows }))
  }
}

function sendText(text) {
  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(new TextEncoder().encode(text))
  }
}

function connect() {
  if (connecting.value || connected.value) return
  connecting.value = true

  buildTerm()

  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = `${proto}//${window.location.host}/ws/terminal`

  // The browser cannot set headers on a WebSocket, so the token rides as a second
  // subprotocol value when there is one. With auth off there is no token, and an
  // empty subprotocol string is illegal (it throws), so send only the name.
  const authToken = getToken()
  const protocols = authToken ? ['airmon-terminal', authToken] : ['airmon-terminal']
  socket = new WebSocket(wsUrl, protocols)
  socket.binaryType = 'arraybuffer'

  socket.onopen = () => {
    connecting.value = false
    connected.value = true
    sendResize()
    term.focus()
  }

  socket.onmessage = (e) => {
    if (!term) return
    if (e.data instanceof ArrayBuffer) {
      term.write(new Uint8Array(e.data))
    } else {
      term.write(e.data)
    }
  }

  socket.onclose = () => {
    connecting.value = false
    connected.value = false
    if (term) {
      term.write('\r\n\x1b[33m[Connection closed. Click Reconnect to start a new session.]\x1b[0m\r\n')
    }
  }

  socket.onerror = () => {
    connecting.value = false
    connected.value = false
    if (term) {
      term.write('\r\n\x1b[31m[WebSocket error. Ensure the backend is running on port 8000.]\x1b[0m\r\n')
    }
  }
}

function disconnect() {
  socket?.close()
}

onMounted(() => {
  // connect() builds the terminal; building here too would dispose and rebuild it.
  connect()

  resizeObserver = new ResizeObserver(() => fitTerm())
  resizeObserver.observe(terminalEl.value)
})

onUnmounted(() => {
  resizeObserver?.disconnect()
  socket?.close()
  term?.dispose()
})
</script>
