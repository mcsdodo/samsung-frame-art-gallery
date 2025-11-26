<template>
  <div class="met-panel">
    <div class="panel-header">
      <h2>Metropolitan Museum of Art</h2>
      <div class="department-select">
        <select v-model="selectedDepartment" @change="loadArtwork()">
          <option :value="null">Highlights</option>
          <option
            v-for="dept in departments"
            :key="dept.departmentId"
            :value="dept.departmentId"
          >
            {{ dept.displayName }}
          </option>
        </select>
      </div>
    </div>

    <ImageGrid
      :images="artwork"
      :selected-ids="selectedIds"
      :loading="loading"
      :loading-more="loadingMore"
      :is-local="false"
      :has-more-external="hasMore"
      :total-count="totalCount"
      @toggle="toggleSelection"
      @select-all="selectAll"
      @preview="(img) => $emit('preview', img)"
      @load-more="loadMore"
    />

    <ActionBar>
      <template #left>
        <MatteSelector @change="matte = $event" />
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

    <ResolutionWarning
      v-if="showResolutionWarning"
      :images="lowResImages"
      @confirm="confirmUpload"
      @cancel="showResolutionWarning = false"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import ImageGrid from '../components/ImageGrid.vue'
import ActionBar from '../components/ActionBar.vue'
import MatteSelector from '../components/MatteSelector.vue'
import ResolutionWarning from '../components/ResolutionWarning.vue'

const emit = defineEmits(['uploaded', 'preview'])

const departments = ref([])
const selectedDepartment = ref(null)
const artwork = ref([])
const selectedIds = ref(new Set())
const loading = ref(false)
const loadingMore = ref(false)
const uploading = ref(false)
const matte = ref({ style: 'none', color: 'neutral' })
const currentPage = ref(1)
const hasMore = ref(false)
const totalCount = ref(0)

const showResolutionWarning = ref(false)
const pendingUpload = ref({ display: false })

// TV resolution threshold
const TV_WIDTH = 3840
const TV_HEIGHT = 2160

const lowResImages = computed(() => {
  return artwork.value.filter(img =>
    selectedIds.value.has(img.object_id) &&
    (img.width < TV_WIDTH || img.height < TV_HEIGHT)
  )
})

const loadDepartments = async () => {
  try {
    const res = await fetch('/api/met/departments')
    const data = await res.json()
    departments.value = data.departments || []
  } catch (e) {
    console.error('Failed to load departments:', e)
  }
}

const loadArtwork = async (append = false) => {
  if (!append) {
    currentPage.value = 1
    artwork.value = []
    totalCount.value = 0
  }

  if (append) {
    loadingMore.value = true
  } else {
    loading.value = true
  }

  try {
    const endpoint = selectedDepartment.value
      ? `/api/met/objects?department_id=${selectedDepartment.value}&page=${currentPage.value}`
      : `/api/met/highlights?page=${currentPage.value}`

    const res = await fetch(endpoint)
    const data = await res.json()

    // Transform for ImageGrid compatibility
    const newArtwork = (data.objects || []).map(obj => ({
      ...obj,
      content_id: `met_${obj.object_id}`,
      thumbnail: obj.image_url_small || obj.image_url,
      path: null
    }))

    if (append) {
      artwork.value = [...artwork.value, ...newArtwork]
    } else {
      artwork.value = newArtwork
      selectedIds.value = new Set()
    }

    hasMore.value = data.has_more
    totalCount.value = data.total || artwork.value.length
  } catch (e) {
    console.error('Failed to load artwork:', e)
  } finally {
    loading.value = false
    loadingMore.value = false
  }
}

const loadMore = async () => {
  if (hasMore.value && !loading.value && !loadingMore.value) {
    currentPage.value++
    await loadArtwork(true)
  }
}

const toggleSelection = (image) => {
  const newSet = new Set(selectedIds.value)
  const id = image.object_id
  if (newSet.has(id)) {
    newSet.delete(id)
  } else {
    newSet.add(id)
  }
  selectedIds.value = newSet
}

const selectAll = (checked) => {
  if (checked) {
    selectedIds.value = new Set(artwork.value.map(a => a.object_id))
  } else {
    selectedIds.value = new Set()
  }
}

const upload = async (display) => {
  if (selectedIds.value.size === 0) return

  // Check for low resolution images
  if (lowResImages.value.length > 0) {
    pendingUpload.value = { display }
    showResolutionWarning.value = true
    return
  }

  await doUpload(display)
}

const confirmUpload = async () => {
  showResolutionWarning.value = false
  await doUpload(pendingUpload.value.display)
}

const doUpload = async (display) => {
  uploading.value = true
  try {
    const res = await fetch('/api/met/upload', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        object_ids: Array.from(selectedIds.value),
        matte_style: matte.value.style,
        matte_color: matte.value.color,
        display
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

onMounted(() => {
  loadDepartments()
  loadArtwork()
})

defineExpose({ loadMore, hasMore })
</script>

<style scoped>
.met-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  overflow: hidden;
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

.department-select select {
  padding: 0.4rem;
  border-radius: 4px;
  border: 1px solid #3a3a5e;
  background: #2a2a4e;
  color: white;
}
</style>
