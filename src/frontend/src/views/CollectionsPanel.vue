<template>
  <div class="collections-panel">
    <!-- Desktop: Sidebar Layout -->
    <div v-if="!isMobile" class="sidebar-layout">
      <CollectionsSidebar
        :collections="collections"
        :selected-id="selectedCollectionId"
        @select="selectCollection"
        @create="showNewModal = true"
      />

      <div class="main-content">
        <!-- No collections state -->
        <EmptyCollections
          v-if="collections.length === 0"
          @create="showNewModal = true"
        />

        <!-- Collection selected -->
        <template v-else-if="selectedCollection">
          <div class="content-header">
            <div class="header-info">
              <h2>{{ selectedCollection.name }}</h2>
              <span class="header-meta">
                {{ selectedCollection.item_count }} {{ selectedCollection.item_count === 1 ? 'item' : 'items' }}
                <span v-if="selectedCollection.created_at"> · Created {{ formatDate(selectedCollection.created_at) }}</span>
              </span>
            </div>
            <div class="header-actions">
              <button class="icon-btn" @click="showRenameModal = true" title="Rename">
                ✏️
              </button>
              <button class="icon-btn danger" @click="confirmDelete" title="Delete">
                🗑️
              </button>
            </div>
          </div>

          <div v-if="unavailableCount > 0" class="unavailable-notice">
            {{ unavailableCount }} image(s) unavailable
          </div>

          <!-- Empty collection -->
          <EmptyCollection
            v-if="items.length === 0 && !loading"
            @go-to-local="goToLocal"
          />

          <!-- Image grid -->
          <ImageGrid
            v-else
            :images="items"
            :selected-ids="selectedIds"
            :loading="loading"
            :is-local="false"
            @toggle="toggleSelection"
            @select-all="selectAll"
            @preview="(img) => $emit('preview', img, img.type === 'local')"
          />

          <!-- Action Bar -->
          <ActionBar v-if="items.length > 0" class="collections-action-bar">
            <template #left>
              <SelectionPreview :images="selectedImages" />
            </template>
            <template #default>
              <div class="action-bar-right">
                <button
                  class="remove-btn"
                  :disabled="selectedIds.size === 0"
                  @click="removeSelected"
                >
                  Remove from Collection
                </button>
                <div class="action-bar-controls">
                  <CropSettings
                    :has-selection="selectedIds.size > 0"
                    :allow-reframe="false"
                    @change="setSettings"
                  />
                  <div class="upload-buttons">
                    <button
                      class="secondary"
                      :disabled="selectedIds.size === 0"
                      @click="upload(false)"
                    >
                      Upload to TV
                    </button>
                    <button
                      class="primary"
                      :disabled="selectedIds.size === 0"
                      @click="upload(true)"
                    >
                      Upload & Display
                    </button>
                  </div>
                </div>
              </div>
            </template>
          </ActionBar>
        </template>
      </div>
    </div>

    <!-- Mobile: Bottom Sheet Layout -->
    <template v-else>
      <CollectionBottomSheet
        :collections="collections"
        :selected-id="selectedCollectionId"
        :selected-collection="selectedCollection"
        @select="selectCollection"
        @create="showNewModal = true"
        @rename="(c) => { selectedCollectionId = c.id; showRenameModal = true }"
        @delete="(c) => { selectedCollectionId = c.id; confirmDelete() }"
      />

      <div v-if="!selectedCollectionId" class="empty-state">
        <EmptyCollections @create="showNewModal = true" />
      </div>

      <template v-else>
        <div v-if="unavailableCount > 0" class="unavailable-notice">
          {{ unavailableCount }} image(s) unavailable
        </div>

        <EmptyCollection
          v-if="items.length === 0 && !loading"
          @go-to-local="goToLocal"
        />

        <ImageGrid
          v-else
          :images="items"
          :selected-ids="selectedIds"
          :loading="loading"
          :is-local="false"
          @toggle="toggleSelection"
          @select-all="selectAll"
          @preview="(img) => $emit('preview', img, img.type === 'local')"
        />

        <!-- Mobile simplified footer -->
        <div v-if="items.length > 0" class="mobile-footer">
          <span class="selected-count">{{ selectedIds.size }} selected</span>
          <button class="settings-btn" @click="showMobileSettings = true">⚙️</button>
          <button
            class="primary"
            :disabled="selectedIds.size === 0"
            @click="upload(true)"
          >
            Upload & Display
          </button>
        </div>
      </template>

      <!-- Mobile settings sheet -->
      <Teleport to="body">
        <div v-if="showMobileSettings" class="settings-overlay" @click.self="showMobileSettings = false">
          <div class="settings-sheet">
            <div class="settings-handle" @click="showMobileSettings = false">
              <div class="handle-bar"></div>
            </div>
            <CropSettings
              :has-selection="selectedIds.size > 0"
              :allow-reframe="false"
              @change="setSettings"
            />
            <div class="settings-actions">
              <button
                class="danger"
                :disabled="selectedIds.size === 0"
                @click="removeSelected(); showMobileSettings = false"
              >
                Remove from Collection
              </button>
              <button
                class="secondary"
                :disabled="selectedIds.size === 0"
                @click="upload(false); showMobileSettings = false"
              >
                Upload to TV
              </button>
            </div>
          </div>
        </div>
      </Teleport>
    </template>

    <!-- New Collection Modal -->
    <div v-if="showNewModal" class="modal-overlay" @click.self="showNewModal = false">
      <div class="modal">
        <h3>New Collection</h3>
        <input
          v-model="newCollectionName"
          type="text"
          placeholder="Collection name"
          @keyup.enter="createCollection"
        />
        <div class="modal-actions">
          <button class="secondary" @click="showNewModal = false">Cancel</button>
          <button class="primary" :disabled="!newCollectionName.trim()" @click="createCollection">Create</button>
        </div>
      </div>
    </div>

    <!-- Rename Modal -->
    <div v-if="showRenameModal" class="modal-overlay" @click.self="showRenameModal = false">
      <div class="modal">
        <h3>Rename Collection</h3>
        <input
          v-model="renameValue"
          type="text"
          placeholder="New name"
          @keyup.enter="renameCollection"
        />
        <div class="modal-actions">
          <button class="secondary" @click="showRenameModal = false">Cancel</button>
          <button class="primary" :disabled="!renameValue.trim()" @click="renameCollection">Rename</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import ImageGrid from '../components/ImageGrid.vue'
