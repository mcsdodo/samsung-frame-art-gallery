<template>
  <div class="source-panel">
    <div class="source-tabs">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        :class="{ active: activeTab === tab.id }"
        @click="activeTab = tab.id"
      >
        {{ tab.label }}
      </button>
    </div>

    <LocalPanel
      v-show="activeTab === 'local'"
      @uploaded="$emit('uploaded')"
      @preview="(img) => $emit('preview', img, true)"
    />

    <MetPanel
      v-show="activeTab === 'met'"
      @uploaded="$emit('uploaded')"
      @preview="(img) => $emit('preview', img, false)"
    />
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import LocalPanel from '../views/LocalPanel.vue'
import MetPanel from '../views/MetPanel.vue'

defineEmits(['uploaded', 'preview'])

const tabs = [
  { id: 'local', label: 'Local Images' },
  { id: 'met', label: 'Metropolitan Museum of Art' }
]

// Read tab from URL if specified
const getUrlTab = () => {
  const params = new URLSearchParams(window.location.search)
  return params.get('tab')
}

// Start with 'local', will switch to 'met' if no local images
const activeTab = ref(getUrlTab() || 'local')

// Check for local images and switch to Met if none exist
onMounted(async () => {
  // Only auto-switch if no tab specified in URL
  if (!getUrlTab()) {
    try {
      const res = await fetch('/api/images')
      const data = await res.json()
      if (!data.images || data.images.length === 0) {
        activeTab.value = 'met'
      }
    } catch (e) {
      // If fetch fails, stay on local tab
    }
  }
})

// Update URL when tab changes
watch(activeTab, (newTab) => {
  const params = new URLSearchParams(window.location.search)
  params.set('tab', newTab)
  const newUrl = `${window.location.pathname}?${params.toString()}`
  window.history.replaceState({}, '', newUrl)
})
</script>

<style scoped>
.source-panel {
  display: contents; /* Let children participate in parent subgrid */
}

.source-tabs {
  display: flex;
  background: #1a1a2e;
  border-bottom: 1px solid #2a2a4e;
}

.source-tabs button {
  flex: 1;
  padding: 0.75rem;
  border: none;
  background: transparent;
  color: #888;
  cursor: pointer;
  font-size: 0.9rem;
  transition: all 0.2s;
}

.source-tabs button:hover {
  color: #aaa;
}

.source-tabs button.active {
  color: white;
  border-bottom: 2px solid #4a90d9;
}
</style>
