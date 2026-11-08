<template>
  <div class="local-panel">
    <div class="panel-header">
      <div class="folder-select">
        <button
          class="chip"
          :class="{ active: !currentFolder }"
          @click="currentFolder = null"
        >All</button>
        <select v-if="folders.length" v-model="currentFolder" class="select">
          <option :value="null">All Folders</option>
          <option v-for="f in folders" :key="f" :value="f">{{ f }}</option>
        </select>
      </div>
      <div class="sort-controls">
        <label class="toggle-label">
          <input type="checkbox" v-model="hideOnTv" />
          <span>Hide on TV ({{ onTvCount }})</span>
        </label>
        <select v-model="sortOrder" class="select" title="Sort">
          <option value="newest">Newest first</option>
          <option value="oldest">Oldest first</option>
          <option value="name">Name</option>
        </select>
      </div>
    </div>

    <ImageGrid
      :images="sortedImages"
      :selected-ids="selectedIds"
      :on-tv-paths="onTvPaths"
      :loading="loading"
      :is-local="true"
      @toggle="toggleSelection"
      @select-all="selectAll"
      @preview="(img) => $emit('preview', img, true)"
    />

    <ActionBar>
      <template #left>
        <CropSettings
          :has-selection="selectedIds.size > 0"
          @change="setSettings"
          @preview="loadPreviews"
        />
      </template>
      <button
        class="secondary"
        :disabled="selectedIds.size === 0"
        @click="showCollectionPicker = true"
      >
        + Collection
      </button>
      <button
        class="secondary"
        :disabled="selectedIds.size === 0"
        @click="upload(false)"
      >
        Upload ({{ selectedIds.size }})
      </button>
      <button
        class="primary"
        :disabled="selectedIds.size === 0"
        @click="upload(true)"
      >
        Upload & Display
      </button>
    </ActionBar>

    <PreviewModal
      v-if="showPreview"
      :previews="previews"
      :crop-percent="cropPercent"
      :matte-percent="mattePercent"
      :loading="previewLoading"
      :reframe-enabled="reframeEnabled"
      :selected-paths="Array.from(selectedIds)"
      @close="showPreview = false"
      @upload="uploadFromPreview"
      @offset-change="fetchPreviewWithOffset"
    />

    <CollectionPicker
      v-if="showCollectionPicker"
      :items="selectedItemsForCollection"
      @close="showCollectionPicker = false"
      @added="onAddedToCollection"
    />
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted, computed } from 'vue'
import ImageGrid from '../components/ImageGrid.vue'
import ActionBar from '../components/ActionBar.vue'
import CropSettings from '../components/CropSettings.vue'
import PreviewModal from '../components/PreviewModal.vue'
import CollectionPicker from '../components/CollectionPicker.vue'
import { enqueue } from '../stores/uploadQueue.js'

const emit = defineEmits(['uploaded', 'preview'])

const images = ref([])
const folders = ref([])
const currentFolder = ref(null)
const selectedIds = ref(new Set())
const loading = ref(false)
const cropPercent = ref(0)
const mattePercent = ref(10)
const showPreview = ref(false)
const previewLoading = ref(false)
const previews = ref([])
const reframeEnabled = ref(false)
const reframeOffsets = ref({})  // path -> {x, y}
const showCollectionPicker = ref(false)
const onTvPaths = ref(new Set())

const readPref = (key, fallback) => {
  try { return localStorage.getItem(key) || fallback } catch { return fallback }
}
const sortOrder = ref(readPref('localSort', 'newest'))
const hideOnTv = ref(readPref('localHideOnTv', '') === '1')
watch(sortOrder, v => { try { localStorage.setItem('localSort', v) } catch {} })
watch(hideOnTv, v => { try { localStorage.setItem('localHideOnTv', v ? '1' : '') } catch {} })

const onTvCount = computed(() => images.value.filter(i => onTvPaths.value.has(i.path)).length)

const sortedImages = computed(() => {
  const list = hideOnTv.value
    ? images.value.filter(i => !onTvPaths.value.has(i.path))
    : [...images.value]
  if (sortOrder.value === 'name') {
    return list.sort((a, b) => a.name.localeCompare(b.name, undefined, { sensitivity: 'base' }))
  }
  const dir = sortOrder.value === 'oldest' ? 1 : -1
  return list.sort((a, b) => dir * ((a.mtime || 0) - (b.mtime || 0)))
})

const onTvArtwork = (e) => { onTvPaths.value = new Set(e.detail) }

const selectedItemsForCollection = computed(() => {
  return Array.from(selectedIds.value).map(path => ({
    type: 'local',
    path
  }))
})

