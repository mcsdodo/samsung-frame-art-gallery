<template>
  <div class="collection-picker-overlay" @click.self="$emit('close')">
    <div class="collection-picker">
      <div class="picker-header">
        <h3>Add to Collection</h3>
        <button class="close-btn" @click="$emit('close')">&times;</button>
      </div>

      <!-- Preview of images being added -->
      <div class="items-preview" v-if="items.length > 0">
        <div class="preview-thumbnails">
          <div
            v-for="(item, index) in previewItems"
            :key="index"
            class="preview-thumb"
          >
            <img :src="getItemThumbnail(item)" alt="" loading="lazy" />
          </div>
          <div v-if="overflowCount > 0" class="overflow-badge">
            +{{ overflowCount }}
          </div>
        </div>
        <span class="preview-label">{{ items.length }} {{ items.length === 1 ? 'image' : 'images' }}</span>
      </div>

      <div class="picker-content">
        <div class="new-collection">
          <input
            v-model="newName"
            type="text"
            placeholder="Create new collection..."
            @keyup.enter="createAndAdd"
          />
          <button
            :disabled="!newName.trim() || creating"
            @click="createAndAdd"
          >
            Create
          </button>
        </div>

        <div v-if="loading" class="loading">Loading collections...</div>

        <template v-else-if="collections.length === 0">
          <div class="empty">
            No collections yet. Create one above.
          </div>
        </template>

        <template v-else>
          <div class="section-label">YOUR COLLECTIONS</div>
          <div class="collections-list">
            <button
              v-for="collection in collections"
              :key="collection.id"
              class="collection-item"
              :disabled="adding"
              @click="addToCollection(collection.id)"
            >
              <div class="item-thumb">
                <img
                  v-if="collection.preview_thumbnail"
                  :src="collection.preview_thumbnail"
                  alt=""
                />
                <span v-else>📁</span>
              </div>
              <div class="item-details">
                <span class="collection-name">{{ collection.name }}</span>
                <span class="collection-count">{{ collection.item_count }} items</span>
              </div>
            </button>
          </div>
        </template>
      </div>

      <!-- Success state -->
      <Transition name="fade">
        <div v-if="showSuccess" class="success-overlay">
          <div class="success-content">
            <div class="success-icon">✓</div>
            <h3>Added to collection</h3>
            <p>{{ successCollection?.name }}</p>
            <div class="success-actions">
              <button class="secondary" @click="$emit('close')">Done</button>
              <button class="primary" @click="viewCollection">View Collection</button>
            </div>
          </div>
        </div>
      </Transition>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

const MAX_PREVIEW = 5

const props = defineProps({
  items: {
    type: Array,
    required: true
  }
})

const emit = defineEmits(['close', 'added'])

const collections = ref([])
const loading = ref(true)
const newName = ref('')
const creating = ref(false)
const adding = ref(false)
const showSuccess = ref(false)
const successCollection = ref(null)

const previewItems = computed(() => props.items.slice(0, MAX_PREVIEW))
const overflowCount = computed(() => Math.max(0, props.items.length - MAX_PREVIEW))

const getItemThumbnail = (item) => {
  if (item.type === 'local') {
    return `/api/images/${encodeURIComponent(item.path)}/thumbnail`
  } else if (item.type === 'met') {
    return item.image_url_small || item.image_url || ''
  }
  return ''
}

const loadCollections = async () => {
  loading.value = true
  try {
    const res = await fetch('/api/collections')
    const data = await res.json()
    collections.value = data.collections || []
  } catch (e) {
    console.error('Failed to load collections:', e)
  } finally {
    loading.value = false
  }
}

const createAndAdd = async () => {
  const name = newName.value.trim()
  if (!name) return

  creating.value = true
  try {
    const createRes = await fetch('/api/collections', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name })
    })
    const collection = await createRes.json()

    await fetch(`/api/collections/${collection.id}/items`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ items: props.items })
    })

    successCollection.value = collection
    showSuccess.value = true
    emit('added', collection)
  } catch (e) {
    console.error('Failed to create collection:', e)
  } finally {
    creating.value = false
  }
}

