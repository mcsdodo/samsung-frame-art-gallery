<template>
  <div
    class="image-card"
    :class="{ selected, current: isCurrent }"
    @click="$emit('toggle')"
  >
    <div class="checkbox" @click.stop="$emit('toggle')">
      <input type="checkbox" :checked="selected" />
    </div>
    <img
      v-if="thumbnailUrl && !imgError"
      :src="thumbnailUrl"
      :alt="displayName"
      loading="lazy"
      @error="imgError = true"
    />
    <div v-else class="placeholder">
      <span>{{ displayName.slice(0, 2).toUpperCase() }}</span>
    </div>
    <div class="overlay">
      <span class="name">{{ displayName }}</span>
      <span v-if="isCurrent" class="current-badge">NOW</span>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  image: { type: Object, required: true },
  selected: { type: Boolean, default: false },
  isCurrent: { type: Boolean, default: false },
  isLocal: { type: Boolean, default: true }
})

defineEmits(['toggle'])

const imgError = ref(false)

const thumbnailUrl = computed(() => {
  if (imgError.value) return null
  if (props.isLocal) {
    return `/api/images/${encodeURIComponent(props.image.path)}/thumbnail`
  }
  // TV artwork doesn't have thumbnails from our API
  return null
})

const displayName = computed(() => {
  if (props.isLocal) {
    return props.image.name
  }
  return props.image.content_id || 'Unknown'
})
</script>

<style scoped>
.image-card {
  position: relative;
  aspect-ratio: 1;
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  border: 3px solid transparent;
  transition: border-color 0.2s, transform 0.2s;
  background: #2a2a4e;
}

.image-card:hover {
  transform: scale(1.02);
}

.image-card.selected {
  border-color: #4a90d9;
}

.image-card.current {
  border-color: #44ff44;
}

.checkbox {
  position: absolute;
  top: 8px;
  left: 8px;
  z-index: 2;
}

.checkbox input {
  width: 20px;
  height: 20px;
  cursor: pointer;
}

img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 2rem;
  font-weight: bold;
  color: #666;
  background: linear-gradient(135deg, #2a2a4e, #1a1a2e);
}

.overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 8px;
  background: linear-gradient(transparent, rgba(0,0,0,0.8));
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.name {
  font-size: 0.75rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 70%;
}

.current-badge {
  background: #44ff44;
  color: black;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.7rem;
  font-weight: bold;
}
</style>
