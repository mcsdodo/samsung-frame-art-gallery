<template>
  <div class="tv-panel">
    <div class="panel-header">
      <h2>TV Artwork</h2>
      <button class="refresh-btn" @click="loadArtwork" :disabled="loading">
        Refresh
      </button>
    </div>

    <ImageGrid
      :images="artwork"
      :selected-ids="selectedIds"
      :current-id="currentId"
      :loading="loading"
      :is-local="false"
      @toggle="toggleSelection"
      @select-all="selectAll"
    />

    <ActionBar>
      <template #left>
        <span class="selected-count">{{ selectedIds.size }} selected</span>
      </template>
      <button
        class="secondary"
        :disabled="selectedIds.size !== 1"
        @click="setAsCurrent"
      >
        Display
      </button>
      <button
        class="danger"
        :disabled="selectedIds.size === 0 || deleting"
        @click="deleteSelected"
      >
        Delete ({{ selectedIds.size }})
      </button>
    </ActionBar>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import ImageGrid from '../components/ImageGrid.vue'
import ActionBar from '../components/ActionBar.vue'

const artwork = ref([])
const currentId = ref(null)
const selectedIds = ref(new Set())
const loading = ref(false)
const deleting = ref(false)

const loadArtwork = async () => {
  loading.value = true
  try {
    const [artRes, currentRes] = await Promise.all([
      fetch('/api/tv/artwork'),
      fetch('/api/tv/artwork/current')
    ])
    const artData = await artRes.json()
    const currentData = await currentRes.json()

    artwork.value = artData.artwork || []
    currentId.value = currentData.content_id || null
    selectedIds.value = new Set()
  } catch (e) {
    console.error('Failed to load TV artwork:', e)
  } finally {
    loading.value = false
  }
}

const toggleSelection = (image) => {
  const newSet = new Set(selectedIds.value)
  if (newSet.has(image.content_id)) {
    newSet.delete(image.content_id)
  } else {
    newSet.add(image.content_id)
  }
  selectedIds.value = newSet
}

const selectAll = (checked) => {
  if (checked) {
    selectedIds.value = new Set(artwork.value.map(a => a.content_id))
  } else {
    selectedIds.value = new Set()
  }
}

const setAsCurrent = async () => {
  const contentId = Array.from(selectedIds.value)[0]
  if (!contentId) return

  try {
    await fetch('/api/tv/artwork/current', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content_id: contentId })
    })
    currentId.value = contentId
    selectedIds.value = new Set()
  } catch (e) {
    console.error('Failed to set current artwork:', e)
  }
}

const deleteSelected = async () => {
  if (selectedIds.value.size === 0) return

  deleting.value = true
  try {
    for (const contentId of selectedIds.value) {
      await fetch(`/api/tv/artwork/${contentId}`, { method: 'DELETE' })
    }
    await loadArtwork()
  } catch (e) {
    console.error('Failed to delete artwork:', e)
  } finally {
    deleting.value = false
  }
}

onMounted(loadArtwork)

defineExpose({ loadArtwork })
</script>

<style scoped>
.tv-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #12121f;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  border-bottom: 1px solid #2a2a4e;
}

.panel-header h2 {
  font-size: 1.1rem;
  margin: 0;
}

.refresh-btn {
  padding: 0.4rem 0.8rem;
  border-radius: 4px;
  border: 1px solid #3a3a5e;
  background: transparent;
  color: #aaa;
  cursor: pointer;
}

.refresh-btn:hover:not(:disabled) {
  background: #2a2a4e;
}

.selected-count {
  color: #888;
  font-size: 0.9rem;
}
</style>
