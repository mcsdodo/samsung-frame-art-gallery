<template>
  <div class="source-panel">
    <div class="source-tabs" :class="{ 'collections-active': activeTab === 'collections' }">
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

    <CollectionsPanel
      ref="collectionsPanel"
      v-show="activeTab === 'collections'"
      @uploaded="$emit('uploaded')"
      @preview="(img, isLocal) => $emit('preview', img, isLocal)"
    />
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import LocalPanel from '../views/LocalPanel.vue'
import MetPanel from '../views/MetPanel.vue'
import CollectionsPanel from '../views/CollectionsPanel.vue'

defineEmits(['uploaded', 'preview'])

const collectionsPanel = ref(null)

const tabs = [
  { id: 'local', label: 'Local Images' },
  { id: 'met', label: 'Met Museum' },
  { id: 'collections', label: 'Collections' }
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

// Update URL when tab changes and refresh data
watch(activeTab, (newTab) => {
  const params = new URLSearchParams(window.location.search)
  params.set('tab', newTab)
  const newUrl = `${window.location.pathname}?${params.toString()}`
  window.history.replaceState({}, '', newUrl)

  // Refresh collections when switching to collections tab
  if (newTab === 'collections' && collectionsPanel.value) {
    collectionsPanel.value.loadCollections()
  }
})
</script>

<style scoped>
.source-panel {
  display: contents; /* Let children participate in parent subgrid */
}

.source-tabs {
  display: flex;
  gap: 4px;
  padding: 8px 12px 0;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
}

.source-tabs button {
  position: relative;
  padding: 10px 14px 12px;
  border: none;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  font-size: 0.875rem;
  font-weight: 550;
  border-radius: var(--radius-sm) var(--radius-sm) 0 0;
  transition: color 0.15s, background 0.15s;
}

.source-tabs button:hover {
  color: var(--text);
  background: var(--surface-2);
}

.source-tabs button.active {
  color: var(--text);
}

.source-tabs button.active::after {
  content: '';
  position: absolute;
  left: 10px;
  right: 10px;
  bottom: -1px;
  height: 2px;
  border-radius: 2px;
  background: var(--accent);
}

/* When Collections tab is active, add left padding to align with sidebar */
.source-tabs.collections-active {
  padding-left: 200px; /* Match sidebar width */
}
</style>