import ActionBar from '../components/ActionBar.vue'
import { enqueue } from '../stores/uploadQueue.js'
import CropSettings from '../components/CropSettings.vue'
import CollectionsSidebar from '../components/CollectionsSidebar.vue'
import SelectionPreview from '../components/SelectionPreview.vue'
import EmptyCollections from '../components/EmptyCollections.vue'
import EmptyCollection from '../components/EmptyCollection.vue'
import CollectionBottomSheet from '../components/CollectionBottomSheet.vue'

const emit = defineEmits(['uploaded', 'preview', 'switch-tab'])

// Responsive
const isMobile = ref(window.innerWidth <= 768)
const checkMobile = () => {
  isMobile.value = window.innerWidth <= 768
}

onMounted(() => {
  window.addEventListener('resize', checkMobile)
})

onUnmounted(() => {
  window.removeEventListener('resize', checkMobile)
})

const collections = ref([])
const selectedCollectionId = ref(null)
const selectedCollection = computed(() =>
  collections.value.find(c => c.id === selectedCollectionId.value)
)

const items = ref([])
const selectedIds = ref(new Set())
const loading = ref(false)
const unavailableCount = ref(0)

const cropPercent = ref(0)
const mattePercent = ref(10)

const showNewModal = ref(false)
const newCollectionName = ref('')
const showRenameModal = ref(false)
const renameValue = ref('')
const showMobileSettings = ref(false)

// Computed for selection preview
const selectedImages = computed(() =>
  items.value.filter(i => selectedIds.value.has(i._id))
)

// Format date helper
const formatDate = (dateStr) => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

// Navigate to local tab
const goToLocal = () => {
  // Update URL and trigger parent to switch tabs
  const params = new URLSearchParams(window.location.search)
  params.set('tab', 'local')
  window.history.replaceState({}, '', `${window.location.pathname}?${params.toString()}`)
  window.location.reload()
}

const selectCollection = (id) => {
  selectedCollectionId.value = id
  loadCollectionItems()
}

const loadCollections = async () => {
  try {
    const res = await fetch('/api/collections')
    const data = await res.json()
    collections.value = data.collections || []

    // Auto-select first collection if none selected and collections exist
    if (!selectedCollectionId.value && collections.value.length > 0) {
      selectedCollectionId.value = collections.value[0].id
      await loadCollectionItems()
    }
  } catch (e) {
    console.error('Failed to load collections:', e)
  }
}

const loadCollectionItems = async () => {
  if (!selectedCollectionId.value) {
    items.value = []
    return
  }

  loading.value = true
  selectedIds.value = new Set()

  try {
    const res = await fetch(`/api/collections/${selectedCollectionId.value}/items`)
    const data = await res.json()

    // Transform items for ImageGrid compatibility
    items.value = (data.items || []).map(item => {
      if (item.type === 'local') {
        return {
          ...item,
          _id: `local:${item.path}`,
          thumbnail: `/api/images/${encodeURIComponent(item.path)}/thumbnail`
        }
      } else {
        return {
          ...item,
          _id: `met:${item.object_id}`,
          content_id: `met_${item.object_id}`,
          thumbnail: item.image_url_small || item.image_url
        }
      }
    })

    unavailableCount.value = data.unavailable_count || 0
  } catch (e) {
    console.error('Failed to load collection items:', e)
  } finally {
    loading.value = false
  }
}

