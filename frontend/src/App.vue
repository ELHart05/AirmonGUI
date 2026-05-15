<template>
  <div class="h-screen overflow-hidden flex bg-slate-950 font-sans relative scanlines">
    <div class="absolute inset-0 cyber-grid opacity-80 pointer-events-none"></div>
    <div class="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_rgba(0,217,255,0.08),_transparent_42%),radial-gradient(ellipse_at_bottom_right,_rgba(0,255,102,0.035),_transparent_36%)] pointer-events-none"></div>
    <!-- Mobile backdrop -->
    <Transition name="fade">
      <div
        v-if="sidebarOpen"
        @click="sidebarOpen = false"
        class="fixed inset-0 z-40 bg-black/60 lg:hidden"
      />
    </Transition>

    <!-- Sidebar wrapper (drawer on mobile, static on desktop) -->
    <div
      :class="[
        'h-full shrink-0 transition-transform duration-300 z-50',
        'fixed inset-y-0 left-0 lg:relative lg:translate-x-0',
        sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0',
      ]"
    >
      <AppSidebar />
    </div>

    <!-- Main content area -->
    <main class="relative z-10 flex-1 overflow-hidden min-w-0 flex flex-col">
      <!-- Mobile top bar -->
      <div class="lg:hidden flex items-center gap-3 px-4 h-12 border-b border-cyber-500/20 bg-black/80 backdrop-blur shrink-0">
        <button
          @click="sidebarOpen = true"
          class="p-1.5 rounded-lg text-cyber-300 hover:text-cyber-100 hover:bg-cyber-500/10 transition-colors"
        >
          <Menu class="w-5 h-5" />
        </button>
        <span class="text-sm font-mono font-bold text-cyber-100 tracking-wide text-glow">AirmonGUI</span>
      </div>

      <!-- View content — terminal fills height, other views scroll -->
      <div
        class="flex-1 min-h-0"
        :class="currentView === 'terminal' ? 'overflow-hidden' : 'overflow-y-auto'"
      >
        <component :is="currentComponent" />
      </div>
    </main>
  </div>
  <ToastContainer />
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { Menu } from 'lucide-vue-next'
import AppSidebar from './components/AppSidebar.vue'
import ToastContainer from './components/ToastContainer.vue'
import OverviewView from './views/OverviewView.vue'
import MonitorView from './views/MonitorView.vue'
import ScanView from './views/ScanView.vue'
import DeauthView from './views/DeauthView.vue'
import HandshakeView from './views/HandshakeView.vue'
import CrackView from './views/CrackView.vue'
import LogsView from './views/LogsView.vue'
import CapturesView from './views/CapturesView.vue'
import SignalView from './views/SignalView.vue'
import TerminalView from './views/TerminalView.vue'
import { useNav } from './composables/useNav.js'
import { useInterfaces } from './composables/useInterfaces.js'
import { useScan } from './composables/useScan.js'

const { currentView, sidebarOpen } = useNav()
const { refresh: refreshInterfaces } = useInterfaces()
const { loadJobs } = useScan()

const views = {
  overview: OverviewView,
  monitor: MonitorView,
  scan: ScanView,
  deauth: DeauthView,
  handshake: HandshakeView,
  crack: CrackView,
  captures: CapturesView,
  signal: SignalView,
  terminal: TerminalView,
  logs: LogsView,
}

const currentComponent = computed(() => views[currentView.value] ?? OverviewView)

onMounted(async () => {
  await refreshInterfaces()
  await loadJobs()
})
</script>

<style>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
