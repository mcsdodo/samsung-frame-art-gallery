<template>
  <div class="app">
    <header class="header">
      <h1>Samsung Frame Art Gallery</h1>
      <div class="header-right">
        <button class="tv-settings-btn" @click="openTvSettings" :title="tvName || 'TV Settings'">
          <span class="tv-icon">📺</span>
          <span class="status-dot" :class="{ connected: tvStatus.connected }"></span>
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
  padding: 1rem 2rem;
  background: #1a1a2e;
  color: white;
}

.header h1 {
  margin: 0;
  font-size: 1.5rem;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.tv-settings-btn {
  position: relative;
  background: none;
  border: none;
  cursor: pointer;
  padding: 0.5rem;
  border-radius: 8px;
  transition: background 0.2s;
}

.tv-settings-btn:hover {
  background: rgba(255, 255, 255, 0.1);
}

.tv-icon {
  font-size: 1.5rem;
}

.tv-settings-btn .status-dot {
  position: absolute;
  bottom: 4px;
  right: 4px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #ff4444;
}

.tv-settings-btn .status-dot.connected {
  background: #44ff44;
}

.mobile-tabs {
  display: flex;
  background: #1a1a2e;
  border-bottom: 1px solid #2a2a4e;
}

.mobile-tabs button {
  flex: 1;
  padding: 0.75rem;
  border: none;
  background: transparent;
  color: #888;
  cursor: pointer;
  font-size: 1rem;
}

.mobile-tabs button.active {
  color: white;
  border-bottom: 2px solid #4a90d9;
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
  background: #2a2a4e;
}

.toast {
  position: fixed;
  bottom: 2rem;
  left: 50%;
  transform: translateX(-50%);
  padding: 0.75rem 1.5rem;
  background: #2a2a4e;
  color: white;
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 1rem;
  z-index: 1001;
  animation: slideUp 0.3s ease;
}

.toast.success {
  background: #2d5a3d;
}

.toast.error {
  background: #5a2d2d;
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
