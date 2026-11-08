<template>
  <div class="tv-panel">
    <!-- Row 1: Tabs placeholder to align with source tabs -->
    <div class="tabs-placeholder">
      <span class="placeholder-text">&nbsp;</span>
    </div>

    <!-- Row 2: Panel header with slideshow controls -->
    <div class="panel-header">
      <div class="header-left">
        <h2>TV Artwork</h2>
        <!-- Slideshow controls inline (only visible when TV connected) -->
        <div v-if="connected" class="slideshow-inline">
          <label class="toggle-label">
            <input
              type="checkbox"
              v-model="slideshowEnabled"
              @change="updateSlideshow"
              :disabled="slideshowLoading"
            />
            <span>Slideshow</span>
          </label>
          <template v-if="slideshowEnabled">
            <select v-model="slideshowLabel" @change="updateSlideshow" :disabled="slideshowLoading" class="select" title="What the slideshow plays">
              <option :value="null">All artwork</option>
              <option v-for="name in labelNames" :key="name" :value="name">{{ name }} ({{ labelCounts[name] }})</option>
            </select>
            <select v-model.number="slideshowDuration" @change="updateSlideshow" :disabled="slideshowLoading" class="select" title="Time per image">
              <option v-for="d in durationOptions" :key="d" :value="d">{{ formatDuration(d) }}</option>
            </select>
            <label class="toggle-label">
              <input
                type="checkbox"
                v-model="slideshowShuffle"
                @change="updateSlideshow"
                :disabled="slideshowLoading"
              />
              <span>Shuffle</span>
            </label>
          </template>
        </div>
      </div>
      <div class="header-right">
        <select v-model="sortOrder" class="select" title="Sort">
          <option value="newest">Newest first</option>
          <option value="oldest">Oldest first</option>
        </select>
          <button class="btn btn-ghost btn-sm" @click="loadArtwork" :disabled="loading">
          Refresh
        </button>
      </div>
    </div>

    <!-- Row 3: Image grid -->
    <ImageGrid
      :images="visibleArtwork"
      :selected-ids="selectedIds"
      :current-id="currentId"
      :loading="loading"
      :is-local="false"
      @toggle="toggleSelection"
      @select-all="selectAll"
      @preview="(img) => $emit('preview', img, false)"
    >
      <template #header-actions>
        <div v-if="labelNames.length" class="chip-row" role="tablist" aria-label="Filter by label">
          <button class="chip" :class="{ active: labelFilter === null }" @click="labelFilter = null">All <span>{{ artwork.length }}</span></button>
          <button v-for="name in labelNames" :key="name" class="chip" :class="{ active: labelFilter === name }" @click="labelFilter = name">
            {{ name }} <span>{{ labelCounts[name] }}</span>
          </button>
          <button v-if="unlabelledCount" class="chip" :class="{ active: labelFilter === UNLABELLED }" @click="labelFilter = UNLABELLED">
            Unlabelled <span>{{ unlabelledCount }}</span>
          </button>
        </div>
      </template>
    </ImageGrid>

    <!-- Row 4: Action bar -->
    <ActionBar>
      <template #left>
        <span class="selected-count">{{ selectedIds.size }} selected</span>
      </template>
      <button
        class="secondary"
        :disabled="selectedIds.size === 0"
        @click="showLabelPicker = true"
      >
        Label
      </button>
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

    <LabelPicker
      v-if="showLabelPicker"
      :selected="artwork.filter(a => selectedIds.has(a.content_id))"
      :counts="labelCounts"
      @close="showLabelPicker = false"
      @apply="applyLabels"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, watch, computed } from 'vue'
import ImageGrid from '../components/ImageGrid.vue'
import ActionBar from '../components/ActionBar.vue'
import LabelPicker from '../components/LabelPicker.vue'

const emit = defineEmits(['preview'])

const artwork = ref([])
const currentId = ref(null)
const selectedIds = ref(new Set())
const loading = ref(false)
const deleting = ref(false)

let savedSort = 'newest'
try { savedSort = localStorage.getItem('tvSort') || 'newest' } catch {}
const sortOrder = ref(savedSort)
watch(sortOrder, v => { try { localStorage.setItem('tvSort', v) } catch {} })

// image_date is "YYYY:MM:DD HH:MM:SS", so it sorts correctly as a string
const sortedArtwork = computed(() => {
  const dir = sortOrder.value === 'oldest' ? 1 : -1
  return [...artwork.value].sort((a, b) =>
    dir * ((a.image_date || '').localeCompare(b.image_date || '') ||
           (a.content_id || '').localeCompare(b.content_id || '')))
})

