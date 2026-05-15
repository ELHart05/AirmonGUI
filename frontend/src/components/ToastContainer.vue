<template>
  <Teleport to="body">
    <div class="fixed bottom-5 right-5 z-50 flex flex-col gap-2 w-80 pointer-events-none">
      <TransitionGroup name="toast">
        <div
          v-for="toast in toasts"
          :key="toast.id"
          :class="[
            'flex items-start gap-3 px-4 py-3 rounded-lg border shadow-2xl text-sm font-medium pointer-events-auto backdrop-blur',
            toast.type === 'success' && 'bg-success-950/90 border-success-500/50 text-success-300',
            toast.type === 'error' && 'bg-red-950 border-red-700/50 text-red-300',
            toast.type === 'warning' && 'bg-amber-950 border-amber-700/50 text-amber-300',
            toast.type === 'info' && 'bg-black/90 border-cyber-500/30 text-slate-200',
          ]"
        >
          <span class="text-base leading-none mt-0.5 shrink-0">
            {{ icons[toast.type] }}
          </span>
          <span class="flex-1 leading-snug">{{ toast.message }}</span>
          <button
            @click="dismiss(toast.id)"
            class="text-current opacity-40 hover:opacity-100 transition-opacity shrink-0 leading-none text-lg"
          >
            ×
          </button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<script setup>
import { useToast } from '../composables/useToast.js'

const { toasts, dismiss } = useToast()
const icons = { success: '✓', error: '✗', warning: '⚠', info: 'ℹ' }
</script>

<style scoped>
.toast-enter-active,
.toast-leave-active {
  transition: all 0.25s ease;
}
.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateX(110%);
}
</style>
