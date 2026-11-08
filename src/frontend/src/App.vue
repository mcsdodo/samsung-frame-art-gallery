<template>
  <div class="app">
    <header class="header">
      <div class="brand">
        <span class="brand-mark" aria-hidden="true"></span>
        <h1>Frame Art Gallery</h1>
      </div>
      <div class="header-right">
        <button class="tv-settings-btn" @click="openTvSettings" :title="tvStatus.connected ? 'TV settings' : 'TV not connected — open settings'">
          <span class="status-dot" :class="{ connected: tvStatus.connected }"></span>
          <span class="tv-name">{{ tvName || 'Connect TV' }}</span>
          <svg viewBox="0 0 20 20" aria-hidden="true"><rect x="2.5" y="4" width="15" height="10" rx="1.5" /><path d="M7 17h6" /></svg>
        </button>
      </div>
    </header>

    <!-- Mobile: Tabs -->
    <div class="mobile-tabs" v-if="isMobile">
      <button
        :class="{ active: activeTab === 'local' }"
        @click="activeTab = 'local'"
      >Images</button>
      <button
        :class="{ active: activeTab === 'tv' }"
        @click="activeTab = 'tv'"
      >TV</button>
    </div>

    <main class="main" :class="{ mobile: isMobile }">
      <!-- Desktop: Split view -->
      <template v-if="!isMobile">
        <SourcePanel class="panel" @uploaded="refreshTV" @preview="showPreview" />
        <div class="divider"></div>
        <TVPanel ref="tvPanel" class="panel" @preview="showPreview" />
      </template>

      <!-- Mobile: Tab content -->
      <template v-else>
        <SourcePanel v-show="activeTab === 'local'" class="panel" @uploaded="refreshTV" @preview="showPreview" />
        <TVPanel v-show="activeTab === 'tv'" ref="tvPanel" class="panel" @preview="showPreview" />
      </template>
    </main>

    <!-- Image Preview Modal -->
    <ImagePreview
      v-if="previewImage"
      :image="previewImage"
      :is-local="previewIsLocal"
      @close="previewImage = null"
    />

    <!-- TV Connection Modal -->
    <TvConnectionModal
      v-if="showTvModal"
      @close="showTvModal = false"
      @connected="handleTvConnected"
    />

    <UploadDock />

    <!-- Toast Notification -->
    <div v-if="toast.show" class="toast" :class="toast.type">
      {{ toast.message }}
      <button v-if="toast.type === 'error'" class="toast-action" @click="showTvModal = true">
        Settings
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import SourcePanel from './components/SourcePanel.vue'
import TVPanel from './views/TVPanel.vue'
import ImagePreview from './components/ImagePreview.vue'
import TvConnectionModal from './components/TvConnectionModal.vue'
import UploadDock from './components/UploadDock.vue'

const tvStatus = ref({ connected: false })
const isMobile = ref(false)
const activeTab = ref('local')
const tvPanel = ref(null)
const previewImage = ref(null)
const previewIsLocal = ref(true)
const showTvModal = ref(false)
const tvName = ref('')
const toast = ref({ show: false, message: '', type: 'info' })
const toastTimeout = ref(null)

const showToast = (message, type = 'info') => {
  // Clear any existing timeout to prevent memory leaks
  if (toastTimeout.value) {
    clearTimeout(toastTimeout.value)
  }
  toast.value = { show: true, message, type }
  toastTimeout.value = setTimeout(() => {
    toast.value.show = false
  }, 4000)
}

const showPreview = (image, isLocal) => {
  previewImage.value = image
  previewIsLocal.value = isLocal
}

const checkMobile = () => {
  isMobile.value = window.innerWidth < 768
}

const refreshTV = () => {
  tvPanel.value?.loadArtwork()
}

const handleTvConnected = (tv) => {
  showTvModal.value = false
  tvName.value = tv.name
  tvStatus.value = { connected: true }
  showToast(`Connected to ${tv.name}`, 'success')
  // Refresh TV panel
  tvPanel.value?.loadArtwork()
}

const openTvSettings = () => {
  showTvModal.value = true
}

