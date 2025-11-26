<template>
  <div class="met-panel">
    <div class="panel-header">
      <h2>Metropolitan Museum of Art</h2>
      <div class="header-controls">
        <div class="search-box">
          <input
            v-model="searchQuery"
            type="text"
            placeholder="Search artwork..."
            @input="onSearchInput"
            @keyup.enter="doSearch"
          />
          <button
            v-if="searchQuery"
            class="clear-search"
            @click="clearSearch"
            title="Clear search"
          >&times;</button>
        </div>
        <select v-model="selectedMedium" @change="onFilterChange">
          <option value="Paintings">Paintings</option>
          <option value="Sculpture">Sculpture</option>
          <option value="Photographs">Photographs</option>
          <option value="Drawings">Drawings</option>
          <option value="Prints">Prints</option>
          <option value="Ceramics">Ceramics</option>
          <option value="Textiles">Textiles</option>
          <option value="Furniture">Furniture</option>
          <option value="">All Media</option>
        </select>
        <select v-model="selectedDepartment" @change="onFilterChange">
          <option :value="null">All Departments</option>
          <option
            v-for="dept in departments"
            :key="dept.departmentId"
            :value="dept.departmentId"
          >
            {{ dept.displayName }}
          </option>
        </select>
        <label class="highlights-filter">
          <input
            type="checkbox"
            v-model="highlightsOnly"
            @change="onFilterChange"
          />
          Highlights
        </label>
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

// Read initial values from URL
const getInitialParams = () => {
  const params = new URLSearchParams(window.location.search)
  return {
    q: params.get('q') || '',
    medium: params.get('medium') || 'Paintings',
    department: params.get('department') ? parseInt(params.get('department')) : null,
    highlights: params.get('highlights') !== 'false' // default true
  }
}

const initialParams = getInitialParams()

const departments = ref([])
const selectedDepartment = ref(initialParams.department)
const selectedMedium = ref(initialParams.medium)
const highlightsOnly = ref(initialParams.highlights)
const artwork = ref([])
const selectedIds = ref(new Set())
const loading = ref(false)
const loadingMore = ref(false)
const uploading = ref(false)
const matte = ref({ style: 'none', color: 'neutral' })
const currentPage = ref(1)
const hasMore = ref(false)
const totalCount = ref(0)

// Search state
const searchQuery = ref(initialParams.q)
const activeSearch = ref(initialParams.q)
let searchDebounceTimer = null

// Update URL with current filter state
const updateUrl = () => {
  const params = new URLSearchParams(window.location.search)
  params.set('tab', 'met')

  if (activeSearch.value) {
    params.set('q', activeSearch.value)
  } else {
    params.delete('q')
  }

  if (selectedMedium.value) {
    params.set('medium', selectedMedium.value)
  } else {
    params.delete('medium')
  }

  if (selectedDepartment.value) {
    params.set('department', selectedDepartment.value)
  } else {
    params.delete('department')
  }

  if (!highlightsOnly.value) {
    params.set('highlights', 'false')
  } else {
    params.delete('highlights')
  }

  const newUrl = `${window.location.pathname}?${params.toString()}`
  window.history.replaceState({}, '', newUrl)
}

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
    let endpoint

    if (activeSearch.value) {
      // Search mode
      const params = new URLSearchParams({
        q: activeSearch.value,
        page: currentPage.value
      })
      if (selectedDepartment.value) {
        params.set('department_id', selectedDepartment.value)
      }
      if (selectedMedium.value) {
        params.set('medium', selectedMedium.value)
      }
      if (highlightsOnly.value) {
        params.set('highlights', 'true')
      }
      endpoint = `/api/met/search?${params}`
    } else if (selectedMedium.value) {
      // Medium browse mode (default: Paintings)
      const params = new URLSearchParams({
        page: currentPage.value
      })
      if (selectedDepartment.value) {
        params.set('department_id', selectedDepartment.value)
      }
      if (highlightsOnly.value) {
        params.set('highlights', 'true')
      }
      endpoint = `/api/met/medium/${encodeURIComponent(selectedMedium.value)}?${params}`
    } else if (selectedDepartment.value) {
      // Department browse mode
      const params = new URLSearchParams({
        department_id: selectedDepartment.value,
        page: currentPage.value
      })
      if (highlightsOnly.value) {
        params.set('highlights', 'true')
      }
      endpoint = `/api/met/objects?${params}`
    } else {
      // All artworks (no filter) - use highlights endpoint
      endpoint = `/api/met/highlights?page=${currentPage.value}`
    }

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

// Search functions
const onSearchInput = () => {
  // Debounce search input
  if (searchDebounceTimer) {
    clearTimeout(searchDebounceTimer)
  }
  searchDebounceTimer = setTimeout(() => {
    doSearch()
  }, 500)
}

const doSearch = () => {
  if (searchDebounceTimer) {
    clearTimeout(searchDebounceTimer)
    searchDebounceTimer = null
  }
  activeSearch.value = searchQuery.value.trim()
  updateUrl()
  loadArtwork()
}

const clearSearch = () => {
  searchQuery.value = ''
  activeSearch.value = ''
  if (searchDebounceTimer) {
    clearTimeout(searchDebounceTimer)
    searchDebounceTimer = null
  }
  updateUrl()
  loadArtwork()
}

const onFilterChange = () => {
  updateUrl()
  loadArtwork()
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

// Get actual image dimensions by loading it
const getImageDimensions = (url) => {
  return new Promise((resolve) => {
    const img = new Image()
    img.onload = () => resolve({ width: img.naturalWidth, height: img.naturalHeight })
    img.onerror = () => resolve({ width: 0, height: 0 })
    img.src = url
  })
}

// Fetch real dimensions for images with unknown resolution
const fetchMissingDimensions = async () => {
  const selectedArtwork = artwork.value.filter(img =>
    selectedIds.value.has(img.object_id)
  )

  for (const img of selectedArtwork) {
    if (!img.width || !img.height) {
      const dims = await getImageDimensions(img.image_url)
      img.width = dims.width
      img.height = dims.height
    }
  }
}

const upload = async (display) => {
  if (selectedIds.value.size === 0) return

  // Fetch real dimensions for images with unknown resolution
  await fetchMissingDimensions()

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
  flex-wrap: wrap;
  gap: 0.5rem;
}

.panel-header h2 {
  font-size: 1.1rem;
  margin: 0;
}

.header-controls {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.search-box {
  position: relative;
  display: flex;
  align-items: center;
}

.search-box input {
  padding: 0.4rem 1.8rem 0.4rem 0.6rem;
  border-radius: 4px;
  border: 1px solid #3a3a5e;
  background: #2a2a4e;
  color: white;
  width: 180px;
  font-size: 0.9rem;
}

.search-box input::placeholder {
  color: #666;
}

.search-box input:focus {
  outline: none;
  border-color: #4a90d9;
}

.clear-search {
  position: absolute;
  right: 4px;
  background: transparent;
  border: none;
  color: #888;
  font-size: 1.2rem;
  cursor: pointer;
  padding: 0 4px;
  line-height: 1;
}

.clear-search:hover {
  color: white;
}

.header-controls select {
  padding: 0.4rem;
  border-radius: 4px;
  border: 1px solid #3a3a5e;
  background: #2a2a4e;
  color: white;
}

.highlights-filter {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  cursor: pointer;
  white-space: nowrap;
  font-size: 0.9rem;
  color: #ccc;
}

.highlights-filter input {
  width: 16px;
  height: 16px;
  cursor: pointer;
}
</style>
