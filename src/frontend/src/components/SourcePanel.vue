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

// Read initial tab from URL, default to 'met'
const getInitialTab = () => {
  const params = new URLSearchParams(window.location.search)
  const tab = params.get('tab')
  return tab === 'local' ? 'local' : 'met'
}

const activeTab = ref(getInitialTab())

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
