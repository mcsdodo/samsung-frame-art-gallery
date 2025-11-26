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
import { ref } from 'vue'
import LocalPanel from '../views/LocalPanel.vue'
import MetPanel from '../views/MetPanel.vue'

defineEmits(['uploaded', 'preview'])

const tabs = [
  { id: 'local', label: 'Local' },
  { id: 'met', label: 'Met Museum' }
]

const activeTab = ref('local')
</script>

<style scoped>
.source-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  overflow: hidden;
}

.source-tabs {
  display: flex;
  background: #1a1a2e;
  border-bottom: 1px solid #2a2a4e;
  flex-shrink: 0;
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
