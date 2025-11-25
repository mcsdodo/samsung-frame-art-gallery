<template>
  <Teleport to="body">
    <div class="preview-overlay" @click="$emit('close')">
      <button class="close-btn" @click="$emit('close')">&times;</button>
      <div class="preview-content" @click.stop>
        <img v-if="imageUrl" :src="imageUrl" :alt="imageName" />
        <div v-else class="loading">Loading...</div>
      </div>
      <div class="preview-info">
        <span class="image-name">{{ imageName }}</span>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  image: { type: Object, required: true },
  isLocal: { type: Boolean, default: true }
})

defineEmits(['close'])

const imageUrl = computed(() => {
  if (props.isLocal) {
    return `/api/images/${encodeURIComponent(props.image.path)}/full`
  }
  // TV artwork - use thumbnail as full image (TV API limitation)
  if (props.image.content_id) {
    return `/api/tv/artwork/${encodeURIComponent(props.image.content_id)}/thumbnail`
  }
  return null
})

const imageName = computed(() => {
  if (props.isLocal) {
    return props.image.name
  }
  return props.image.content_id || 'Unknown'
})
</script>

<style scoped>
.preview-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.95);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.close-btn {
  position: absolute;
  top: 20px;
  right: 20px;
  background: rgba(255, 255, 255, 0.1);
  border: none;
  color: white;
  font-size: 2.5rem;
  width: 50px;
  height: 50px;
  border-radius: 50%;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s;
  z-index: 1001;
}

.close-btn:hover {
  background: rgba(255, 255, 255, 0.2);
}

.preview-content {
  max-width: 90vw;
  max-height: 80vh;
  display: flex;
  align-items: center;
  justify-content: center;
}

.preview-content img {
  max-width: 100%;
  max-height: 80vh;
  object-fit: contain;
  border-radius: 4px;
  box-shadow: 0 10px 50px rgba(0, 0, 0, 0.5);
}

.loading {
  color: #888;
  font-size: 1.2rem;
}

.preview-info {
  margin-top: 1rem;
  padding: 0.5rem 1rem;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 4px;
  max-width: 90vw;
}

.image-name {
  color: white;
  font-size: 0.9rem;
  word-break: break-all;
}
</style>
