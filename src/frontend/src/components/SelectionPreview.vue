<template>
  <div class="selection-preview" v-if="images.length > 0">
    <div class="preview-header">
      {{ images.length }} {{ images.length === 1 ? 'image' : 'images' }} selected
    </div>
    <div class="preview-thumbnails">
      <div
        v-for="(img, index) in displayImages"
        :key="img._id || index"
        class="preview-thumb"
      >
        <img :src="img.thumbnail" alt="" loading="lazy" />
      </div>
      <div v-if="overflowCount > 0" class="overflow-indicator">
        +{{ overflowCount }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const MAX_DISPLAY = 5

const props = defineProps({
  images: {
    type: Array,
    default: () => []
  }
})

const displayImages = computed(() => props.images.slice(0, MAX_DISPLAY))
const overflowCount = computed(() => Math.max(0, props.images.length - MAX_DISPLAY))
</script>

<style scoped>
.selection-preview {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 0.75rem;
  background: var(--surface-2);
  border-radius: 8px;
  min-width: 200px;
}

.preview-header {
  font-size: 0.85rem;
  color: var(--collection-text-primary);
  font-weight: 500;
}

.preview-thumbnails {
  display: flex;
  gap: 0.25rem;
  align-items: center;
}

.preview-thumb {
  width: 36px;
  height: 36px;
  border-radius: 4px;
  overflow: hidden;
  background: var(--surface-3);
}

.preview-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.overflow-indicator {
  width: 36px;
  height: 36px;
  border-radius: 4px;
  background: var(--surface-hover);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
  color: var(--collection-text-secondary);
}
</style>
