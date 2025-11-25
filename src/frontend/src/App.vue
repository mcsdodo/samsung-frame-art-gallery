<template>
  <div class="app">
    <header class="header">
      <h1>Samsung Frame Art Gallery</h1>
      <div class="status" :class="{ connected: tvStatus.connected }">
        <span class="status-dot"></span>
        {{ tvStatus.connected ? 'Connected' : 'Disconnected' }}
      </div>
    </header>

    <!-- Mobile: Tabs -->
    <div class="mobile-tabs" v-if="isMobile">
      <button
        :class="{ active: activeTab === 'local' }"
        @click="activeTab = 'local'"
      >Local</button>
      <button
        :class="{ active: activeTab === 'tv' }"
        @click="activeTab = 'tv'"
      >TV</button>
    </div>

    <main class="main" :class="{ mobile: isMobile }">
      <!-- Desktop: Split view -->
      <template v-if="!isMobile">
        <LocalPanel class="panel" @uploaded="refreshTV" />
        <div class="divider"></div>
        <TVPanel ref="tvPanel" class="panel" />
      </template>

      <!-- Mobile: Tab content -->
      <template v-else>
        <LocalPanel v-show="activeTab === 'local'" class="panel" @uploaded="refreshTV" />
        <TVPanel v-show="activeTab === 'tv'" ref="tvPanel" class="panel" />
      </template>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import LocalPanel from './views/LocalPanel.vue'
import TVPanel from './views/TVPanel.vue'

const tvStatus = ref({ connected: false })
const isMobile = ref(false)
const activeTab = ref('local')
const tvPanel = ref(null)

const checkMobile = () => {
  isMobile.value = window.innerWidth < 768
}

const refreshTV = () => {
  tvPanel.value?.loadArtwork()
}

onMounted(async () => {
  checkMobile()
  window.addEventListener('resize', checkMobile)

  try {
    const res = await fetch('/api/tv/status')
    tvStatus.value = await res.json()
  } catch (e) {
    console.error('Failed to get TV status:', e)
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', checkMobile)
})
</script>

<style scoped>
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

.status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.9rem;
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #ff4444;
}

.status.connected .status-dot {
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
  display: flex;
  overflow: hidden;
}

.main.mobile {
  flex-direction: column;
}

.panel {
  flex: 1;
  overflow: hidden;
}

.divider {
  width: 1px;
  background: #2a2a4e;
}
</style>