onMounted(async () => {
  checkMobile()
  window.addEventListener('resize', checkMobile)
  window.addEventListener('tv-uploads-finished', refreshTV)

  try {
    const res = await fetch('/api/tv/settings')
    const settings = await res.json()

    if (!settings.configured) {
      showTvModal.value = true
    } else {
      tvName.value = settings.selected_tv_name || ''
      // Check actual connection status
      const statusRes = await fetch('/api/tv/status')
      tvStatus.value = await statusRes.json()
    }
  } catch (e) {
    console.error('Failed to get TV settings:', e)
    showTvModal.value = true
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', checkMobile)
  window.removeEventListener('tv-uploads-finished', refreshTV)
  if (toastTimeout.value) {
    clearTimeout(toastTimeout.value)
  }
})
</script>

<style scoped>
.app {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 56px;
  padding: 0 16px 0 20px;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
}

.brand-mark {
  width: 22px;
  height: 22px;
  border-radius: 6px;
  background: linear-gradient(135deg, #8b7bff 0%, #6e5df6 45%, #e0a85a 100%);
  box-shadow: inset 0 0 0 3px rgba(10, 11, 15, 0.55);
}

.header h1 {
  margin: 0;
  font-size: 1rem;
  font-weight: 650;
  letter-spacing: -0.01em;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.tv-settings-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  height: 34px;
  padding: 0 12px;
  border-radius: 999px;
  border: 1px solid var(--border-strong);
  background: var(--surface-2);
  color: var(--text);
  font-size: 0.82rem;
  font-weight: 550;
  cursor: pointer;
  transition: background 0.15s;
}

.tv-settings-btn:hover {
  background: var(--surface-3);
}

.tv-settings-btn svg {
  width: 16px;
  height: 16px;
  fill: none;
  stroke: var(--text-muted);
  stroke-width: 1.6;
  stroke-linecap: round;
}

.tv-name {
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tv-settings-btn .status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--danger);
  box-shadow: 0 0 0 3px var(--danger-soft);
}

.tv-settings-btn .status-dot.connected {
  background: var(--success);
  box-shadow: 0 0 0 3px var(--success-soft);
}

.mobile-tabs {
  display: flex;
  background: var(--surface-2);
  border-bottom: 1px solid var(--border);
}

.mobile-tabs button {
  flex: 1;
  padding: 0.75rem;
  border: none;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  font-size: 1rem;
}

.mobile-tabs button.active {
  color: white;
  border-bottom: 2px solid var(--accent);
}

.main {
  flex: 1;
  display: grid;
  grid-template-columns: 1fr 1px 1fr;
  grid-template-rows: auto auto 1fr auto; /* tabs, header, content, action bar */
  overflow: hidden;
  min-height: 0;
}

.main.mobile {
  display: flex;
  flex-direction: column;
}

.panel {
  display: grid;
  grid-template-rows: subgrid;
  grid-row: 1 / -1; /* Span all 4 rows */
  overflow: hidden;
  min-height: 0;
}

.main.mobile .panel {
  display: flex;
  flex-direction: column;
  flex: 1;
}

.divider {
  grid-row: 1 / -1; /* Span all rows */
  background: var(--border);
}

.toast {
  position: fixed;
  bottom: 2rem;
  left: 50%;
  transform: translateX(-50%);
  padding: 0.75rem 1.5rem;
  background: var(--surface-2);
  border: 1px solid var(--border-strong);
  box-shadow: var(--shadow-lg);
  color: var(--text);
  border-radius: var(--radius);
  display: flex;
  align-items: center;
  gap: 1rem;
  z-index: 1001;
  animation: slideUp 0.3s ease;
}

.toast.success {
  border-left: 3px solid var(--success);
}

.toast.error {
  border-left: 3px solid var(--danger);
}

.toast-action {
  background: rgba(255, 255, 255, 0.2);
  border: none;
  color: white;
  padding: 0.25rem 0.75rem;
  border-radius: 4px;
  cursor: pointer;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateX(-50%) translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateX(-50%) translateY(0);
  }
}
</style>