// Labels
const UNLABELLED = '\u0000unlabelled'
const labelFilter = ref(null)
const showLabelPicker = ref(false)
const labelCounts = computed(() => {
  const counts = {}
  for (const a of artwork.value) for (const l of a.labels || []) counts[l] = (counts[l] || 0) + 1
  return counts
})
const labelNames = computed(() => Object.keys(labelCounts.value).sort((a, b) => a.localeCompare(b, undefined, { sensitivity: 'base' })))
const unlabelledCount = computed(() => artwork.value.filter(a => !(a.labels || []).length).length)
const visibleArtwork = computed(() => {
  if (labelFilter.value === null) return sortedArtwork.value
  if (labelFilter.value === UNLABELLED) return sortedArtwork.value.filter(a => !(a.labels || []).length)
  return sortedArtwork.value.filter(a => (a.labels || []).includes(labelFilter.value))
})
// A filter whose label no longer exists falls back to All
watch(labelNames, names => {
  if (labelFilter.value && labelFilter.value !== UNLABELLED && !names.includes(labelFilter.value)) labelFilter.value = null
})

const applyLabels = async ({ add, remove }) => {
  showLabelPicker.value = false
  const ids = Array.from(selectedIds.value)
  try {
    const res = await fetch('/api/tv/labels', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content_ids: ids, add, remove })
    })
    const data = await res.json()
    if (!res.ok) console.error('Label sync:', data.detail)
    // Update in place; re-listing the TV is slow
    const map = data.labels || {}
    artwork.value = artwork.value.map(a => ({ ...a, labels: map[a.content_id] || [] }))
  } catch (e) {
    console.error('Failed to save labels:', e)
  }
}

// Slideshow state
const connected = ref(false)
const slideshowEnabled = ref(false)
const slideshowDuration = ref(15)
const slideshowShuffle = ref(true)
const slideshowLoading = ref(false)
const slideshowLabel = ref(null)

// Minutes. The TV takes any value; keep one it reports (e.g. set on the TV itself) selectable.
const DURATIONS = [2, 3, 5, 10, 15, 30, 60]
const durationOptions = computed(() =>
  DURATIONS.includes(slideshowDuration.value)
    ? DURATIONS
    : [...DURATIONS, slideshowDuration.value].sort((a, b) => a - b))
const formatDuration = (m) => m % 1440 === 0 ? `${m / 1440} day` : m % 60 === 0 ? `${m / 60} hr` : `${m} min`

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
    // Lets the local panel mark files that are already on the TV
    window.dispatchEvent(new CustomEvent('tv-artwork-loaded', {
      detail: artwork.value.map(a => a.source_path).filter(Boolean)
    }))
    currentId.value = currentData.content_id || null
    selectedIds.value = new Set()

    // Check if TV is connected
    connected.value = true

    // Load slideshow status when we successfully connect
    await loadSlideshowStatus()
  } catch (e) {
    console.error('Failed to load TV artwork:', e)
    connected.value = false
  } finally {
    loading.value = false
  }
}

const loadSlideshowStatus = async () => {
  try {
    const res = await fetch('/api/tv/slideshow')
    const data = await res.json()
    if (!data.error) {
      // Parse the response - format varies by TV
      slideshowEnabled.value = data.value !== 'off' && data.value !== '0'
      // The TV reports the interval in minutes as `value` ("off" when stopped)
      const minutes = parseInt(data.value)
      if (minutes > 0) slideshowDuration.value = minutes
      slideshowLabel.value = data.label || null
      if (data.type !== undefined) {
        slideshowShuffle.value = data.type === true || String(data.type).startsWith('shuffle')
      }
    }
  } catch (e) {
    console.error('Failed to load slideshow status:', e)
  }
}

const updateSlideshow = async () => {
  slideshowLoading.value = true
  try {
    await fetch('/api/tv/slideshow', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        enabled: slideshowEnabled.value,
        duration: slideshowDuration.value,
        shuffle: slideshowShuffle.value,
        label: slideshowLabel.value
      })
    })
  } catch (e) {
    console.error('Failed to update slideshow:', e)
  } finally {
    slideshowLoading.value = false
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
    selectedIds.value = new Set(visibleArtwork.value.map(a => a.content_id))
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
  display: contents; /* Let children participate in parent subgrid */
}

/* Row 1: matches the source tabs' height on the left */
.tabs-placeholder {
  display: flex;
  padding: 8px 12px 0;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
}

.placeholder-text {
  padding: 10px 14px 12px;
  font-size: 0.875rem;
}

/* Row 2: Panel header */
.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border);
  background: var(--surface);
  gap: 12px;
  flex-wrap: wrap;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.panel-header h2 {
  font-size: 1rem;
  font-weight: 600;
  margin: 0;
}

.slideshow-inline {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.selected-count {
  color: var(--text-muted);
  font-size: 0.85rem;
}
</style>
