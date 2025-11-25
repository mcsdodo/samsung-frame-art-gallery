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
      :src="thumbnailUrl"
      :alt="image.name"
      loading="lazy"
    />
    <div class="overlay">
      <span class="name">{{ image.name }}</span>
      <span v-if="isCurrent" class="current-badge">NOW</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  image: { type: Object, required: true },
  selected: { type: Boolean, default: false },
  isCurrent: { type: Boolean, default: false },
  isLocal: { type: Boolean, default: true }
})

defineEmits(['toggle'])

const thumbnailUrl = computed(() => {
  if (props.isLocal) {
    return `/api/images/${encodeURIComponent(props.image.path)}/thumbnail`
  }
  // TV artwork - use content_id for identification
  return `/api/tv/artwork/${props.image.content_id}/thumbnail`
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
  font-size: 0.8rem;
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
