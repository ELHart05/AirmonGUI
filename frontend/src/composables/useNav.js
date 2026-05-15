import { ref } from 'vue'

// Singleton — current active view + mobile sidebar state
const currentView = ref('overview')
const sidebarOpen = ref(false)

export function useNav() {
  function navigate(view) {
    currentView.value = view
    sidebarOpen.value = false  // close mobile sidebar on navigation
  }
  return { currentView, navigate, sidebarOpen }
}
