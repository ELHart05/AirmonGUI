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

    <!-- Warning banner -->
    <div class="shrink-0 mx-4 mt-3 rounded-lg border border-amber-600/30 bg-amber-950/30 px-4 py-2.5 text-xs text-amber-300 flex items-start gap-2">
      <span class="shrink-0 mt-0.5">&#9888;</span>
      <span>
        This terminal opens a shell with the same privileges as the backend process.
        <template v-if="authRequired">
          It is gated by your API token — the same one that unlocks the app — and by the allowed Origin.
        </template>
        <template v-else>
          Auth is off, so it is gated by the allowed Origin alone and refuses to open as root unless you set <code>AIRMON_GUI_ALLOW_TERMINAL_AS_ROOT=1</code>.
        </template>
        Turn it off with <code>AIRMON_GUI_TERMINAL_ENABLED=0</code>. Use only on trusted machines.
      </span>
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
import { onMounted, onUnmounted, nextTick, ref } from 'vue'
import { Terminal } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import '@xterm/xterm/css/xterm.css'
import { getToken, useAuth } from '../composables/useAuth.js'

const { authRequired } = useAuth()
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
  // Defer fit until after the browser has measured the flex layout
  nextTick(() => fitAddon.fit())

  term.onData((data) => {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(new TextEncoder().encode(data))
    }
  })
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

  // The browser cannot set headers on a WebSocket, so the token rides as a
  // second subprotocol value. The server reads it before accepting the socket.
  socket = new WebSocket(wsUrl, ['airmon-terminal', getToken()])
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
  buildTerm()
  connect()

  resizeObserver = new ResizeObserver(() => {
    fitAddon?.fit()
    sendResize()
  })
  resizeObserver.observe(terminalEl.value)
})

onUnmounted(() => {
  resizeObserver?.disconnect()
  socket?.close()
  term?.dispose()
})
</script>
