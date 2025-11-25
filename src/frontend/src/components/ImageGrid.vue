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
          Select All ({{ selectedCount }}/{{ images.length }})
        </label>
        <button
          v-if="selectedCount > 0"
          class="deselect-btn"
          @click="$emit('select-all', false)"
        >
          Deselect All
        </button>
      </div>
      <slot name="header-actions"></slot>
    </div>

    <div v-if="loading" class="loading">Loading...</div>

    <div v-else-if="images.length === 0" class="empty">
      No images found
    </div>

    <div v-else ref="gridRef" class="grid" @scroll="onScroll">
      <ImageCard
        v-for="image in visibleImages"
        :key="image.path || image.content_id"
        :image="image"
        :selected="selectedIds.has(image.path || image.content_id)"
        :is-current="currentId === (image.content_id)"
        :is-local="isLocal"
        @toggle="$emit('toggle', image)"
        @preview="$emit('preview', image)"
      />
      <div v-if="hasMore" ref="sentinelRef" class="load-more-sentinel"></div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch, onMounted, onUnmounted } from 'vue'
import ImageCard from './ImageCard.vue'

const BATCH_SIZE = 24

const props = defineProps({
  images: { type: Array, default: () => [] },
  selectedIds: { type: Set, default: () => new Set() },
  currentId: { type: String, default: null },
  loading: { type: Boolean, default: false },
  isLocal: { type: Boolean, default: true }
})

defineEmits(['toggle', 'select-all', 'preview'])

const gridRef = ref(null)
const sentinelRef = ref(null)
const displayCount = ref(BATCH_SIZE)
let observer = null

const visibleImages = computed(() => props.images.slice(0, displayCount.value))
const hasMore = computed(() => displayCount.value < props.images.length)
const selectedCount = computed(() => props.selectedIds.size)
const allSelected = computed(() =>
  props.images.length > 0 && props.selectedIds.size === props.images.length
)

// Reset display count when images change
watch(() => props.images, () => {
  displayCount.value = BATCH_SIZE
}, { deep: false })

const loadMore = () => {
  if (hasMore.value) {
    displayCount.value = Math.min(displayCount.value + BATCH_SIZE, props.images.length)
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
  height: 100%;
}

.grid-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 1rem;
  background: #1a1a2e;
  border-bottom: 1px solid #2a2a4e;
}

.select-controls {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.select-all {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
}

.select-all input {
  width: 18px;
  height: 18px;
}

.deselect-btn {
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  border: 1px solid #3a3a5e;
  background: transparent;
  color: #aaa;
  cursor: pointer;
  font-size: 0.8rem;
}

.deselect-btn:hover {
  background: #2a2a4e;
  color: white;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 1rem;
  padding: 1rem;
  overflow-y: auto;
  flex: 1;
}

.load-more-sentinel {
  height: 1px;
  grid-column: 1 / -1;
}

.loading, .empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: #888;
}
</style>