const toggleSelection = (item) => {
  const id = item._id
  const newSet = new Set(selectedIds.value)
  if (newSet.has(id)) {
    newSet.delete(id)
  } else {
    newSet.add(id)
  }
  selectedIds.value = newSet
}

const selectAll = (checked) => {
  if (checked) {
    selectedIds.value = new Set(items.value.map(i => i._id))
  } else {
    selectedIds.value = new Set()
  }
}

const setSettings = (settings) => {
  cropPercent.value = settings.crop
  mattePercent.value = settings.matte
}

const createCollection = async () => {
  const name = newCollectionName.value.trim()
  if (!name) return

  try {
    const res = await fetch('/api/collections', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name })
    })
    const collection = await res.json()
    await loadCollections()
    selectedCollectionId.value = collection.id
    showNewModal.value = false
    newCollectionName.value = ''
  } catch (e) {
    console.error('Failed to create collection:', e)
  }
}

const renameCollection = async () => {
  const name = renameValue.value.trim()
  if (!name || !selectedCollectionId.value) return

  try {
    await fetch(`/api/collections/${selectedCollectionId.value}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name })
    })
    await loadCollections()
    showRenameModal.value = false
  } catch (e) {
    console.error('Failed to rename collection:', e)
  }
}

const confirmDelete = async () => {
  if (!selectedCollection.value) return
  if (!confirm(`Delete "${selectedCollection.value.name}"? This cannot be undone.`)) return

  try {
    await fetch(`/api/collections/${selectedCollectionId.value}`, {
      method: 'DELETE'
    })
    selectedCollectionId.value = null
    items.value = []
    await loadCollections()
  } catch (e) {
    console.error('Failed to delete collection:', e)
  }
}

const removeSelected = async () => {
  if (selectedIds.value.size === 0 || !selectedCollectionId.value) return

  const itemsToRemove = items.value
    .filter(i => selectedIds.value.has(i._id))
    .map(i => i.type === 'local'
      ? { type: 'local', path: i.path }
      : { type: 'met', object_id: i.object_id }
    )

  try {
    await fetch(`/api/collections/${selectedCollectionId.value}/items`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ items: itemsToRemove })
    })
    await loadCollectionItems()
    await loadCollections()
  } catch (e) {
    console.error('Failed to remove items:', e)
  }
}

const upload = (display) => {
  if (selectedIds.value.size === 0) return
  const common = { crop_percent: cropPercent.value, matte_percent: mattePercent.value }
  const selected = items.value.filter(i => selectedIds.value.has(i._id))
  enqueue(selected.map(i => i.type === 'local'
    ? { name: i.path.split('/').pop(), thumb: i.thumbnail, endpoint: '/api/tv/upload', body: { paths: [i.path], ...common } }
    : { name: i.title || `Met #${i.object_id}`, thumb: i.thumbnail, endpoint: '/api/met/upload', body: { object_ids: [i.object_id], ...common } }
  ), { display })
  selectedIds.value = new Set()
}

watch(showRenameModal, (show) => {
  if (show && selectedCollection.value) {
    renameValue.value = selectedCollection.value.name
  }
})

onMounted(loadCollections)

defineExpose({ loadCollections })
</script>

<style scoped>
.collections-panel {
  display: contents;
}

.sidebar-layout {
  display: flex;
  grid-row: 2 / -1; /* Start after tabs, span to end */
  min-height: 0;
  overflow: hidden;
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.content-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 1rem 1.5rem;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
}

.header-info h2 {
  margin: 0 0 0.25rem 0;
  font-size: 1.5rem;
  font-weight: 600;
}

.header-meta {
  font-size: 0.85rem;
  color: var(--collection-text-secondary);
}

.header-actions {
  display: flex;
  gap: 0.5rem;
  opacity: 0.6;
  transition: opacity 0.2s;
}

.content-header:hover .header-actions {
  opacity: 1;
}

.header-actions .icon-btn {
  padding: 0.4rem 0.6rem;
  background: transparent;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1rem;
  transition: background 0.2s;
}

.header-actions .icon-btn:hover {
  background: var(--surface-3);
}

.header-actions .icon-btn.danger:hover {
  background: var(--danger-soft);
}

/* Action bar styling for collections */
.collections-action-bar {
  flex-wrap: nowrap;
  padding: 1rem 1.5rem;
}

