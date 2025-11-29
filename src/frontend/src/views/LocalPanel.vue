<template>
  <div class="local-panel">
    <div class="panel-header">
      <div class="folder-select">
        <button
          :class="{ active: !currentFolder }"
          @click="currentFolder = null"
        >All</button>
        <select v-if="folders.length" v-model="currentFolder">
          <option :value="null">All Folders</option>
          <option v-for="f in folders" :key="f" :value="f">{{ f }}</option>
        </select>
      </div>
    </div>

    <ImageGrid
      :images="images"
      :selected-ids="selectedIds"
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
        :disabled="selectedIds.size === 0 || uploading"
        @click="upload(false)"
      >
        Upload ({{ selectedIds.size }})
      </button>
      <button
        class="primary"
        :disabled="selectedIds.size === 0 || uploading"
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
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import ImageGrid from '../components/ImageGrid.vue'
import ActionBar from '../components/ActionBar.vue'
import CropSettings from '../components/CropSettings.vue'
import PreviewModal from '../components/PreviewModal.vue'

const emit = defineEmits(['uploaded', 'preview'])

const images = ref([])
const folders = ref([])
const currentFolder = ref(null)
const selectedIds = ref(new Set())
const loading = ref(false)
const uploading = ref(false)
const cropPercent = ref(0)
const mattePercent = ref(10)
const showPreview = ref(false)
const previewLoading = ref(false)
const previews = ref([])
const reframeEnabled = ref(false)
const reframeOffsets = ref({})  // path -> {x, y}

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
    selectedIds.value = new Set(images.value.map(i => i.path))
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

const uploadFromPreview = async () => {
  showPreview.value = false
  await upload(false)
}

const upload = async (display) => {
  if (selectedIds.value.size === 0) return

  uploading.value = true
  try {
    const res = await fetch('/api/tv/upload', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        paths: Array.from(selectedIds.value),
        crop_percent: cropPercent.value,
        matte_percent: mattePercent.value,
        display,
        reframe_enabled: reframeEnabled.value,
        reframe_offsets: reframeOffsets.value
      })
    })
    const data = await res.json()
    console.log('Upload results:', data)
    selectedIds.value = new Set()
    emit('uploaded')
  } catch (e) {
    console.error('Upload failed:', e)
  } finally {
    uploading.value = false
  }
}

watch(currentFolder, loadImages)

onMounted(() => {
  loadImages()
  loadFolders()
})
</script>

<style scoped>
.local-panel {
  display: contents; /* Let children participate in parent subgrid */
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  border-bottom: 1px solid #2a2a4e;
  background: #12121f;
}

.panel-header h2 {
  font-size: 1.1rem;
  margin: 0;
}

.folder-select {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.folder-select button {
  padding: 0.4rem 0.8rem;
  border-radius: 4px;
  border: 1px solid #3a3a5e;
  background: transparent;
  color: #aaa;
  cursor: pointer;
}

.folder-select button.active {
  background: #4a90d9;
  color: white;
  border-color: #4a90d9;
}

.folder-select select {
  padding: 0.4rem;
  border-radius: 4px;
  border: 1px solid #3a3a5e;
  background: #2a2a4e;
  color: white;
}
</style>