const loadImages = async () => {
  loading.value = true
  try {
    const url = currentFolder.value
      ? `/api/images?folder=${encodeURIComponent(currentFolder.value)}`
      : '/api/images'
    const res = await fetch(url)
    const data = await res.json()
    images.value = data.images || []
    selectedIds.value = new Set()
  } catch (e) {
    console.error('Failed to load images:', e)
  } finally {
    loading.value = false
  }
}

const loadFolders = async () => {
  try {
    const res = await fetch('/api/images/folders')
    const data = await res.json()
    folders.value = data.folders || []
  } catch (e) {
    console.error('Failed to load folders:', e)
  }
}

const toggleSelection = (image) => {
  const newSet = new Set(selectedIds.value)
  if (newSet.has(image.path)) {
    newSet.delete(image.path)
  } else {
    newSet.add(image.path)
  }
  selectedIds.value = newSet
}

const selectAll = (checked) => {
  if (checked) {
    selectedIds.value = new Set(sortedImages.value.map(i => i.path))
  } else {
    selectedIds.value = new Set()
  }
}

const setSettings = (settings) => {
  cropPercent.value = settings.crop
  mattePercent.value = settings.matte
  reframeEnabled.value = settings.reframe || false
}

const loadPreviews = async () => {
  if (selectedIds.value.size === 0) return

  showPreview.value = true
  previewLoading.value = false  // Don't show loading initially for reframe
  previews.value = []

  // Reset offsets when opening preview
  reframeOffsets.value = {}

  // For reframe mode with single image, we don't fetch preview immediately
  // The PreviewModal handles initial display and offset updates
  if (reframeEnabled.value && selectedIds.value.size === 1) {
    previewLoading.value = false
    return
  }

  previewLoading.value = true

  try {
    const res = await fetch('/api/tv/preview', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        paths: Array.from(selectedIds.value),
        crop_percent: cropPercent.value,
        matte_percent: mattePercent.value,
        reframe_enabled: reframeEnabled.value,
        reframe_offsets: reframeOffsets.value
      })
    })
    const data = await res.json()
    previews.value = data.previews || []
  } catch (e) {
    console.error('Preview failed:', e)
  } finally {
    previewLoading.value = false
  }
}

const fetchPreviewWithOffset = async (path, offsetX, offsetY) => {
  // Update stored offset
  reframeOffsets.value = {
    ...reframeOffsets.value,
    [path]: { x: offsetX, y: offsetY }
  }

  try {
    const res = await fetch('/api/tv/preview', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        paths: [path],
        crop_percent: cropPercent.value,
        matte_percent: mattePercent.value,
        reframe_enabled: true,
        reframe_offsets: { [path]: { x: offsetX, y: offsetY } }
      })
    })
    const data = await res.json()
    if (data.previews && data.previews.length > 0) {
      previews.value = data.previews
    }
  } catch (e) {
    console.error('Preview update failed:', e)
  }
}

const uploadFromPreview = () => {
  showPreview.value = false
  upload(false)
}

// Uploads run in the background queue (see stores/uploadQueue.js); the dock shows progress.
const upload = (display) => {
  if (selectedIds.value.size === 0) return
  const names = new Map(images.value.map(i => [i.path, i.name]))
  // In on-screen order; selected images hidden by a filter still go, at the end
  const order = new Map(sortedImages.value.map((i, k) => [i.path, k]))
  const paths = [...selectedIds.value].sort((a, b) => (order.get(a) ?? Infinity) - (order.get(b) ?? Infinity))
  enqueue(paths.map(path => ({
    name: names.get(path) || path,
    thumb: `/api/images/${encodeURIComponent(path)}/thumbnail?size=120`,
    endpoint: '/api/tv/upload',
    body: {
      paths: [path],
      crop_percent: cropPercent.value,
      matte_percent: mattePercent.value,
      reframe_enabled: reframeEnabled.value,
      reframe_offsets: reframeOffsets.value[path] ? { [path]: reframeOffsets.value[path] } : {}
    }
  })), { display })
  selectedIds.value = new Set()
}

const onAddedToCollection = (collection) => {
  console.log(`Added ${selectedIds.value.size} items to collection: ${collection.name}`)
  // Optionally clear selection after adding
  // selectedIds.value = new Set()
}

watch(currentFolder, loadImages)

onMounted(() => {
  loadImages()
  loadFolders()
})

window.addEventListener('tv-artwork-loaded', onTvArtwork)
onUnmounted(() => window.removeEventListener('tv-artwork-loaded', onTvArtwork))
</script>

<style scoped>
.local-panel {
  display: contents; /* Let children participate in parent subgrid */
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border);
  background: var(--surface);
}

.folder-select,
.sort-controls {
  display: flex;
  gap: 10px;
  align-items: center;
}
</style>