const addToCollection = async (collectionId) => {
  adding.value = true
  try {
    await fetch(`/api/collections/${collectionId}/items`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ items: props.items })
    })

    const collection = collections.value.find(c => c.id === collectionId)
    successCollection.value = collection
    showSuccess.value = true
    emit('added', collection)
  } catch (e) {
    console.error('Failed to add to collection:', e)
  } finally {
    adding.value = false
  }
}

const viewCollection = () => {
  const params = new URLSearchParams(window.location.search)
  params.set('tab', 'collections')
  window.history.replaceState({}, '', `${window.location.pathname}?${params.toString()}`)
  window.location.reload()
}

onMounted(loadCollections)
</script>

<style scoped>
.collection-picker-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.collection-picker {
  background: var(--surface-2);
  border-radius: 12px;
  width: 90%;
  max-width: 420px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden;
}

.picker-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid var(--border);
}

.picker-header h3 {
  margin: 0;
  font-size: 1.1rem;
}

.close-btn {
  background: transparent;
  border: none;
  color: var(--text-muted);
  font-size: 1.5rem;
  cursor: pointer;
  padding: 0;
  line-height: 1;
}

.close-btn:hover {
  color: white;
}

/* Items preview */
.items-preview {
  padding: 1rem 1.25rem;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.preview-thumbnails {
  display: flex;
  gap: 0.25rem;
}

.preview-thumb {
  width: 40px;
  height: 40px;
  border-radius: 4px;
  overflow: hidden;
  background: var(--surface-3);
}

.preview-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.overflow-badge {
  width: 40px;
  height: 40px;
  border-radius: 4px;
  background: var(--surface-hover);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.8rem;
  color: var(--collection-text-secondary);
}

.preview-label {
  font-size: 0.9rem;
  color: var(--collection-text-secondary);
}

.picker-content {
  padding: 1rem 1.25rem;
  overflow-y: auto;
  flex: 1;
}

.new-collection {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.new-collection input {
  flex: 1;
  padding: 0.6rem 0.75rem;
  border-radius: 6px;
  border: 1px solid var(--border-strong);
  background: var(--surface-3);
  color: white;
}

.new-collection input:focus {
  outline: none;
  border-color: var(--collection-accent);
}

.new-collection button {
  padding: 0.6rem 1rem;
  border-radius: 6px;
  border: none;
  background: var(--collection-accent);
  color: var(--surface-2);
  font-weight: 600;
  cursor: pointer;
}

.new-collection button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.loading, .empty {
  text-align: center;
  color: var(--text-muted);
  padding: 2rem;
}

.section-label {
  font-size: 0.7rem;
  font-weight: 600;
  letter-spacing: 0.1em;
  color: var(--collection-text-muted);
  text-transform: uppercase;
  margin-bottom: 0.75rem;
}

.collections-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.collection-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem;
  background: var(--collection-card-bg);
  border: 1px solid transparent;
  border-radius: 8px;
  cursor: pointer;
  color: white;
  text-align: left;
  transition: all 0.2s;
}

.collection-item:hover:not(:disabled) {
  background: var(--collection-card-bg-hover);
  border-color: var(--collection-accent-muted);
}

.collection-item:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.item-thumb {
  width: 44px;
  height: 44px;
  border-radius: 6px;
  background: var(--surface-3);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.item-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.item-details {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.collection-name {
  font-weight: 500;
}

.collection-count {
  color: var(--collection-text-secondary);
  font-size: 0.85rem;
}

/* Success overlay */
.success-overlay {
  position: absolute;
  inset: 0;
  background: var(--surface-2);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10;
}

.success-content {
  text-align: center;
  padding: 2rem;
}

.success-icon {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: var(--collection-accent);
  color: var(--surface-2);
  font-size: 2rem;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 1.5rem;
}

.success-content h3 {
  margin: 0 0 0.5rem 0;
}

.success-content p {
  margin: 0 0 1.5rem 0;
  color: var(--collection-text-secondary);
}

.success-actions {
  display: flex;
  gap: 0.75rem;
  justify-content: center;
}

.success-actions button {
  padding: 0.6rem 1.25rem;
  border-radius: 6px;
  border: none;
  cursor: pointer;
  font-weight: 500;
}

.success-actions .primary {
  background: var(--collection-accent);
  color: var(--surface-2);
}

.success-actions .secondary {
  background: var(--surface-hover);
  color: white;
}

/* Transitions */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
