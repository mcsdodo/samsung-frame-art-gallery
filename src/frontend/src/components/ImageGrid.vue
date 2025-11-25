<template>
  <div class="image-grid-container">
    <div class="grid-header">
      <label class="select-all">
        <input
          type="checkbox"
          :checked="allSelected"
          @change="$emit('select-all', $event.target.checked)"
        />
        Select All ({{ selectedCount }}/{{ images.length }})
      </label>
      <slot name="header-actions"></slot>
    </div>

    <div v-if="loading" class="loading">Loading...</div>

    <div v-else-if="images.length === 0" class="empty">
      No images found
    </div>

    <div v-else class="grid">
      <ImageCard
        v-for="image in images"
        :key="image.path || image.content_id"
        :image="image"
        :selected="selectedIds.has(image.path || image.content_id)"
        :is-current="currentId === (image.content_id)"
        :is-local="isLocal"
        @toggle="$emit('toggle', image)"
        @preview="$emit('preview', image)"
      />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import ImageCard from './ImageCard.vue'

const props = defineProps({
  images: { type: Array, default: () => [] },
  selectedIds: { type: Set, default: () => new Set() },
  currentId: { type: String, default: null },
  loading: { type: Boolean, default: false },
  isLocal: { type: Boolean, default: true }
})

defineEmits(['toggle', 'select-all', 'preview'])

const selectedCount = computed(() => props.selectedIds.size)
const allSelected = computed(() =>
  props.images.length > 0 && props.selectedIds.size === props.images.length
)
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

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 1rem;
  padding: 1rem;
  overflow-y: auto;
  flex: 1;
}

.loading, .empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: #888;
}
</style>
