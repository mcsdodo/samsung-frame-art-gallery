<template>
  <div class="image-grid-container">
    <div class="grid-header">
      <div class="select-controls">
        <label class="select-all">
          <input
            type="checkbox"
            :checked="allSelected"
            @change="$emit('select-all', $event.target.checked)"
          />
          Select All ({{ selectedCount }}/{{ displayTotal }})
        </label>
        <button
          v-if="selectedCount > 0"
          class="deselect-btn"
          @click="$emit('select-all', false)"
        >
          Clear
        </button>
      </div>
      <slot name="header-actions"></slot>
    </div>

    <div v-if="loading && images.length === 0" class="loading">Loading...</div>

    <div v-else-if="!loading && images.length === 0" class="empty">
      No images found
    </div>

    <div v-else ref="gridRef" class="grid-container" @scroll="onScroll">
      <MasonryWall
        :items="visibleImages"
        :column-width="180"
        :gap="16"
        :ssr-columns="4"
        :scroll-container="gridRef"
      >
        <template #default="{ item }">
          <ImageCard
            :image="item"
            :selected="selectedIds.has(item._id || item.path || item.object_id || item.content_id)"
            :is-current="currentId === (item.content_id)"
            :on-tv="onTvPaths.has(item.path)"
            :is-local="isLocal"
            @toggle="$emit('toggle', item)"
            @preview="$emit('preview', item)"
          />
        </template>
      </MasonryWall>
      <div v-if="hasMore" ref="sentinelRef" class="load-more-sentinel">
        <div v-if="loadingMore" class="loading-spinner">
          <div class="spinner"></div>
          <span>Loading more...</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch, onMounted, onUnmounted, provide } from 'vue'
import MasonryWall from '@yeger/vue-masonry-wall'
import ImageCard from './ImageCard.vue'

const BATCH_SIZE = 24

const props = defineProps({
  images: { type: Array, default: () => [] },
  selectedIds: { type: Set, default: () => new Set() },
  currentId: { type: String, default: null },
  onTvPaths: { type: Set, default: () => new Set() },
  loading: { type: Boolean, default: false },
  loadingMore: { type: Boolean, default: false },
  isLocal: { type: Boolean, default: true },
  hasMoreExternal: { type: Boolean, default: false },
  totalCount: { type: Number, default: null }
})

const emit = defineEmits(['toggle', 'select-all', 'preview', 'load-more'])

const gridRef = ref(null)
const sentinelRef = ref(null)
const displayCount = ref(BATCH_SIZE)
let observer = null

// Provide scroll container to child ImageCards for IntersectionObserver
provide('scrollContainer', gridRef)

const visibleImages = computed(() => props.images.slice(0, displayCount.value))
const hasMoreInternal = computed(() => displayCount.value < props.images.length)
const hasMore = computed(() => hasMoreInternal.value || props.hasMoreExternal)
const selectedCount = computed(() => props.selectedIds.size)
const displayTotal = computed(() => props.totalCount ?? props.images.length)
const allSelected = computed(() =>
  props.images.length > 0 && props.selectedIds.size === props.images.length
)

// Reset display count when images change
watch(() => props.images, () => {
  displayCount.value = BATCH_SIZE
}, { deep: false })

const loadMore = () => {
  if (hasMoreInternal.value) {
    // Still have local images to reveal
    displayCount.value = Math.min(displayCount.value + BATCH_SIZE, props.images.length)
  } else if (props.hasMoreExternal) {
    // Need to fetch more from API
    emit('load-more')
  }
}

const onScroll = () => {
  // Fallback scroll handler if IntersectionObserver doesn't work
  if (!gridRef.value || !hasMore.value) return
  const { scrollTop, scrollHeight, clientHeight } = gridRef.value
  if (scrollTop + clientHeight >= scrollHeight - 200) {
    loadMore()
  }
}

onMounted(() => {
  // Use IntersectionObserver for infinite scroll
  observer = new IntersectionObserver(
    (entries) => {
      if (entries[0]?.isIntersecting) {
        loadMore()
      }
    },
    {
      root: gridRef.value,
      rootMargin: '200px',
      threshold: 0
    }
  )

  if (sentinelRef.value) {
    observer.observe(sentinelRef.value)
  }
})

// Re-observe sentinel when it changes
watch(sentinelRef, (newSentinel, oldSentinel) => {
  if (observer) {
    if (oldSentinel) observer.unobserve(oldSentinel)
    if (newSentinel) observer.observe(newSentinel)
  }
})

onUnmounted(() => {
  if (observer) {
    observer.disconnect()
    observer = null
  }
})
</script>

<style scoped>
.image-grid-container {
  display: flex;
  flex-direction: column;
  min-height: 0; /* Allow flex child to shrink below content size */
  overflow: hidden;
  background: var(--bg);
}

.grid-header {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 48px;
  padding: 8px 16px;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  min-width: 0;
}

.grid-header > :deep(.chip-row) {
  flex-wrap: nowrap;
  overflow-x: auto;
  margin-left: auto;
  min-width: 0;
  scrollbar-width: none;
}

.select-controls {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: none;
}

.select-all {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  color: var(--text-muted);
  font-size: 0.85rem;
  white-space: nowrap;
}

.select-all input {
  width: 16px;
  height: 16px;
}

.deselect-btn {
  height: 26px;
  padding: 0 10px;
  border-radius: 999px;
  border: 1px solid var(--border-strong);
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  font-size: 0.75rem;
  white-space: nowrap;
}

.deselect-btn:hover {
  background: var(--surface-3);
  color: var(--text);
}

.grid-container {
  padding: 1rem;
  overflow-y: auto;
  flex: 1;
  min-height: 0;
}

.load-more-sentinel {
  grid-column: 1 / -1;
  min-height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.loading-spinner {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  color: var(--text-muted);
  padding: 1rem;
}

.spinner {
  width: 24px;
  height: 24px;
  border: 3px solid var(--surface-3);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.loading, .empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: var(--text-muted);
}
</style>