.action-bar-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.75rem;
  flex: 1;
}

.remove-btn {
  padding: 0.4rem 0.75rem;
  background: transparent;
  border: 1px solid var(--danger-soft);
  border-radius: 4px;
  color: var(--danger-text);
  cursor: pointer;
  font-size: 0.85rem;
  transition: all 0.2s;
}

.remove-btn:hover:not(:disabled) {
  background: var(--danger-soft);
  border-color: var(--danger-soft);
}

.remove-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.action-bar-controls {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.upload-buttons {
  display: flex;
  gap: 0.5rem;
}

/* Mobile/Original styles */
.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  border-bottom: 1px solid var(--border);
  background: var(--surface);
  gap: 1rem;
  flex-wrap: wrap;
}

.collection-select {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.collection-select select {
  padding: 0.4rem;
  border-radius: 4px;
  border: 1px solid var(--border-strong);
  background: var(--surface-3);
  color: white;
  min-width: 200px;
}

.new-btn {
  padding: 0.4rem 0.8rem;
  border-radius: 4px;
  border: 1px solid var(--border-strong);
  background: var(--accent);
  color: white;
  cursor: pointer;
  font-size: 1rem;
  font-weight: bold;
}

.collection-actions {
  display: flex;
  gap: 0.5rem;
}

.icon-btn {
  padding: 0.4rem 0.8rem;
  border-radius: 4px;
  border: 1px solid var(--border-strong);
  background: var(--surface-3);
  color: var(--text-muted);
  cursor: pointer;
  font-size: 0.85rem;
}

.icon-btn:hover {
  background: var(--surface-hover);
}

.icon-btn.danger {
  color: var(--danger);
}

.icon-btn.danger:hover {
  background: var(--danger-soft);
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem 2rem;
  color: var(--text-muted);
  gap: 1rem;
}

.empty-state button {
  padding: 0.75rem 1.5rem;
  border-radius: 4px;
  border: none;
  background: var(--accent);
  color: white;
  cursor: pointer;
}

.unavailable-notice {
  padding: 0.5rem 1rem;
  background: var(--danger-soft);
  color: var(--danger-text);
  font-size: 0.85rem;
  text-align: center;
}

/* Modal styles */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: var(--surface-2);
  border-radius: 8px;
  padding: 1.5rem;
  width: 90%;
  max-width: 400px;
}

.modal h3 {
  margin: 0 0 1rem 0;
}

.modal input {
  width: 100%;
  padding: 0.75rem;
  border-radius: 4px;
  border: 1px solid var(--border-strong);
  background: var(--surface-3);
  color: white;
  margin-bottom: 1rem;
  box-sizing: border-box;
}

.modal input:focus {
  outline: none;
  border-color: var(--accent);
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
}

.modal-actions button {
  padding: 0.5rem 1rem;
  border-radius: 4px;
  border: none;
  cursor: pointer;
}

.modal-actions button.primary {
  background: var(--accent);
  color: white;
}

.modal-actions button.secondary {
  background: var(--surface-hover);
  color: white;
}

.modal-actions button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Mobile footer */
.mobile-footer {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  background: var(--surface-2);
  border-top: 1px solid var(--border);
}

.selected-count {
  flex: 1;
  font-size: 0.9rem;
  color: var(--collection-text-secondary);
}

.settings-btn {
  padding: 0.5rem;
  background: var(--surface-3);
  border: none;
  border-radius: 6px;
  font-size: 1.25rem;
  cursor: pointer;
}

.mobile-footer .primary {
  padding: 0.6rem 1rem;
  background: var(--collection-accent);
  color: var(--surface-2);
  border: none;
  border-radius: 6px;
  font-weight: 600;
  cursor: pointer;
}

.mobile-footer .primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Mobile settings sheet */
.settings-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 1000;
  display: flex;
  align-items: flex-end;
}

.settings-sheet {
  width: 100%;
  background: var(--surface-2);
  border-radius: 16px 16px 0 0;
  padding: 0 1rem 1.5rem;
}

.settings-handle {
  padding: 0.75rem 0;
  display: flex;
  justify-content: center;
  cursor: pointer;
}

.settings-handle .handle-bar {
  width: 40px;
  height: 4px;
  background: var(--surface-hover);
  border-radius: 2px;
}

.settings-actions {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-top: 1rem;
}

.settings-actions button {
  width: 100%;
  padding: 0.75rem;
  border: none;
  border-radius: 6px;
  font-weight: 500;
  cursor: pointer;
}

.settings-actions .danger {
  background: var(--danger-soft);
  color: var(--danger-text);
}

.settings-actions .secondary {
  background: var(--surface-hover);
  color: white;
}
</style>
